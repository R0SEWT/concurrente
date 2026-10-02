package main

import (
	"bufio"
	"encoding/json"
	"flag"
	"fmt"
	"math"
	"os"
	"runtime"
	"strconv"
	"strings"

	"upc.edu.pe/concurrente/kmeans"
)

// Constantes del pipeline de limpieza (tp/reports/limpieza_yellow_2024-01.json)
const (
	mediaLogDuracion  = 2.558153941705323
	desvLogDuracion   = 0.6389417133082955
	mediaLogDistancia = 1.1704400695404638
	desvLogDistancia  = 0.6560886966217637
	tau               = 2 * math.Pi
)

type ClusterMeta struct {
	ID          int     `json:"id"`
	Nombre      string  `json:"nombre"`
	Icono       string  `json:"icono"`
	Descripcion string  `json:"descripcion"`
	Color       string  `json:"color"`
	DuracionMin float64 `json:"duracion_min"`
	DistanciaMi float64 `json:"distancia_mi"`
	HoraPico    float64 `json:"hora_pico"`
	DiaPico     float64 `json:"dia_pico"`
	DiaNombre   string  `json:"dia_nombre"`
	ViajesTotal int     `json:"viajes_total"`
	Porcentaje  float64 `json:"porcentaje"`
}

type ZonaHoraInfo struct {
	Dominante int   `json:"dom"`
	Total     int   `json:"total"`
	Counts    []int `json:"counts"`
	Baja      bool  `json:"baja,omitempty"`
}

type SalidaResumen struct {
	TotalViajes int                            `json:"total_viajes"`
	K           int                            `json:"k"`
	Inercia     float64                        `json:"inercia"`
	Clusters    []ClusterMeta                  `json:"clusters"`
	Zonas       map[int]map[string][]ZonaHoraInfo `json:"zonas"` // zona_id -> "semana"|"finde" -> array de 24 horas
}

func main() {
	var (
		datosRuta = flag.String("datos", "../data/gold/yellow_2024-01_features.csv", "CSV de gold")
		salida    = flag.String("salida", "../reports/nyc_clusters_resumen.json", "ruta del JSON de salida")
		k         = flag.Int("k", 8, "clusters")
		iter      = flag.Int("iter", 60, "iteraciones de convergencia")
		workers   = flag.Int("workers", runtime.NumCPU(), "goroutines")
	)
	flag.Parse()

	fmt.Println("1. Cargando gold y metadatos de zona/tiempo...")
	f, err := os.Open(*datosRuta)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error al abrir gold: %v\n", err)
		os.Exit(1)
	}
	defer f.Close()

	sc := bufio.NewScanner(f)
	sc.Buffer(make([]byte, 0, 64*1024), 1024*1024)
	if !sc.Scan() {
		fmt.Fprintf(os.Stderr, "gold vacío\n")
		os.Exit(1)
	}

	var (
		puLocations []int
		horas       []int
		esFinde     []bool
		xValues     []float64
	)

	linea := 1
	for sc.Scan() {
		linea++
		txt := strings.TrimRight(sc.Text(), "\r")
		if txt == "" {
			continue
		}
		campos := strings.Split(txt, ",")
		if len(campos) != 9 {
			continue
		}

		pu, _ := strconv.Atoi(campos[1])
		hSin, _ := strconv.ParseFloat(campos[3], 64)
		hCos, _ := strconv.ParseFloat(campos[4], 64)
		dSin, _ := strconv.ParseFloat(campos[5], 64)
		dCos, _ := strconv.ParseFloat(campos[6], 64)
		durZ, _ := strconv.ParseFloat(campos[7], 64)
		distZ, _ := strconv.ParseFloat(campos[8], 64)

		// Decodificar hora aproximada
		angH := math.Atan2(hSin, hCos)
		if angH < 0 {
			angH += tau
		}
		horaAprox := int(math.Round(angH * 24 / tau)) % 24

		// Decodificar día aproximado (0=Lunes, 4=Viernes, 5=Sábado, 6=Domingo)
		angD := math.Atan2(dSin, dCos)
		if angD < 0 {
			angD += tau
		}
		diaAprox := int(math.Round(angD * 7 / tau)) % 7
		finde := (diaAprox == 5 || diaAprox == 6)

		puLocations = append(puLocations, pu)
		horas = append(horas, horaAprox)
		esFinde = append(esFinde, finde)
		xValues = append(xValues, hSin, hCos, dSin, dCos, durZ, distZ)
	}

	n := len(puLocations)
	dim := 6
	fmt.Printf("   Cargados %d viajes.\n", n)

	d := &kmeans.Datos{
		X: xValues,
		N: n,
		D: dim,
	}

	fmt.Println("2. Inicializando centroides k-means++ (semilla 2024)...")
	centInit, kEf, err := kmeans.KMeansPP(d, *k, 2024)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error k-means++: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("3. Ejecutando Lloyd concurrente con %d workers hasta %d iteraciones...\n", *workers, *iter)
	op := kmeans.OpcionesConc{
		Opciones: kmeans.Opciones{
			K:       kEf,
			MaxIter: *iter,
			TolAbs:  1e-9,
			TolRel:  1e-9,
		},
		Workers: *workers,
		Chunk:   16384,
	}
	res, err := kmeans.Concurrente(d, centInit, op)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error en clustering: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("   Convergencia lograda en %d iteraciones (inercia: %.6f).\n", res.Iteraciones, res.Inercia)

	fmt.Println("4. Interpretando centroides y des-normalizando métricas...")
	diasSemana := []string{"Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"}
	colores := []string{
		"#0072B2", // Azul Bang Wong (Salida laboral & cena)
		"#CC79A7", // Púrpura rojizo Bang Wong (Noche & ocio)
		"#009E73", // Verde azulado Bang Wong (Micro-salto almuerzo)
		"#D55E00", // Bermellón Bang Wong (Tráfico denso)
		"#56B4E9", // Azul cielo Bang Wong (Retorno nocturno)
		"#E69F00", // Naranja Bang Wong (Aeropuertos & autopista)
		"#F0E442", // Amarillo Bang Wong (Paseo fin de semana)
		"#2DD4BF", // Menta/Teal accesible (Cierre rápido viernes)
	}

	clustersConteo := make([]int, *k)
	for _, c := range res.Asignaciones {
		clustersConteo[c]++
	}

	metas := make([]ClusterMeta, *k)
	for i := 0; i < *k; i++ {
		cent := res.Centroide(i)
		hSin, hCos := cent[0], cent[1]
		dSin, dCos := cent[2], cent[3]
		durZ, distZ := cent[4], cent[5]

		// Hora pico del centroide
		angH := math.Atan2(hSin, hCos)
		if angH < 0 {
			angH += tau
		}
		hPico := angH * 24 / tau

		// Día pico del centroide
		angD := math.Atan2(dSin, dCos)
		if angD < 0 {
			angD += tau
		}
		dPico := angD * 7 / tau
		idxDia := int(math.Round(dPico)) % 7

		// Inversión de escala: x = exp(z * desv + media) - 1
		durReal := math.Exp(durZ*desvLogDuracion+mediaLogDuracion) - 1
		distReal := math.Exp(distZ*desvLogDistancia+mediaLogDistancia) - 1

		pct := float64(clustersConteo[i]) / float64(n) * 100

		metas[i] = ClusterMeta{
			ID:          i,
			Nombre:      fmt.Sprintf("Cluster %d", i),
			Color:       colores[i%len(colores)],
			DuracionMin: math.Round(durReal*10) / 10,
			DistanciaMi: math.Round(distReal*10) / 10,
			HoraPico:    math.Round(hPico*10) / 10,
			DiaPico:     math.Round(dPico*10) / 10,
			DiaNombre:   diasSemana[idxDia],
			ViajesTotal: clustersConteo[i],
			Porcentaje:  math.Round(pct*10) / 10,
		}

		fmt.Printf("   Cluster %d: %7d viajes (%4.1f%%) | Hora ~%04.1f h | Día %-9s | Dur: %4.1f min | Dist: %4.1f mi\n",
			i, clustersConteo[i], pct, hPico, diasSemana[idxDia], durReal, distReal)
	}

	fmt.Println("5. Agregando por zona TLC, día y hora...")
	// zona -> "semana"|"finde" -> 24 horas
	zonasMap := make(map[int]map[string][]ZonaHoraInfo)

	// Inicializar acumuladores: [zona][tipo_dia][hora][cluster]
	// tipo_dia: 0=semana, 1=finde
	type Acumulador struct {
		counts [8]int
		total  int
	}
	acum := make(map[int]*[2][24]Acumulador)

	for i := 0; i < n; i++ {
		z := puLocations[i]
		if z <= 0 || z > 265 {
			continue
		}
		td := 0
		if esFinde[i] {
			td = 1
		}
		h := horas[i]
		c := res.Asignaciones[i]

		a, ok := acum[z]
		if !ok {
			a = &[2][24]Acumulador{}
			acum[z] = a
		}
		a[td][h].counts[c]++
		a[td][h].total++
	}

	for z, datosZ := range acum {
		zonasMap[z] = map[string][]ZonaHoraInfo{
			"semana": make([]ZonaHoraInfo, 24),
			"finde":  make([]ZonaHoraInfo, 24),
		}

		for td := 0; td < 2; td++ {
			clave := "semana"
			if td == 1 {
				clave = "finde"
			}
			for h := 0; h < 24; h++ {
				cell := datosZ[td][h]
				dom := 0
				maxC := -1
				for c := 0; c < *k; c++ {
					if cell.counts[c] > maxC {
						maxC = cell.counts[c]
						dom = c
					}
				}

				baja := (cell.total < 10)
				zonasMap[z][clave][h] = ZonaHoraInfo{
					Dominante: dom,
					Total:     cell.total,
					Counts:    cell.counts[:],
					Baja:      baja,
				}
			}
		}
	}

	sal := SalidaResumen{
		TotalViajes: n,
		K:           *k,
		Inercia:     res.Inercia,
		Clusters:    metas,
		Zonas:       zonasMap,
	}

	fmt.Printf("6. Guardando JSON resumen en %s...\n", *salida)
	outF, err := os.Create(*salida)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error al crear archivo de salida: %v\n", err)
		os.Exit(1)
	}
	defer outF.Close()

	enc := json.NewEncoder(outF)
	enc.SetIndent("", "  ")
	if err := enc.Encode(sal); err != nil {
		fmt.Fprintf(os.Stderr, "error al serializar JSON: %v\n", err)
		os.Exit(1)
	}

	fi, _ := outF.Stat()
	fmt.Printf("✓ Completado. Archivo generado con éxito: %.1f KB\n", float64(fi.Size())/1024)
}

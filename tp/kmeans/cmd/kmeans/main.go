// Comando kmeans corre el K-means sobre el gold, en modo secuencial o
// concurrente, y reporta tiempos por fase con todos los metadatos que hacen
// falta para reproducir la corrida.
//
// Es la evidencia de funcionamiento que pide la rúbrica y la pieza que el
// harness de benchmark (concurrente-3r8.9) invoca. Imprime a mano, sin
// dependencias de terceros, como exige el enunciado.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"runtime"
	"time"

	"upc.edu.pe/concurrente/kmeans"
)

type salida struct {
	kmeans.Metadatos
	Datos          string          `json:"datos"`
	DatosSha256    string          `json:"datos_sha256,omitempty"`
	N              int             `json:"n"`
	D              int             `json:"d"`
	Modo           string          `json:"modo"`
	K              int             `json:"k"`
	KEfectivo      int             `json:"k_efectivo"`
	Semilla        int64           `json:"semilla"`
	Workers        int             `json:"workers,omitempty"`
	Chunk          int             `json:"chunk,omitempty"`
	MaxIter        int             `json:"max_iter"`
	TolAbs         float64         `json:"tol_abs"`
	TolRel         float64         `json:"tol_rel"`
	CentroidesHash string          `json:"centroides_iniciales_sha256"`
	MsCarga        float64         `json:"ms_carga"`
	MsInicializar  float64         `json:"ms_inicializacion"`
	MsClustering   float64         `json:"ms_clustering"`
	MsTotal        float64         `json:"ms_total"`
	Iteraciones    int             `json:"iteraciones"`
	Paro           string          `json:"paro"`
	Vacios         int             `json:"clusters_vacios"`
	Inercia        float64         `json:"inercia"`
	TrasCarga      kmeans.Recursos `json:"recursos_tras_carga"`
	Final          kmeans.Recursos `json:"recursos_finales"`
}

func main() {
	var (
		datos      = flag.String("datos", "../data/gold/yellow_2024-01_features.csv", "CSV de gold")
		modo       = flag.String("modo", "conc", "seq | conc")
		k          = flag.Int("k", 8, "cantidad de clusters")
		maxIter    = flag.Int("iter", 100, "máximo de iteraciones")
		tolAbs     = flag.Float64("tol-abs", 1e-9, "tolerancia absoluta del criterio de parada")
		tolRel     = flag.Float64("tol-rel", 1e-9, "tolerancia relativa del criterio de parada")
		workers    = flag.Int("workers", runtime.NumCPU(), "goroutines del pool (solo en modo conc)")
		chunk      = flag.Int("chunk", 16384, "viajes por chunk (solo en modo conc)")
		semilla    = flag.Int64("semilla", 2024, "semilla de k-means++")
		centroides = flag.String("centroides", "", "archivo de centroides iniciales; si no existe, se genera y se guarda")
		conHash    = flag.Bool("hash-datos", true, "calcular el sha256 del gold (fuera del tiempo medido)")
		enJSON     = flag.Bool("json", false, "imprimir el resultado como JSON")
		procs      = flag.Int("gomaxprocs", 0, "GOMAXPROCS; 0 deja el valor por defecto")
		progreso   = flag.Bool("progreso", false, "barra de progreso por iteración en stderr (para verlo correr, no para medir)")
	)
	flag.CommandLine.Parse(argumentos(os.Args))
	mostrarProgreso = *progreso

	if err := correr(*datos, *modo, *k, *maxIter, *tolAbs, *tolRel, *workers, *chunk,
		*semilla, *centroides, *conHash, *enJSON, *procs); err != nil {
		fmt.Fprintln(os.Stderr, "error:", err)
		os.Exit(1)
	}
}

// mostrarProgreso lo fija -progreso. Es de la CLI, no del paquete kmeans.
var mostrarProgreso bool

func correr(ruta, modo string, k, maxIter int, tolAbs, tolRel float64,
	workers, chunk int, semilla int64, rutaCent string, conHash, enJSON bool, procs int) error {

	if modo != "seq" && modo != "conc" {
		return fmt.Errorf("modo %q: se esperaba seq o conc", modo)
	}
	if procs > 0 {
		runtime.GOMAXPROCS(procs)
	}
	s := salida{Metadatos: kmeans.RecolectarMetadatos(), Datos: ruta, Modo: modo,
		K: k, Semilla: semilla, MaxIter: maxIter, TolAbs: tolAbs, TolRel: tolRel}

	if conHash {
		h, err := kmeans.Sha256Archivo(ruta)
		if err != nil {
			return err
		}
		s.DatosSha256 = h
	}

	var b *barra
	if mostrarProgreso {
		b = nuevaBarra(os.Stderr, maxIter)
		fmt.Fprintf(os.Stderr, "\n  \033[1mK-means · %s · %s · %d CPUs\033[0m\n", s.Maquina, s.VersionGo, s.CPUsLogicas)
	}

	inicio := time.Now()
	t0 := time.Now()
	d, err := kmeans.LeerGoldArchivo(ruta)
	if err != nil {
		return err
	}
	s.MsCarga = ms(time.Since(t0))
	if b != nil {
		b.fase("gold: %d viajes × %d features", d.N, d.D)
	}
	s.N, s.D = d.N, d.D
	// Foto después de cargar: separa el costo de parsear el CSV del clustering.
	s.TrasCarga = kmeans.MedirRecursos()

	t0 = time.Now()
	cent, kEfectivo, err := centroidesIniciales(d, k, semilla, rutaCent)
	if err != nil {
		return err
	}
	s.MsInicializar = ms(time.Since(t0))
	s.KEfectivo = kEfectivo
	s.CentroidesHash = kmeans.HashCentroides(cent)
	if b != nil {
		b.fase("centroides: k=%d, sha256 %s…", kEfectivo, s.CentroidesHash[:8])
		if modo == "seq" {
			b.titulo("Lloyd secuencial, 1 hilo, %d iter.", maxIter)
		} else {
			b.titulo("Lloyd concurrente, %d workers, chunk %d", workers, chunk)
		}
	}

	op := kmeans.Opciones{K: kEfectivo, MaxIter: maxIter, TolAbs: tolAbs, TolRel: tolRel}
	if b != nil {
		op.AlIterar = b.iterar
	}
	t0 = time.Now()
	var r *kmeans.Resultado
	if modo == "seq" {
		r, err = kmeans.Secuencial(d, cent, op)
	} else {
		s.Workers, s.Chunk = workers, chunk
		r, err = kmeans.Concurrente(d, cent, kmeans.OpcionesConc{Opciones: op, Workers: workers, Chunk: chunk})
	}
	if err != nil {
		return err
	}
	s.MsClustering = ms(time.Since(t0))
	s.MsTotal = ms(time.Since(inicio))
	if b != nil {
		b.fin(r.Iteraciones, r.Paro)
	}
	s.Iteraciones, s.Paro, s.Vacios, s.Inercia = r.Iteraciones, r.Paro, r.Vacios, r.Inercia
	s.Final = kmeans.MedirRecursos()
	s.GOMAXPROCS = runtime.GOMAXPROCS(0)

	if enJSON {
		enc := json.NewEncoder(os.Stdout)
		enc.SetIndent("", "  ")
		return enc.Encode(s)
	}
	imprimir(s)
	return nil
}

// centroidesIniciales reusa el archivo si existe y, si no, genera con k-means++
// y lo guarda. Es lo que garantiza que la corrida secuencial y la concurrente
// parten exactamente de los mismos centroides.
func centroidesIniciales(d *kmeans.Datos, k int, semilla int64, ruta string) ([]float64, int, error) {
	if ruta != "" {
		if f, err := os.Open(ruta); err == nil {
			defer f.Close()
			cent, kLeido, dim, err := kmeans.LeerCentroides(f)
			if err != nil {
				return nil, 0, err
			}
			if dim != d.D {
				return nil, 0, fmt.Errorf("los centroides tienen D=%d y el gold D=%d", dim, d.D)
			}
			// El archivo es una caché de ESTA configuración, no una fuente de k: si
			// trae otro k, la corrida no respetaría -k y los metadatos registrarían
			// un K distinto del usado. Mejor fallar y que el usuario decida.
			if kLeido != k {
				return nil, 0, fmt.Errorf("los centroides de %s tienen k=%d y se pidió -k %d", ruta, kLeido, k)
			}
			return cent, kLeido, nil
		} else if !os.IsNotExist(err) {
			return nil, 0, err
		}
	}

	cent, kEfectivo, err := kmeans.KMeansPP(d, k, semilla)
	if err != nil {
		return nil, 0, err
	}
	if ruta != "" {
		f, err := os.Create(ruta)
		if err != nil {
			return nil, 0, err
		}
		defer f.Close()
		if err := kmeans.GuardarCentroides(f, cent, kEfectivo, d.D); err != nil {
			return nil, 0, err
		}
	}
	return cent, kEfectivo, nil
}

func imprimir(s salida) {
	fmt.Printf("gold        %s\n", s.Datos)
	fmt.Printf("            %d viajes × %d features", s.N, s.D)
	if s.DatosSha256 != "" {
		fmt.Printf(" · sha256 %s…", s.DatosSha256[:12])
	}
	fmt.Println()
	fmt.Printf("centroides  k-means++ semilla %d · k efectivo %d · sha256 %s…\n",
		s.Semilla, s.KEfectivo, s.CentroidesHash[:12])
	if s.Modo == "seq" {
		fmt.Printf("modo        secuencial\n")
	} else {
		fmt.Printf("modo        concurrente · workers %d · chunk %d\n", s.Workers, s.Chunk)
	}
	fmt.Printf("máquina     %s · %s · GOMAXPROCS %d de %d CPUs lógicas\n",
		s.Maquina, s.VersionGo, s.GOMAXPROCS, s.CPUsLogicas)
	fmt.Printf("tiempos     carga %.0f ms · init %.0f ms · clustering %.0f ms · total %.0f ms\n",
		s.MsCarga, s.MsInicializar, s.MsClustering, s.MsTotal)
	fmt.Printf("memoria     heap tras carga %.0f MB · heap final %.0f MB · RSS máximo %.0f MB · %d GC\n",
		s.TrasCarga.HeapMB, s.Final.HeapMB, s.Final.MaxRSSMB, s.Final.NumGC)
	fmt.Printf("cpu         usuario %.2f s · sistema %.2f s · pared %.2f s → %.1f núcleos efectivos\n",
		s.Final.CPUUsuarioS, s.Final.CPUSistemaS, s.MsTotal/1000,
		(s.Final.CPUUsuarioS+s.Final.CPUSistemaS)/(s.MsTotal/1000))
	fmt.Printf("resultado   %d iteraciones (paro=%s) · %d clusters vacíos · inercia %.6e\n",
		s.Iteraciones, s.Paro, s.Vacios, s.Inercia)
}

func ms(d time.Duration) float64 { return float64(d.Nanoseconds()) / 1e6 }

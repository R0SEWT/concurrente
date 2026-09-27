// Comando benchmark produce los tiempos del informe de la PC2.
//
// El protocolo está fijado acá y no se negocia en tiempo de corrida, que es lo
// que evita que dos ejecuciones "según el mismo criterio" den cifras distintas:
//
//   - N repeticiones medidas por configuración, más un calentamiento que se descarta.
//   - Orden aleatorizado por bloques: en cada ronda se barajan las configuraciones,
//     para que el orden no favorezca a ninguna (la caché de disco y el turbo del
//     procesador premian a la que corre segunda).
//   - Media recortada simétrica; speedup = mediaRecortada(seq) / mediaRecortada(conc),
//     nunca el promedio de los cocientes por corrida.
//   - Incertidumbre del speedup por bootstrap sobre las dos muestras.
//   - Se mide solo el clustering: la carga del CSV y la inicialización quedan fuera.
//   - Dos experimentos: iteraciones fijas (mismo trabajo) y hasta convergencia
//     (mismo resultado).
//
// Se guardan los tiempos crudos además de los agregados, para poder recalcular
// cualquier estadística sin volver a medir.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"math/rand"
	"os"
	"path/filepath"
	"runtime"
	"sort"
	"strconv"
	"strings"
	"time"

	"upc.edu.pe/concurrente/kmeans"
)

type corrida struct {
	Experimento   string  `json:"experimento"`
	Tamano        int     `json:"tamano"`
	Modo          string  `json:"modo"`
	Workers       int     `json:"workers,omitempty"`
	Ronda         int     `json:"ronda"`
	Orden         int     `json:"orden_en_la_ronda"`
	Calentamiento bool    `json:"calentamiento"`
	MsClustering  float64 `json:"ms_clustering"`
	Iteraciones   int     `json:"iteraciones"`
	Paro          string  `json:"paro"`
	Inercia       float64 `json:"inercia"`
}

type resumen struct {
	Experimento      string                    `json:"experimento"`
	Tamano           int                       `json:"tamano"`
	Modo             string                    `json:"modo"`
	Workers          int                       `json:"workers,omitempty"`
	Repeticiones     int                       `json:"repeticiones"`
	MediaRecortadaMs float64                   `json:"media_recortada_ms"`
	MedianaMs        float64                   `json:"mediana_ms"`
	DesvMs           float64                   `json:"desviacion_ms"`
	MinMs            float64                   `json:"min_ms"`
	MaxMs            float64                   `json:"max_ms"`
	Speedup          *kmeans.IntervaloCociente `json:"speedup,omitempty"`
	Eficiencia       float64                   `json:"eficiencia_por_worker,omitempty"`
	Iteraciones      int                       `json:"iteraciones"`
	Inercia          float64                   `json:"inercia"`
}

type informe struct {
	Metadatos   kmeans.Metadatos  `json:"metadatos"`
	Protocolo   map[string]any    `json:"protocolo"`
	Datos       map[string]any    `json:"datos"`
	Centroides  map[string]string `json:"centroides_por_tamano"`
	Corridas    []corrida         `json:"corridas"`
	Resumen     []resumen         `json:"resumen"`
	DuracionMin float64           `json:"duracion_total_min"`
}

func main() {
	var (
		ruta        = flag.String("datos", "../data/gold/yellow_2024-01_features.csv", "CSV de gold")
		k           = flag.Int("k", 8, "cantidad de clusters")
		semilla     = flag.Int64("semilla", 2024, "semilla de k-means++")
		semillaOrd  = flag.Int64("semilla-orden", 7, "semilla del barajado de configuraciones")
		chunk       = flag.Int("chunk", 16384, "viajes por chunk")
		repes       = flag.Int("repes", 20, "repeticiones medidas por configuración")
		calent      = flag.Int("calentamiento", 1, "rondas de calentamiento descartadas")
		recorte     = flag.Float64("recorte", 0.10, "proporción recortada por extremo")
		boot        = flag.Int("bootstrap", 2000, "réplicas del bootstrap")
		workersCSV  = flag.String("workers", "1,2,4,8,16", "valores de P")
		tamanosCSV  = flag.String("tamanos", "0", "tamaños de n; 0 = dataset completo")
		iterFijas   = flag.Int("iter-fijas", 10, "iteraciones del experimento de trabajo fijo")
		maxIterConv = flag.Int("max-iter", 60, "tope del experimento hasta convergencia")
		experCSV    = flag.String("experimentos", "fijas,convergencia", "fijas | convergencia")
		salida      = flag.String("salida", "", "archivo JSON de salida; vacío = tp/reports/benchmark_<maquina>_<fecha>.json")
	)
	flag.CommandLine.Parse(argumentos(os.Args))

	if err := correr(*ruta, *k, *semilla, *semillaOrd, *chunk, *repes, *calent, *recorte, *boot,
		*workersCSV, *tamanosCSV, *iterFijas, *maxIterConv, *experCSV, *salida); err != nil {
		fmt.Fprintln(os.Stderr, "error:", err)
		os.Exit(1)
	}
}

func correr(ruta string, k int, semilla, semillaOrd int64, chunk, repes, calent int,
	recorte float64, boot int, workersCSV, tamanosCSV string, iterFijas, maxIterConv int,
	experCSV, salida string) error {

	inicioTodo := time.Now()
	workers, err := enteros(workersCSV)
	if err != nil {
		return fmt.Errorf("workers: %w", err)
	}
	tamanos, err := enteros(tamanosCSV)
	if err != nil {
		return fmt.Errorf("tamaños: %w", err)
	}
	experimentos := strings.Split(experCSV, ",")

	fmt.Fprintf(os.Stderr, "leyendo %s\n", ruta)
	d, err := kmeans.LeerGoldArchivo(ruta)
	if err != nil {
		return err
	}
	hash, err := kmeans.Sha256Archivo(ruta)
	if err != nil {
		return err
	}

	inf := informe{
		Metadatos:  kmeans.RecolectarMetadatos(),
		Centroides: map[string]string{},
		Protocolo: map[string]any{
			"repeticiones_medidas": repes, "rondas_calentamiento": calent,
			"recorte_por_extremo": recorte, "replicas_bootstrap": boot,
			"orden":         "aleatorizado por bloques; se guarda el orden de cada ronda",
			"semilla_orden": semillaOrd, "k": k, "semilla_kmeanspp": semilla, "chunk": chunk,
			"iteraciones_fijas": iterFijas, "max_iter_convergencia": maxIterConv,
			"se_mide": "solo el clustering; carga e inicialización quedan fuera",
		},
		Datos: map[string]any{"ruta": ruta, "sha256": hash, "n": d.N, "d": d.D},
	}

	for _, exper := range experimentos {
		for _, tam := range tamanos {
			// 0 = dataset completo. Cualquier otro tamaño pasa por Submuestra, que
			// devuelve el dataset entero si tam == N y falla si tam > N: pedir más
			// filas de las que hay es un error de configuración, no "el completo".
			sub := d
			if tam > 0 {
				if sub, err = kmeans.Submuestra(d, tam); err != nil {
					return fmt.Errorf("tamaño %d: %w", tam, err)
				}
			}
			n := sub.N

			cent, kEf, err := kmeans.KMeansPP(sub, k, semilla)
			if err != nil {
				return fmt.Errorf("k-means++ con n=%d: %w", n, err)
			}
			inf.Centroides[fmt.Sprintf("%s/%d", exper, n)] = kmeans.HashCentroides(cent)

			op := kmeans.Opciones{K: kEf, MaxIter: iterFijas, TolAbs: 0, TolRel: 0}
			if exper == "convergencia" {
				op = kmeans.Opciones{K: kEf, MaxIter: maxIterConv, TolAbs: 1e-9, TolRel: 1e-9}
			}

			configs := []corrida{{Experimento: exper, Tamano: n, Modo: "seq"}}
			for _, p := range workers {
				configs = append(configs, corrida{Experimento: exper, Tamano: n, Modo: "conc", Workers: p})
			}

			rng := rand.New(rand.NewSource(semillaOrd))
			for ronda := 0; ronda < calent+repes; ronda++ {
				orden := rng.Perm(len(configs))
				for pos, idx := range orden {
					c := configs[idx]
					c.Ronda, c.Orden = ronda, pos
					c.Calentamiento = ronda < calent

					runtime.GC()
					inicio := time.Now()
					var r *kmeans.Resultado
					if c.Modo == "seq" {
						r, err = kmeans.Secuencial(sub, cent, op)
					} else {
						r, err = kmeans.Concurrente(sub, cent,
							kmeans.OpcionesConc{Opciones: op, Workers: c.Workers, Chunk: chunk})
					}
					if err != nil {
						return err
					}
					c.MsClustering = float64(time.Since(inicio).Nanoseconds()) / 1e6
					c.Iteraciones, c.Paro, c.Inercia = r.Iteraciones, r.Paro, r.Inercia
					inf.Corridas = append(inf.Corridas, c)
				}
				fmt.Fprintf(os.Stderr, "\r%s n=%d ronda %d/%d", exper, n, ronda+1, calent+repes)
			}
			fmt.Fprintln(os.Stderr)
		}
	}

	inf.Resumen, err = resumir(inf.Corridas, recorte, boot, semillaOrd)
	if err != nil {
		return err
	}
	inf.DuracionMin = time.Since(inicioTodo).Minutes()

	if salida == "" {
		salida = filepath.Join("..", "reports", fmt.Sprintf("benchmark_%s_%s.json",
			inf.Metadatos.Maquina, time.Now().Format("2006-01-02_1504")))
	}
	if err := os.MkdirAll(filepath.Dir(salida), 0o755); err != nil {
		return err
	}
	f, err := os.Create(salida)
	if err != nil {
		return err
	}
	defer f.Close()
	enc := json.NewEncoder(f)
	enc.SetIndent("", " ")
	if err := enc.Encode(inf); err != nil {
		return err
	}

	imprimirTabla(inf.Resumen)
	fmt.Fprintf(os.Stderr, "\n%d corridas en %.1f min → %s\n", len(inf.Corridas), inf.DuracionMin, salida)
	return nil
}

// resumir agrega las corridas medidas (sin calentamiento) por configuración.
func resumir(corridas []corrida, recorte float64, boot int, semilla int64) ([]resumen, error) {
	tiempos := map[string][]float64{}
	ultima := map[string]corrida{}
	var claves []string
	for _, c := range corridas {
		if c.Calentamiento {
			continue
		}
		clave := fmt.Sprintf("%s|%d|%s|%d", c.Experimento, c.Tamano, c.Modo, c.Workers)
		if _, visto := tiempos[clave]; !visto {
			claves = append(claves, clave)
		}
		tiempos[clave] = append(tiempos[clave], c.MsClustering)
		ultima[clave] = c
	}
	sort.Strings(claves)

	var salida []resumen
	for _, clave := range claves {
		ts := tiempos[clave]
		c := ultima[clave]
		media, err := kmeans.MediaRecortada(ts, recorte)
		if err != nil {
			return nil, err
		}
		mediana, err := kmeans.Mediana(ts)
		if err != nil {
			return nil, err
		}
		desv, err := kmeans.DesviacionEstandar(ts)
		if err != nil {
			return nil, err
		}
		orden := append([]float64(nil), ts...)
		sort.Float64s(orden)

		r := resumen{
			Experimento: c.Experimento, Tamano: c.Tamano, Modo: c.Modo, Workers: c.Workers,
			Repeticiones: len(ts), MediaRecortadaMs: media, MedianaMs: mediana, DesvMs: desv,
			MinMs: orden[0], MaxMs: orden[len(orden)-1],
			Iteraciones: c.Iteraciones, Inercia: c.Inercia,
		}
		if c.Modo == "conc" {
			claveSeq := fmt.Sprintf("%s|%d|seq|0", c.Experimento, c.Tamano)
			if seq, ok := tiempos[claveSeq]; ok {
				ic, err := kmeans.ICBootstrapCociente(seq, ts, recorte, boot, semilla)
				if err != nil {
					return nil, err
				}
				r.Speedup = &ic
				r.Eficiencia = ic.Punto / float64(c.Workers)
			}
		}
		salida = append(salida, r)
	}
	return salida, nil
}

func imprimirTabla(rs []resumen) {
	fmt.Printf("\n%-13s %10s %-6s %7s %12s %10s %18s %6s\n",
		"experimento", "n", "modo", "workers", "recortada", "desv", "speedup [IC 95%]", "efic")
	for _, r := range rs {
		sp, efic := "", ""
		if r.Speedup != nil {
			sp = fmt.Sprintf("%.2fx [%.2f, %.2f]", r.Speedup.Punto, r.Speedup.Inferior, r.Speedup.Superior)
			efic = fmt.Sprintf("%.0f%%", 100*r.Eficiencia)
		}
		w := ""
		if r.Modo == "conc" {
			w = strconv.Itoa(r.Workers)
		}
		fmt.Printf("%-13s %10d %-6s %7s %10.1fms %8.1fms %18s %6s\n",
			r.Experimento, r.Tamano, r.Modo, w, r.MediaRecortadaMs, r.DesvMs, sp, efic)
	}
}

func enteros(csv string) ([]int, error) {
	var out []int
	for _, campo := range strings.Split(csv, ",") {
		campo = strings.TrimSpace(campo)
		if campo == "" {
			continue
		}
		v, err := strconv.Atoi(campo)
		if err != nil {
			return nil, fmt.Errorf("%q no es un entero", campo)
		}
		out = append(out, v)
	}
	if len(out) == 0 {
		return nil, fmt.Errorf("lista vacía")
	}
	return out, nil
}

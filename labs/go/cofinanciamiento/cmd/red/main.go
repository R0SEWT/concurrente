// Command red construye la red de co-financiamiento sobre el CSV de AidData.
//
// No es un test: es el banco de pruebas para medir cómo escalan los dos
// acumuladores del paquete sobre 1,23 GB reales. El CSV no está versionado,
// ver labs/go/cofinanciamiento/README.md para bajarlo.
//
//	go run ./cofinanciamiento/cmd/red -csv ~/data/aiddata.csv -workers 8
package main

import (
	"encoding/csv"
	"flag"
	"fmt"
	"io"
	"os"
	"runtime"
	"strings"
	"sync"
	"time"

	"upc.edu.pe/concurrente/cofinanciamiento"
)

// Índices de columna en AidDataCoreFull_ResearchRelease_Level1_v3.1.csv.
const (
	colAnio     = 2
	colDonante  = 3
	colReceptor = 9
	colSector   = 23
	colsMin     = 24
)

func main() {
	csvPath := flag.String("csv", "", "ruta al CSV de AidData (obligatorio)")
	workers := flag.Int("workers", runtime.NumCPU(), "goroutines que parsean en paralelo")
	modo := flag.String("modo", "parciales", "parciales | shardeado")
	shards := flag.Int("shards", 0, "shards del modo shardeado (0 = 4x workers)")
	sector := flag.String("sector", "", "filtrar por substring en aiddata_sector_name, p.ej. AGRIC")
	top := flag.Int("top", 15, "cuántas aristas mostrar")
	decadas := flag.Bool("decadas", false, "mostrar la fragmentación por década")
	flag.Parse()

	if *csvPath == "" {
		fmt.Fprintln(os.Stderr, "falta -csv")
		flag.Usage()
		os.Exit(2)
	}

	f, err := os.Open(*csvPath)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	defer f.Close()
	st, err := f.Stat()
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}

	cortes, err := limites(f, st.Size(), *workers)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	n := len(cortes) - 1

	filtro := strings.ToUpper(*sector)
	inicio := time.Now()

	var red cofinanciamiento.Red
	var tam map[cofinanciamiento.Grupo]int
	leidos := make([]int, n)
	usados := make([]int, n)

	switch *modo {
	case "parciales":
		// Sin candados: cada worker escribe solo en su Parcial y se fusionan
		// los conjuntos al final. Fusionar redes en vez de conjuntos perdería
		// las aristas partidas entre chunks.
		partes := make([]*cofinanciamiento.Parcial, n)
		var wg sync.WaitGroup
		wg.Add(n)
		for i := 0; i < n; i++ {
			i := i
			go func() {
				defer wg.Done()
				p := cofinanciamiento.NuevoParcial()
				leidos[i], usados[i] = consumir(io.NewSectionReader(f, cortes[i], cortes[i+1]-cortes[i]), p, filtro)
				partes[i] = p
			}()
		}
		wg.Wait()
		total := cofinanciamiento.Fusionar(partes...)
		red, tam = total.Red(), total.Tamanios()

	case "shardeado":
		// Estado compartido: un mapa partido en shards con candado por shard.
		s := *shards
		if s == 0 {
			s = 4 * n
		}
		acc := cofinanciamiento.NuevoShardeado(s)
		var wg sync.WaitGroup
		wg.Add(n)
		for i := 0; i < n; i++ {
			i := i
			go func() {
				defer wg.Done()
				leidos[i], usados[i] = consumir(io.NewSectionReader(f, cortes[i], cortes[i+1]-cortes[i]), acc, filtro)
			}()
		}
		wg.Wait()
		red, tam = acc.Red(), acc.Tamanios()

	default:
		fmt.Fprintf(os.Stderr, "modo desconocido: %s\n", *modo)
		os.Exit(2)
	}

	transcurrido := time.Since(inicio)

	total, usadosTotal, min, max := 0, 0, leidos[0], leidos[0]
	for i, c := range leidos {
		total += c
		usadosTotal += usados[i]
		if c < min {
			min = c
		}
		if c > max {
			max = c
		}
	}

	fmt.Printf("modo=%s workers=%d  %.2fs  %.0f MB/s\n",
		*modo, n, transcurrido.Seconds(), float64(st.Size())/1e6/transcurrido.Seconds())
	fmt.Printf("registros leídos=%d  usados=%d  aristas=%d  desbalance min/max = %d/%d = %.2fx\n",
		total, usadosTotal, len(red), min, max, float64(max)/float64(min))
	if filtro != "" {
		fmt.Printf("filtro de sector: %q (substring simple sobre aiddata_sector_name)\n", filtro)
	}
	if *decadas {
		// Cuántos donantes distintos concurren sobre un mismo receptor-año.
		// Es la otra cara de la red: en vez de mirar pares, mira el tamaño
		// del grupo que los produce.
		fmt.Printf("\n%8s %9s %8s %9s %6s\n", "década", "grupos", "media", "mediana", "máx")
		for _, f := range cofinanciamiento.PorDecada(tam) {
			fmt.Printf("%6ds %9d %8.1f %9d %6d\n", f.Decada, f.Grupos, f.Media, f.Mediana, f.Max)
		}
	}

	if *top > 0 {
		fmt.Println()
		for i, pp := range red.Top(*top) {
			fmt.Printf("%2d. %6d  %s — %s\n", i+1, pp.Peso, pp.A, pp.B)
		}
	}
}

// limites parte el archivo en n tramos alineados a fin de línea, saltando la
// cabecera. Alinear importa: un corte a mitad de línea rompería el parseo del
// chunk siguiente. Se puede cortar en cualquier '\n' porque en este CSV se
// verificó que ningún campo citado contiene saltos de línea.
func limites(r io.ReaderAt, size int64, n int) ([]int64, error) {
	if n < 1 {
		n = 1
	}
	inicio, err := finDeLinea(r, 0, size)
	if err != nil {
		return nil, err
	}
	cortes := []int64{inicio}
	paso := (size - inicio) / int64(n)
	for i := 1; i < n; i++ {
		p, err := finDeLinea(r, inicio+int64(i)*paso, size)
		if err != nil {
			return nil, err
		}
		if p > cortes[len(cortes)-1] && p < size {
			cortes = append(cortes, p)
		}
	}
	return append(cortes, size), nil
}

// finDeLinea devuelve el offset justo después del primer '\n' en o tras off.
func finDeLinea(r io.ReaderAt, off, size int64) (int64, error) {
	buf := make([]byte, 64*1024)
	for off < size {
		n, err := r.ReadAt(buf, off)
		if n > 0 {
			for i := 0; i < n; i++ {
				if buf[i] == '\n' {
					return off + int64(i) + 1, nil
				}
			}
			off += int64(n)
		}
		if err == io.EOF {
			break
		}
		if err != nil {
			return 0, err
		}
	}
	return size, nil
}

// consumir parsea un tramo y lo vuelca en el acumulador. Devuelve cuántos
// registros leyó y cuántos pasaron el filtro.
//
// Los leídos son la medida real del desbalance: los tramos tienen el mismo
// tamaño en bytes pero no la misma cantidad de filas, porque
// long_description llega a 48 220 caracteres.
func consumir(r io.Reader, acc cofinanciamiento.Acumulador, filtro string) (leidos, usados int) {
	cr := csv.NewReader(r)
	cr.ReuseRecord = true
	cr.FieldsPerRecord = -1
	for {
		rec, err := cr.Read()
		if err == io.EOF {
			return leidos, usados
		}
		if err != nil {
			// Una línea mal formada no debe tumbar el barrido completo.
			continue
		}
		if len(rec) < colsMin {
			continue
		}
		leidos++
		if filtro != "" && !strings.Contains(strings.ToUpper(rec[colSector]), filtro) {
			continue
		}
		usados++
		acc.Agregar(cofinanciamiento.Registro{
			Receptor: rec[colReceptor],
			Anio:     rec[colAnio],
			Donante:  rec[colDonante],
		})
	}
}

// Package kmeans implementa K-means (Lloyd) sobre el gold de viajes de NYC TLC,
// en versión secuencial y concurrente, usando solo la biblioteca estándar.
//
// El diseño, el contrato numérico y el protocolo de medición están en
// ../docs/kmeans.md. Lo que el código no puede documentar solo: los IDs de zona
// viajan en el CSV pero NO son features, porque un identificador no es una
// coordenada; entran al análisis recién después del clustering, al agregar las
// asignaciones por zona.
package kmeans

import (
	"bufio"
	"fmt"
	"io"
	"math"
	"os"
	"strconv"
	"strings"
)

// columnasGold es la cabecera exacta que produce tp/src/nyc_tlc/features.py.
// Se valida completa: una permutación de las columnas (por ejemplo duración y
// distancia intercambiadas) daría un CSV que se lee sin error y un K-means
// sobre features equivocadas.
var columnasGold = [...]string{
	"viaje_id", "PULocationID", "DOLocationID",
	"hora_sin", "hora_cos", "dia_sin", "dia_cos",
	"log_duracion_z", "log_distancia_z",
}

// primeraFeature es el índice de hora_sin dentro de la fila del CSV.
const primeraFeature = 3

// Dimension es la cantidad de features que consume la distancia euclídea.
const Dimension = len(columnasGold) - primeraFeature

// Datos es el gold cargado en memoria: X guarda los puntos uno tras otro, por
// filas (el punto i ocupa X[i*D : (i+1)*D]). Un arreglo plano en vez de [][]float64
// evita N indirecciones y deja las 6 features de un viaje contiguas en caché.
//
// Invariante: todos los valores de X son finitos. LeerGold lo garantiza al
// cargar (rechaza NaN e Inf) y Submuestra lo conserva. Secuencial y Concurrente
// NO lo vuelven a comprobar, a propósito: recorrer los N*D valores es una pasada
// serial completa sobre los datos y caería dentro del tiempo que mide el
// benchmark, sesgando el speedup. Quien construya Datos a mano es responsable
// de cumplirlo.
type Datos struct {
	X []float64
	N int
	D int
}

// Punto devuelve las features del viaje i. Comparte memoria con X: no se modifica.
func (d *Datos) Punto(i int) []float64 {
	return d.X[i*d.D : (i+1)*d.D]
}

// LeerGoldArchivo carga el gold desde una ruta.
func LeerGoldArchivo(ruta string) (*Datos, error) {
	f, err := os.Open(ruta)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	return LeerGold(f)
}

// LeerGold carga el gold y devuelve solo las features, en float64.
//
// No usa encoding/csv: el gold no tiene comillas ni comas dentro de los campos,
// así que partir por coma es correcto y bastante más rápido, y esto se lee una
// vez por corrida de benchmark.
func LeerGold(r io.Reader) (*Datos, error) {
	sc := bufio.NewScanner(r)
	sc.Buffer(make([]byte, 0, 64*1024), 1024*1024)

	if !sc.Scan() {
		if err := sc.Err(); err != nil {
			return nil, fmt.Errorf("leer la cabecera del gold: %w", err)
		}
		return nil, fmt.Errorf("gold vacío: no tiene ni cabecera")
	}
	if err := validarCabecera(sc.Text()); err != nil {
		return nil, err
	}

	datos := &Datos{D: Dimension, X: make([]float64, 0, Dimension*4096)}
	linea := 1
	for sc.Scan() {
		linea++
		fila := strings.TrimRight(sc.Text(), "\r")
		if fila == "" {
			continue
		}
		if err := agregarFila(datos, fila, linea); err != nil {
			return nil, err
		}
	}
	if err := sc.Err(); err != nil {
		return nil, fmt.Errorf("leer el gold: %w", err)
	}
	if datos.N == 0 {
		return nil, fmt.Errorf("el gold no tiene viajes: solo la cabecera")
	}
	return datos, nil
}

func validarCabecera(fila string) error {
	campos := strings.Split(strings.TrimRight(fila, "\r"), ",")
	if len(campos) != len(columnasGold) {
		return fmt.Errorf("cabecera del gold: %d columnas, se esperaban %d (%s)",
			len(campos), len(columnasGold), strings.Join(columnasGold[:], ","))
	}
	for i, quiero := range columnasGold {
		if strings.TrimSpace(campos[i]) != quiero {
			return fmt.Errorf("cabecera del gold: la columna %d es %q, se esperaba %q",
				i+1, campos[i], quiero)
		}
	}
	return nil
}

func agregarFila(d *Datos, fila string, linea int) error {
	campos := strings.Split(fila, ",")
	if len(campos) != len(columnasGold) {
		return fmt.Errorf("línea %d del gold: %d columnas, se esperaban %d",
			linea, len(campos), len(columnasGold))
	}
	for i := primeraFeature; i < len(columnasGold); i++ {
		v, err := strconv.ParseFloat(campos[i], 64)
		if err != nil {
			return fmt.Errorf("línea %d del gold, columna %s: %q no es un número",
				linea, columnasGold[i], campos[i])
		}
		// El contrato del diseño: NaN e Inf no entran. Un NaN contamina el
		// centroide entero y el criterio de parada deja de tener sentido.
		if math.IsNaN(v) || math.IsInf(v, 0) {
			return fmt.Errorf("línea %d del gold, columna %s: valor no finito (%v)",
				linea, columnasGold[i], v)
		}
		d.X = append(d.X, v)
	}
	d.N++
	return nil
}

// Package week04 resuelve el ejercicio 8 del capítulo 2 de Ben-Ari sobre el
// algoritmo 2.18 (algoritmo concurrente C):
//
//	integer n <- 1
//	p                        q
//	p1: while n < 1          q1: while n >= 0
//	p2:     n <- n + 1       q2:     n <- n - 1
//
// Un escenario, en el sentido de Ben-Ari, es un entrelazado concreto: quién
// ejecuta cada instrucción y qué valor toma n. Acá se construyen a mano y se
// ejecutan de forma determinista, porque el ejercicio pide *exhibir* un
// entrelazado, no observar uno al azar.
//
// Por eso el modelo no usa goroutines: con goroutines el planificador elige y
// no se puede pedir "el bucle de p exactamente tres veces". La versión con
// goroutines y su carrera de datos está en cmd/race, y la verificación sobre
// *todos* los entrelazados, en ../../spin/.
package week04

import (
	"encoding/csv"
	"fmt"
	"strconv"
	"strings"
)

// Escenarios del ejercicio 8. Cada carácter es un turno: qué proceso ejecuta
// su siguiente instrucción.
const (
	// EscenarioA: el bucle de p se ejecuta exactamente una vez (8a).
	EscenarioA = "qqpppqqqqq"
	// EscenarioB: el bucle de p se ejecuta exactamente tres veces (8b).
	EscenarioB = "qqppqqppqqpppqqqqq"
	// EscenarioC: una vuelta que devuelve el estado al inicial habiendo
	// iterado los dos bucles. Repetida para siempre, ninguno termina (8c).
	EscenarioC = "qqpp"
)

// Posiciones del contador de programa de cada proceso.
const (
	enGuarda = iota // p1 / q1
	enCuerpo        // p2 / q2
	terminado
)

// Paso es una fila de la tabla de escenarios: la instrucción que se ejecutó y
// el valor de n inmediatamente después.
type Paso struct {
	Proceso  string // "p" o "q"
	Etiqueta string // "p1", "p2", "q1", "q2"
	Codigo   string // la instrucción tal como aparece en el algoritmo
	Detalle  string // la guarda evaluada o la asignación hecha, con valores
	N        int
}

// Traza es la sucesión de pasos de un escenario.
type Traza []Paso

// Estado es lo que hace falta para saber si un escenario volvió al inicio.
type Estado struct {
	N      int
	PC     map[string]int
	iteras map[string]int
}

// Ejecucion mantiene el estado compartido y el contador de programa de cada
// proceso mientras se recorre un escenario.
type Ejecucion struct {
	n      int
	pc     map[string]int
	iteras map[string]int
}

// NuevaEjecucion arranca con n = 1 y los dos procesos en su guarda.
func NuevaEjecucion() *Ejecucion {
	return &Ejecucion{
		n:      1,
		pc:     map[string]int{"p": enGuarda, "q": enGuarda},
		iteras: map[string]int{"p": 0, "q": 0},
	}
}

// N es el valor actual de la variable compartida.
func (e *Ejecucion) N() int { return e.n }

// Iteraciones cuenta cuántas veces ejecutó su cuerpo el bucle del proceso.
func (e *Ejecucion) Iteraciones(proceso string) int { return e.iteras[proceso] }

// Termino indica si la guarda del proceso ya resultó falsa.
func (e *Ejecucion) Termino(proceso string) bool { return e.pc[proceso] == terminado }

// Paso ejecuta la siguiente instrucción del proceso y devuelve la fila
// correspondiente de la tabla.
func (e *Ejecucion) Paso(proceso string) (Paso, error) {
	pc, conocido := e.pc[proceso]
	if !conocido {
		return Paso{}, fmt.Errorf("proceso desconocido %q: solo hay p y q", proceso)
	}

	switch pc {
	case terminado:
		return Paso{}, fmt.Errorf("el proceso %s ya terminó: su guarda resultó falsa", proceso)

	case enGuarda:
		anterior := e.n
		vale := e.guarda(proceso)
		if vale {
			e.pc[proceso] = enCuerpo
		} else {
			e.pc[proceso] = terminado
		}
		return Paso{
			Proceso:  proceso,
			Etiqueta: proceso + "1",
			Codigo:   e.codigoGuarda(proceso),
			Detalle:  fmt.Sprintf("%s → %s", e.guardaConValores(proceso, anterior), veredicto(vale)),
			N:        e.n,
		}, nil

	default: // enCuerpo
		anterior := e.n
		if proceso == "p" {
			e.n++
		} else {
			e.n--
		}
		e.iteras[proceso]++
		e.pc[proceso] = enGuarda
		return Paso{
			Proceso:  proceso,
			Etiqueta: proceso + "2",
			Codigo:   e.codigoCuerpo(proceso),
			Detalle:  fmt.Sprintf("n = %d %s 1", anterior, signo(proceso)),
			N:        e.n,
		}, nil
	}
}

// Correr ejecuta un escenario completo, un turno por carácter.
func (e *Ejecucion) Correr(escenario string) (Traza, error) {
	traza := make(Traza, 0, len(escenario))
	for i, turno := range escenario {
		paso, err := e.Paso(string(turno))
		if err != nil {
			return traza, fmt.Errorf("turno %d (%q): %w", i+1, string(turno), err)
		}
		traza = append(traza, paso)
	}
	return traza, nil
}

// Estado devuelve una copia del estado, para comparar el inicio con el final.
func (e *Ejecucion) Estado() Estado {
	return Estado{
		N:      e.n,
		PC:     map[string]int{"p": e.pc["p"], "q": e.pc["q"]},
		iteras: map[string]int{"p": e.iteras["p"], "q": e.iteras["q"]},
	}
}

// Ciclo resume una vuelta candidata a repetirse para siempre.
type Ciclo struct {
	Traza          Traza
	VuelveAlInicio bool // n y los contadores de programa quedaron como al inicio
	IteracionesP   int
	IteracionesQ   int
	TerminoAlguno  bool
}

// AnalizarCiclo corre el escenario una vez y reporta si puede repetirse para
// siempre: basta que deje el estado igual al inicial, que ningún proceso haya
// terminado y que los dos bucles hayan iterado. Eso responde 8(c) sin
// simular infinitos pasos.
func AnalizarCiclo(escenario string) (Ciclo, error) {
	e := NuevaEjecucion()
	inicial := e.Estado()

	traza, err := e.Correr(escenario)
	if err != nil {
		return Ciclo{}, err
	}
	final := e.Estado()

	return Ciclo{
		Traza:          traza,
		VuelveAlInicio: final.N == inicial.N && final.PC["p"] == inicial.PC["p"] && final.PC["q"] == inicial.PC["q"],
		IteracionesP:   e.Iteraciones("p"),
		IteracionesQ:   e.Iteraciones("q"),
		TerminoAlguno:  e.Termino("p") || e.Termino("q"),
	}, nil
}

// Markdown arma la matriz de escenarios: una columna por proceso, como en las
// tablas de Ben-Ari, y el valor de n después de cada instrucción.
func Markdown(t Traza) string {
	var b strings.Builder
	b.WriteString("| # | p | q | n |\n")
	b.WriteString("|--:|---|---|--:|\n")
	for i, paso := range t {
		celda := fmt.Sprintf("`%s` %s — %s", paso.Etiqueta, paso.Codigo, paso.Detalle)
		p, q := "", ""
		if paso.Proceso == "p" {
			p = celda
		} else {
			q = celda
		}
		fmt.Fprintf(&b, "| %d | %s | %s | %d |\n", i+1, p, q, paso.N)
	}
	return b.String()
}

// CSV exporta la traza con encabezado, una fila por paso. Es la entrada del
// gráfico de la entrega (grafico/escenarios.py).
func CSV(escenario string, t Traza) string {
	return "escenario,paso,proceso,etiqueta,detalle,n\n" + FilasCSV(escenario, t)
}

// FilasCSV es CSV sin el encabezado, para juntar varios escenarios en un
// mismo archivo.
func FilasCSV(escenario string, t Traza) string {
	var b strings.Builder
	w := csv.NewWriter(&b)
	for i, paso := range t {
		// Escribir en un strings.Builder no falla; el error de csv se revisa abajo.
		_ = w.Write([]string{
			escenario, strconv.Itoa(i + 1), paso.Proceso, paso.Etiqueta,
			paso.Detalle, strconv.Itoa(paso.N),
		})
	}
	w.Flush()
	if err := w.Error(); err != nil {
		panic(err)
	}
	return b.String()
}

func (e *Ejecucion) guarda(proceso string) bool {
	if proceso == "p" {
		return e.n < 1
	}
	return e.n >= 0
}

func (e *Ejecucion) codigoGuarda(proceso string) string {
	if proceso == "p" {
		return "while n < 1"
	}
	return "while n >= 0"
}

func (e *Ejecucion) codigoCuerpo(proceso string) string {
	if proceso == "p" {
		return "n <- n + 1"
	}
	return "n <- n - 1"
}

func (e *Ejecucion) guardaConValores(proceso string, n int) string {
	if proceso == "p" {
		return fmt.Sprintf("%d < 1", n)
	}
	return fmt.Sprintf("%d >= 0", n)
}

func signo(proceso string) string {
	if proceso == "p" {
		return "+"
	}
	return "-"
}

func veredicto(vale bool) string {
	if vale {
		return "verdadero"
	}
	return "falso"
}

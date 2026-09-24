package week04

import (
	"os"
	"strings"
	"testing"
)

// Los escenarios se escriben como una cadena de turnos: cada carácter dice qué
// proceso ejecuta su siguiente instrucción. "qqppp" = q, q, p, p, p.

func TestSinInterferenciaPNuncaEntraAlBucle(t *testing.T) {
	// n arranca en 1, así que la guarda n < 1 de p es falsa desde el principio.
	e := NuevaEjecucion()
	if _, err := e.Correr("p"); err != nil {
		t.Fatalf("Correr: %v", err)
	}

	if !e.Termino("p") {
		t.Error("p debería haber terminado con la primera evaluación de p1")
	}
	if got := e.Iteraciones("p"); got != 0 {
		t.Errorf("iteraciones de p = %d, se esperaba 0", got)
	}
	if got := e.N(); got != 1 {
		t.Errorf("n = %d, se esperaba 1 (p no alcanzó a incrementar)", got)
	}
}

func TestSinInterferenciaQIteraDosVeces(t *testing.T) {
	// q decrementa mientras n >= 0: 1 → 0 → -1 y la guarda se vuelve falsa.
	e := NuevaEjecucion()
	if _, err := e.Correr("qqqqq"); err != nil {
		t.Fatalf("Correr: %v", err)
	}

	if !e.Termino("q") {
		t.Error("q debería haber terminado")
	}
	if got := e.Iteraciones("q"); got != 2 {
		t.Errorf("iteraciones de q = %d, se esperaba 2", got)
	}
	if got := e.N(); got != -1 {
		t.Errorf("n = %d, se esperaba -1", got)
	}
}

// Ejercicio 8(a): un escenario donde el bucle de p se ejecuta exactamente una vez.
func TestEscenarioA_ElBucleDePSeEjecutaUnaVez(t *testing.T) {
	e := NuevaEjecucion()
	traza, err := e.Correr(EscenarioA)
	if err != nil {
		t.Fatalf("Correr: %v", err)
	}

	if got := e.Iteraciones("p"); got != 1 {
		t.Errorf("iteraciones de p = %d, se esperaba 1", got)
	}
	if !e.Termino("p") || !e.Termino("q") {
		t.Errorf("los dos procesos deberían terminar: p=%v q=%v", e.Termino("p"), e.Termino("q"))
	}
	if got := len(traza); got != len(EscenarioA) {
		t.Errorf("la traza tiene %d pasos y el escenario %d", got, len(EscenarioA))
	}
}

// Ejercicio 8(b): un escenario donde el bucle de p se ejecuta exactamente tres veces.
func TestEscenarioB_ElBucleDePSeEjecutaTresVeces(t *testing.T) {
	e := NuevaEjecucion()
	if _, err := e.Correr(EscenarioB); err != nil {
		t.Fatalf("Correr: %v", err)
	}

	if got := e.Iteraciones("p"); got != 3 {
		t.Errorf("iteraciones de p = %d, se esperaba 3", got)
	}
	if !e.Termino("p") || !e.Termino("q") {
		t.Errorf("los dos procesos deberían terminar: p=%v q=%v", e.Termino("p"), e.Termino("q"))
	}
}

// Ejercicio 8(c): un escenario donde los dos bucles se ejecutan infinitas veces.
// No se puede "correr" un escenario infinito: lo que se demuestra es que el
// ciclo devuelve el estado al inicial habiendo iterado los dos bucles, así que
// repetirlo para siempre es un escenario válido.
func TestEscenarioC_AmbosBuclesIteranInfinitamente(t *testing.T) {
	ciclo, err := AnalizarCiclo(EscenarioC)
	if err != nil {
		t.Fatalf("AnalizarCiclo: %v", err)
	}

	if !ciclo.VuelveAlInicio {
		t.Error("el escenario debería dejar n y los contadores de programa como al inicio")
	}
	if ciclo.IteracionesP < 1 || ciclo.IteracionesQ < 1 {
		t.Errorf("cada vuelta debe iterar los dos bucles: p=%d q=%d",
			ciclo.IteracionesP, ciclo.IteracionesQ)
	}
	if ciclo.TerminoAlguno {
		t.Error("ningún proceso puede terminar dentro del ciclo")
	}
}

func TestNoSePuedeAvanzarUnProcesoTerminado(t *testing.T) {
	e := NuevaEjecucion()
	if _, err := e.Correr("p"); err != nil { // p termina en su primera guarda
		t.Fatalf("Correr: %v", err)
	}

	if _, err := e.Paso("p"); err == nil {
		t.Error("avanzar p después de que terminó debería dar error")
	}
}

func TestTurnoDesconocidoDaError(t *testing.T) {
	e := NuevaEjecucion()
	if _, err := e.Correr("x"); err == nil {
		t.Error("un turno que no es p ni q debería dar error")
	}
}

func TestLaTrazaRegistraGuardasYAsignaciones(t *testing.T) {
	e := NuevaEjecucion()
	traza, err := e.Correr("qqp")
	if err != nil {
		t.Fatalf("Correr: %v", err)
	}

	// Valores calculados a mano: q1 con n=1 es verdadera, q2 deja n=0,
	// y entonces la guarda de p (n < 1) pasa a ser verdadera.
	quiero := []Paso{
		{Proceso: "q", Etiqueta: "q1", Codigo: "while n >= 0", Detalle: "1 >= 0 → verdadero", N: 1},
		{Proceso: "q", Etiqueta: "q2", Codigo: "n <- n - 1", Detalle: "n = 1 - 1", N: 0},
		{Proceso: "p", Etiqueta: "p1", Codigo: "while n < 1", Detalle: "0 < 1 → verdadero", N: 0},
	}
	if len(traza) != len(quiero) {
		t.Fatalf("la traza tiene %d pasos, se esperaban %d", len(traza), len(quiero))
	}
	for i, p := range quiero {
		if traza[i] != p {
			t.Errorf("paso %d = %+v, se esperaba %+v", i+1, traza[i], p)
		}
	}
}

func TestMarkdownEsLaTablaDeEscenarios(t *testing.T) {
	e := NuevaEjecucion()
	traza, err := e.Correr("qp")
	if err != nil {
		t.Fatalf("Correr: %v", err)
	}

	got := Markdown(traza)
	quiero := strings.Join([]string{
		"| # | p | q | n |",
		"|--:|---|---|--:|",
		"| 1 |  | `q1` while n >= 0 — 1 >= 0 → verdadero | 1 |",
		"| 2 | `p1` while n < 1 — 1 < 1 → falso |  | 1 |",
		"",
	}, "\n")
	if got != quiero {
		t.Errorf("Markdown devolvió:\n%s\nse esperaba:\n%s", got, quiero)
	}
}

// El gráfico de la entrega se dibuja desde este CSV, así que sale del mismo
// modelo que las tablas y no puede contradecirlas.
func TestCSVTraeUnaFilaPorPaso(t *testing.T) {
	e := NuevaEjecucion()
	traza, err := e.Correr("qp")
	if err != nil {
		t.Fatalf("Correr: %v", err)
	}

	got := CSV("8x", traza)
	quiero := strings.Join([]string{
		"escenario,paso,proceso,etiqueta,detalle,n",
		"8x,1,q,q1,1 >= 0 → verdadero,1",
		"8x,2,p,p1,1 < 1 → falso,1",
		"",
	}, "\n")
	if got != quiero {
		t.Errorf("CSV devolvió:\n%s\nse esperaba:\n%s", got, quiero)
	}
}

func TestCSVSinEncabezadoParaConcatenar(t *testing.T) {
	e := NuevaEjecucion()
	traza, err := e.Correr("q")
	if err != nil {
		t.Fatalf("Correr: %v", err)
	}

	if got := FilasCSV("8x", traza); got != "8x,1,q,q1,1 >= 0 → verdadero,1\n" {
		t.Errorf("FilasCSV = %q", got)
	}
}

// La matriz de escenarios que se entrega es un archivo generado: si el modelo
// cambia, este test falla en vez de dejar el .md desactualizado.
func TestArchivoEscenariosEstaAlDia(t *testing.T) {
	enDisco, err := os.ReadFile("ESCENARIOS.md")
	if err != nil {
		t.Fatalf("leer ESCENARIOS.md: %v", err)
	}

	if string(enDisco) != Documento() {
		t.Error("ESCENARIOS.md está desactualizado: regeneralo con " +
			"`go run ./week04/cmd/escenarios > week04/ESCENARIOS.md`")
	}
}

func TestDocumentoIncluyeLosTresEscenarios(t *testing.T) {
	doc := Documento()
	for _, titulo := range []string{"8(a)", "8(b)", "8(c)"} {
		if !strings.Contains(doc, titulo) {
			t.Errorf("el documento no menciona el escenario %s", titulo)
		}
	}
	if !strings.Contains(doc, "| # | p | q | n |") {
		t.Error("el documento debería traer la tabla de escenarios")
	}
}

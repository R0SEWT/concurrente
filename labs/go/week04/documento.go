package week04

import (
	"fmt"
	"strings"
)

// Documento arma la matriz de escenarios que se entrega: el algoritmo, una
// tabla por escenario del ejercicio 8 y lo que se observa en cada uno.
//
// Se genera desde el mismo modelo que corren los tests, así que las tablas no
// pueden contradecir al código. Regenerar con:
//
//	go run ./week04/cmd/escenarios > week04/ESCENARIOS.md
func Documento() string {
	var b strings.Builder

	b.WriteString(`# Matriz de escenarios — algoritmo concurrente C (Ben-Ari 2.18)

Ejercicio 8 del capítulo 2. **Archivo generado**: sale del mismo modelo que
verifican los tests (` + "`go test -race ./week04/`" + `), no se edita a mano.

    integer n <- 1

    p                        q
    p1: while n < 1          q1: while n >= 0
    p2:     n <- n + 1       q2:     n <- n - 1

Cada fila es una instrucción ejecutada por un proceso, y la columna ` + "`n`" + ` es el
valor de la variable compartida **después** de esa instrucción. La guarda y la
asignación son instrucciones separadas: ahí está todo el asunto, porque entre
evaluar ` + "`n < 1`" + ` y hacer ` + "`n <- n + 1`" + ` el otro proceso puede cambiar n.

Sin interferencia no hay nada que ver: con n = 1, la guarda de p es falsa de
entrada (0 iteraciones) y q decrementa dos veces hasta n = -1. Los escenarios
interesantes son los que intercalan a los dos.
`)

	escenarios := []struct {
		titulo, escenario, lectura string
	}{
		{
			titulo:    "8(a) · el bucle de p se ejecuta exactamente una vez",
			escenario: EscenarioA,
			lectura: "q entra a su bucle y deja n = 0, así que la guarda de p ahora es verdadera. " +
				"p incrementa una vez y n vuelve a 1, con lo que su guarda se vuelve falsa y p " +
				"termina. q sigue solo hasta n = -1.",
		},
		{
			titulo:    "8(b) · el bucle de p se ejecuta exactamente tres veces",
			escenario: EscenarioB,
			lectura: "El mismo truco, tres veces: cada vez que q baja n a 0, p lo sube a 1. " +
				"A la cuarta evaluación p ya no encuentra n < 1 porque q no volvió a decrementar " +
				"antes, y termina. Nada impide repetir el patrón las veces que uno quiera: el " +
				"número de iteraciones de p no es una propiedad del programa, lo elige el " +
				"entrelazado.",
		},
		{
			titulo:    "8(c) · los dos bucles se ejecutan infinitas veces",
			escenario: EscenarioC,
			lectura: "Esta vuelta deja n y los dos contadores de programa exactamente como al " +
				"inicio, y en ella cada bucle iteró una vez. Un escenario que la repita para " +
				"siempre es válido, y en él ningún proceso termina: q nunca llega a n < 0 porque " +
				"p lo sube, y p nunca ve n >= 1 de forma estable porque q lo baja. El programa no " +
				"es incorrecto por una guarda mal escrita, sino porque el entrelazado puede " +
				"conspirar para que ninguno avance.",
		},
	}

	for _, esc := range escenarios {
		e := NuevaEjecucion()
		traza, err := e.Correr(esc.escenario)
		if err != nil { // no debería pasar: los escenarios son constantes verificadas por los tests
			panic(err)
		}

		fmt.Fprintf(&b, "\n## %s\n\n", esc.titulo)
		fmt.Fprintf(&b, "Turnos: `%s` (%d pasos)\n\n", esc.escenario, len(esc.escenario))
		b.WriteString(Markdown(traza))
		fmt.Fprintf(&b, "\nIteraciones: p = %d, q = %d. n final = %d. ",
			e.Iteraciones("p"), e.Iteraciones("q"), e.N())
		fmt.Fprintf(&b, "Terminaron: p = %s, q = %s.\n\n%s\n",
			siNo(e.Termino("p")), siNo(e.Termino("q")), esc.lectura)
	}

	ciclo, err := AnalizarCiclo(EscenarioC)
	if err != nil {
		panic(err)
	}
	fmt.Fprintf(&b, `
## Por qué 8(c) es infinito y no solo largo

No se puede exhibir una tabla infinita, así que lo que se comprueba es el ciclo:
después de los %d turnos de `+"`%s`"+`, n vuelve a %d y los dos procesos quedan otra
vez en su guarda (p1 y q1). El estado es idéntico al inicial y en la vuelta
iteraron los dos bucles (p = %d, q = %d), sin que ninguno termine. Por inducción,
repetirlo es siempre posible: el escenario infinito existe.

Es la diferencia entre *safety* y *liveness*: ninguna de las dos guardas se viola
nunca, y sin embargo el programa puede no terminar. El test
`+"`TestEscenarioC_AmbosBuclesIteranInfinitamente`"+` verifica justo esas tres
condiciones, y la verificación sobre **todos** los entrelazados —no solo los tres
que elegimos— corresponde a Spin, en `+"`labs/spin/`"+`.
`, len(EscenarioC), EscenarioC, ciclo.Traza[len(ciclo.Traza)-1].N,
		ciclo.IteracionesP, ciclo.IteracionesQ)

	return b.String()
}

func siNo(b bool) string {
	if b {
		return "sí"
	}
	return "no"
}

// Command race ejecuta el algoritmo concurrente C con goroutines de verdad,
// para mostrar lo que el modelo determinista de week04 no puede mostrar: que
// sobre memoria compartida sin sincronización esto es una carrera de datos.
//
//	go run -race ./week04/cmd/race
//
// Qué esperar:
//
//   - Con -race: un reporte "WARNING: DATA RACE" sobre n, con la lectura de una
//     guarda y la escritura de la otra goroutine.
//   - El resultado cambia entre corridas: a veces p no itera nunca, a veces
//     itera muchas veces. Ese número no es una propiedad del programa, lo elige
//     el planificador — que es justo lo que el ejercicio 8 pide construir a
//     mano en ESCENARIOS.md.
//   - Puede chocar con el tope de pasos: el escenario infinito de 8(c) no es
//     teórico, y sin el tope esto no terminaría.
//
// Ojo con una trampa extra: nada obliga al compilador a releer n en cada vuelta
// del bucle. Sin sincronización, una goroutine puede quedarse con un valor
// cacheado y girar para siempre aunque la otra ya haya cambiado la variable.
package main

import (
	"fmt"
	"sync"
)

// tope corta la corrida: el algoritmo puede no terminar (ejercicio 8c).
const tope = 10_000_000

func main() {
	n := 1 // la variable compartida del algoritmo
	var iterP, iterQ int

	var wg sync.WaitGroup
	wg.Add(2)

	go func() { // p1: while n < 1 / p2: n <- n + 1
		defer wg.Done()
		for n < 1 {
			n++
			if iterP++; iterP >= tope {
				return
			}
		}
	}()

	go func() { // q1: while n >= 0 / q2: n <- n - 1
		defer wg.Done()
		for n >= 0 {
			n--
			if iterQ++; iterQ >= tope {
				return
			}
		}
	}()

	wg.Wait()

	fmt.Printf("n final = %d\n", n)
	fmt.Printf("iteraciones: p = %d, q = %d\n", iterP, iterQ)
	if iterP >= tope || iterQ >= tope {
		fmt.Printf("se alcanzó el tope de %d pasos: este entrelazado no terminaba\n", tope)
	}
	fmt.Println("compará con week04/ESCENARIOS.md, donde el entrelazado se elige a mano")
}

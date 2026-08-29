// Command race demuestra la carrera de datos que el test suite no puede
// afirmar sin volverse flaky.
//
//	go run -race ./week01/cmd/race
//
// Salida esperada: un reporte "WARNING: DATA RACE" del detector y un total
// menor a 10000. Sin -race probablemente imprima 10000 y no reporte nada —
// esa es justamente la trampa.
package main

import (
	"fmt"
	"sync"

	"upc.edu.pe/concurrente/week01"
)

func main() {
	const goroutines, adds = 50, 200

	c := &week01.Unsafe{}
	var wg sync.WaitGroup
	wg.Add(goroutines)
	for i := 0; i < goroutines; i++ {
		go func() {
			defer wg.Done()
			for j := 0; j < adds; j++ {
				c.Add()
			}
		}()
	}
	wg.Wait()

	fmt.Printf("esperado %d, obtenido %d\n", goroutines*adds, c.Value())
}

package week01

import (
	"sync"
	"testing"
)

// hammer lanza goroutines*adds incrementos concurrentes y devuelve el total.
func hammer(c Counter, goroutines, adds int) int {
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
	return c.Value()
}

// Correr siempre con -race: sin él, un contador roto puede pasar por suerte.
func TestCounterNoPierdeIncrementos(t *testing.T) {
	const goroutines, adds = 50, 200
	const want = goroutines * adds

	casos := map[string]func() Counter{
		"mutex": func() Counter { return &Mutex{} },
		"chan":  func() Counter { return NewChan() },
	}

	for nombre, nuevo := range casos {
		t.Run(nombre, func(t *testing.T) {
			t.Parallel()
			if got := hammer(nuevo(), goroutines, adds); got != want {
				t.Errorf("total = %d, se esperaba %d (se perdieron %d incrementos)", got, want, want-got)
			}
		})
	}
}

// Unsafe no se testea acá a propósito: un test que espera una carrera es
// flaky por construcción y ensuciaría `go test ./...`. La demostración vive
// en cmd/race, donde el detector la reporta de forma determinista.

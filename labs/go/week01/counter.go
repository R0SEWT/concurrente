// Package week01 acompaña la semana 1: el problema de la sección crítica.
//
// Tres contadores con la misma interfaz y garantías distintas. El punto no es
// que Mutex y Chan funcionen, es que Unsafe se ve igual de razonable en el
// código fuente y aun así pierde incrementos. Solo `-race` y el modelo en
// labs/spin/ lo hacen visible.
package week01

import "sync"

// Counter acumula incrementos concurrentes. Add debe ser seguro desde
// múltiples goroutines; Value se lee cuando ya nadie incrementa.
type Counter interface {
	Add()
	Value() int
}

// Unsafe es la versión ingenua: n++ no es atómico (load, add, store), así que
// dos goroutines pueden leer el mismo valor y una sobrescribe a la otra.
// Existe para ser observada fallando, no para usarse. Ver cmd/race.
type Unsafe struct{ n int }

func (c *Unsafe) Add()       { c.n++ }
func (c *Unsafe) Value() int { return c.n }

// Mutex protege la sección crítica con exclusión mutua explícita.
type Mutex struct {
	mu sync.Mutex
	n  int
}

func (c *Mutex) Add() {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.n++
}

func (c *Mutex) Value() int {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.n
}

// Chan no comparte memoria: serializa los incrementos en una sola goroutine
// dueña del estado. "Don't communicate by sharing memory; share memory by
// communicating." Requiere NewChan y Close.
type Chan struct {
	adds chan struct{}
	done chan int
}

func NewChan() *Chan {
	c := &Chan{adds: make(chan struct{}), done: make(chan int)}
	go func() {
		n := 0
		for range c.adds {
			n++
		}
		c.done <- n
	}()
	return c
}

func (c *Chan) Add() { c.adds <- struct{}{} }

// Value cierra el canal de incrementos y espera el total. Solo puede llamarse
// una vez, y después de que todos los Add hayan retornado.
func (c *Chan) Value() int {
	close(c.adds)
	return <-c.done
}

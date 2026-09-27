//go:build ignore

// Tercer intento: turno estricto con la variable turn. Programa de clase, se
// corre con `go run week03/main1.go` — ver la nota en main0.go.
package main

import (
	"fmt"
	// "sync"
	"time"
)

var turn int

//var wg sync.WaitGroup

func P() {
	for {
		fmt.Print("Snc P - Line 1 \n")
		for turn != 1 {
			//espera activa (busy waiting) pre-protocol
		}
		fmt.Print("Seccion critica p3 \n")
		turn = 2 // post-protocol

	}
	//defer wg.Done()

}

func Q() {
	for {
		fmt.Print("Snc Q - Line 1 \n")
		for turn != 2 {
			//espera activa (busy waiting) pre-protocol
		}
		fmt.Print("Seccion critica q4\n")
		turn = 1 // post-protocol
	}
	//defer wg.Done()
}

func main() {
	turn = 1

	//wg.Add(2)
	go P()
	go Q()

	time.Sleep(2 * time.Minute)
}

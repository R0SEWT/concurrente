//go:build ignore

// Segundo intento de sección crítica: cada proceso avisa con wantp/wantq y
// espera al otro. Programa de clase, se corre con `go run week03/main0.go`:
// los tres archivos de week03 son `package main` en la misma carpeta y solo
// uno puede entrar al build del módulo (mismo criterio que week02/sesion2).
package main

import (
	"fmt"
	// "sync"
	"time"
)

var wantp bool
var wantq bool

//var wg sync.WaitGroup

func P() {
	for {
		fmt.Print("P1 - NON CRITICAL SECTION \n")
		wantp = true // pre-protocol

		for wantq {
			//espera activa (busy waiting) pre-protocol
		}
		fmt.Print("P4 CRITICAL SECTION \n")
		wantp = false // post-protocol

	}
	//defer wg.Done()

}

func Q() {
	for {
		fmt.Print("Q1 - NON CRITICAL SECTION \n")
		wantq = true // pre-protocol
		for wantp {
			//espera activa (busy waiting) pre-protocol
		}
		fmt.Print("Q4 CRITICAL SECTION \n")
		wantq = false // post-protocol
	}
	//defer wg.Done()
}

func main() {
	wantp = false
	wantq = false

	//wg.Add(2)
	go P()
	go Q()

	time.Sleep(1 * time.Minute)
}

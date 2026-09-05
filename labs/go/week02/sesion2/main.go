package main

import (
	"fmt"
	"time"
)

var n int

func P() {
	k1 := 1
	time.Sleep(time.Millisecond * 50) //espera 50 milisegundos para que la gorutina Q se ejecute primero
	n = k1 //q1
}

func Q() {
	k2 := 2
	n = k2 //p1
}

func main() {
	n = 0

	// gorunties (goroutines) son hilos de ejecucion ligeros, que se ejecutan de manera concurrente

	go P()
	go Q()

	time.Sleep(time.Millisecond * 100) //espera 100 milisegundos para que las gorutinas terminen de ejecutarse
	fmt.Printf("El valor de n es %d\n", n)

}

package main

import (
	"fmt"
	"time"
)

var n int

func P() {
	temp := n
	n = temp + 1

}

func Q() {
	temp := n
	n = temp + 1
}

func main() {
	n = 0

	go P()
	go Q()

	time.Sleep(time.Millisecond * 100) //espera 100 milisegundos para que las gorutinas terminen de ejecutarse
	fmt.Printf("El valor de n es %d\n", n)
}

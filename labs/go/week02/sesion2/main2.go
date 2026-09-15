package main

import (
	"fmt"
	"sync"
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
	var x int
	var wg sync.WaitGroup

	wg.Add(2)

	go func() {
		x = 1
		wg.Done()
	}()

	go func() {
		fmt.Println(x)
		wg.Done()
	}()

}

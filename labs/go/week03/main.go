package main

import (
	"fmt"
	"sync"
)

var budget int = 100
var wg sync.WaitGroup

func Stingy() {
	for i := 0; i < 100; i++ {
		budget = budget + 10
	}
	defer wg.Done()

}

func Spendy() {
	for i := 0; i < 100; i++ {
		budget = budget - 10
	}
	defer wg.Done()
}

func main() {

	wg.Add(2)
	go Stingy()
	go Spendy()
	defer wg.Done()
	fmt.Println("Budget: ", budget)

}

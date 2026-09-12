// Command escenarios imprime la matriz de escenarios del ejercicio 8.
//
//	go run ./week04/cmd/escenarios > week04/ESCENARIOS.md
//
// El archivo se versiona y un test comprueba que esté al día, así que la tabla
// entregada nunca puede contradecir al modelo.
package main

import (
	"fmt"

	"upc.edu.pe/concurrente/week04"
)

func main() {
	fmt.Print(week04.Documento())
}

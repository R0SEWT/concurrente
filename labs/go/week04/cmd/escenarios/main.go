// Command escenarios imprime la matriz de escenarios del ejercicio 8.
//
//	go run ./week04/cmd/escenarios > week04/ESCENARIOS.md
//	go run ./week04/cmd/escenarios -csv > week04/grafico/escenarios.csv
//
// El archivo se versiona y un test comprueba que esté al día, así que la tabla
// entregada nunca puede contradecir al modelo. Con -csv saca los mismos pasos
// en crudo, para el gráfico de la entrega.
package main

import (
	"flag"
	"fmt"
	"os"
	"strings"

	"upc.edu.pe/concurrente/week04"
)

// vueltasC es cuántas veces se repite el ciclo de 8(c) en el CSV: una sola
// vuelta no se ve como ciclo en el gráfico.
const vueltasC = 3

func main() {
	comoCSV := flag.Bool("csv", false, "exportar los pasos de los tres escenarios como CSV")
	flag.Parse()

	if !*comoCSV {
		fmt.Print(week04.Documento())
		return
	}

	escenarios := []struct{ nombre, turnos string }{
		{"8a", week04.EscenarioA},
		{"8b", week04.EscenarioB},
		{"8c", strings.Repeat(week04.EscenarioC, vueltasC)},
	}
	fmt.Print("escenario,paso,proceso,etiqueta,detalle,n\n")
	for _, esc := range escenarios {
		traza, err := week04.NuevaEjecucion().Correr(esc.turnos)
		if err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
		fmt.Print(week04.FilasCSV(esc.nombre, traza))
	}
}

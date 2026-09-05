package main

import "fmt"

func main() {
	pagos := []float64{100, 2500, 0, 8000, 300}
	validos, total, sospechosos := procesarPagos(pagos)

	fmt.Println("=== Procesamiento de lote ===")
	fmt.Printf("Pagos válidos: %d\n", validos)
	fmt.Printf("Total procesado: %.2f\n", total)
	fmt.Printf("Pagos sospechosos: %d\n", sospechosos)

	fmt.Println("\n=== Control de flujo ===")
	filtrarTransacciones([]float64{100, -50, 200, 0, 300, 15000})

	transacciones := []Transaccion{
		{Monto: 100, Moneda: "PEN", Activo: true, Metodo: "visa", Pais: "PE"},
		{Monto: 0, Moneda: "USD", Activo: true, Metodo: "mastercard", Pais: "PE"},
		{Monto: 6000, Moneda: "PEN", Activo: true, Metodo: "yape", Pais: "PE"},
		{Monto: 250, Moneda: "USD", Activo: true, Metodo: "mastercard", Pais: "CL"},
	}

	fmt.Println("\n=== Caso integrador ===")
	mostrarResultados(procesarTransacciones(transacciones))

	fmt.Println("\n=== Bonus: validación de horario ===")
	fmt.Printf("10:00 permitido: %t\n", validarHorario(10))
	fmt.Printf("18:00 permitido: %t\n", validarHorario(18))
}

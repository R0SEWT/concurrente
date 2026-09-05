package main

import (
	"fmt"
	"strings"
)

const (
	estadoAprobada       = "Aprobada"
	riesgoAprobado       = "Aprobado"
	riesgoAlto           = "Riesgo alto"
	riesgoRevisionManual = "Revisión manual"
)

// validarTransaccion comprueba las reglas básicas en el orden indicado por el
// laboratorio. Solo se evalúa la siguiente regla si la anterior se cumple.
func validarTransaccion(monto float64, moneda string, activo bool) string {
	moneda = strings.ToUpper(strings.TrimSpace(moneda))

	if monto <= 0 {
		return "Monto inválido"
	} else if moneda != "PEN" && moneda != "USD" && moneda != "EUR" {
		return "Moneda inválida"
	} else if !activo {
		return "Usuario inactivo"
	} else {
		return estadoAprobada
	}
}

// calcularComision retorna el importe de la comisión, no el monto final.
func calcularComision(monto float64, metodo string) float64 {
	var tasa float64

	switch strings.ToLower(strings.TrimSpace(metodo)) {
	case "visa":
		tasa = 0.03
	case "mastercard":
		tasa = 0.028
	case "yape":
		tasa = 0.01
	default:
		tasa = 0.05
	}

	return monto * tasa
}

// evaluarRiesgo prioriza la revisión manual por monto sobre el riesgo por país,
// respetando el orden de reglas del enunciado.
func evaluarRiesgo(monto float64, pais string) string {
	pais = strings.ToUpper(strings.TrimSpace(pais))

	if monto > 5000 {
		return riesgoRevisionManual
	} else if pais != "PE" {
		return riesgoAlto
	} else {
		return riesgoAprobado
	}
}

// procesarPagos resume únicamente montos válidos. Todo pago sospechoso también
// es válido porque necesariamente es mayor que cero.
func procesarPagos(pagos []float64) (int, float64, int) {
	var cantidadValidos int
	var totalProcesado float64
	var cantidadSospechosos int

	for _, monto := range pagos {
		if monto <= 0 {
			continue
		}

		cantidadValidos++
		totalProcesado += monto
		if monto > 5000 {
			cantidadSospechosos++
		}
	}

	return cantidadValidos, totalProcesado, cantidadSospechosos
}

// filtrarTransacciones ignora montos inválidos y detiene el recorrido antes de
// procesar una transacción que supere el límite de seguridad.
func filtrarTransacciones(transacciones []float64) {
	for _, monto := range transacciones {
		if monto <= 0 {
			continue
		}

		if monto > 10000 {
			fmt.Printf("Límite de seguridad alcanzado: %.2f. Procesamiento detenido.\n", monto)
			break
		}

		fmt.Printf("Pago procesado: %.2f\n", monto)
	}
}

// validarHorario implementa el bonus: el PSP opera desde las 09:00 hasta antes
// de las 18:00. Se usa un intervalo semiabierto [9, 18).
func validarHorario(hora int) bool {
	return hora >= 9 && hora < 18
}

// Transaccion reúne los datos que necesitan las funciones del caso integrador.
type Transaccion struct {
	Monto   float64
	Moneda  string
	Activo  bool
	Metodo  string
	Pais    string
}

// ResultadoTransaccion conserva tanto el resultado exitoso como la causa de un
// rechazo, evitando recalcular reglas al presentar la salida.
type ResultadoTransaccion struct {
	Numero   int
	Aprobada bool
	Motivo   string
	Comision float64
	Riesgo   string
}

func procesarTransacciones(transacciones []Transaccion) []ResultadoTransaccion {
	resultados := make([]ResultadoTransaccion, 0, len(transacciones))

	for i, tx := range transacciones {
		resultado := ResultadoTransaccion{Numero: i + 1}
		validacion := validarTransaccion(tx.Monto, tx.Moneda, tx.Activo)

		if validacion != estadoAprobada {
			resultado.Motivo = validacion
			resultados = append(resultados, resultado)
			continue
		}

		resultado.Aprobada = true
		resultado.Comision = calcularComision(tx.Monto, tx.Metodo)
		resultado.Riesgo = evaluarRiesgo(tx.Monto, tx.Pais)
		resultados = append(resultados, resultado)
	}

	return resultados
}

func mostrarResultados(resultados []ResultadoTransaccion) {
	for _, resultado := range resultados {
		if !resultado.Aprobada {
			fmt.Printf("Tx %d: Rechazada | %s\n", resultado.Numero, resultado.Motivo)
			continue
		}

		if resultado.Riesgo == riesgoRevisionManual {
			fmt.Printf("Tx %d: Revisión manual | Comisión: %.2f\n", resultado.Numero, resultado.Comision)
			continue
		}

		fmt.Printf(
			"Tx %d: Aprobada | Comisión: %.2f | Riesgo: %s\n",
			resultado.Numero,
			resultado.Comision,
			resultado.Riesgo,
		)
	}
}

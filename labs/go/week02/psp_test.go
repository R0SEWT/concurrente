package main

import (
	"io"
	"math"
	"os"
	"strings"
	"testing"
)

func TestValidarTransaccion(t *testing.T) {
	tests := []struct {
		nombre string
		monto  float64
		moneda string
		activo bool
		want   string
	}{
		{"válida", 100, "PEN", true, "Aprobada"},
		{"normaliza moneda", 100, " usd ", true, "Aprobada"},
		{"monto cero", 0, "PEN", true, "Monto inválido"},
		{"monto negativo", -1, "PEN", true, "Monto inválido"},
		{"moneda inválida", 100, "GBP", true, "Moneda inválida"},
		{"usuario inactivo", 100, "EUR", false, "Usuario inactivo"},
	}

	for _, tt := range tests {
		t.Run(tt.nombre, func(t *testing.T) {
			if got := validarTransaccion(tt.monto, tt.moneda, tt.activo); got != tt.want {
				t.Fatalf("validarTransaccion() = %q; se esperaba %q", got, tt.want)
			}
		})
	}
}

func TestCalcularComision(t *testing.T) {
	tests := []struct {
		metodo string
		want   float64
	}{
		{"visa", 30},
		{"MASTERCARD", 28},
		{" yape ", 10},
		{"transferencia", 50},
	}

	for _, tt := range tests {
		t.Run(tt.metodo, func(t *testing.T) {
			got := calcularComision(1000, tt.metodo)
			if math.Abs(got-tt.want) > 1e-9 {
				t.Fatalf("calcularComision() = %.4f; se esperaba %.4f", got, tt.want)
			}
		})
	}
}

func TestEvaluarRiesgo(t *testing.T) {
	tests := []struct {
		nombre string
		monto  float64
		pais   string
		want   string
	}{
		{"aprobado", 5000, "PE", "Aprobado"},
		{"país extranjero", 100, "CL", "Riesgo alto"},
		{"revisión por monto", 5000.01, "PE", "Revisión manual"},
		{"monto tiene precedencia", 6000, "CL", "Revisión manual"},
	}

	for _, tt := range tests {
		t.Run(tt.nombre, func(t *testing.T) {
			if got := evaluarRiesgo(tt.monto, tt.pais); got != tt.want {
				t.Fatalf("evaluarRiesgo() = %q; se esperaba %q", got, tt.want)
			}
		})
	}
}

func TestProcesarPagos(t *testing.T) {
	validos, total, sospechosos := procesarPagos([]float64{100, 2500, 0, 8000, 300})

	if validos != 4 || total != 10900 || sospechosos != 1 {
		t.Fatalf(
			"procesarPagos() = (%d, %.2f, %d); se esperaba (4, 10900.00, 1)",
			validos,
			total,
			sospechosos,
		)
	}
}

func TestFiltrarTransacciones(t *testing.T) {
	salida := capturarSalida(t, func() {
		filtrarTransacciones([]float64{100, -50, 200, 0, 300, 10000, 15000, 400})
	})

	want := "Pago procesado: 100.00\n" +
		"Pago procesado: 200.00\n" +
		"Pago procesado: 300.00\n" +
		"Pago procesado: 10000.00\n" +
		"Límite de seguridad alcanzado: 15000.00. Procesamiento detenido.\n"
	if salida != want {
		t.Fatalf("salida inesperada:\n%s\nse esperaba:\n%s", salida, want)
	}
	if strings.Contains(salida, "400.00") {
		t.Fatal("se procesó una transacción posterior al límite")
	}
}

func TestProcesarTransacciones(t *testing.T) {
	transacciones := []Transaccion{
		{Monto: 100, Moneda: "PEN", Activo: true, Metodo: "visa", Pais: "PE"},
		{Monto: 0, Moneda: "USD", Activo: true, Metodo: "yape", Pais: "PE"},
		{Monto: 6000, Moneda: "EUR", Activo: true, Metodo: "yape", Pais: "PE"},
	}

	resultados := procesarTransacciones(transacciones)
	if len(resultados) != 3 {
		t.Fatalf("se obtuvieron %d resultados; se esperaban 3", len(resultados))
	}
	if !resultados[0].Aprobada || resultados[0].Comision != 3 || resultados[0].Riesgo != "Aprobado" {
		t.Fatalf("resultado de Tx 1 incorrecto: %+v", resultados[0])
	}
	if resultados[1].Aprobada || resultados[1].Motivo != "Monto inválido" {
		t.Fatalf("resultado de Tx 2 incorrecto: %+v", resultados[1])
	}
	if !resultados[2].Aprobada || resultados[2].Comision != 60 || resultados[2].Riesgo != "Revisión manual" {
		t.Fatalf("resultado de Tx 3 incorrecto: %+v", resultados[2])
	}
}

func TestValidarHorario(t *testing.T) {
	tests := []struct {
		hora int
		want bool
	}{
		{8, false},
		{9, true},
		{17, true},
		{18, false},
	}

	for _, tt := range tests {
		if got := validarHorario(tt.hora); got != tt.want {
			t.Errorf("validarHorario(%d) = %t; se esperaba %t", tt.hora, got, tt.want)
		}
	}
}

func capturarSalida(t *testing.T, f func()) string {
	t.Helper()

	anterior := os.Stdout
	lector, escritor, err := os.Pipe()
	if err != nil {
		t.Fatalf("no se pudo crear el pipe: %v", err)
	}
	os.Stdout = escritor

	f()

	if err := escritor.Close(); err != nil {
		t.Fatalf("no se pudo cerrar la salida: %v", err)
	}
	os.Stdout = anterior

	datos, err := io.ReadAll(lector)
	if err != nil {
		t.Fatalf("no se pudo leer la salida: %v", err)
	}
	if err := lector.Close(); err != nil {
		t.Fatalf("no se pudo cerrar la entrada: %v", err)
	}

	return string(datos)
}

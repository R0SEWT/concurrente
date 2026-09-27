package main

import (
	"os"
	"path/filepath"
	"testing"

	"upc.edu.pe/concurrente/kmeans"
)

func datosDePrueba() *kmeans.Datos {
	// Doce puntos en R^2, bien separados, para que k-means++ tenga de dónde elegir.
	var x []float64
	for i := 0; i < 12; i++ {
		x = append(x, float64(i*10), float64(i%3))
	}
	return &kmeans.Datos{X: x, N: 12, D: 2}
}

func TestCentroidesInicialesGeneraYReusaElArchivo(t *testing.T) {
	d := datosDePrueba()
	ruta := filepath.Join(t.TempDir(), "c.txt")

	cent1, k1, err := centroidesIniciales(d, 3, 7, ruta)
	if err != nil {
		t.Fatalf("primera corrida: %v", err)
	}
	if k1 != 3 || len(cent1) != 3*d.D {
		t.Fatalf("k=%d, len=%d; se esperaban 3 y %d", k1, len(cent1), 3*d.D)
	}
	if _, err := os.Stat(ruta); err != nil {
		t.Fatalf("no se guardó el archivo de centroides: %v", err)
	}

	cent2, k2, err := centroidesIniciales(d, 3, 999, ruta) // otra semilla: debe ganar el archivo
	if err != nil {
		t.Fatalf("segunda corrida: %v", err)
	}
	if k2 != 3 {
		t.Fatalf("k leído = %d, se esperaba 3", k2)
	}
	for i := range cent1 {
		if cent1[i] != cent2[i] {
			t.Fatalf("el archivo no se reusó: centroide %d difiere (%v vs %v)", i, cent1[i], cent2[i])
		}
	}
}

func TestCentroidesInicialesRechazaUnArchivoConOtroK(t *testing.T) {
	// Sourcery (PR #21): si el archivo trae otro k, la corrida no respetaría -k y
	// los metadatos registrarían un K distinto del que se usó. Mejor fallar.
	d := datosDePrueba()
	ruta := filepath.Join(t.TempDir(), "c.txt")
	if _, _, err := centroidesIniciales(d, 3, 7, ruta); err != nil {
		t.Fatalf("generar el archivo: %v", err)
	}

	_, _, err := centroidesIniciales(d, 4, 7, ruta)
	if err == nil {
		t.Fatal("se aceptó un archivo con k=3 para una corrida con -k 4")
	}
}

func TestCentroidesInicialesRechazaUnArchivoConOtraDimension(t *testing.T) {
	d := datosDePrueba()
	ruta := filepath.Join(t.TempDir(), "c.txt")
	if _, _, err := centroidesIniciales(d, 3, 7, ruta); err != nil {
		t.Fatalf("generar el archivo: %v", err)
	}

	d3 := &kmeans.Datos{X: make([]float64, 12*3), N: 12, D: 3}
	if _, _, err := centroidesIniciales(d3, 3, 7, ruta); err == nil {
		t.Fatal("se aceptó un archivo con D=2 para un gold con D=3")
	}
}

func TestArgumentosDescartaLaRutaDuplicadaDeAndroid(t *testing.T) {
	// En Android el binario se lanza vía el enlazador del sistema y recibe su
	// propia ruta dos veces: flag.Parse se detenía en la copia y descartaba todos
	// los flags. Se vio en un Pixel 9a con Termux.
	casos := []struct {
		nombre string
		args   []string
		quiere []string
	}{
		{"android", []string{"/h/kmeans", "/h/kmeans", "-modo", "seq"}, []string{"-modo", "seq"}},
		{"normal", []string{"/h/kmeans", "-modo", "seq"}, []string{"-modo", "seq"}},
		{"sin flags", []string{"./kmeans"}, []string{}},
		{"primer argumento distinto", []string{"/h/kmeans", "otra", "-k", "3"}, []string{"otra", "-k", "3"}},
	}
	// El caso real de Termux: "./kmeans" y la ruta absoluta del mismo archivo.
	dir := t.TempDir()
	bin := filepath.Join(dir, "kmeans")
	if err := os.WriteFile(bin, []byte("x"), 0o755); err != nil {
		t.Fatal(err)
	}
	previo, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	if err := os.Chdir(dir); err != nil {
		t.Fatal(err)
	}
	defer os.Chdir(previo)
	casos = append(casos, struct {
		nombre string
		args   []string
		quiere []string
	}{"relativa y absoluta", []string{"./kmeans", bin, "-modo", "seq"}, []string{"-modo", "seq"}})

	for _, c := range casos {
		got := argumentos(c.args)
		if len(got) != len(c.quiere) {
			t.Fatalf("%s: %q, se esperaba %q", c.nombre, got, c.quiere)
		}
		for i := range got {
			if got[i] != c.quiere[i] {
				t.Fatalf("%s: %q, se esperaba %q", c.nombre, got, c.quiere)
			}
		}
	}
}

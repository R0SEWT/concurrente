package kmeans

import (
	"math"
	"os"
	"testing"
	"time"
)

const rutaGoldReal = "../data/gold/yellow_2024-01_features.csv"

// TestLeerGoldArchivoReal comprueba el contrato contra el gold de verdad.
// Se salta si el archivo no está (el CI no lo descarga) y con -short.
func TestLeerGoldArchivoReal(t *testing.T) {
	if testing.Short() {
		t.Skip("-short: no se lee el gold completo")
	}
	if _, err := os.Stat(rutaGoldReal); err != nil {
		t.Skipf("no está el gold en %s: %v", rutaGoldReal, err)
	}

	inicio := time.Now()
	d, err := LeerGoldArchivo(rutaGoldReal)
	if err != nil {
		t.Fatalf("LeerGoldArchivo: %v", err)
	}
	tardo := time.Since(inicio)

	const viajesEsperados = 2831486 // reporte de limpieza de yellow 2024-01
	if d.N != viajesEsperados {
		t.Errorf("N = %d, se esperaban %d viajes", d.N, viajesEsperados)
	}
	if d.D != 6 {
		t.Errorf("D = %d, se esperaban 6 features", d.D)
	}
	if len(d.X) != d.N*d.D {
		t.Errorf("len(X) = %d, se esperaba N*D = %d", len(d.X), d.N*d.D)
	}
	t.Logf("gold leído en %s: %d viajes, %.1f MiB en float64",
		tardo.Round(time.Millisecond), d.N, float64(len(d.X)*8)/(1<<20))
}

// TestSecuencialSobreElGoldReal es la corrida piloto de punta a punta: mide
// cuánto cuesta de verdad una iteración sobre los 2,8 millones de viajes, que
// es lo que decide si el benchmark cabe en el calendario.
func TestSecuencialSobreElGoldReal(t *testing.T) {
	if testing.Short() {
		t.Skip("-short: no se corre sobre el gold completo")
	}
	if _, err := os.Stat(rutaGoldReal); err != nil {
		t.Skipf("no está el gold en %s: %v", rutaGoldReal, err)
	}

	d, err := LeerGoldArchivo(rutaGoldReal)
	if err != nil {
		t.Fatalf("LeerGoldArchivo: %v", err)
	}

	const k = 8
	inicio := time.Now()
	cent, kEfectivo, err := KMeansPP(d, k, 2024)
	if err != nil {
		t.Fatalf("KMeansPP: %v", err)
	}
	tardoInit := time.Since(inicio)
	if kEfectivo != k {
		t.Fatalf("k efectivo = %d, se esperaban %d", kEfectivo, k)
	}

	const iteraciones = 5
	inicio = time.Now()
	r, err := Secuencial(d, cent, Opciones{K: k, MaxIter: iteraciones, TolAbs: 1e-9, TolRel: 1e-9})
	if err != nil {
		t.Fatalf("Secuencial: %v", err)
	}
	tardo := time.Since(inicio)

	for i := 1; i < len(r.Inercias); i++ {
		if r.Inercias[i] > r.Inercias[i-1]+1e-6 {
			t.Errorf("la inercia creció en la iteración %d: %v → %v", i+1, r.Inercias[i-1], r.Inercias[i])
		}
	}
	t.Logf("k-means++ (k=%d) en %s, hash %s", k, tardoInit.Round(time.Millisecond), HashCentroides(cent)[:16])
	t.Logf("%d iteraciones en %s (%s por iteración), paro=%s, vacíos=%d",
		r.Iteraciones, tardo.Round(time.Millisecond),
		(tardo / time.Duration(r.Iteraciones)).Round(time.Millisecond), r.Paro, r.Vacios)
	t.Logf("inercia: %.4g → %.4g (final con centroides finales: %.4g)",
		r.Inercias[0], r.Inercias[len(r.Inercias)-1], r.Inercia)
}

// TestPilotoSpeedupSobreElGoldReal es un piloto, NO el benchmark de la PC2:
// una sola corrida por configuración, sin media recortada ni orden alternado.
// Sirve para ver si el speedup aparece y para dimensionar el harness real
// (concurrente-3r8.9), que es el que produce los números del informe.
func TestPilotoSpeedupSobreElGoldReal(t *testing.T) {
	if testing.Short() {
		t.Skip("-short: no se corre sobre el gold completo")
	}
	if _, err := os.Stat(rutaGoldReal); err != nil {
		t.Skipf("no está el gold en %s: %v", rutaGoldReal, err)
	}

	d, err := LeerGoldArchivo(rutaGoldReal)
	if err != nil {
		t.Fatalf("LeerGoldArchivo: %v", err)
	}
	const (
		k           = 8
		iteraciones = 10
		chunk       = 16384
	)
	cent, _, err := KMeansPP(d, k, 2024)
	if err != nil {
		t.Fatalf("KMeansPP: %v", err)
	}
	op := Opciones{K: k, MaxIter: iteraciones, TolAbs: 1e-9, TolRel: 1e-9}

	inicio := time.Now()
	sec, err := Secuencial(d, cent, op)
	if err != nil {
		t.Fatalf("Secuencial: %v", err)
	}
	tSec := time.Since(inicio)
	t.Logf("secuencial: %s (%d iteraciones, inercia %.6g)",
		tSec.Round(time.Millisecond), sec.Iteraciones, sec.Inercia)

	for _, p := range []int{1, 2, 4, 8} {
		inicio := time.Now()
		con, err := Concurrente(d, cent, OpcionesConc{Opciones: op, Workers: p, Chunk: chunk})
		if err != nil {
			t.Fatalf("Concurrente P=%d: %v", p, err)
		}
		tCon := time.Since(inicio)

		if rel := math.Abs(con.Inercia-sec.Inercia) / math.Abs(sec.Inercia); rel > 1e-12 {
			t.Errorf("P=%d: la inercia difiere del secuencial en %.3g relativo", p, rel)
		}
		t.Logf("P=%-2d: %s · speedup %.2fx · eficiencia %.0f%%",
			p, tCon.Round(time.Millisecond),
			tSec.Seconds()/tCon.Seconds(), 100*tSec.Seconds()/tCon.Seconds()/float64(p))
	}
}

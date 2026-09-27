package kmeans

import (
	"math"
	"strings"
	"testing"
)

const cabecera = "viaje_id,PULocationID,DOLocationID,hora_sin,hora_cos,dia_sin,dia_cos,log_duracion_z,log_distancia_z"

// goldMinimo arma un gold válido con las filas dadas (sin la cabecera).
func goldMinimo(filas ...string) string {
	return cabecera + "\n" + strings.Join(filas, "\n") + "\n"
}

func TestLeerGoldCargaLasSeisFeaturesEnOrden(t *testing.T) {
	csv := goldMinimo(
		"0,186,79,0.250028,0.968239,0.000000,1.000000,0.746232,-0.258819",
		"1,140,236,0.013090,0.999914,0.000000,1.000000,-0.829506,-0.214637",
	)

	d, err := LeerGold(strings.NewReader(csv))
	if err != nil {
		t.Fatalf("LeerGold devolvió error: %v", err)
	}
	if d.N != 2 {
		t.Errorf("N = %d, se esperaban 2 viajes", d.N)
	}
	if d.D != 6 {
		t.Errorf("D = %d, se esperaban 6 features", d.D)
	}
	if len(d.X) != 12 {
		t.Fatalf("len(X) = %d, se esperaban N*D = 12", len(d.X))
	}
	// La primera feature del primer viaje es hora_sin, no viaje_id ni la zona.
	if d.X[0] != 0.250028 {
		t.Errorf("X[0] = %v, se esperaba hora_sin = 0.250028", d.X[0])
	}
	if d.X[5] != -0.258819 {
		t.Errorf("X[5] = %v, se esperaba log_distancia_z = -0.258819", d.X[5])
	}
	if d.X[6] != 0.013090 {
		t.Errorf("X[6] = %v, se esperaba la hora_sin del segundo viaje", d.X[6])
	}
}

func TestPuntoDevuelveLaFilaCompleta(t *testing.T) {
	csv := goldMinimo(
		"0,1,2,1,2,3,4,5,6",
		"1,1,2,7,8,9,10,11,12",
	)

	d, err := LeerGold(strings.NewReader(csv))
	if err != nil {
		t.Fatalf("LeerGold devolvió error: %v", err)
	}
	p := d.Punto(1)
	if len(p) != 6 {
		t.Fatalf("len(Punto(1)) = %d, se esperaban 6", len(p))
	}
	for i, quiero := range []float64{7, 8, 9, 10, 11, 12} {
		if p[i] != quiero {
			t.Errorf("Punto(1)[%d] = %v, se esperaba %v", i, p[i], quiero)
		}
	}
}

func TestLeerGoldRechazaCabeceraDistinta(t *testing.T) {
	// Mismo número de columnas, pero duración y distancia cambiadas de lugar:
	// si no se valida, el K-means corre con las features permutadas y nadie se entera.
	mala := "viaje_id,PULocationID,DOLocationID,hora_sin,hora_cos,dia_sin,dia_cos,log_distancia_z,log_duracion_z"
	csv := mala + "\n0,1,2,1,2,3,4,5,6\n"

	_, err := LeerGold(strings.NewReader(csv))
	if err == nil {
		t.Fatal("se esperaba error por cabecera distinta")
	}
	if !strings.Contains(err.Error(), "log_duracion_z") {
		t.Errorf("el error debería nombrar la columna esperada, fue: %v", err)
	}
}

func TestLeerGoldRechazaArchivoVacio(t *testing.T) {
	_, err := LeerGold(strings.NewReader(""))
	if err == nil {
		t.Fatal("se esperaba error con un archivo vacío")
	}
}

func TestLeerGoldRechazaGoldSinFilas(t *testing.T) {
	_, err := LeerGold(strings.NewReader(cabecera + "\n"))
	if err == nil {
		t.Fatal("se esperaba error: un gold sin viajes no sirve para agrupar")
	}
}

func TestLeerGoldRechazaFilaConColumnasDeMenos(t *testing.T) {
	csv := goldMinimo(
		"0,186,79,0.25,0.96,0.0,1.0,0.74,-0.25",
		"1,140,236,0.01,0.99,0.0,1.0,-0.82",
	)

	_, err := LeerGold(strings.NewReader(csv))
	if err == nil {
		t.Fatal("se esperaba error por fila incompleta")
	}
	if !strings.Contains(err.Error(), "3") {
		t.Errorf("el error debería indicar la línea 3, fue: %v", err)
	}
}

func TestLeerGoldRechazaValorNoNumerico(t *testing.T) {
	csv := goldMinimo("0,186,79,0.25,ocho,0.0,1.0,0.74,-0.25")

	_, err := LeerGold(strings.NewReader(csv))
	if err == nil {
		t.Fatal("se esperaba error por valor no numérico")
	}
	if !strings.Contains(err.Error(), "hora_cos") {
		t.Errorf("el error debería nombrar la columna, fue: %v", err)
	}
}

func TestLeerGoldRechazaNoFinitos(t *testing.T) {
	// El contrato del diseño: NaN e Inf no entran. Un NaN en la distancia
	// euclídea vuelve NaN a todo el centroide y el K-means deja de converger.
	casos := map[string]string{
		"NaN":  "0,186,79,0.25,NaN,0.0,1.0,0.74,-0.25",
		"+Inf": "0,186,79,0.25,0.96,0.0,1.0,Inf,-0.25",
		"-Inf": "0,186,79,0.25,0.96,0.0,1.0,0.74,-Inf",
	}
	for nombre, fila := range casos {
		t.Run(nombre, func(t *testing.T) {
			_, err := LeerGold(strings.NewReader(goldMinimo(fila)))
			if err == nil {
				t.Fatalf("se esperaba error con %s", nombre)
			}
		})
	}
}

func TestLeerGoldAceptaFinalSinSaltoDeLinea(t *testing.T) {
	csv := cabecera + "\n0,186,79,0.25,0.96,0.0,1.0,0.74,-0.25"

	d, err := LeerGold(strings.NewReader(csv))
	if err != nil {
		t.Fatalf("LeerGold devolvió error: %v", err)
	}
	if d.N != 1 {
		t.Errorf("N = %d, se esperaba 1", d.N)
	}
}

func TestLeerGoldNoPierdePrecisionDelCSV(t *testing.T) {
	// El gold se exporta con seis decimales y Go lo lee como float64.
	csv := goldMinimo("0,186,79,0.250028,0.968239,0.000000,1.000000,0.746232,-0.258819")

	d, err := LeerGold(strings.NewReader(csv))
	if err != nil {
		t.Fatalf("LeerGold devolvió error: %v", err)
	}
	if math.Abs(d.X[1]-0.968239) > 0 {
		t.Errorf("X[1] = %.17g, se esperaba exactamente 0.968239", d.X[1])
	}
}

package cofinanciamiento

import (
	"reflect"
	"sync"
	"testing"
)

// fixture chico y verificable a mano. Incluye tres casos borde a propósito:
// un donante repetido en el mismo grupo (no debe pesar doble), un grupo con
// un solo donante (no produce aristas) y el mismo par en dos años distintos
// (sí debe pesar doble).
var fixture = []Registro{
	{Receptor: "Peru", Anio: "2010", Donante: "USA"},
	{Receptor: "Peru", Anio: "2010", Donante: "Japan"},
	{Receptor: "Peru", Anio: "2010", Donante: "Spain"},
	{Receptor: "Peru", Anio: "2010", Donante: "USA"}, // repetido
	{Receptor: "Peru", Anio: "2011", Donante: "USA"},
	{Receptor: "Peru", Anio: "2011", Donante: "Japan"},
	{Receptor: "Bolivia", Anio: "2010", Donante: "USA"},
	{Receptor: "Bolivia", Anio: "2010", Donante: "Germany"},
	{Receptor: "Ecuador", Anio: "2010", Donante: "Spain"}, // solo, sin aristas
}

var esperada = Red{
	{A: "Japan", B: "Spain"}: 1,
	{A: "Japan", B: "USA"}:   2, // Peru 2010 y Peru 2011
	{A: "Spain", B: "USA"}:   1,
	{A: "Germany", B: "USA"}: 1,
}

func alimentar(a Acumulador, rs []Registro) Acumulador {
	for _, r := range rs {
		a.Agregar(r)
	}
	return a
}

func TestParcialProduceLaRedEsperada(t *testing.T) {
	got := alimentar(NuevoParcial(), fixture).Red()
	if !reflect.DeepEqual(got, esperada) {
		t.Errorf("red = %v\nse esperaba %v", got, esperada)
	}
}

func TestGrupoDeUnSoloDonanteNoProduceArista(t *testing.T) {
	p := NuevoParcial()
	p.Agregar(Registro{Receptor: "Ecuador", Anio: "2010", Donante: "Spain"})
	if n := len(p.Red()); n != 0 {
		t.Errorf("un grupo con un solo donante produjo %d aristas, se esperaban 0", n)
	}
}

// Correr siempre con -race. Varias goroutines alimentan el mismo Shardeado
// con el fixture completo; como la etapa intermedia es un conjunto, agregar
// el mismo registro N veces es idempotente y el resultado no debe cambiar.
func TestShardeadoEsSeguroYCoincideConParcial(t *testing.T) {
	for _, shards := range []int{1, 4, 17} {
		shards := shards
		t.Run("shards", func(t *testing.T) {
			t.Parallel()
			s := NuevoShardeado(shards)
			var wg sync.WaitGroup
			const goroutines = 32
			wg.Add(goroutines)
			for i := 0; i < goroutines; i++ {
				go func() {
					defer wg.Done()
					for _, r := range fixture {
						s.Agregar(r)
					}
				}()
			}
			wg.Wait()
			if got := s.Red(); !reflect.DeepEqual(got, esperada) {
				t.Errorf("con %d shards: red = %v\nse esperaba %v", shards, got, esperada)
			}
		})
	}
}

// Reparte el fixture en chunks disjuntos, uno por worker, y fusiona. Es el
// camino sin candados: cada worker escribe solo en su Parcial.
func TestFusionarParcialesCoincideConSecuencial(t *testing.T) {
	for _, workers := range []int{2, 3, 9} {
		partes := make([]*Parcial, workers)
		var wg sync.WaitGroup
		wg.Add(workers)
		for w := 0; w < workers; w++ {
			w := w
			go func() {
				defer wg.Done()
				p := NuevoParcial()
				for i := w; i < len(fixture); i += workers {
					p.Agregar(fixture[i])
				}
				partes[w] = p
			}()
		}
		wg.Wait()
		if got := Fusionar(partes...).Red(); !reflect.DeepEqual(got, esperada) {
			t.Errorf("con %d workers: red = %v\nse esperaba %v", workers, got, esperada)
		}
	}
}

// El error que el diseño evita, escrito como test para que no se reintroduzca.
//
// Si cada worker construye SU red y después se suman las redes, un par de
// donantes que quedó partido entre dos chunks desaparece: ninguno de los dos
// workers vio a los dos juntos. Fusionar en la etapa de conjuntos sí lo ve.
func TestFusionarRedesPierdeAristas(t *testing.T) {
	a := NuevoParcial()
	a.Agregar(Registro{Receptor: "Peru", Anio: "2010", Donante: "USA"})
	b := NuevoParcial()
	b.Agregar(Registro{Receptor: "Peru", Anio: "2010", Donante: "Japan"})

	// Mal: sumar las redes ya materializadas.
	malo := make(Red)
	for _, p := range []*Parcial{a, b} {
		for ar, n := range p.Red() {
			malo[ar] += n
		}
	}
	if len(malo) != 0 {
		t.Fatalf("premisa del test rota: sumar redes dio %v, se esperaba vacío", malo)
	}

	// Bien: fusionar los conjuntos y recién ahí materializar.
	bueno := Fusionar(a, b).Red()
	if got := bueno.Peso("USA", "Japan"); got != 1 {
		t.Errorf("fusionando conjuntos, peso(USA,Japan) = %d, se esperaba 1", got)
	}
	if len(bueno) != 1 {
		t.Errorf("red fusionada = %v, se esperaba exactamente una arista", bueno)
	}
}

func TestAristaSeNormaliza(t *testing.T) {
	if NuevaArista("USA", "Japan") != NuevaArista("Japan", "USA") {
		t.Error("la arista no es simétrica")
	}
}

func TestTopEsDeterministaYOrdenado(t *testing.T) {
	r := alimentar(NuevoParcial(), fixture).Red()
	top := r.Top(2)
	if len(top) != 2 {
		t.Fatalf("Top(2) devolvió %d aristas", len(top))
	}
	if top[0].Peso < top[1].Peso {
		t.Errorf("Top no está ordenado por peso: %v", top)
	}
	if top[0].A != "Japan" || top[0].B != "USA" || top[0].Peso != 2 {
		t.Errorf("la arista más pesada fue %v, se esperaba Japan-USA con peso 2", top[0])
	}
}

func TestTamaniosCuentaDonantesDistintos(t *testing.T) {
	tam := alimentar(NuevoParcial(), fixture).Tamanios()
	quiero := map[Grupo]int{
		{Receptor: "Peru", Anio: "2010"}:    3, // USA, Japan, Spain (USA va repetido)
		{Receptor: "Peru", Anio: "2011"}:    2,
		{Receptor: "Bolivia", Anio: "2010"}: 2,
		{Receptor: "Ecuador", Anio: "2010"}: 1,
	}
	if !reflect.DeepEqual(tam, quiero) {
		t.Errorf("tamaños = %v\nse esperaba %v", tam, quiero)
	}
}

func TestPorDecadaResumeElFixture(t *testing.T) {
	// Los cuatro grupos del fixture caen en los 2010: tamaños 1, 2, 2, 3.
	got := PorDecada(alimentar(NuevoParcial(), fixture).Tamanios())
	quiero := []Fragmentacion{{Decada: 2010, Grupos: 4, Media: 2.0, Mediana: 2, Max: 3}}
	if !reflect.DeepEqual(got, quiero) {
		t.Errorf("por década = %+v\nse esperaba %+v", got, quiero)
	}
}

func TestPorDecadaIgnoraAniosImposibles(t *testing.T) {
	// AidData trae 59 filas con año 9999. No deben inventar una década.
	p := NuevoParcial()
	p.Agregar(Registro{Receptor: "Peru", Anio: "9999", Donante: "USA"})
	p.Agregar(Registro{Receptor: "Peru", Anio: "sin dato", Donante: "USA"})
	if got := PorDecada(p.Tamanios()); len(got) != 0 {
		t.Errorf("años imposibles produjeron %+v, se esperaba nada", got)
	}
}

func TestShardeadoDaLosMismosTamanios(t *testing.T) {
	s := alimentar(NuevoShardeado(7), fixture)
	if !reflect.DeepEqual(s.Tamanios(), alimentar(NuevoParcial(), fixture).Tamanios()) {
		t.Error("shardeado y parcial difieren en los tamaños de grupo")
	}
}

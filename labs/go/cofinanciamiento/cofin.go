// Package cofinanciamiento construye la red de co-financiamiento entre
// donantes de ayuda al desarrollo a partir de AidData.
//
// Dos donantes co-financian cuando aparecen en el mismo receptor y el mismo
// año. La red es el grafo no dirigido que sale de contar esas coincidencias
// sobre 1 561 039 proyectos (1947-2013, 96 donantes, 252 receptores).
//
// El paquete existe para el trabajo del curso, no para producción: hay dos
// acumuladores con la misma interfaz y garantías distintas, más un fusionador,
// y el punto es compararlos bajo -race y medir cómo escalan.
//
// La sutileza que justifica el diseño está en Fusionar: el estado intermedio
// que se puede repartir entre workers es el *conjunto de donantes por grupo*,
// no la red ya construida. Ver TestFusionarRedesPierdeAristas.
package cofinanciamiento

import (
	"hash/fnv"
	"sort"
	"sync"
)

// Registro es una fila de AidData reducida a lo que la red necesita.
type Registro struct {
	Receptor string
	Anio     string
	Donante  string
}

// Grupo es la unidad de co-financiamiento: un receptor en un año.
type Grupo struct {
	Receptor string
	Anio     string
}

// Arista es un par no ordenado de donantes. Se normaliza A<B para que
// (USA, Japan) y (Japan, USA) sean la misma clave de mapa.
type Arista struct {
	A, B string
}

// NuevaArista normaliza el par.
func NuevaArista(x, y string) Arista {
	if x > y {
		x, y = y, x
	}
	return Arista{A: x, B: y}
}

// Red cuenta, por par de donantes, en cuántos grupos coincidieron.
type Red map[Arista]int

// Acumulador consume registros y produce la red. Las implementaciones
// difieren en si Agregar es seguro desde varias goroutines.
type Acumulador interface {
	Agregar(Registro)
	Red() Red
}

// conjuntos es el estado intermedio: por grupo, qué donantes se vieron.
// Es un conjunto y no una lista porque un donante puede tener muchos
// proyectos en el mismo receptor-año y eso no debe pesar la arista.
type conjuntos map[Grupo]map[string]struct{}

func (c conjuntos) agregar(r Registro) {
	g := Grupo{Receptor: r.Receptor, Anio: r.Anio}
	d, ok := c[g]
	if !ok {
		d = make(map[string]struct{}, 8)
		c[g] = d
	}
	d[r.Donante] = struct{}{}
}

// red materializa los pares. Se ordenan los donantes del grupo para que el
// recorrido sea determinista; con mapas de Go no lo sería, y aunque el
// resultado no cambia, un orden fijo hace los tests legibles.
func (c conjuntos) red() Red {
	out := make(Red)
	nombres := make([]string, 0, 64)
	for _, donantes := range c {
		nombres = nombres[:0]
		for d := range donantes {
			nombres = append(nombres, d)
		}
		sort.Strings(nombres)
		for i := 0; i < len(nombres); i++ {
			for j := i + 1; j < len(nombres); j++ {
				out[Arista{A: nombres[i], B: nombres[j]}]++
			}
		}
	}
	return out
}

// Parcial es el acumulado de un solo worker. NO es seguro para uso
// concurrente: cada goroutine debe tener el suyo y fusionarlos al final.
// También sirve como implementación de referencia secuencial.
type Parcial struct {
	grupos conjuntos
}

// NuevoParcial crea un acumulador de una sola goroutine.
func NuevoParcial() *Parcial {
	return &Parcial{grupos: make(conjuntos, 1024)}
}

// Agregar suma un registro. No sincroniza nada a propósito.
func (p *Parcial) Agregar(r Registro) { p.grupos.agregar(r) }

// Red materializa la red de este parcial.
func (p *Parcial) Red() Red { return p.grupos.red() }

// Fusionar une parciales por unión de conjuntos de donantes. La unión es
// asociativa y conmutativa, que es justo lo que permite que cada worker
// acumule por su cuenta sin candados.
//
// Es obligatorio fusionar en esta etapa y no en la red: si el chunk 1 vio a
// USA en (Perú, 2010) y el chunk 2 vio a Japón en el mismo grupo, ninguno de
// los dos produce la arista USA-Japón por separado. Sumar sus redes la pierde.
func Fusionar(partes ...*Parcial) *Parcial {
	total := NuevoParcial()
	for _, p := range partes {
		if p == nil {
			continue
		}
		for g, donantes := range p.grupos {
			d, ok := total.grupos[g]
			if !ok {
				d = make(map[string]struct{}, len(donantes))
				total.grupos[g] = d
			}
			for nombre := range donantes {
				d[nombre] = struct{}{}
			}
		}
	}
	return total
}

// Shardeado es la variante con estado compartido: un mapa partido en N
// shards, cada uno con su candado. Agregar es seguro desde varias goroutines.
//
// Existe para contrastarla con Parcial+Fusionar: acá la sección crítica es
// real y el número de shards es la perilla que decide cuánta contención hay.
type Shardeado struct {
	shards []*shard
}

type shard struct {
	mu     sync.Mutex
	grupos conjuntos
}

// NuevoShardeado crea el acumulador con n shards. n<1 se trata como 1.
func NuevoShardeado(n int) *Shardeado {
	if n < 1 {
		n = 1
	}
	s := &Shardeado{shards: make([]*shard, n)}
	for i := range s.shards {
		s.shards[i] = &shard{grupos: make(conjuntos, 1024)}
	}
	return s
}

// indice reparte por hash del grupo, no del donante: todos los registros de
// un mismo receptor-año tienen que caer en el mismo shard o el conjunto de
// donantes quedaría partido y perderíamos aristas, igual que en Fusionar.
func (s *Shardeado) indice(g Grupo) int {
	h := fnv.New32a()
	_, _ = h.Write([]byte(g.Receptor))
	_, _ = h.Write([]byte{0})
	_, _ = h.Write([]byte(g.Anio))
	return int(h.Sum32() % uint32(len(s.shards)))
}

// Agregar es seguro desde múltiples goroutines.
func (s *Shardeado) Agregar(r Registro) {
	g := Grupo{Receptor: r.Receptor, Anio: r.Anio}
	sh := s.shards[s.indice(g)]
	sh.mu.Lock()
	sh.grupos.agregar(r)
	sh.mu.Unlock()
}

// Red materializa la red juntando los shards. Se llama cuando ya nadie agrega.
//
// Acá sí se pueden sumar las redes por shard sin perder aristas, porque el
// sharding es por grupo: un grupo vive entero en un shard.
func (s *Shardeado) Red() Red {
	out := make(Red)
	for _, sh := range s.shards {
		for a, n := range sh.grupos.red() {
			out[a] += n
		}
	}
	return out
}

// Peso devuelve el peso de un par en cualquier orden.
func (r Red) Peso(x, y string) int { return r[NuevaArista(x, y)] }

// Top devuelve las n aristas de mayor peso, desempatando por nombre para que
// el resultado sea determinista.
func (r Red) Top(n int) []ParPeso {
	out := make([]ParPeso, 0, len(r))
	for a, p := range r {
		out = append(out, ParPeso{Arista: a, Peso: p})
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].Peso != out[j].Peso {
			return out[i].Peso > out[j].Peso
		}
		if out[i].A != out[j].A {
			return out[i].A < out[j].A
		}
		return out[i].B < out[j].B
	})
	if n > 0 && n < len(out) {
		out = out[:n]
	}
	return out
}

// ParPeso es una arista con su peso, para reportes ordenados.
type ParPeso struct {
	Arista
	Peso int
}

var (
	_ Acumulador = (*Parcial)(nil)
	_ Acumulador = (*Shardeado)(nil)
)

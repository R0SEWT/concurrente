package main

import (
	"fmt"
	"io"
	"strings"
	"time"
)

// barra es la barra de progreso de la CLI. Escribe en stderr para no mezclarse
// con el resultado, que va a stdout y puede ser JSON. Se activa con -progreso:
// sirve para verlo correr en vivo (en un celular, por ejemplo), no para medir.
type barra struct {
	w      io.Writer
	total  int
	ancho  int
	inicio time.Time
	ultimo time.Time
}

func nuevaBarra(w io.Writer, total int) *barra {
	// 16 celdas: la línea entera cabe en las ~50 columnas de un celular en vertical.
	return &barra{w: w, total: total, ancho: 16, inicio: time.Now(), ultimo: time.Now()}
}

// fase anuncia una etapa terminada (carga, inicialización) con su duración.
func (b *barra) fase(formato string, args ...any) {
	ahora := time.Now()
	fmt.Fprintf(b.w, "\r\033[K  \033[36m▸\033[0m %s \033[90m· %.1f s\033[0m\n",
		fmt.Sprintf(formato, args...), ahora.Sub(b.ultimo).Seconds())
	b.ultimo = ahora
}

// titulo anuncia la etapa que empieza y de la que la barra va a informar.
func (b *barra) titulo(formato string, args ...any) {
	fmt.Fprintf(b.w, "  \033[36m▸\033[0m %s\n", fmt.Sprintf(formato, args...))
	b.ultimo = time.Now()
}

// iterar es el callback para kmeans.Opciones.AlIterar.
func (b *barra) iterar(it int, inercia float64) {
	lleno := it * b.ancho / b.total
	if lleno > b.ancho {
		lleno = b.ancho
	}
	fmt.Fprintf(b.w, "\r\033[K  \033[32m%s\033[90m%s\033[0m %3d%% \033[1m%d/%d\033[0m J=%.3e %.1fs",
		strings.Repeat("█", lleno), strings.Repeat("░", b.ancho-lleno),
		100*it/b.total, it, b.total, inercia, time.Since(b.ultimo).Seconds())
	if it == b.total {
		fmt.Fprintln(b.w)
	}
}

// fin cierra la barra si el algoritmo paró antes del tope (por tolerancia).
func (b *barra) fin(iteraciones int, paro string) {
	if iteraciones < b.total {
		fmt.Fprintf(b.w, "\n    \033[90mparó en %d/%d por %s\033[0m\n", iteraciones, b.total, paro)
	}
	fmt.Fprintf(b.w, "  \033[36m▸\033[0m listo \033[90m· %.1f s en total\033[0m\n\n", time.Since(b.inicio).Seconds())
}

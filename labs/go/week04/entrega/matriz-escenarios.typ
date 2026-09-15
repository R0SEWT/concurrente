// Entrega de la semana 4: matriz de escenarios del algoritmo C (Ben-Ari 2.18).
// Las tablas y el gráfico salen de ../grafico/escenarios.csv, que exporta el
// mismo modelo Go que verifican los tests. Se arma con ./build.sh.

#set document(title: "Matriz de escenarios — algoritmo C", author: "Rody Vilchez")
#set page(paper: "a4", margin: (x: 1.8cm, y: 2cm), numbering: "1 / 1")
#set text(lang: "es", size: 10pt)
#set par(justify: true)
#set heading(numbering: "1.")
#show heading.where(level: 1): set block(above: 1.6em, below: 0.8em)
#show raw.where(block: true): set text(size: 7.5pt)
#show raw.where(block: true): block.with(fill: luma(246), inset: 8pt, radius: 3pt, width: 100%)

#let filas = csv("../grafico/escenarios.csv", row-type: dictionary)
#let codigo = (
  p1: "while n < 1", p2: "n <- n + 1",
  q1: "while n >= 0", q2: "n <- n - 1",
)
#let pasos(nombre) = filas.filter(f => f.escenario == nombre)

#let matriz(nombre, vuelta: none) = {
  let ps = pasos(nombre)
  table(
    columns: (auto, 1fr, 1fr, auto),
    align: (right, left, left, right),
    stroke: none,
    inset: (x: 6pt, y: 3.5pt),
    fill: (_, y) => if vuelta != none and y > 0 and calc.rem(calc.quo(y - 1, vuelta), 2) == 0 { luma(243) },
    table.hline(),
    table.header([*\#*], [*p*], [*q*], [*n*]),
    table.hline(stroke: 0.5pt),
    ..ps.map(f => {
      let texto = [#raw(f.etiqueta) #raw(codigo.at(f.etiqueta)) — #f.detalle]
      let celda = if f.detalle.contains("falso") { strong(texto) } else { texto }
      (
        f.paso,
        if f.proceso == "p" { celda } else { [] },
        if f.proceso == "q" { celda } else { [] },
        strong(f.n),
      )
    }).flatten(),
    table.hline(),
  )
}

#let resumen(nombre) = {
  let ps = pasos(nombre)
  let iter(proc) = ps.filter(f => f.etiqueta == proc + "2").len()
  let termina(proc) = if ps.any(f => f.proceso == proc and f.detalle.contains("falso")) { "sí" } else { "no" }
  (
    raw(ps.map(f => f.proceso).join()),
    str(ps.len()),
    str(iter("p")), str(iter("q")),
    termina("p"), termina("q"),
    ps.last().n,
  )
}

// ---------------------------------------------------------------------------

#align(center)[
  #text(size: 16pt, weight: "bold")[Matriz de escenarios — algoritmo concurrente C]\
  #v(2pt)
  #text(size: 10.5pt)[Ben-Ari, _Principles of Concurrent and Distributed Programming_, cap. 2, ejercicio 8]
]
#v(4pt)
#align(center, text(size: 9pt, fill: luma(80))[
  Programación Concurrente y Distribuida (1ACC0065) · NRC 8809 · 2026-20 \
  Docente: Carlos Alberto Jara Garcia · Alumno: Rody Vilchez (u202216562) · Semana 4 · 13/09/2026
])

= Algoritmo y enunciado

#grid(
  columns: (1fr, 1fr),
  gutter: 16pt,
  ```
  integer n <- 1

  p                      q
  p1: while n < 1        q1: while n >= 0
  p2:     n <- n + 1     q2:     n <- n - 1
  ```,
  [
    Construir escenarios en los que: *(a)* el bucle de `p` se ejecuta exactamente una vez;
    *(b)* exactamente tres veces; *(c)* los dos bucles se ejecutan infinitas veces.

    La guarda (`p1`, `q1`) y la asignación (`p2`, `q2`) son instrucciones *atómicas separadas*:
    entre evaluar `n < 1` y hacer `n <- n + 1`, el otro proceso puede cambiar `n`.
  ],
)

Un escenario es la cadena de turnos: cada carácter indica qué proceso ejecuta su siguiente
instrucción. Los escenarios se ejecutan con un modelo determinista en Go
(`week04/escenarios.go`), verificado con `go test -race`; las tablas y el gráfico de este
documento se generan desde ese modelo, así que no pueden contradecir al código.

#let r = ("8a", "8b", "8c").map(resumen)
#figure(
  table(
    columns: 8,
    align: (left, left, center, center, center, center, center, center),
    stroke: none,
    inset: (x: 6pt, y: 4pt),
    table.hline(),
    table.header([*Ejercicio*], [*Turnos*], [*Pasos*], [*Iter. p*], [*Iter. q*],
      [*p termina*], [*q termina*], [*n final*]),
    table.hline(stroke: 0.5pt),
    [8(a)], ..r.at(0),
    [8(b)], ..r.at(1),
    [8(c) · 3 vueltas], ..r.at(2),
    table.hline(),
  ),
  caption: [Resumen de los tres escenarios. En 8(c) se muestran tres repeticiones de `qqpp`.],
)

#figure(
  image("../grafico/escenarios.svg", width: 100%),
  caption: [Valor de `n` después de cada instrucción. Azul/círculo = `p`, naranja/cuadrado = `q`;
    marca hueca = evaluación de guarda, rellena = asignación.],
)

= Matriz de escenarios

Cada fila es una instrucción; la columna `n` es el valor de la variable compartida
*después* de ejecutarla. En negrita, la guarda que resulta falsa y termina al proceso.

== 8(a) · el bucle de `p` se ejecuta exactamente una vez

#matriz("8a")

`q` entra a su bucle y deja `n = 0`, así que la guarda de `p` ahora es verdadera. `p`
incrementa una vez y `n` vuelve a 1, con lo que su guarda se vuelve falsa y termina. `q`
sigue solo hasta `n = -1`.

== 8(b) · el bucle de `p` se ejecuta exactamente tres veces

#matriz("8b")

El mismo patrón tres veces: cada vez que `q` baja `n` a 0, `p` lo sube a 1. En la cuarta
evaluación `p` encuentra `n = 1` porque `q` no volvió a decrementar antes, y termina. El
número de iteraciones de `p` no es una propiedad del programa: lo elige el entrelazado.

== 8(c) · los dos bucles se ejecutan infinitas veces

#matriz("8c", vuelta: 4)

Cada vuelta `qqpp` (bandas alternadas) deja `n = 1` y a los dos procesos otra vez en su
guarda (`p1`, `q1`): el estado es idéntico al inicial y en la vuelta iteraron los dos
bucles, sin que ninguno termine. Por inducción, repetir la vuelta siempre es posible, así
que el escenario infinito existe. Ninguna guarda se viola nunca (_safety_), y sin embargo el
programa puede no terminar (_liveness_). La verificación sobre *todos* los entrelazados, no
solo estos tres, corresponde a Spin.

= La carrera real con goroutines

El modelo anterior elige el entrelazado a mano. `week04/cmd/race` ejecuta el mismo
algoritmo con dos goroutines sobre `n` sin sincronización; el detector de carreras de Go la
reporta y el número de iteraciones cambia entre corridas. Salida de
`go run -race ./week04/cmd/race` (recortada):

#let race = read("race.txt").trim().split("\n")
#raw(
  if race.len() <= 30 { race.join("\n") } else {
    (race.slice(0, 20) + ("   [...]",) + race.slice(race.len() - 6)).join("\n")
  },
  block: true,
)

= Verificación

```
cd labs/go
go test -race ./week04/...        # 12 tests: escenarios 8(a-c), traza, tablas y CSV
go run ./week04/cmd/escenarios    # regenera ESCENARIOS.md (un test falla si queda viejo)
go run -race ./week04/cmd/race    # la carrera de datos real
```

#pagebreak()
= Anexo: código Go

== `week04/escenarios.go` — modelo determinista

#raw(read("../escenarios.go"), lang: "go", block: true)

== `week04/escenarios_test.go` — tests

#raw(read("../escenarios_test.go"), lang: "go", block: true)

== `week04/cmd/race/main.go` — versión con goroutines

#raw(read("../cmd/race/main.go"), lang: "go", block: true)

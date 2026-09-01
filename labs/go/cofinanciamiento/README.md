# cofinanciamiento — red de co-financiamiento entre donantes

Paquete del **trabajo del curso** (TB1 y TB2). Vive acá y no en `weekNN/` porque el
mismo código se usa en las dos unidades: la U1 lo trabaja dentro de un proceso y la
U2 lo reparte entre nodos.

## Qué hace esto, en cuatro pasos

Empieza por acá. El resto del README es detalle.

Tenemos 1,5 millones de proyectos de ayuda al desarrollo. Cada uno dice **quién dio**
plata, **quién la recibió** y **en qué año**. Nada más que eso hace falta.

1. Agrupamos por *(receptor, año)*.
2. De cada grupo nos quedamos con la **lista de donantes distintos**. Distintos: si
   Japón puso 40 proyectos en Perú 2010, cuenta una vez.
3. Dentro de cada grupo, **cada par de donantes suma 1**.
4. Sumamos sobre todos los grupos.

```
Perú 2010    → {USA, Japón, España}   USA-Japón +1 · USA-España +1 · Japón-España +1
Perú 2011    → {USA, Japón}           USA-Japón +1
Bolivia 2010 → {USA, Alemania}        USA-Alemania +1

resultado:  USA-Japón 2 · USA-España 1 · Japón-España 1 · USA-Alemania 1
```

Eso es todo el cálculo. Lo difícil no es la fórmula: es hacerlo rápido repartiendo
el archivo entre goroutines **sin equivocarse**, y ahí está el trabajo del curso.

## Por qué es un buen problema para el curso

Tiene una trampa que no falla ruidosamente. Si repartimos el archivo en pedazos y
cada worker arma **su propia red**, y después sumamos las redes:

```
worker 1 leyó:  Perú 2010 → USA      → su red: (vacía, un solo donante)
worker 2 leyó:  Perú 2010 → Japón    → su red: (vacía, un solo donante)
suma de redes:  (vacía)              ← perdimos la arista USA-Japón
```

Ninguno de los dos vio a los dos juntos. El programa no falla, no tira error: da un
número plausible y equivocado.

La solución es fusionar **una etapa antes**: cada worker guarda el *conjunto de
donantes por grupo*, se unen los conjuntos, y recién ahí se arman los pares. La
unión de conjuntos sí se puede repartir; la suma de redes no.

Está fijado en el test `TestFusionarRedesPierdeAristas` para que nadie lo
reintroduzca. Por la misma razón `Shardeado` reparte por **grupo** y no por donante:
un receptor-año tiene que vivir entero en un solo shard.

## Qué queremos mostrar

**Lo técnico**, que es lo que se evalúa:

1. Paralelizar no cambia el resultado — cuatro configuraciones dan 3 727 aristas idénticas.
2. La etapa que se puede repartir es el conjunto, no la red (la trampa de arriba).
3. El escalado no es monótono y los candados no siempre pierden (ver la tabla más abajo).

**Lo sustantivo**, que es el pretexto que le da sentido: la proliferación de donantes
en la ayuda al desarrollo. Cuántos donantes distintos caen sobre el mismo receptor el
mismo año, y con quién se solapa cada uno.

## Cómo correrlo

```bash
go test -race ./cofinanciamiento/...                              # los tests, sin bajar nada

curl -L -o aiddata.csv https://dataverse.harvard.edu/api/access/datafile/5794842
go run ./cofinanciamiento/cmd/red -csv aiddata.csv -workers 8
go run ./cofinanciamiento/cmd/red -csv aiddata.csv -decadas -top 0
go run ./cofinanciamiento/cmd/red -csv aiddata.csv -sector AGRIC -top 10
```

`-modo parciales|shardeado` elige la estrategia, `-workers` cuántas goroutines,
`-shards` la perilla de contención del modo shardeado.

## El dataset

`AidDataCoreFull_ResearchRelease_Level1_v3.1.csv` — 1,23 GB, 1 561 039 registros,
68 columnas, 1947-2013, 96 donantes, 252 receptores. `doi:10.7910/DVN/QNHR2D`,
descarga libre. **No está versionado**, son 1,23 GB.

Tres propiedades del archivo que el diseño da por ciertas, las tres verificadas:

- **Ningún campo citado contiene saltos de línea** (1 561 040 líneas físicas − 1
  cabecera = 1 561 039 registros). Por eso cortar el archivo en cualquier `\n` es
  seguro. Sí hay comas dentro de comillas, así que el parseo de campos no es trivial.
- **Registros de tamaño muy desigual**: `long_description` llega a 48 220 caracteres.
  Tramos de igual tamaño en bytes dan hasta **1,42x** de diferencia en cantidad de filas.
- **Claves sesgadas**: Estados Unidos es el 13,3% de las filas y `Africa, South of
  Sahara` el 31,3%. Repartir *por clave* desbalancea; repartir por bytes no, pero
  obliga a fusionar.

## Las piezas

| pieza | qué es |
|---|---|
| `Parcial` | acumulador de una sola goroutine. Referencia secuencial y estado por worker |
| `Shardeado` | mapa partido en N shards con candado por shard. `Agregar` es seguro concurrentemente |
| `Fusionar` | une parciales por unión de conjuntos de donantes, no por suma de redes |
| `PorDecada` | resume cuántos donantes concurren por receptor-año, por década |
| `cmd/red` | corre sobre el CSV real con `io.SectionReader`, sin cargarlo a RAM |

## Resultados

**La red.** 3 727 aristas de las 4 560 posibles entre 96 donantes — 82% de densidad.
Casi todos los donantes se cruzaron con casi todos alguna vez, así que lo informativo
es el peso, no que la arista exista. El par más pesado es Canadá–Estados Unidos con
3 972 receptor-años compartidos.

**La fragmentación** (`-decadas`), que es la otra cara: en vez de mirar pares, mira
el tamaño del grupo que los produce.

| década | grupos | media | mediana | máx |
|---:|---:|---:|---:|---:|
| 1960s | 382 | 1,2 | 1 | 4 |
| 1970s | 1 361 | 5,2 | 3 | 22 |
| 1980s | 1 733 | 8,3 | 8 | 24 |
| 1990s | 2 020 | 11,4 | 11 | 31 |
| 2000s | 2 038 | 20,0 | 22 | 47 |
| 2010s | 701 | 26,2 | 29 | 48 |

De ~1 donante por receptor-año en los 60 a 26 en los 2010.

**Ojo con leer eso como proliferación real.** Parte de la subida es cobertura de
reporte: AidData registra más donantes conforme avanza el tiempo, y los 2010s son una
década incompleta — termina en 2013 y tiene solo 701 grupos. La tendencia es
sugerente, no demostrada, y conviene decirlo antes de que lo pregunten.

**El recorte agrícola** (`-sector AGRIC`, 71 332 proyectos) da 1 599 aristas y el par
más pesado pasa a ser Japón–Estados Unidos con 917. La fragmentación agrícola sigue la
misma forma pero es **la mitad**: 6,8 donantes por receptor-año en los 2010 contra
26,2 del total. Perú es el 4.º receptor mundial de proyectos agrícolas y Bolivia el 5.º.

> `-sector` es un substring simple sobre `aiddata_sector_name`. `AGRIC` deja fuera
> silvicultura y pesca; con esas tres el universo sube a 87 601 proyectos.

## Línea base de rendimiento

Una corrida por celda, laptop de 14 núcleos, archivo en caché de página. Hay ruido
entre corridas: es punto de partida, no resultado.

| workers | `parciales` | `shardeado` |
|--------:|------------:|------------:|
| 1 | 3,88 s | 4,76 s |
| 2 | 1,70 s | 1,82 s |
| 4 | 1,12 s | 1,05 s |
| 8 | **0,80 s** | 0,69 s |
| 14 | 0,87 s | **0,65 s** |

Los cuatro modos producen exactamente el mismo resultado (1 561 039 registros,
3 727 aristas). Ese es el oráculo: no hay tolerancia numérica, es igualdad exacta.

Dos cosas que contradicen la intuición y son el material del informe:

1. **`shardeado` gana pese a tener candados.** Arranca peor con 1 worker (4,76 s
   contra 3,88 s: el candado se paga aunque nadie compita) pero escala mejor. El
   costo de `Fusionar` crece con el número de workers y termina dominando.
2. **`parciales` regresa entre 8 y 14 workers** (0,80 → 0,87 s) por lo mismo. El
   escalado no es monótono y el punto de quiebre depende del tamaño de la fusión,
   no del parseo.

## Pendiente

- U1 / TB1: medir la contención de `Shardeado` variando el número de shards, y
  comparar reparto estático contra work-stealing sobre el desbalance de 1,42x.
- U2 / TB2: repartir los tramos entre nodos, fusionar por árbol en vez de en un
  solo punto, y resolver el top-K global — que no es la unión de los top-K locales.
- Spin: modelar el reparto de tramos y verificar que ninguno se pierde, ninguno se
  procesa dos veces y no hay deadlock.

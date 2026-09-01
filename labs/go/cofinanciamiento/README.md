# cofinanciamiento — red de co-financiamiento entre donantes

Paquete del **trabajo del curso** (TB1 y TB2), no de una semana. Vive acá y no en
`weekNN/` porque el mismo código se usa en las dos unidades: la U1 lo trabaja
dentro de un proceso y la U2 lo reparte entre nodos.

## Objeto de estudio

Dos donantes **co-financian** cuando aparecen en el mismo receptor y el mismo año.
Contando esas coincidencias sobre AidData sale un grafo no dirigido de donantes,
y la pregunta es la proliferación institucional en la ayuda al desarrollo: cuántos
donantes concurren sobre un mismo receptor, con quién se solapa cada uno, y si eso
cambió entre 1947 y 2013.

Medido sobre el dataset completo: **12,3 donantes distintos por (receptor, año)**
en promedio sobre 8 452 pares receptor-año, con un máximo de **48**. La red tiene
**3 727 aristas de las 4 560 posibles** entre 96 donantes — 82% de densidad, o sea
casi todos los donantes se han cruzado con casi todos alguna vez. Lo interesante
no es la existencia de la arista sino su peso.

Recorte del sector agrícola (`-sector AGRIC`, 87 601 proyectos): la red baja a
**1 599 aristas** y el par más pesado pasa a ser Japón–Estados Unidos con 917
receptor-años compartidos. Perú es el 4.º receptor mundial de proyectos agrícolas
(1 969) y Bolivia el 5.º (1 814).

## Dataset

`AidDataCoreFull_ResearchRelease_Level1_v3.1.csv` — 1,23 GB, 1 561 039 registros,
68 columnas, 1947-2013. No está versionado.

```bash
curl -L -o aiddata.csv https://dataverse.harvard.edu/api/access/datafile/5794842
# doi:10.7910/DVN/QNHR2D — descarga libre, sin guestbook
```

Propiedades verificadas del archivo que el diseño da por ciertas:

- **Ningún campo citado contiene saltos de línea** (1 561 040 líneas físicas − 1
  cabecera = 1 561 039 registros). Por eso cortar el archivo en cualquier `\n` es
  seguro. Sí hay comas dentro de comillas, así que el parseo de campos no es trivial.
- **Registros de tamaño muy desigual**: `long_description` llega a 48 220 caracteres.
  Tramos de igual tamaño en bytes dan hasta **1,42x** de diferencia en cantidad de filas.
- **Claves sesgadas**: Estados Unidos es el 13,3% de las filas y `Africa, South of
  Sahara` el 31,3%. Repartir *por clave* desbalancea; repartir por bytes no, pero
  obliga a fusionar.

## Diseño

Tres piezas, y la tercera es la que importa:

| pieza | qué es |
|---|---|
| `Parcial` | acumulador de una sola goroutine. Referencia secuencial y estado por worker |
| `Shardeado` | mapa partido en N shards con candado por shard. `Agregar` es seguro concurrentemente |
| `Fusionar` | une parciales **por unión de conjuntos de donantes**, no por suma de redes |

La sutileza: el estado intermedio que se puede repartir es *el conjunto de donantes
por grupo*, no la red ya construida. Si el chunk 1 vio a USA en (Perú, 2010) y el
chunk 2 vio a Japón en el mismo grupo, ninguno produce la arista USA–Japón por su
cuenta y sumar sus redes la pierde. Está escrito como test para que no se
reintroduzca: `TestFusionarRedesPierdeAristas`.

Por la misma razón `Shardeado` hashea el **grupo** y no el donante: un receptor-año
tiene que vivir entero en un shard.

## Uso

```bash
go test -race ./cofinanciamiento/...
go run ./cofinanciamiento/cmd/red -csv ~/data/aiddata.csv -workers 8 -modo shardeado
go run ./cofinanciamiento/cmd/red -csv ~/data/aiddata.csv -sector AGRIC -top 10
```

## Línea base medida

Una corrida por celda, laptop de 14 núcleos, archivo en caché de página. Hay ruido
entre corridas: tómalo como punto de partida, no como resultado.

| workers | `parciales` | `shardeado` |
|--------:|------------:|------------:|
| 1 | 3,88 s | 4,76 s |
| 2 | 1,70 s | 1,82 s |
| 4 | 1,12 s | 1,05 s |
| 8 | **0,80 s** | 0,69 s |
| 14 | 0,87 s | **0,65 s** |

Los cuatro modos producen exactamente el mismo resultado (1 561 039 registros,
3 727 aristas), que es el oráculo.

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

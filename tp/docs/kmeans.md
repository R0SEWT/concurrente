# K-means concurrente sobre el gold de NYC TLC (diseño)

Diseño de referencia para la PC2: qué se implementa en Go, con qué contrato numérico y qué se mide.
Es el documento que cierra las ambigüedades antes de escribir código, para que el benchmark compare
dos implementaciones del **mismo** algoritmo y no dos algoritmos distintos.

Continúa el diseño publicado en el informe de la PC1 (`tp/informe/pc1`, sección «Diseño concurrente
de referencia», Algoritmo 1 y Figura «Worker pool para una iteración de Lloyd»). Lo que aquí se
decide, se decide una vez: cambiarlo después obliga a repetir las corridas.

Alcance de la PC2: **Lloyd en CPU, float64, sobre el gold de yellow 2024-01**. GPU y más meses son
una decisión aparte (`concurrente-3r8.8`) que no bloquea la entrega.

## 1. Entrada

`tp/data/gold/yellow_2024-01_features.csv`: 2 831 486 viajes, 9 columnas, sha256
`a3ad5205201b05dd9359e8352b9f79b46c5c3283579dfde49d49383c56a14750`.

| Columna | Rol |
|---|---|
| `viaje_id` | Identidad de la fila en silver. No es feature. |
| `PULocationID`, `DOLocationID` | Zonas. **No son features**: un ID no es una coordenada. Sirven para agregar las asignaciones por zona después del clustering. |
| `hora_sin`, `hora_cos`, `dia_sin`, `dia_cos` | Hora del día y día de la semana en el círculo. |
| `log_duracion_z`, `log_distancia_z` | `log1p` y z-score (desviación poblacional). |

Son **cuatro componentes seno/coseno y dos transformaciones `log1p` estandarizadas**, no seis
z-scores. Las varianzas medidas son 0,389 / 0,487 / 0,509 / 0,487 / 1,0 / 1,0; por concepto suman
hora 0,876, día 0,996, duración 1,0 y distancia 1,0, así que los cuatro conceptos pesan parecido en
la distancia euclídea. Seno y coseno **no** se estandarizan por separado: eso deformaría el círculo
y rompería la propiedad de que las 23:00 y la 01:00 estén cerca.

Duración y distancia están correlacionadas (r = 0,833): en ese bloque de dos dimensiones, las
direcciones principales tienen varianza 1,833 y 0,167, es decir, ambas refuerzan un mismo factor de
«tamaño del viaje». Se conservan las dos a propósito, porque dos viajes de la misma distancia y
distinta duración son tipos de viaje distintos (tráfico), que es justo lo que el caso quiere
distinguir. Queda como sensibilidad opcional sobre una muestra comparar contra quitar una de las
dos. El CSV se exporta con seis decimales; Go lo lee como `float64`.

## 2. Algoritmo

Lloyd, con la iteración del Algoritmo 1 de la PC1: asignar cada viaje al centroide más cercano,
luego recalcular cada centroide como la media de los viajes que se le asignaron.

### Contrato numérico

Todo esto vale igual para la versión secuencial y la concurrente:

- **Distancia**: euclídea al cuadrado sobre las 6 features (no hace falta la raíz para comparar).
- **Desempate**: si dos centroides empatan, gana el de **menor índice**.
- **Inicialización**: k-means++ con semilla fija. Se ejecuta **una vez**, los centroides iniciales
  se **materializan** en disco con su sha256, y ambas versiones parten de ese archivo. La misma
  semilla no garantiza los mismos centroides si cambia el generador o el orden en que se consume;
  el archivo sí.
- **Criterio de parada**: `max_j ||μ_j(t) − μ_j(t−1)||∞ ≤ tol_abs + tol_rel · max_j ||μ_j(t−1)||∞`,
  con `tol_abs = 1e-9` y `tol_rel = 1e-9`, o `max_iter = 100`. Lo que ocurra primero. El resultado
  registra cuál de los dos paró la corrida.
- **Cluster vacío**: conserva su centroide anterior. No se re-siembra (re-sembrar con el punto más
  lejano haría que la corrida dependa del orden de recorrido).
- **Puntos idénticos y suma de probabilidades cero** en k-means++: si `sum(D²) = 0`, todos los
  puntos restantes coinciden con algún centroide ya elegido; se completan los centroides faltantes
  repitiendo puntos distintos si existen y, si no, se reduce k y se registra.
- **Entradas inválidas**: se rechazan `NaN`/`Inf` en las features, y `k ≤ 0`, `workers ≤ 0`,
  `max_iter ≤ 0`, `k > n`.
- **Inercia**: `J(t) = Σ_i ||x_i − μ_{a(i)}(t)||²` con los centroides **que produjeron esa
  asignación**, es decir los de la iteración t antes de actualizarlos. Es la inercia que se acumula
  gratis durante la asignación. La **inercia final que se reporta** se recalcula con los centroides
  finales, en una pasada extra, para que el número publicado corresponda al modelo publicado. El
  pseudocódigo de la PC1 devolvía centroides actualizados junto a la inercia de los anteriores; esa
  ambigüedad queda resuelta acá.

### Elección de k

k ∈ {4, 8, 12, 16}, con 3 semillas, sobre una **muestra reproducible** (200 000 viajes, muestreo
sistemático por `viaje_id`). Se compara inercia (codo) y silueta; la silueta se calcula sobre una
muestra menor (10 000 puntos), porque es O(n²) y sobre 2,8 millones es inviable. El k elegido se
**congela** antes de las corridas de benchmark: k no cambia junto con P.

## 3. Versión secuencial

Un solo hilo, mismo contrato. Es el `T_secuencial` del speedup: la referencia honesta es el mismo
algoritmo sin goroutines, no una versión degradada ni una librería ajena.

## 4. Versión concurrente: worker pool

```
       ┌──────────── canal de chunks (buffer) ────────────┐
main → │ [0,c) [c,2c) [2c,3c) ...                         │ → P workers (goroutines fijas)
       └──────────────────────────────────────────────────┘
             cada worker: lee chunk → asigna → acumula en SU parcial
                                  ↓
                      barrera (sync.WaitGroup)
                                  ↓
           reducción en orden de chunk → centroides nuevos → siguiente iteración
```

- **Pool persistente**: las P goroutines se crean una vez y viven todas las iteraciones. No se
  relanzan por iteración.
- **Los centroides son de solo lectura durante la asignación.** Ningún worker los escribe. Por eso
  el bucle caliente no necesita `sync.Mutex`.
- **Acumuladores parciales por chunk**, no por worker: cada chunk produce sus sumas `s_j`, conteos
  `n_j` e inercia parcial. La reducción los suma **en orden de índice de chunk**.
- **La sincronización es la barrera** (`sync.WaitGroup`) al final de cada iteración, más el canal
  que reparte los chunks. Nada más.
- **Chunk**: tamaño variable del experimento (la PC1 lo comprometió). Con muchos más chunks que
  workers, el reparto por canal equilibra la carga solo.

### Por qué la reducción va en orden de chunk

Sumar en punto flotante no es asociativo: el orden cambia los últimos dígitos. Si cada worker
acumulara todo lo que le toca, el resultado dependería de **qué chunks le tocaron**, o sea del
planificador, y dos corridas idénticas darían números distintos. Acumulando por chunk y reduciendo
en orden de índice, el resultado es el mismo en toda corrida con el mismo tamaño de chunk,
**independiente de P y del planificador**. Cuesta `K·(d+1)` floats por chunk, que con 1000 chunks,
k=8 y d=6 son unos 56 000 floats: irrelevante frente a los 136 MB de datos.

Contra la versión secuencial sigue habiendo diferencia de orden, así que la equivalencia se
comprueba **con tolerancia** (como comprometió la PC1), no bit a bit.

### Variante con mutex

Compromiso de la PC1: una variante con acumuladores compartidos protegidos por `sync.Mutex`, para
cuantificar el costo de la contención. Es un contraste chico, sobre una muestra; no es la versión
que se mide en el benchmark principal. Si no entra por tiempo, se retira explícitamente en el
informe (`concurrente-3r8.12`), no en silencio.

## 5. Qué se compara y cómo

- **Equivalencia seq/conc**: mismos centroides iniciales, mismo k, mismas iteraciones. Se comparan
  asignaciones, centroides (con correspondencia de etiquetas si hace falta) e inercia, con
  tolerancia explícita. Inercia parecida **no** demuestra la misma partición: se comparan también
  las etiquetas.
- **P = 1 en la versión concurrente debe dar el mismo resultado que la secuencial**, dentro de la
  misma tolerancia.
- **Casos borde con test**: `n < P`, chunk mayor que n, cluster que queda vacío, todos los puntos
  iguales, k = 1, k = n.

## 6. Qué no entra en la PC2

Se mencionan en el informe como alternativas conocidas, sin prometer resultados:

- **SoA** en vez del arreglo plano por filas: su ventaja depende del bucle y del compilador.
- **float32**: no hay presión de memoria que lo justifique (136 MB en float64).
- **Caché binaria** del gold con `encoding/binary`: solo si el parseo del CSV domina el tiempo de
  experimentación.
- **Elkan y Hamerly**: reducen evaluaciones de distancia con cotas, pero cambian el algoritmo; Lloyd
  se mantiene para que la comparación mida concurrencia y no otra cosa.
- **Mini-batch**: cambia el trabajo y la aproximación. Fuera.
- **k-means‖**: inicialización escalable; se menciona y se difiere.

## 7. Medición (resumen)

El protocolo completo está en `concurrente-3r8.9`. Lo que el diseño garantiza para que ese
protocolo sea aplicable:

- Fases cronometradas por separado: **carga**, **inicialización**, **iteraciones**, **total**.
- El tiempo concurrente incluye su sincronización y el ciclo de vida del pool.
- Estado reiniciado entre corridas.
- Cada resultado trae sus metadatos (commit, sha256 del gold, hash de centroides iniciales, k,
  semilla, workers, `GOMAXPROCS`, chunk, versión de Go, máquina).
- La laptop tiene **4 núcleos físicos y 8 hilos**: la curva principal va a P ∈ {1,2,4,8} y el tramo
  4→8 se rotula como SMT, no como «el doble de núcleos».

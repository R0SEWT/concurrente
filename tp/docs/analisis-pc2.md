# Análisis de rendimiento del K-means concurrente (PC2)

Todo lo que sigue sale de `tp/reports/benchmark_*.json` y se regenera con
`tp/scripts/analisis_benchmark.py`. Ninguna cifra de este documento se
transcribió a mano.

## 1. Cómo se midió

El protocolo está en `tp/kmeans/cmd/benchmark` y no se decide en tiempo de
corrida: 20 repeticiones medidas por configuración más una ronda de
calentamiento que se descarta, orden de las configuraciones **barajado en cada
ronda**, media recortada simétrica al 10 % por extremo y bootstrap de 2000
réplicas para el intervalo del speedup.

Barajar el orden no es un detalle: la caché de disco y el turbo del procesador
premian a la configuración que corre segunda, así que medir siempre «primero
secuencial, después concurrente» infla el speedup.

El speedup es el **cociente de las medias recortadas**, no el promedio de los
cocientes por corrida. Se mide solo el clustering: la carga del CSV y la
inicialización quedan fuera, y se reportan aparte.

Dos experimentos independientes:

- **iteraciones fijas** (10, con tolerancia 0): compara el mismo trabajo;
- **hasta convergencia** (tope 60, tolerancia 1e-9): compara el tiempo hasta la
  misma solución.

Ambos dan lo mismo dentro del ruido —5,82x contra 5,77x con P=8 sobre el dataset
completo— lo que descarta que el resultado dependa de cuál se elija.

## 2. Plataformas

| | Procesador | Núcleos físicos | Lógicos | RAM | Papel |
|---|---|---:|---:|---:|---|
| Máquina virtual en Proxmox (`fischl-ubuntusv`) | AMD Ryzen 5 7600X | 6 | 11 vCPU | 9 GB | corridas oficiales; ociosa |
| Laptop (`fedora`) | Intel Core i5-10210U | 4 | 8 (SMT) | 15 GB | recursos y contraste de SMT |

La distinción importa en las dos: las 11 vCPU de la máquina virtual son hilos de 6
núcleos físicos, y en la laptop pasar de P=4 a P=8 no agrega núcleos, agrega hilos
SMT sobre los mismos 4. Cualquier lectura de la curva que ignore eso atribuye al
algoritmo un techo que es del hardware.

## 3. Escalamiento fuerte

Dataset completo (2 831 486 viajes), k=8, 10 iteraciones, chunk 16384, en la máquina virtual:

| P | Media recortada | Speedup [IC 95 %] | Eficiencia | Karp–Flatt |
|---:|---:|:--|---:|---:|
| — (secuencial) | 1106,3 ms | — | — | — |
| 1 | 1141,2 ms | 0,97x [0,97, 0,97] | 97 % | — |
| 2 | 574,4 ms | 1,93x [1,92, 1,93] | 96 % | 0,038 |
| 4 | 291,0 ms | 3,80x [3,77, 3,82] | 95 % | 0,017 |
| 8 | 190,1 ms | 5,82x [5,73, 5,89] | 73 % | 0,054 |
| 16 | 177,1 ms | 6,25x [6,17, 6,31] | 39 % | 0,104 |

**La curva se aplana donde se acaban los núcleos físicos**, en las dos máquinas.
En la virtual, con 4 workers cada uno tiene su núcleo (95 % de eficiencia); con 8
ya hay más workers que los 6 núcleos físicos y la eficiencia cae a 73 %. En la
laptop, medida con el mismo protocolo de 20 repeticiones
(`reports/benchmark_laptop_i5.json`):

| P | Speedup [IC 95 %] | Eficiencia |
|---:|:--|---:|
| 2 | 1,83x [1,74, 1,87] | 91 % |
| 4 | 3,29x [3,17, 3,36] | 82 % |
| 8 | 3,27x [3,09, 3,35] | 41 % |
| 16 | 3,32x [3,08, 3,39] | 21 % |

Techo exacto en los 4 núcleos físicos: los hilos SMT no aportan nada, porque los
dos hilos de un núcleo compiten por las mismas unidades de coma flotante.

Los speedups son relativos al secuencial de cada máquina: dicen cuánto aprovecha
cada una sus núcleos, no cuál es más rápida. La virtual tarda 1106 ms en
secuencial y la laptop 2307 ms; esa diferencia es del procesador, no de la
concurrencia.

Dos lecturas que conviene no confundir:

- **P=1 concurrente es 3 % más lento que el secuencial** (0,97x, con intervalo
  que no toca el 1). Ese 3 % es el precio del pool y del troceado: crear las
  goroutines, repartir por canal y reducir los parciales. Es el costo fijo que
  el paralelismo tiene que recuperar antes de ganar algo.
- **P=16 sobre 11 vCPU** todavía mejora un poco (6,25x contra 5,82x) porque
  hay más chunks listos para ocupar cualquier núcleo que se libere, pero la
  eficiencia por worker se desploma a 39 %. No son 16 procesadores: es
  sobresuscripción.

## 4. Fracción serial efectiva

La columna Karp–Flatt de la tabla anterior es la fracción serial **efectiva**:
absorbe la sincronización, el desbalance y los efectos de memoria, y no es el
porcentaje de líneas secuenciales del programa.

Lo informativo es que **crece con P**: 0,017 con P=4, 0,054 con P=8, 0,104 con
P=16. Si el límite fuera una sección secuencial fija —la reducción, por
ejemplo— la fracción sería constante y el techo de Amdahl, una predicción útil.
Que crezca dice lo contrario: el costo que limita es el de coordinar, y aumenta
con la cantidad de workers. Por eso no publicamos un «techo de Amdahl» como
predicción: con e=0,017 daría 57x, que es un número sin sentido físico acá.

## 5. Punto de equilibrio

Barrido fino entre 10 mil y 100 mil viajes, en la máquina virtual, con el mismo protocolo:

| n | Speedup con P=4 [IC 95 %] | ¿Gana el concurrente? |
|---:|:--|:--|
| 1 000 | 0,94x [0,87, 1,01] | no |
| 10 000 | 0,93x [0,91, 0,96] | no, pierde |
| 15 000 | 0,98x [0,95, 1,01] | indistinguible de 1 |
| **20 000** | **1,09x [1,07, 1,12]** | **sí, primer intervalo entero sobre 1** |
| 30 000 | 1,73x [1,65, 1,77] | sí |
| 50 000 | 2,33x [2,22, 2,45] | sí |
| 70 000 | 2,96x [2,80, 3,11] | sí |
| 100 000 | 2,87x [2,81, 2,92] | sí |

El punto de equilibrio está en **n ≈ 20 000 viajes**: el primer tamaño cuyo
intervalo de confianza queda completamente por encima de 1. Debajo de 15 mil, el
concurrente **pierde** de forma consistente, y el intervalo lo confirma: no es
ruido, es que el costo fijo de armar el pool y repartir chunks supera el trabajo
útil de cada iteración.

Dicho de otro modo: con el dataset del trabajo —2,8 millones de viajes, 140 veces
el punto de equilibrio— la concurrencia está plenamente justificada, pero no lo
estaría para un mes de una flota chica.

## 6. Recursos de cómputo

Laptop, dataset completo, k=8, 10 iteraciones (`tp/scripts/medir_recursos.sh`).
Una corrida por configuración: acá interesa el consumo, que es estable, y no el
tiempo, que es lo que el benchmark mide con repeticiones.

| modo | P | Clustering | Heap tras carga | RSS máximo | CPU (usuario+sistema) | Núcleos efectivos |
|---|---:|---:|---:|---:|---:|---:|
| seq | — | 2344 ms | 349 MB | 453 MB | 5,05 s | 1,2 |
| conc | 1 | 2708 ms | 349 MB | 466 MB | 6,11 s | 1,2 |
| conc | 2 | 1451 ms | 349 MB | 452 MB | 6,26 s | 1,7 |
| conc | 4 | 813 ms | 349 MB | 532 MB | 6,71 s | 2,1 |
| conc | 8 | 742 ms | 349 MB | 531 MB | 9,07 s | 3,0 |
| conc | 16 | 741 ms | 349 MB | 531 MB | 9,07 s | 3,0 |

Tres cosas:

- **El pico de memoria es de la carga, no del clustering.** El heap tras leer el
  CSV son 349 MB para 130 MB de datos: la diferencia es el crecimiento del slice
  al ir agregando filas. Atribuirle ese pico al K-means sería un error de
  lectura. El RSS sube un poco con P (453 → 531 MB) por los acumuladores
  parciales y las pilas de las goroutines, pero la memoria la manda el dato.
- **El costo del paralelismo se ve en el tiempo de CPU**: sube de 5,05 s a
  9,07 s mientras el tiempo de pared baja. Se paga trabajo extra a cambio de
  terminar antes.
- **Los núcleos efectivos** (CPU dividido por tiempo de pared) llegan a 3,0 sobre
  4 núcleos físicos y no se mueven entre P=8 y P=16. Es una comprobación
  independiente del speedup, y coincide: ahí está el techo de la máquina.

La memoria del algoritmo, analíticamente: los datos son O(n·d), los acumuladores
parciales O(C·k·d) con C la cantidad de chunks, y las etiquetas O(n). Con chunk
16384 sobre el dataset completo son 173 chunks, o sea unos 66 KB de parciales:
el precio de que el resultado sea idéntico bit a bit para cualquier P es
despreciable en memoria.

## 7. Escalamiento débil

La pregunta del escalamiento fuerte es «¿cuánto más rápido resuelvo el mismo
problema?». La del débil es «¿cuánto más problema resuelvo en el mismo tiempo?»,
que es la que importa cuando el dataset crece. Se mantiene **n/P constante** en
353 936 viajes por worker:

| P | n | n/P | Tiempo | Eficiencia débil |
|---:|---:|---:|---:|---:|
| 1 | 353 936 | 353 936 | 147,5 ms | 100 % |
| 2 | 707 872 | 353 936 | 152,7 ms | 97 % |
| 4 | 1 415 743 | 353 935 | 150,1 ms | 98 % |
| 8 | 2 831 486 | 353 935 | 201,5 ms | 73 % |

Hasta P=4 el tiempo se mantiene plano: duplicar el problema y los workers al
mismo tiempo sale casi gratis. Con P=8 aparece el mismo costo de coordinación
que muestra la fracción efectiva de Karp–Flatt, y el tiempo sube 37 %.

El contraste con la misma carga sin paralelismo es lo que le da sentido:

| n | Con P=1 | Con P proporcional | |
|---:|---:|---:|:--|
| 707 872 | 296 ms | 153 ms (P=2) | |
| 1 415 743 | 577 ms | 150 ms (P=4) | |
| 2 831 486 | 1174 ms | 201 ms (P=8) | ocho veces el problema en 1,37 veces el tiempo |

Esto es lo que describe la ley de Gustafson, y conviene enunciarlo con cuidado:
**no** dice que el problema fijo escale linealmente —eso lo desmiente la sección
3— sino que, si el problema crece con los recursos, el tiempo se sostiene.

## 8. Tamaño de chunk

La PC1 comprometió el tamaño de bloque como variable del experimento, junto con
la cantidad de workers. Con P=8 fijo sobre el dataset completo, en la máquina virtual:

| Chunk | Cantidad de chunks | Tiempo | Speedup [IC 95 %] |
|---:|---:|---:|:--|
| 1 024 | 2766 | 190,0 ms | 5,84x [5,79, 5,88] |
| 4 096 | 692 | 188,5 ms | 5,87x [5,80, 5,93] |
| 16 384 | 173 | 196,0 ms | 5,71x [5,63, 5,83] |
| 65 536 | 44 | 199,5 ms | 5,56x [5,49, 5,63] |
| 262 144 | 11 | 232,4 ms | 4,79x [4,65, 4,91] |
| 1 048 576 | 3 | 439,0 ms | 2,54x [2,52, 2,56] |

El resultado contradice la intuición de que trocear fino cuesta caro: con 2766
chunks el rendimiento es el mejor del barrido, empatado con 692. Mandar un
índice por un canal buffereado es baratísimo comparado con procesar mil viajes.

El castigo aparece del otro lado. Con 3 chunks y 8 workers, **cinco workers se
quedan sin trabajo**: el speedup cae a 2,54x, que es aproximadamente lo que se
esperaría de tres workers ocupados. El problema del chunk grande no es el
tamaño, es que deja de haber suficientes unidades para repartir.

De ahí la regla práctica: **muchos más chunks que workers**. El óptimo es una
meseta ancha (de 1024 a 16384 viajes por chunk), así que el parámetro no es
delicado mientras se respete esa condición. El valor por defecto del código,
16384, está dentro de la meseta aunque no en su mejor punto: 4096 rinde un 4 %
más. Las corridas oficiales de las secciones anteriores usaron 16384.

## 9. Trade-offs y límites

**Lo que se gana.** Sobre el dataset del trabajo, 3,80x con 4 workers y 95 % de
eficiencia. Con 8 workers, 5,82x. El problema es suficientemente grande para que
la concurrencia pague.

**Lo que se paga.**

- Un 3 % de sobrecosto fijo, visible en que P=1 concurrente es más lento que el
  secuencial.
- Más tiempo total de CPU: 5,05 s contra 9,07 s en la laptop, a cambio de
  terminar en menos tiempo de pared.
- Complejidad: el código concurrente necesita el contrato de fases, la barrera y
  la reducción ordenada, más el modelo en Promela para justificar que es
  correcto.
- Debajo de 20 000 viajes, el paralelismo **cuesta más de lo que rinde**.

**Lo que decidimos pagar a propósito.** Acumular por chunk y reducir en orden de
índice cuesta unos 66 KB con la configuración oficial. A cambio, sobre el gold
completo con k=8 y 10 iteraciones:

| | Inercia | Dónde |
|---|---|---|
| Secuencial | 4531798,74797024 | idéntica en laptop y en la máquina virtual |
| Concurrente | 4531798,747970126 | idéntica en laptop y en la máquina virtual, **para P = 1, 2, 4, 8 y 16** |

Es decir: el resultado concurrente no depende de la cantidad de workers, ni del
planificador, ni de la máquina. La única diferencia es entre secuencial y
concurrente, y es de 2,53e-14 en términos relativos: el redondeo de sumar en otro
orden, que es exactamente lo que la PC1 anticipó y la razón por la que la
equivalencia se comprueba con tolerancia y no bit a bit.

Sin esa decisión de diseño, dos corridas idénticas darían números distintos en
los últimos dígitos y la comparación entre versiones sería una inspección a ojo
con tolerancias elegidas después de ver el resultado.

**Hasta dónde llega esto.** Un mes de una flota, una arquitectura por plataforma,
k=8, y la elección de k todavía por cerrar. Nada de esto dice qué pasa con varios
meses, con otra distribución de datos ni con más de seis núcleos físicos.

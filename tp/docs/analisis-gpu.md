# Contraste GPU frente a CPU del K-means (TB1)

Todo lo que sigue sale de `reports/gpu_wsl4060_fijas.json`, `reports/gpu_wsl4060_convergencia.json`
y `reports/benchmark_wsl4060.json`, y las tablas se regeneran con `scripts/analisis_gpu.py`. Ninguna
cifra se transcribió a mano. El montaje, el contrato replicado y las decisiones de diseño están en
`kmeans-gpu.md`.

## 1. Qué se compara

Configuraciones completas sobre la **misma máquina** (la caja `4060`: i7-10700 de 8 núcleos y 16
hilos, RTX 4060 de 8 GB), el **mismo gold** (2 831 486 viajes, 6 features), los **mismos centroides
iniciales** (k-means++ con semilla 2024, materializados por la CLI de Go) y el **mismo protocolo**
(20 repeticiones más calentamiento, orden barajado, media recortada al 10 %, IC por bootstrap):

- CPU, Go, float64: secuencial y worker pool con P ∈ {1, 2, 4, 8, 16};
- GPU, PyTorch sobre CUDA 12.4, Lloyd escrito a mano con el contrato de Go: fp64 y fp32.

Lo que se mide es solo el clustering. La carga del CSV y la transferencia a la GPU se reportan aparte.

## 2. Trabajo fijo: 10 iteraciones sobre el dataset completo

| Configuración | Detalle | Media recortada | Desv. | Iter. | Speedup vs seq [IC 95%] | Δ rel. inercia vs seq |
|---|---|---:|---:|---:|:--|---:|
| CPU Go secuencial | 1 hilo, float64 | 1650.5 ms | 5.1 ms | 10 | — | 0.0e+00 |
| CPU Go concurrente P=1 | worker pool, chunk 16,384, float64 | 1650.4 ms | 3.1 ms | 10 | 1.00x [1.00, 1.00] | 2.5e-14 |
| CPU Go concurrente P=2 | worker pool, chunk 16,384, float64 | 953.3 ms | 28.4 ms | 10 | 1.73x [1.71, 1.76] | 2.5e-14 |
| CPU Go concurrente P=4 | worker pool, chunk 16,384, float64 | 483.1 ms | 11.7 ms | 10 | 3.42x [3.38, 3.45] | 2.5e-14 |
| CPU Go concurrente P=8 | worker pool, chunk 16,384, float64 | 269.7 ms | 7.1 ms | 10 | 6.12x [6.04, 6.20] | 2.5e-14 |
| CPU Go concurrente P=16 | worker pool, chunk 16,384, float64 | 209.6 ms | 3.5 ms | 10 | 7.88x [7.81, 7.90] | 2.5e-14 |
| GPU PyTorch fp64 | NVIDIA GeForce RTX 4060, más 26 ms de transferencia | 380.7 ms | 0.9 ms | 10 | 4.34x [4.33, 4.34] | 2.5e-14 |
| GPU PyTorch fp32 | NVIDIA GeForce RTX 4060, más 92 ms de transferencia | 189.1 ms | 0.6 ms | 10 | 8.73x [8.71, 8.75] | 9.0e-05 (sumada en fp64: 9.0e-05) |

Máquina DESKTOP-8BQUEDR: NVIDIA GeForce RTX 4060 (8188 MB, 24 SMs), torch 2.6.0+cu124, CUDA 12.4. 20 repeticiones medidas + 1 de calentamiento, media recortada al 10%, IC por bootstrap de 2,000 réplicas, trabajo fijo de 10 iteraciones sobre 2,831,486 viajes, k=8, mismos centroides iniciales que la CPU.
- GPU PyTorch fp64 frente a la mejor CPU concurrente (P=16): 0.55x [0.55, 0.55].
- GPU PyTorch fp32 frente a la mejor CPU concurrente (P=16): 1.11x [1.11, 1.12].
- Asignaciones distintas entre fp64 y fp32: 5,870 de 2,831,486 (0.21 %).

Tres lecturas.

**En fp64 la GPU calcula exactamente lo mismo que Go.** La inercia final difiere en 2,5·10⁻¹⁴ en
términos relativos, que es la misma diferencia que hay entre el Go secuencial y el concurrente: el
redondeo de sumar en otro orden. El contrato replicado línea por línea (diferencias directas,
desempate por menor índice, `s · (1/n)`, cluster vacío conserva) funciona.

**En fp64 la GPU pierde contra la CPU de 16 hilos.** 4,3× frente al secuencial, pero 0,55× frente al
worker pool con P = 16. No es un defecto de la implementación: la RTX 4060 es una GPU de consumo con
unidades de doble precisión a 1/64 de la velocidad de simple precisión. El mismo algoritmo en fp32
tarda la mitad (189 ms contra 381 ms), que es exactamente la relación que se espera cuando el cuello
de botella pasa de las unidades fp64 al ancho de banda de memoria.

**En fp32 la GPU gana por poco, y a cambio da otra respuesta.** 1,11× frente a P = 16, con intervalo
que no toca el 1. Pero 5 870 viajes (0,21 %) quedan asignados a otro cluster y la inercia se desvía
9,0·10⁻⁵. La columna «sumada en fp64» muestra que esa desviación **no** viene de acumular 2,8
millones de términos en simple precisión (sumar las mismas distancias en fp64 da lo mismo): viene de
que las distancias y los centroides en fp32 producen otra partición. Es un cambio del resultado, no
del redondeo del reporte.

## 3. Hasta convergencia: 60 iteraciones

| Configuración | Detalle | Media recortada | Desv. | Iter. | Speedup vs seq [IC 95%] | Δ rel. inercia vs seq |
|---|---|---:|---:|---:|:--|---:|
| CPU Go secuencial | 1 hilo, float64 | 9080.5 ms | 25.9 ms | 60 | — | 0.0e+00 |
| CPU Go concurrente P=1 | worker pool, chunk 16,384, float64 | 9029.6 ms | 20.1 ms | 60 | 1.01x [1.00, 1.01] | 8.5e-14 |
| CPU Go concurrente P=2 | worker pool, chunk 16,384, float64 | 5215.5 ms | 61.8 ms | 60 | 1.74x [1.73, 1.75] | 8.5e-14 |
| CPU Go concurrente P=4 | worker pool, chunk 16,384, float64 | 2625.1 ms | 28.6 ms | 60 | 3.46x [3.44, 3.48] | 8.5e-14 |
| CPU Go concurrente P=8 | worker pool, chunk 16,384, float64 | 1468.6 ms | 24.3 ms | 60 | 6.18x [6.14, 6.22] | 8.5e-14 |
| CPU Go concurrente P=16 | worker pool, chunk 16,384, float64 | 1150.4 ms | 8.0 ms | 60 | 7.89x [7.87, 7.91] | 8.5e-14 |
| GPU PyTorch fp64 | NVIDIA GeForce RTX 4060, más 27 ms de transferencia | 2145.5 ms | 2.1 ms | 60 | 4.23x [4.23, 4.24] | 8.5e-14 |
| GPU PyTorch fp32 | NVIDIA GeForce RTX 4060, más 70 ms de transferencia | 1070.1 ms | 2.2 ms | 60 | 8.49x [8.48, 8.50] | 7.2e-06 (sumada en fp64: 7.1e-06) |

Máquina DESKTOP-8BQUEDR: NVIDIA GeForce RTX 4060 (8188 MB, 24 SMs), torch 2.6.0+cu124, CUDA 12.4. 20 repeticiones medidas + 1 de calentamiento, media recortada al 10%, IC por bootstrap de 2,000 réplicas, hasta convergencia (tolerancia 1e-09, tope 60 iteraciones) sobre 2,831,486 viajes, k=8, mismos centroides iniciales que la CPU.
- GPU PyTorch fp64 frente a la mejor CPU concurrente (P=16): 0.54x [0.54, 0.54].
- GPU PyTorch fp32 frente a la mejor CPU concurrente (P=16): 1.07x [1.07, 1.08].
- Asignaciones distintas entre fp64 y fp32: 5,539 de 2,831,486 (0.20 %).

Con seis veces más trabajo las relaciones se sostienen dentro del ruido: fp64 0,54× y fp32 1,07×
frente a P = 16. La desviación de inercia de fp32 baja a 7,2·10⁻⁶ porque tras 60 iteraciones ambas
precisiones están cerca del mismo mínimo local, pero la partición sigue siendo distinta en 5 539
viajes. Ninguna de las dos plataformas converge con tolerancia 10⁻⁹ antes del tope: el criterio de
parada es tan estricto como en la PC2 a propósito, para que la comparación sea de trabajo igual.

## 4. Barrido por tamaño: dónde paga la GPU

| n (viajes) | CPU seq (ms) | Mejor CPU conc (ms) | GPU fp64 (ms) | GPU fp32 (ms) | fp32 vs seq | fp32 vs mejor conc | fp64 vs mejor conc |
|---:|---:|---:|---:|---:|:--|:--|:--|
| 1,000 | 0.6 | 0.8 (P=2) | 12.9 | 13.1 | 0.0x [0.0, 0.0] | 0.06x [0.06, 0.06] | 0.06x [0.06, 0.06] |
| 10,000 | 6.1 | 6.3 (P=2) | 13.0 | 13.1 | 0.5x [0.5, 0.5] | 0.48x [0.47, 0.49] | 0.48x [0.48, 0.49] |
| 100,000 | 60.4 | 14.0 (P=8) | 22.9 | 15.6 | 3.9x [3.8, 3.9] | 0.90x [0.88, 0.91] | 0.61x [0.60, 0.62] |
| 1,000,000 | 579.5 | 78.7 (P=16) | 136.0 | 66.4 | 8.7x [8.7, 8.8] | 1.19x [1.18, 1.20] | 0.58x [0.57, 0.59] |
| 2,831,486 | 1650.5 | 209.6 (P=16) | 380.7 | 189.1 | 8.7x [8.7, 8.7] | 1.11x [1.11, 1.12] | 0.55x [0.55, 0.55] |

La GPU tiene un **piso de unos 13 ms por 10 iteraciones** (1,3 ms por iteración) que no depende de
n: es el costo de lanzar los kernels y sincronizar. Con mil o diez mil viajes ese piso es todo el
tiempo, y la CPU secuencial gana por 20 y por 2 veces. La GPU empieza a ganarle al secuencial
alrededor de 100 000 viajes, y a la mejor CPU concurrente recién con un millón, y solo en fp32. En
fp64 no le gana a los 16 hilos en ningún tamaño medido.

Es el mismo fenómeno que el punto de equilibrio de la PC2, un escalón más arriba: la CPU concurrente
necesitaba unos 20 000 viajes para pagar su costo fijo de pool y reparto; la GPU necesita unos
100 000 para pagar el suyo, y un millón para justificar la precisión que sacrifica.

## 5. Lo que no entra en el tiempo medido

Llevar los datos a la GPU cuesta entre 26 ms (fp64) y 92 ms (fp32, porque incluye la conversión
desde float64) para el dataset completo, y cargar el `.npy` cacheado, 66 ms. Son costos que se pagan
una vez por corrida, no por iteración, y que la CPU no tiene. Frente a los 189 ms del clustering en
fp32, la transferencia es la mitad del tiempo otra vez: en una corrida única y fría, la ventaja de la
GPU sobre P = 16 desaparece.

## 6. Conclusión para el TB1

En la GPU que el equipo tiene a mano, el mismo algoritmo en la misma precisión que Go **no** supera al
worker pool de 16 hilos. Sí lo supera, apenas, si se acepta calcular en simple precisión, y ese
cambio no es gratis: mueve el 0,2 % de los viajes de cluster. Para un caso donde el resultado tiene
que ser reproducible y comparable con la versión secuencial, como exige la rúbrica, la versión
concurrente en Go sigue siendo la elección correcta. La GPU pasaría a ser la opción si el dataset
creciera a decenas de millones de viajes, si k fuera mucho mayor (la asignación es O(n·k·d) y la GPU
escala mejor en k), o con hardware que no castigue la doble precisión.

## Hasta dónde llega esto

Una GPU de consumo, una implementación de Lloyd a mano en PyTorch (kernels genéricos, no fusionados),
un mes de una flota y k = 8. No dice nada sobre GPUs de centro de datos, sobre cuML o Faiss
optimizados, ni sobre otros k. Sí dice, con intervalos y sobre la misma máquina, qué pasa al llevar
este algoritmo a esta GPU.

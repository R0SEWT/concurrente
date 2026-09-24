# K-means en GPU: el contraste del TB1

Contraste entre **configuraciones completas** (máquina + lenguaje + implementación + precisión),
no una comparación controlada de una sola variable: cambiar Go en CPU por PyTorch en GPU cambia
todo a la vez. Lo que se controla es el **algoritmo**: misma entrada, mismos centroides iniciales,
mismo k, mismas iteraciones, mismo criterio de parada y mismo protocolo de medición que
`tp/kmeans/cmd/benchmark`. Y para que la máquina no sea una variable más, el benchmark de Go se
corre **en la misma caja** que la GPU.

Bead: `concurrente-3r8.7`. Los números están en `tp/reports/gpu_wsl4060_*.json` y
`tp/reports/benchmark_wsl4060.json`; las tablas salen de `tp/scripts/analisis_gpu.py` y el análisis
está en `analisis-gpu.md`.

## La máquina

`ssh gpu` (alias `ssh 4060`): la caja WSL2 de lizfer sobre Tailscale.

| | |
|---|---|
| GPU | NVIDIA GeForce RTX 4060, 8 GB, 24 SMs, driver 610.47 |
| CPU | Intel i7-10700, 8 núcleos / 16 hilos |
| RAM | 15 GB |
| SO | Ubuntu 24.04 en WSL2, Python 3.12 |
| Toolchain | PyTorch 2.6.0+cu124 en un venv de `uv`; Go 1.26.7 en `~/go-sdk` (sin sudo) |

Es una máquina compartida (corre n8n): trabajo en `~/proj/concurrente-gpu/`, venv aislado, nada
instalado a nivel de sistema. Distinta de **gorgo** (`fischl-ubuntusv`, RTX 4060 Ti 16 GB, 11
núcleos, 9 GB de RAM, `/home` al 97 %), donde corrieron las mediciones oficiales de CPU de la PC2.

La RTX 4060 es una GPU de consumo: su rendimiento en doble precisión es 1/64 del de simple
precisión. Eso es parte del resultado, no un defecto del experimento.

## Montaje (una vez)

```bash
/usr/bin/ssh gpu                                   # ojo: `ssh` a secas puede ser el kitten de kitty
mkdir -p ~/proj/concurrente-gpu/{data,reports,logs} && cd ~/proj/concurrente-gpu
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python torch --index-url https://download.pytorch.org/whl/cu124
uv pip install --python .venv/bin/python numpy polars
curl -sSL https://go.dev/dl/go1.26.7.linux-amd64.tar.gz | tar -C ~ -xz && mv ~/go ~/go-sdk
```

Desde la laptop, llevar el gold, los centroides iniciales y el módulo de Go:

```bash
cd tp
kmeans/cmd/kmeans -modo seq -k 8 -iter 1 -hash-datos=false -centroides /tmp/centroides_k8_s2024.txt   # los materializa
scp data/gold/yellow_2024-01_features.csv /tmp/centroides_k8_s2024.txt gpu:~/proj/concurrente-gpu/data/
rsync -a -e /usr/bin/ssh kmeans/ gpu:~/proj/concurrente-gpu/kmeans/
scp scripts/kmeans_gpu.py scripts/gpu/correr_remoto.sh gpu:~/proj/concurrente-gpu/
```

El archivo de centroides es el mismo que produce k-means++ con semilla 2024 dentro del benchmark
de Go para el dataset completo (sha256 `a1755469195d…`): las dos plataformas parten exactamente del
mismo punto.

## Corrida

En el remoto, `nohup ./correr_remoto.sh > logs/todo.log 2>&1 &`. Hace tres cosas, en orden:

1. **CPU, Go**: `cmd/benchmark` con trabajo fijo y hasta convergencia, tamaños
   1 000 · 10 000 · 100 000 · 1 000 000 · completo, P ∈ {1, 2, 4, 8, 16}. Va primero para que no
   compita con el host de la GPU.
2. **GPU, trabajo fijo**: `kmeans_gpu.py --experimento fijas --iter 10`, mismos tamaños, fp64 y
   fp32, con `--referencia` al JSON de 1.
3. **GPU, hasta convergencia**: `--experimento convergencia --iter 60 --tol-abs 1e-9 --tol-rel 1e-9`
   sobre el dataset completo.

Se bajan `reports/benchmark_cpu.json`, `reports/gpu_fijas.json` y `reports/gpu_convergencia.json`
a `tp/reports/` con el prefijo de la máquina, y las tablas se regeneran con

```bash
python3 scripts/analisis_gpu.py reports/gpu_wsl4060_fijas.json --cpu reports/benchmark_wsl4060.json
```

## Decisiones de diseño de `kmeans_gpu.py`

- **PyTorch y no cuML ni Faiss.** Las bibliotecas de K-means en GPU no dejan fijar los centroides
  iniciales exactos, el desempate ni la regla del cluster vacío; con tensores se replica el contrato
  de `secuencial.go` línea por línea. El costo es que no es una implementación "de biblioteca"
  optimizada; es Lloyd escrito a mano sobre la GPU, que es justo lo comparable con el Lloyd escrito
  a mano en Go.
- **Distancia por diferencias directas**, `((x − c)²).sum()`, y no por la expansión
  `‖x‖² − 2x·c + ‖c‖²` que usa `torch.cdist` para entradas grandes: la expansión redondea distinto y
  rompería la equivalencia bit a bit en fp64. El tensor `N × k × d` se trocea por filas para no
  pasar de ~512 MB.
- **Desempate por menor índice**: `torch.min(dim=1)` devuelve el primer mínimo, igual que el `<`
  estricto de `masCercano` en Go.
- **Actualización `s · (1/n)`**, no `s / n`: es lo que hace `actualizar` en Go, y en fp64 la
  diferencia se ve en el último bit.
- **Cluster vacío conserva su centroide**, con `torch.where` sobre la máscara de conteos.
- **Inercia final recalculada** con los centroides finales, en una pasada extra que sí entra en el
  tiempo medido, igual que en Go. En fp32 se guarda además **sumada en fp64**, para separar dos
  efectos distintos: el error de acumular 2,8 millones de términos en simple precisión y el efecto
  de las asignaciones que cambian.
- **Se mide solo el clustering**, con `torch.cuda.synchronize()` antes y después. La carga del CSV
  (cacheada en `.npy`) y la transferencia a la GPU se reportan aparte: un contraste honesto dice
  cuánto cuesta llevar los datos.
- **Submuestras sistemáticas** con paso `N/n`, idénticas a `kmeans.Submuestra`. Los centroides
  iniciales son los del archivo en todos los tamaños; por eso la equivalencia de inercia con Go
  solo se afirma para el dataset completo, que es el n del que salió ese archivo.
- **Protocolo**: 20 repeticiones + 1 de calentamiento, orden barajado entre (tamaño, precisión) en
  cada ronda, media recortada al 10 % por extremo, speedup como cociente de medias recortadas e IC
  del 95 % por bootstrap de 2 000 réplicas sobre los tiempos crudos de las dos muestras.

## Hasta dónde llega

Una GPU de consumo, un mes de una flota, k = 8, y una implementación de Lloyd a mano en ambas
plataformas. No dice nada sobre GPUs de centro de datos con fp64 completo, ni sobre bibliotecas
optimizadas, ni sobre k grandes donde la asignación domina de otra manera. Sí dice, con intervalos,
qué pasa cuando el mismo algoritmo se lleva a la GPU que el equipo tiene a mano.

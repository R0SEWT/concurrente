# Informe de GAPs del código con IA (Entregable 3)

Análisis del código del Trabajo Parcial con un modelo de IA y un prompt estructurado, como pide el
Entregable 3. Busca brechas en calidad de código, seguridad, patrones de concurrencia, pruebas,
rendimiento y reproducibilidad.

- **Modelo**: Claude Opus 5.5 (`claude-opus-5-5`), de Anthropic, como agente de Claude Code.
- **Prompt**: [`gaps-ia-prompt.md`](gaps-ia-prompt.md), versionado para que el análisis se pueda
  repetir.
- **Código analizado**: commit `97ba37c` de `develop`, en https://github.com/R0SEWT/concurrente,
  directorio `tp/` y `.github/workflows/`.
- **Fecha**: 29 de septiembre de 2026.

## Método

1. **El prompt.** Fija el rol, el contexto, el alcance, seis categorías con preguntas guía, las
   reglas y el formato de salida. La regla central es que un hallazgo sin evidencia `ruta:línea`
   no cuenta, y que lo que no se puede demostrar se marca como hipótesis.
2. **Por qué este modelo.** Puede leer el repositorio completo con herramientas en vez de fragmentos
   pegados. Puede correr `go vet`, `go test -race`, Spin y pruebas propias para confirmar lo que
   sospecha. Y razona bien sobre concurrencia en Go.
3. **Un agente sin contexto.** El mismo modelo ayudó a escribir parte del código (ver la
   declaración de uso de IA del informe). Para no revisarlo con los sesgos de quien lo escribió, el
   análisis lo hizo un agente en una sesión nueva, sin la conversación en la que se desarrolló el
   proyecto. Trabajó sobre una copia de solo lectura del commit.
4. **Cada hallazgo se contrastó contra el código** antes de incluirlo. La columna «Contraste» de la
   tabla dice cómo. El agente corrió 35 comandos para confirmar los suyos; los del grupo se
   repitieron por separado.

## Resultado en una línea

Ninguno de los 18 hallazgos es un error de sincronización. Eso coincide con lo que ya habían
verificado Spin y `go test -race`: el diseño y la implementación del worker pool son correctos. Las
brechas están en otras partes:

- en el rendimiento de la concurrencia (*false sharing*, G2), que ninguna de las dos herramientas
  puede ver;
- en el harness de medición (G1, G7, G8, G11);
- en la trazabilidad de los resultados (G3, G4, G10).

## Hallazgos

Contraste:
- **Confirmado (grupo)**: se repitió por separado, con el comando o la medición indicados.
- **Confirmado (agente)**: el agente lo demostró con un test o un comando, y el grupo revisó el
  código citado.
- **Hipótesis**: plausible pero no demostrada.

| ID | Categoría | Sev. | Dónde | Hallazgo | Contraste |
|---|---|---|---|---|---|
| G1 | Calidad | alta | `kmeans/cmd/benchmark/main.go:203` | El benchmark escribe las corridas crudas solo al final: un error tardío (p. ej. `-repes 1`) descarta todas las mediciones | Confirmado (grupo): lectura de `main.go:188-220`; el agente lo reprodujo con `-repes 1` |
| G2 | Concurrencia / rendimiento | media | `kmeans/concurrente.go:52-56` | *False sharing* en los contadores por bloque cuando `k` no es múltiplo de 8 | Confirmado (grupo): 256 → 224 ms con k=4 al alinear cada parcial a 64 bytes (−12,5 %); sin efecto con k=8 |
| G3 | Reproducibilidad | media | `kmeans/metadatos.go:63-66` | Sin git, los metadatos quedan con `commit` vacío y `arbol_sucio=false`: 10 de los 12 JSON de benchmark, incluido el principal del informe, no se pueden atar a un commit | Confirmado (grupo): recorrido de `reports/benchmark_*.json` |
| G4 | Reproducibilidad | media | `scripts/kmeans_gpu.py:143,357` | La GPU no es determinista (`index_add_`) y las métricas de equivalencia salen de la última corrida | Confirmado (grupo): 8 inercias distintas en fp64 y 9 en fp32 sobre 21 corridas iguales |
| G5 | Seguridad / reproducibilidad | media | `src/nyc_tlc/ingest.py:24-26` | La descarga de bronze no se compara contra un sha256 esperado y no tiene timeout | Confirmado (grupo): lectura de `ingest.py` |
| G6 | Pruebas | media | `kmeans/gold_real_test.go:135` | Sobre datos reales, secuencial y concurrente se comparan solo por inercia, no por asignaciones | Hipótesis (el efecto); el código citado, confirmado (grupo) |
| G7 | Pruebas | media | `kmeans/cmd/benchmark/` | `cmd/benchmark` no tiene tests | Confirmado (grupo): el directorio no tiene `*_test.go` |
| G8 | Calidad | baja | `kmeans/cmd/benchmark/main.go:118,164` | Los nombres de experimento no se validan: `fija` corre como `fijas` con otra etiqueta | Confirmado (agente) |
| G9 | Calidad | baja | `kmeans/cmd/kmeans/main.go:186,205` | Si k-means++ reduce k, el archivo de centroides no sirve para la siguiente corrida con el mismo `-k` | Confirmado (agente) |
| G10 | Reproducibilidad | baja | `kmeans/cmd/benchmark/main.go:157` | El benchmark recalcula k-means++ en vez de leer los centroides materializados | Confirmado (agente) |
| G11 | Pruebas | baja | `kmeans/cmd/benchmark/main.go:163` | «Iteraciones fijas» con tolerancias en 0 puede parar antes por tolerancia | Confirmado (grupo): `secuencial.go:173` compara con `<=`; ninguna corrida publicada paró antes |
| G12 | Robustez | baja | `kmeans/inicializacion.go:124-131` | `LeerCentroides` reserva memoria según la cabecera: un `k` enorme produce `panic` en vez de error | Confirmado (agente); código revisado (grupo) |
| G13 | Robustez | baja | `kmeans/concurrente.go:50-53` | La memoria de los parciales crece como N/Chunk sin cota | Cálculo sobre el código, no medido |
| G14 | Robustez | baja | `kmeans/secuencial.go:166` | `converge` ignora los NaN: una corrida con un NaN informa convergencia | Confirmado (agente); código revisado (grupo) |
| G15 | Verificación | baja | `spin/kmeans.pml:38-41,96` | La regresión de Spin solo cubre P = C = 2 | Confirmado (agente): P=3 y C=3 también dan 0 errores, pero no están en `check.sh` |
| G16 | CI | baja | `kmeans/go.mod:3`, `.github/workflows/` | La CI prueba con Go 1.22 (las cifras son de 1.26.7), las acciones se fijan por tag y `uv sync` corre sin `--locked` | Confirmado (grupo): lectura de `go.mod` y de los workflows |
| G17 | Calidad | baja | `kmeans/cmd/*/argumentos.go` | `argumentos.go` está duplicado idéntico; la estadística de la GPU usa otra regla de percentil | Confirmado (grupo): `diff -q` sin diferencias |
| G18 | Reproducibilidad | baja | `scripts/kmeans_gpu.py:77` | La caché `.npy` se invalida solo por fecha de modificación | Confirmado (agente) |

## Contraste con la verificación del proyecto

**Lo que ya estaba cubierto, y el análisis confirmó.** El agente buscó lo que Spin y
`go test -race` verifican (carreras, un `Done` faltante, canales mal cerrados, goroutines vivas al
terminar) y no encontró nada. Además revisó lo que ninguna de las dos herramientas mira:

- el orden de `pool.Add` y `barrera.Add` respecto del lanzamiento y del encolado;
- el `close` y el `Wait` en un `defer`.

Encontró ambas cosas correctas.

**Lo que ninguna de las dos herramientas cubre y el análisis encontró.**
- **G2** es un problema de concurrencia que no es de corrección: el resultado es correcto, pero dos
  workers que escriben contadores vecinos compiten por la misma línea de caché. Spin no modela la
  memoria y `-race` solo detecta accesos a la misma variable, no a la misma línea. Los resultados
  publicados usan k=8, donde cada bloque ocupa líneas completas por casualidad, así que no están
  afectados. Con k=4 o k=12 lo estarían.
- **G15** muestra un límite de la verificación formal: la regresión fija una sola configuración del
  modelo, aunque el agente comprobó a mano que otras tres también dan cero errores.
- **G1, G3, G4, G7, G10 y G11** son brechas del harness de medición y de la trazabilidad, que están
  fuera del alcance de las dos herramientas.

**Lo que se corrigió del informe del agente.**
- En G3 el agente contó 9 de 11 JSON sin commit. Son 10 de 12: `benchmark_wsl4060.json` tampoco lo
  tiene.
- En G7 citaba a G12 entre los errores que habría detectado un test del benchmark, pero G12 está en
  `inicializacion.go`. El que corresponde es G11.

Lo demás coincidió con la verificación del grupo, incluida la medición de G2, que dio casi lo mismo
(−12 % frente a −12,5 %).

**Consecuencia para el informe.** G4 obliga a matizar el contraste en GPU: las cifras de
equivalencia en `float32` (el 0,21 % de asignaciones distintas) son de una sola corrida entre 21 que
no dan lo mismo. La Sección de correcciones de la PC2 lo dice.

**Decisión.** No se corrigió ningún hallazgo en este entregable, para no cambiar el código que
produjo las cifras del informe. Las recomendaciones van en orden de prioridad:

1. G1 y G7: que el benchmark escriba cada corrida al terminarla y tenga tests. Es el harness que
   produce todas las cifras del informe.
2. G2: alinear cada parcial a 64 bytes. Son cinco líneas y el resultado numérico no cambia.
3. G3 y G4: exigir el commit en los metadatos y registrar la dispersión de la GPU.
4. G5 y G16: verificar el sha256 de la descarga, fijar el toolchain de Go en `go.mod` y usar
   `uv sync --locked`.
5. G15: parametrizar el modelo Promela y agregar a la regresión los casos P > C y C > P.

---

## Informe del modelo

Lo que sigue es la salida del agente, con el formato unificado y las dos correcciones señaladas
arriba (G3 y G7). El contenido técnico, la evidencia y las mediciones son los suyos.

### Detalle por hallazgo

#### G1 · El benchmark pierde todas las mediciones si falla al final (alta)

**Evidencia**: `tp/kmeans/cmd/benchmark/main.go:195`, `:203`, `:216`, `:262`.

```go
inf.Corridas = append(inf.Corridas, c)                         // 195: solo en memoria
...
inf.Resumen, err = resumir(inf.Corridas, recorte, boot, semillaOrd)   // 203
if err != nil { return err }                                   // sale sin escribir nada
...
f, err := os.Create(salida)                                    // 216: recién acá se escribe
// en resumir:
desv, err := kmeans.DesviacionEstandar(ts)                     // 262: error si hay < 2 observaciones
```

El comentario de cabecera (`main.go:17-18`) dice «Se guardan los tiempos crudos además de los
agregados, para poder recalcular cualquier estadística sin volver a medir», pero eso no se cumple si
hay un error.

**Impacto**: con `-repes 1`, o con un `return err` desde cualquier corrida de `Secuencial` o
`Concurrente` (líneas 190-191), se pierde el trabajo de toda la sesión, que en gorgo, la laptop o el
Pixel dura decenas de minutos. Confirmado: con `-repes 1` el programa corre todo, termina con
`error: hacen falta al menos 2 observaciones, hay 1` y no crea el JSON. No afecta a los JSON ya
publicados.

**Recomendación**: escribir `inf` (corridas, sin resumen) antes de llamar a `resumir`, o volcar cada
corrida como JSONL a medida que termina. Además, rechazar `repes < 2` al principio de `correr`,
antes de cargar el gold.

**Cómo verificarlo**: `go run ./cmd/benchmark -datos tiny.csv -repes 1 -workers 1,2 -tamanos 0
-salida out.json`. Hoy termina con exit 1 y sin `out.json`. Con el arreglo, debe fallar de
inmediato o dejar las corridas crudas en el archivo.

#### G2 · *False sharing* en los acumuladores por bloque (media)

**Evidencia**: `tp/kmeans/concurrente.go:52-56`.

```go
sumasBase := make([]float64, cantChunks*k*dim)
conteosBase := make([]int, cantChunks*k)
for c := range parciales {
    parciales[c].sumas = sumasBase[c*k*dim : (c+1)*k*dim]
    parciales[c].conteos = conteosBase[c*k : (c+1)*k]
}
```

El lazo caliente escribe `conteos[j]++` una vez por punto (`secuencial.go:138`). Como el canal
entrega los bloques en orden, los bloques c y c+1 suelen procesarse a la vez en workers distintos.
Cuando `k*8` bytes no es múltiplo de 64, sus contadores comparten una línea de caché.

**Impacto**: medido en una copia del paquete, con 2²¹ puntos, D=6, P=8, chunk=16384 y
5 iteraciones. La variante «con relleno» solo cambia el paso de `conteosBase` y `sumasBase` al
múltiplo de 8 siguiente.

| k | actual | con relleno |
|---|---|---|
| 4 | 250-254 ms | 220-222 ms (−12 %) |
| 8 | 346-347 ms | 347-353 ms (sin diferencia) |
| 12 | 478-493 ms | 471-489 ms (≈ −1 %) |

Con k=8 y D=6, cada bloque ocupa exactamente 6 líneas de sumas y 1 de contadores. Por eso los
resultados publicados (k=8) no están afectados, pero es por casualidad: `docs/kmeans.md:73` evalúa
k ∈ {4, 8, 12, 16}.

**Recomendación**: redondear el paso de cada parcial a 8 palabras (64 bytes), que es cambiar las
cinco líneas citadas. Opcionalmente, acumular `conteos` en locales por bloque y copiarlos al final
de `procesarChunk`.

**Cómo verificarlo**: un `BenchmarkConcurrente` con subcasos k ∈ {4, 8, 12}, comparando antes y
después con `benchstat`.

#### G3 · Los metadatos no distinguen «sin commit» de «árbol limpio» (media)

**Evidencia**: `tp/kmeans/metadatos.go:54-58` y `:63-66`.

```go
if m.Commit == "" {
    // ... Como sin commit el resultado no se puede reproducir, se pregunta directamente.
    m.Commit, m.ArbolSucio = commitDeGit()
}
...
rev, err := exec.Command("git", "rev-parse", "HEAD").Output()
if err != nil {
    return "", false
}
```

En los JSON publicados:
- `benchmark_gorgo*.json` (9 archivos) y `benchmark_wsl4060.json` tienen `"arbol_sucio": false` y
  no tienen `commit`.
- `benchmark_laptop_i5.json` y `benchmark_pixel9a.json` tienen commit, pero
  `"arbol_sucio": true`.
- `tp/scripts/tablas_informe.py:24` toma `benchmark_gorgo.json` como `PRINCIPAL`.

**Impacto**: ninguna cifra de la tabla principal del informe se puede atar a un commit, y `false`
se lee como «árbol limpio» cuando significa «no se sabe».

**Recomendación**:
- serializar explícitamente el estado desconocido, con `ArbolSucio *bool` o
  `"commit": "desconocido"`;
- que la CLI y el benchmark avisen por stderr cuando no hay commit o el árbol está sucio, o que
  fallen si se pasa un flag `-exigir-commit`;
- que el script remoto pase el commit con `-ldflags "-X ..."`.

**Cómo verificarlo**: un test que haga `os.Chdir(t.TempDir())` y llame a `RecolectarMetadatos()`.
Hoy da `commit="" arbol_sucio=false`; debería marcar el estado como desconocido.

#### G4 · La versión GPU no es determinista (media)

**Evidencia**: `tp/scripts/kmeans_gpu.py:143`.

```python
sumas = torch.zeros(k, d, dtype=x.dtype, device=x.device).index_add_(0, etiquetas, x)
```

En `:357`, `resultado[n, p] = r` se pisa en cada ronda, y de ahí salen
`asignaciones_distintas_entre_precisiones` (`:388`) y `diferencia_relativa_inercia` (`:396`). El
docstring (`:2`) promete «el MISMO contrato que tp/kmeans (Go)», y Go garantiza determinismo bit a
bit (`concurrente.go:34-37`). En `reports/gpu_wsl4060_fijas.json`, para n=2 831 486, la inercia
toma 8 valores distintos en fp64 y 9 en fp32 a lo largo de 21 corridas con los mismos datos y
centroides. Esto no se menciona en `docs/` ni en el informe.

**Impacto**: las cifras de equivalencia GPU/CPU describen una corrida elegida sin criterio. En fp64
la variación es chica (~1e-15 relativo); en fp32 llega a ~1e-6, del mismo orden que la diferencia
entre fp32 y la CPU que se reporta.

**Recomendación**: registrar el mínimo y el máximo de la inercia entre corridas en el resumen y
documentar la fuente del no determinismo. Opcionalmente, `torch.use_deterministic_algorithms(True)`,
tras confirmar que `index_add_` en CUDA tiene un camino determinista en torch 2.6.

**Cómo verificarlo**: sobre el JSON,
`len({c["inercia"] for c in corridas if c["tamano"]==N and c["precision"]=="fp64"})`. Hoy da 8; con
el modo determinista debería dar 1.

#### G5 · La descarga no verifica integridad (media)

**Evidencia**: `tp/src/nyc_tlc/ingest.py:24-26`.

```python
if not destino.exists():
    parcial = destino.with_name(destino.name + ".part")
    with urllib.request.urlopen(url) as respuesta, open(parcial, "wb") as f:
```

El sha256 solo se registra en el reporte, no se compara. `docs/kmeans.md:16-17` fija el sha del
gold (`a3ad52…`) y `configs/limpieza.toml` no tiene un campo con el hash esperado.

**Impacto**: el docstring reconoce que TLC re-publica meses, pero no su consecuencia: en un clon
nuevo, `uv run nyc-tlc all` produce en silencio otro gold y los benchmarks dejan de ser comparables
con el informe. Lo único que lo detectaría es `TestLeerGoldArchivoReal`, que en la CI se salta.
Además, `urlopen` sin `timeout` puede quedar colgado para siempre.

**Recomendación**: agregar `sha256_viajes` y `sha256_zonas` en `[fuente]` y fallar si no coinciden,
con un flag para aceptar a propósito una re-publicación. Usar `urlopen(url, timeout=60)`.

**Cómo verificarlo**: un test en `test_pipeline.py` que sirva por `file://` un parquet con otro
contenido y ponga un `sha256` esperado en la config, y que espere la excepción.

#### G6 · La equivalencia sobre datos reales solo compara la inercia (media, hipótesis)

**Evidencia**: `tp/kmeans/gold_real_test.go:135`.

```go
if rel := math.Abs(con.Inercia-sec.Inercia) / math.Abs(sec.Inercia); rel > 1e-12 {
```

`docs/kmeans.md:128-131` dice «Inercia parecida **no** demuestra la misma partición: se comparan
también las etiquetas». La comparación de etiquetas solo existe con datos sintéticos
(`concurrente_test.go:123-131`), y el benchmark solo guarda la inercia. En los JSON, la inercia
secuencial y la concurrente difieren (p. ej. convergencia n=2 831 486: 4461447.055723612 frente a
4461447.055723991).

**Impacto (hipótesis)**: en 60 iteraciones sobre 2,8 millones de puntos, la diferencia en el orden
de las sumas podría cambiar la asignación de puntos de frontera sin que ningún test lo detecte. No
se pudo confirmar sin el gold.

**Recomendación**: en `TestPilotoSpeedupSobreElGoldReal`, contar las `Asignaciones` distintas y el
máximo |Δcentroide|, y registrarlos. Si no dan 0, documentar cuántas cambian.

**Cómo verificarlo**: `go test -run TestPilotoSpeedupSobreElGoldReal -v` con el gold presente,
después del cambio.

#### G7 · `cmd/benchmark` no tiene tests (media)

**Evidencia**: `go test -race -count=1 ./...` muestra
`?  upc.edu.pe/concurrente/kmeans/cmd/benchmark  [no test files]`. Quedan sin cubrir `resumir`
(`main.go:233-289`), `enteros` (`:309-326`), la validación de flags y `argumentos` (duplicado, G17).

**Impacto**: el harness que produce todas las cifras del informe no tiene red de seguridad. G1, G8
y G11 son justo el tipo de error que habría detectado un test de `correr` sobre un CSV mínimo.

**Recomendación**: un test de `correr` con un gold sintético de ~200 filas en `t.TempDir()`, más
tests de tabla para `resumir` (claves, speedup solo con `seq`, `repes=1`) y para `enteros`.

**Cómo verificarlo**: `go test -race ./cmd/benchmark` deja de decir `[no test files]` y cubre
`repes=1`.

#### G8 · Nombres de experimento sin validar (baja)

**Evidencia**: `tp/kmeans/cmd/benchmark/main.go:118` y `:163-166`.

```go
experimentos := strings.Split(experCSV, ",")
...
op := kmeans.Opciones{K: kEf, MaxIter: iterFijas, TolAbs: 0, TolRel: 0}
if exper == "convergencia" {
```

`-experimentos fija` corre 10 iteraciones fijas y deja todas las corridas con
`experimento: "fija"`. Los valores de `-workers` (≤ 0 o repetidos) tampoco se validan hasta después
de cargar el gold.

**Impacto**: un error de tipeo no hace fallar la corrida. El JSON queda etiquetado con un nombre que
`tablas_informe.py` y `kmeans_gpu.py`, que filtran por `"fijas"`, no encuentran.

**Recomendación**: validar contra `{"fijas", "convergencia"}` y `workers > 0` antes de
`LeerGoldArchivo`.

**Cómo verificarlo**: `-experimentos fija` debe terminar con un error inmediato.

#### G9 · La caché de centroides no sirve cuando k-means++ reduce k (baja)

**Evidencia**: `tp/kmeans/cmd/kmeans/main.go:205` guarda con `kEfectivo`, y `:186` exige en la
siguiente corrida que `kLeido == k`.

```go
if err := kmeans.GuardarCentroides(f, cent, kEfectivo, d.D); err != nil {
...
if kLeido != k { return nil, 0, fmt.Errorf("... tienen k=%d y se pidió -k %d", ...) }
```

Hay además una discrepancia con el diseño: `docs/kmeans.md:59-61` promete completar «repitiendo
puntos distintos si existen», pero `inicializacion.go:61-63` solo corta el lazo y reduce k.

**Impacto**: con 2 puntos distintos y `-k 3`, la primera corrida da k efectivo 2 y la segunda, con
el mismo `-k 3`, falla con `tienen k=2 y se pidió -k 3`. Con el gold real no ocurre.

**Recomendación**: guardar el k pedido en la cabecera (`k=3 k_efectivo=2 d=6`) y comparar contra
ese valor. Alinear el diseño con el código.

**Cómo verificarlo**: un test en `cmd/kmeans` con datos degenerados que llame dos veces a
`centroidesIniciales` con el mismo k.

#### G10 · El benchmark no usa los centroides materializados (baja)

**Evidencia**: `tp/kmeans/cmd/benchmark/main.go:157`.

```go
cent, kEf, err := kmeans.KMeansPP(sub, k, semilla)
```

`docs/kmeans.md:50-53` exige que los centroides se materialicen y que «ambas versiones parten de ese
archivo», porque «la misma semilla no garantiza los mismos centroides si cambia el generador».
`kmeans_gpu.py` sí lee el archivo. Los hashes registrados no se pueden cruzar: el benchmark guarda
`HashCentroides` (sha256 de los bits) y la GPU, el sha256 de los bytes del archivo.

**Impacto**: la comparación GPU/CPU depende de que dos caminos distintos den los mismos centroides.
Hoy la `diferencia_relativa_inercia` de 2,5e-14 sugiere que sí, pero nada lo garantiza si cambia la
versión de Go (`math/rand`).

**Recomendación**: un flag `-centroides` en `cmd/benchmark` para el dataset completo, y registrar el
mismo hash en ambos lados (`HashCentroides` de los valores leídos).

**Cómo verificarlo**: que `centroides_por_tamano["fijas/2831486"]` del JSON de Go sea igual al hash
que registra la GPU.

#### G11 · «Iteraciones fijas» puede parar antes (baja)

**Evidencia**: `tp/kmeans/cmd/benchmark/main.go:163` usa `TolAbs: 0, TolRel: 0`, y
`secuencial.go:173` devuelve `desp <= op.TolAbs+op.TolRel*escala`, que es verdadero con
`desp == 0`. El propio `concurrente_test.go:253` espera `Iteraciones == 2` con tolerancias en 0.

**Impacto**: `nubes(200)` con `MaxIter: 10` y tolerancias en 0 para en 2 iteraciones, con
`paro=tolerancia`. En los JSON publicados no pasó: todas las corridas `fijas` dicen `max_iter`, 10.
Pero con n chico el experimento de «mismo trabajo» dejaría de serlo sin avisar.

**Recomendación**: usar `TolAbs: -1` en «fijas», o un campo `SinParadaTemprana`, y que `resumir`
falle si en «fijas» `Iteraciones != iterFijas`.

**Cómo verificarlo**: el mismo caso de `nubes(200)`, que debe dar 10 iteraciones.

#### G12 · `LeerCentroides` confía en la cabecera (baja)

**Evidencia**: `tp/kmeans/inicializacion.go:124-131`.

```go
fmt.Sscanf(strings.TrimSpace(sc.Text()), "k=%d d=%d", &k, &dim)
if k <= 0 || dim <= 0 { ... }
cent := make([]float64, 0, k*dim)
```

**Impacto**: la cabecera `k=4611686018427387904 d=2` produce
`panic: runtime error: makeslice: cap out of range` en vez de un error. Un k grande pero
representable reserva gigabytes antes de descubrir que el archivo tiene una sola fila. El impacto es
local: el archivo lo controla quien corre el programa.

**Recomendación**: no reservar según la cabecera (dejar que `append` crezca), o acotar `k*dim`
(p. ej. ≤ 1<<20) con chequeo de desbordamiento.

**Cómo verificarlo**: un caso más en `TestLeerCentroidesRechazaArchivoCorrupto` con esa cabecera,
que debe devolver un error sin `panic`.

#### G13 · Memoria de los parciales sin cota (baja)

**Evidencia**: `tp/kmeans/concurrente.go:50-53`.

```go
cantChunks := (n + op.Chunk - 1) / op.Chunk
parciales := make([]parcial, cantChunks)
sumasBase := make([]float64, cantChunks*k*dim)
conteosBase := make([]int, cantChunks*k)
```

`docs/kmeans.md:113-114` razona con «1000 chunks» y concluye que el costo es irrelevante.

**Impacto**: con `-chunk 1` sobre el gold (N=2 831 486, k=8, D=6) son ≈ 1,27 GB de acumuladores y
≈ 158 MB de structs, frente a los 136 MB de los datos. Es un cálculo sobre el código, no una
medición.

**Recomendación**: validar que `Chunk` no produzca más de, por ejemplo, 64·Workers bloques, o
documentar la cota en `OpcionesConc`.

**Cómo verificarlo**: `kmeans -chunk 1` con `-json`, comparando `recursos_finales.max_rss_mb` contra
`-chunk 16384`.

#### G14 · `converge` ignora los NaN (baja)

**Evidencia**: `tp/kmeans/secuencial.go:166`.

```go
if delta := math.Abs(cent[i] - previos[i]); delta > desp {
```

`NaN > desp` es falso, así que un centroide NaN no cuenta como desplazamiento.

**Impacto**: con un NaN en `X`, `Secuencial` devuelve `err=nil`, `paro=tolerancia`,
`cent0=[NaN …]` e `inercia=+Inf`. `gold.go:41-46` documenta que no se revalida X, por el sesgo que
eso agregaría al benchmark. Lo que no reconoce es que la corrida **informa convergencia**, un falso
éxito. Revisar los k·D valores en `converge` cuesta O(k·D) por iteración y no sesga la medición.

**Recomendación**: si algún `cent[i]` es NaN, que `converge` devuelva un error o un
`Paro = "no_finito"`.

**Cómo verificarlo**: un test con `X[0] = NaN` que espere un error o un paro distinto de
`tolerancia`.

#### G15 · La regresión de Spin solo cubre P = C = 2 (baja)

**Evidencia**: `tp/spin/kmeans.pml:38-41` y `:96`.

```promela
#define N     4
#define C     2
...
atomic { run worker(); run worker() }   /* P = 2 */
```

`check.sh` no varía los parámetros. El README reconoce las cotas, pero no que P > C y C > P son
casos distintos. En Go, esos casos tienen tests propios (`TestConcurrenteConMasWorkersQuePuntos`).

**Impacto**: bajo. Comprobado a mano en una copia: N=4, C=2, P=3 da 0 errores (11 814 estados);
N=6, C=3, P=2 da 0 (9 579); N=6, C=3, P=3 da 0 (136 782). El modelo aguanta esos casos, pero la
regresión no los fija.

**Recomendación**: `#ifndef N / #define N 4 / #endif` (y lo mismo para C y P), y dos casos más en
`check.sh` con `spin -DN=6 -DC=3 -DP=3`. Cuesta segundos.

**Cómo verificarlo**: `make check` con 9 casos.

#### G16 · Dependencias y toolchain de la CI (baja)

**Evidencia**:
- `tp/kmeans/go.mod:3` dice `go 1.22` sin línea `toolchain`, y `.github/workflows/go.yml:36` usa
  `go-version-file`, así que la CI instala Go 1.22.x, mientras que los JSON son de `go1.26.7`.
- `go.yml:31,34`, `tp-data.yml:24,27` y `tp-spin.yml:28` fijan las acciones por tag
  (`astral-sh/setup-uv@v5` es de terceros).
- `tp-data.yml:32` corre `uv sync --extra dev` sin `--locked`.
- Los `permissions: contents: read` están bien.

**Impacto**: la CI prueba con un compilador distinto del que produjo las cifras. Un tag movido en
una acción de terceros cambia lo que corre, y un `uv.lock` desactualizado se re-resuelve en
silencio.

**Recomendación**: `toolchain go1.26.7` en `go.mod`, acciones fijadas por SHA y
`uv sync --locked --extra dev`.

**Cómo verificarlo**: que el paso *Setup Go* de la CI muestre `go1.26.7`, y que `uv sync --locked`
falle si se modifica `pyproject.toml` sin re-lockear.

#### G17 · Código duplicado (baja)

**Evidencia**: `diff tp/kmeans/cmd/benchmark/argumentos.go tp/kmeans/cmd/kmeans/argumentos.go` no
muestra diferencias, y solo el de `cmd/kmeans` tiene test. En `tp/scripts/kmeans_gpu.py:173-206`, la
media recortada y el bootstrap están reimplementados, y el percentil superior usa
`int(0.975*replicas)` (índice 1950 con 2000 réplicas) donde Go (`estadistica.go:137`) usa
`round(p*(n-1))` (1949).

**Impacto**: un arreglo en un `argumentos.go` no llega al otro. Los intervalos de confianza de GPU y
CPU no se calculan exactamente con el mismo estimador, aunque la diferencia es mínima.

**Recomendación**: mover `argumentos` a un paquete compartido `internal/cli` e igualar la regla de
percentil en Python.

**Cómo verificarlo**: `TestArgumentos…` sobre el paquete compartido, y un test en Python que
compare el intervalo con un caso calculado en Go.

#### G18 · La caché `.npy` se invalida solo por fecha (baja)

**Evidencia**: `tp/scripts/kmeans_gpu.py:77-78`.

```python
if cache.exists() and cache.stat().st_mtime >= ruta.stat().st_mtime:
    return np.load(cache)
```

El JSON registra `sha256_archivo(args.datos)` (`:433`), que es el hash del CSV y no el de lo que se
procesó.

**Impacto**: si se copia un gold distinto que conserva una fecha anterior (`rsync -a`, `cp -p`), se
usa la caché vieja y el JSON declara el sha del CSV nuevo.

**Recomendación**: guardar el sha256 del CSV junto a la caché y compararlo, o registrar en el JSON
el hash de la matriz cargada.

**Cómo verificarlo**: reemplazar el CSV con `touch -d` a una fecha anterior y comprobar que se
regenera la caché.

### Fortalezas

- **Reducción determinista.** Reducir en orden de bloque da resultados idénticos bit a bit para
  cualquier P; lo prueba `TestConcurrenteDaElMismoResultadoParaCualquierP`, y los JSON muestran una
  sola inercia por configuración de CPU en 126 corridas.
- **Sincronización correcta y mínima.** `pool.Add` va antes de lanzar, `barrera.Add` antes de
  encolar, y `close` + `Wait` en un `defer` (`concurrente.go:69-87`): no quedan goroutines vivas
  aunque `AlIterar` haga *panic*, y no hay asignaciones en el lazo caliente. `go test -race` y
  `go vet` pasan.
- **Una verificación formal que prueba algo.** Cada propiedad tiene su mutante, y `check.sh` exige
  el número de errores, el tipo de error y que la fórmula sea el *never claim* activo, lo que cubre
  las tres trampas de `pan`.
- **Entradas estrictas.** La cabecera del gold se valida completa y en orden, NaN e Inf se rechazan
  al cargar, y los centroides hacen ida y vuelta con `%.17g` y se identifican con un hash por bits.
- **Un pipeline auditable.** La auditoría independiente en DuckDB usa parámetros en vez de SQL
  armado a mano, la cascada de reglas suma exactamente lo descartado, los tests no usan red
  (`file://`) y las tablas del informe se generan desde los JSON.

### Comandos que corrió el agente

| Comando | Resultado |
|---|---|
| `cd tp/kmeans && go vet ./...` | Sin salida (OK). |
| `go test -race -count=1 ./...` | `ok kmeans`, `ok cmd/kmeans`, `cmd/benchmark [no test files]`; los 3 tests que usan el gold real se saltan porque falta el CSV. |
| `diff cmd/benchmark/argumentos.go cmd/kmeans/argumentos.go` | Sin diferencias. |
| Script en Python sobre `tp/reports/benchmark_*.json` | Todas las `fijas` con `max_iter` 10; laptop y Pixel con `arbol_sucio=true`; una sola inercia por configuración de CPU. |
| Script en Python sobre `tp/reports/gpu_wsl4060_*.json` | fp64 n=2 831 486: 8 inercias distintas en 21 corridas; fp32: 9. |
| `go run ./cmd/benchmark -datos tiny.csv -experimentos fija …` (copia, CSV sintético de 2000 filas) | Corre 10 iteraciones etiquetadas `fija`. |
| `go run ./cmd/benchmark -datos tiny.csv -repes 1 …` | `error: hacen falta al menos 2 observaciones, hay 1`, exit 1, sin JSON. |
| `go test -race -run TestGap -v ./...` (tests temporales en la copia) | Tolerancias en 0 con MaxIter=10: 2 iteraciones, `paro=tolerancia`. Cabecera enorme: `panic: makeslice`. Fuera de git: `commit="" arbol_sucio=false`. NaN en X: `err=nil paro=tolerancia`. k reducido: la 2.ª corrida falla con `tienen k=2 y se pidió -k 3`. |
| `go test -bench FalseSharing -benchtime 10x -count 5` (copia con variante con relleno) | k=4: ~252 frente a ~221 ms; k=8: ~347 frente a ~348 ms; k=12: ~482 frente a ~477 ms. |
| `./check.sh` en una copia de `tp/spin` | `== regresión OK: 7 casos ==`. |
| Variantes de `kmeans.pml` con otros N, C y P (copia) | N4 C2 P3: 0 errores, 11 814 estados; N6 C3 P2: 0, 9 579; N6 C3 P3: 0, 136 782. |

### Comandos que corrió el grupo para el contraste

| Comando | Resultado |
|---|---|
| Recorrido de los metadatos de `tp/reports/benchmark_*.json` | 10 de 12 sin `commit`; laptop y Pixel con `arbol_sucio=true`. |
| Conteo de inercias distintas en `gpu_wsl4060_fijas.json` | fp64: 8 valores; fp32: 9. |
| Benchmark propio de *false sharing* (2²¹ puntos, P=8, chunk=16384), las dos variantes alternadas 8 veces | k=4: 254,7-268,1 ms actual frente a 221,1-224,8 ms con relleno. |
| Lectura de `benchmark/main.go:188-220`, `ingest.py:20-30`, `secuencial.go:160-175`, `inicializacion.go:122-132`, `go.mod`, workflows | Coincide con la evidencia citada. |
| `diff -q` de los dos `argumentos.go` | Idénticos. |

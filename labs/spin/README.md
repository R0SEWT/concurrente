# labs/spin

Modelos Promela verificados con [Spin](https://spinroot.com). Acá se verifica el
**algoritmo**; en `../go/` se prueba la **implementación**. El curso pide ambos.

## Instalación

Spin no está empaquetado ni en Fedora ni en Ubuntu — se compila desde fuente:

```bash
./bootstrap.sh          # clona, compila e instala en ~/.local/bin (sin sudo, ~10 s)
spin -V                 # Spin Version 6.5.2 -- 18 September 2025
```

Necesita `gcc`, `make` y `bison`. Ninguna distro trae el binario `yacc` que el
makefile de Spin espera; el script lo suple con `bison -y`.

El binario pesa **894 KB** y su única dependencia es `libc`, así que también se
copia con `scp` a otra máquina (verificado: un binario compilado en Fedora 43
corre sin cambios en Ubuntu 24.04).

## Uso

```bash
make verify MODEL=critical                       # safety: aserciones
make verify MODEL=peterson CLAIM=exclusion       # una propiedad LTL nombrada
make fair   MODEL=peterson CLAIM=sin_inanicion   # liveness: necesita fairness
make trail  MODEL=critical                       # reproduce el contraejemplo
make check                                       # regresión: los 3 casos de abajo
```

Resultados esperados (los verifica `make check`):

| modelo | propiedad | flags | esperado |
|---|---|---|---|
| `critical.pml` | `assert(n == 2)` | — | **errors: 1** — encuentra el incremento perdido |
| `peterson.pml` | `exclusion` | `-N exclusion` | **errors: 0** — 64 estados |
| `peterson.pml` | `sin_inanicion` | `-f -N sin_inanicion` | **errors: 0** — 116 estados |

## Cómo funciona

Spin **no ejecuta** el modelo: genera un verificador en C especializado en él.

```
peterson.pml --[ spin -a ]--> pan.c --[ cc ]--> ./pan --> errors: 0
```

Por eso hace falta un compilador de C para verificar, y por eso `pan`, `pan.*` y
`*.trail` están gitignoreados: son artefactos que se regeneran desde el `.pml`.

## Cómo leer un resultado

- `errors: 0` → la propiedad se cumple **en todos los estados alcanzables**. Es una
  prueba, no un muestreo; distinto de que `go test` pase.
- `assertion violated` / `acceptance cycle` → Spin escribió un `.trail`. `make trail`
  lo reproduce paso a paso: esa secuencia es el contraejemplo concreto.
- Si el reporte dice que la búsqueda no se completó, el `errors: 0` **no vale**:
  el espacio de estados no cupo en memoria. Sube los límites con `MEM="-m100000 -w26"`.

## Dos trampas que ya nos mordieron

**1. El `-N` va en `pan`, no en `spin`.** `spin -N` espera un *archivo* con un never
claim; con `ltl` inline falla con un error de preprocesador confuso. La forma correcta
es `spin -a modelo.pml` y después `./pan -a -N nombre`. El propio Spin lo dice al
generar `pan.c`: *"choose which one with ./pan -a -N name"*.

**2. Liveness sin `-f` da falsos positivos.** `sin_inanicion` "falla" con un acceptance
cycle si no habilitas fairness débil — el contraejemplo es una corrida donde un proceso
simplemente nunca se planifica. Eso es un defecto del scheduler modelado, no del
algoritmo de Peterson. Con `-f` (target `make fair`) da 0 errores.

## Dónde correr esto

**Local, no en gorgo.** La verificación es *memory-bound*: el límite real es la
explosión del espacio de estados, no el CPU. La laptop tiene 15 GB de RAM contra los
9.1 GB de gorgo, así que mandar un modelo grande a gorgo lo empeora. gorgo sirve para
los benchmarks de Go de la Unidad 2 (11 núcleos vs 8) y para la investigación con GPU.

Si aun así necesitas verificar allá: `scp` el binario de `~/.local/bin/spin` (gorgo no
tiene `bison` ni `flex` para compilarlo, pero sí `gcc` para el `pan.c`).

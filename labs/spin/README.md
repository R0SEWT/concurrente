# labs/spin

Modelos Promela verificados con [Spin](https://spinroot.com). Acá se verifica el
**algoritmo**; en `../go/` se prueba la **implementación**. El curso pide ambos.

## Requisitos

```bash
spin -V || echo "instalar: sudo dnf install spin  (o https://spinroot.com/spin/Man/README.html)"
```

Spin genera un verificador en C (`pan.c`), así que hace falta un compilador C.

## Uso

```bash
make verify MODEL=critical              # falla: encuentra el incremento perdido
make trail  MODEL=critical              # reproduce el entrelazado culpable

make verify MODEL=peterson CLAIM=exclusion       # safety: pasa
make fair   MODEL=peterson CLAIM=sin_inanicion   # liveness: necesita -f
```

## Cómo leer un resultado

- `errors: 0` → la propiedad se cumple **en todos los estados alcanzables**. Es una
  prueba, no un muestreo; distinto de que `go test` pase.
- `assertion violated` / `acceptance cycle` → Spin escribió un `.trail`. `make trail`
  lo reproduce paso a paso: esa secuencia es el contraejemplo concreto.
- Si el reporte dice que el espacio de estados se truncó (`hash factor` bajo, o
  "search not completed"), el `errors: 0` no vale — sube la memoria con `./pan -m` o `-w`.

## Notas

- **Liveness necesita `-f`** (fairness débil). Sin él, Spin "refuta" cualquier propiedad
  de progreso exhibiendo una corrida donde un proceso nunca es planificado — eso es un
  defecto del scheduler modelado, no del algoritmo.
- Un solo never-claim a la vez: con varios `ltl` en el archivo, selecciona con
  `spin -a -N <nombre>` (el `CLAIM=` del Makefile).
- `pan`, `pan.*` y `*.trail` son artefactos regenerables y están gitignoreados.

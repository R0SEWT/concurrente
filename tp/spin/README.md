# Modelo Promela de la sincronización del K-means

Verifica el *algoritmo* de sincronización de `tp/kmeans/concurrente.go` sobre
**todos** los entrelazados posibles. El test en Go verifica la implementación;
Spin verifica el diseño. El curso pide las dos cosas y ninguna reemplaza a la otra.

```bash
make check     # regresión completa: 7 casos, cada uno con su número y tipo de error esperado
make verify    # el modelo correcto sin fórmulas: aserciones y deadlock
make ltl       # el modelo correcto contra las fórmulas exclusion y termina
make trail     # lee el contraejemplo del mutante de la carrera
make informe   # salidas de pan, tabla de los 7 casos y figuras para tp/informe/tp/
```

`make figuras` y `make informe` escriben en el informe del TP. El de la PC2 quedó congelado en el
tag `pc2`: si hiciera falta regenerarlo, `make figuras INFORME=pc2`, desde ese tag.

## Qué se modela

Un dominio chiquito —4 puntos, 2 chunks, 2 workers, 2 iteraciones— sin
distancias, centroides reales ni punto flotante. Lo que importa es el esqueleto:
el canal que reparte chunks entre workers persistentes, los acumuladores
privados por chunk, la barrera del final de cada iteración y la publicación de
centroides nuevos.

**Dos iteraciones, no una**: los errores de reutilizar la barrera o de no
reiniciar los acumuladores no se ven en la primera.

## Qué se verifica

| Propiedad | Cómo |
|---|---|
| Cada punto se procesa **exactamente una vez** | `seen[i] == 1` al final de cada iteración |
| Los centroides no se escriben mientras se leen | `assert(escribiendo == 0)` en los workers, `assert(lectores == 0)` antes de publicar |
| La reducción conserva los puntos | `total == N` |
| No hay deadlock | estados finales válidos, que `pan` comprueba por su cuenta |

Sobre la primera: **sumar los conteos no alcanza**. Procesar A dos veces y
omitir B da exactamente el mismo total, así que un `assert(suma == N)` pasaría
con un bug de cobertura. Por eso se cuenta por punto.

## El mutante

`make mutante` compila el mismo archivo con `-DMUTANTE`, que reemplaza el
acumulador privado por uno compartido y separa la lectura de la escritura
(`tmp = compartido; tmp++; compartido = tmp`). Si la lectura y la escritura
fueran un solo enunciado, Promela lo ejecutaría de forma indivisible y la
carrera quedaría escondida.

Spin encuentra el contraejemplo: `assertion violated (compartido==4)`.

Esto es lo que le da valor a que el modelo correcto dé 0 errores: si el mutante
también pasara, el modelo no estaría probando nada.

## Resultados (Spin 6.5.2, búsqueda exhaustiva completada)

| | Estados | Transiciones | Profundidad | Errores |
|---|---|---|---|---|
| Correcto | 2412 | 3234 | 181 | **0** |
| Mutante | 393 | 435 | 209 | **1** |

Corridas sin fórmulas LTL (`-DNOCLAIM`). La PC2 midió 2407 y 391 estados, antes de sumar la
variable `fin` del Entregable 3. Vector de estado de 56 bytes; 0,4 MB de memoria para estados. La búsqueda
termina sin recortes: no hace falta `bitstate` ni aproximaciones.

## Hasta dónde llega esta prueba

La conclusión vale **para este modelo y estos parámetros**: 4 puntos, 2 chunks,
2 workers, 2 iteraciones. No es una demostración del programa en Go para
cualquier tamaño. Lo que sí descarta es toda una clase de errores —pérdida o
duplicación de puntos, escritura de centroides durante la lectura, barrera mal
reutilizada— sobre todos los entrelazados de ese dominio, que es exactamente lo
que ningún test puede hacer, porque el test observa un entrelazado por corrida.

## Entregable 3: deadlock, exclusión mutua y progreso

El enunciado del TP pide verificar formalmente la **ausencia de deadlocks** y la
**exclusión mutua**. El modelo lo hace de dos formas complementarias: las aserciones
de arriba y dos fórmulas LTL.

```promela
ltl exclusion { [] !(escribiendo && lectores > 0) }   /* nunca se publica con lectores */
ltl termina   { <> fin }                              /* las ITERS iteraciones terminan */
```

- **Deadlock.** Es un estado final inválido: algún proceso quedó bloqueado fuera de
  una etiqueta `end`. Los workers esperando trabajo están bajo `end:`, que marca como
  legítima esa espera. Si la barrera nunca llega a cero, el que queda bloqueado es
  `init`, y `pan` lo reporta.
- **Exclusión mutua.** El escritor es el coordinador, que publica centroides con
  `escribiendo = 1`. Los lectores son los workers mientras asignan, contados en
  `lectores`. La fórmula exige que las dos cosas no pasen nunca a la vez, en ningún
  entrelazado.
- **Progreso.** `<> fin` con **weak fairness** (`pan -a -f`): ningún proceso que queda
  habilitado para siempre se posterga para siempre. Es la hipótesis que da el
  planificador de Go para goroutines ejecutables.

### Cada propiedad con su mutante

| Variante | Corrida | Errores | Qué encuentra Spin |
|---|---|---|---|
| correcto | sin LTL (`-DNOCLAIM`) | **0** | 2412 estados; aserciones y estados finales válidos |
| correcto | `-a -N exclusion` | **0** | 2412 estados |
| correcto | `-a -f -N termina` | **0** | 2412 estados, 12 643 visitados con fairness |
| `MUTANTE` | sin LTL | **1** | `assertion violated (compartido==4)`: incremento perdido |
| `MUTANTE_DEADLOCK` | sin LTL | **1** | `invalid end state` a profundidad 64: la barrera queda en `pendientes = 1` y `init` bloqueado |
| `MUTANTE_DEADLOCK` | `-a -f -N termina` | **1** | `acceptance cycle`: la corrida nunca llega a `fin` |
| `MUTANTE_SIN_BARRERA` | `-a -N exclusion` | **1** | la fórmula `exclusion` se viola a profundidad 295 |

- `MUTANTE_DEADLOCK`: un worker se salta el `wg.Done` del último chunk, que en Go es un
  `return` temprano antes del `Done`.
- `MUTANTE_SIN_BARRERA`: el coordinador publica sin `wg.Wait`.

`make check` (`check.sh`) corre los siete casos. Para cada uno exige el número de errores
**y** el tipo de error: que un mutante falle por otra razón también es una falla del
modelo.

### Tres trampas de pan que check.sh deja cubiertas

1. **Con fórmulas LTL en el archivo, `pan` sin `-N` usa la primera** y desactiva la
   búsqueda de estados finales inválidos (`invalid end states - (disabled by never
   claim)`). Una corrida de «seguridad» dejaba entonces de detectar deadlocks sin avisar.
   `pan -noclaim` no existe y se ignora en silencio. Lo que sí sirve es compilar con
   `-DNOCLAIM`.
2. **`pan -N nombre` con un nombre que no existe no verifica nada y da `errors: 0`.**
   Pasó al escribir `check.sh` antes que las fórmulas: los casos del modelo correcto
   «pasaban». Ahora el script exige que la fórmula figure como el never claim activo.
3. **`-A` también apaga la fórmula.** Spin traduce una propiedad de seguridad `[] p` a
   un never claim con un `assert` adentro (`spin -f '!([] p)'` lo muestra). Para aislar
   la fórmula del resto de las aserciones, el mutante sin barrera se salta también su
   `assert(lectores == 0)`, y el tipo de error esperado nombra la fórmula.

### Hasta dónde llega

Las mismas cotas de arriba: 4 puntos, 2 chunks, 2 workers, 2 iteraciones. El progreso
se prueba bajo weak fairness, no para cualquier planificador. El cierre del pool
(`close(trabajos)` y `pool.Wait()`) no está modelado: los workers terminan bloqueados
en el canal, lo que el modelo declara legítimo con `end:`.

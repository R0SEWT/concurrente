# Modelo Promela de la sincronización del K-means

Verifica el *algoritmo* de sincronización de `tp/kmeans/concurrente.go` sobre
**todos** los entrelazados posibles. El test en Go verifica la implementación;
Spin verifica el diseño. El curso pide las dos cosas y ninguna reemplaza a la otra.

```bash
make check     # regresión completa: 0 errores en el correcto, 1 en el mutante
make verify    # solo el modelo correcto
make trail     # lee el contraejemplo del mutante
```

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
| Correcto | 2407 | 3229 | 180 | **0** |
| Mutante | 391 | 433 | 208 | **1** |

Vector de estado de 56 bytes; 0,4 MB de memoria para estados. La búsqueda
termina sin recortes: no hace falta `bitstate` ni aproximaciones.

## Hasta dónde llega esta prueba

La conclusión vale **para este modelo y estos parámetros**: 4 puntos, 2 chunks,
2 workers, 2 iteraciones. No es una demostración del programa en Go para
cualquier tamaño. Lo que sí descarta es toda una clase de errores —pérdida o
duplicación de puntos, escritura de centroides durante la lectura, barrera mal
reutilizada— sobre todos los entrelazados de ese dominio, que es exactamente lo
que ningún test puede hacer, porque el test observa un entrelazado por corrida.

Para el Entregable 3 quedan pendientes las propiedades de progreso (que toda
iteración termine), que necesitan declarar sus hipótesis de fairness.

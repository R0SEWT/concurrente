# Procedimiento de limpieza — NYC TLC yellow 2024-01

Este documento explica **por qué** existe cada regla. Los **números** de la última corrida están
en [`reports/limpieza_yellow_2024-01.md`](../reports/limpieza_yellow_2024-01.md), que se regenera
con `uv run nyc-tlc all`.

## 1. Selección del dataset

| Decisión | Valor | Motivo |
|---|---|---|
| Fuente | NYC TLC Trip Record Data (oficial) | Son datos reales, públicos, con diccionario de datos, y los usa mucha literatura de movilidad. |
| Flota | Yellow taxi | Es la flota con mejor cobertura de Manhattan. Mezclar flotas (green, FHV) cambia el esquema y la población de viajes. |
| Periodo | Enero 2024 (un mes) | Tiene 2,96 M de viajes crudos: supera el mínimo de 1 M con holgura y se procesa en ~2 min. El mes se cambia en `configs/limpieza.toml`. |
| Formato | Parquet (bronze) → Parquet (silver) → CSV (gold) | TLC solo publica Parquet. Go no lo lee sin librerías de terceros, y el enunciado exige Go puro, así que gold es CSV (`encoding/csv`). |

## 2. Reglas bronze → silver

Las reglas se aplican **en cascada**, en este orden. Cada viaje descartado se atribuye a la primera
regla que falla, así el total de descartes es exactamente la diferencia entre bronze y silver.

| # | Regla | Condición para quedarse | Por qué |
|---|---|---|---|
| 1 | `requeridos` | Sin nulos en pickup, dropoff, distancia, zonas, tarifa y total | Sin esos campos no se puede validar ni construir features. Los nulos en columnas que **no** usamos no descartan nada (ver §3). |
| 2 | `mes` | El pickup está en `[2024-01-01, 2024-02-01)` | El archivo mensual trae viajes sueltos de otros meses (incluso de años atrás), por errores de reloj del taxímetro. |
| 3 | `duracion` | Entre 60 s y 6 h | Una duración ≤ 0 es imposible. Menos de 1 min corresponde a pruebas de taxímetro o anulaciones. Más de 6 h es un taxímetro que quedó corriendo. |
| 4 | `distancia` | En (0, 100] millas | Distancia 0 significa viaje anulado o GPS sin datos. El p99,9 está en ~30 mi y el máximo crudo en 312.722 mi, que es un error de registro. 100 mi deja margen para aeropuertos y las afueras. |
| 5 | `velocidad` | Velocidad media ≤ 80 mph | Duración y distancia pueden ser plausibles por separado e imposibles juntas: 50 mi en 5 min pasan las reglas 3 y 4. |
| 6 | `montos` | Tarifa > 0 y total > 0 | Los montos negativos son reembolsos o anulaciones que TLC registra como filas espejo del viaje original. |
| 7 | `zonas` | Origen y destino ∈ zonas ubicables del lookup | Las zonas 264 (`Unknown`) y 265 (`Outside of NYC`) no se pueden ubicar. El análisis por zona que viene después las necesita. Las zonas válidas salen del `taxi_zone_lookup.csv`, no de una lista escrita a mano. |

## 3. Qué **no** se limpia, y por qué

- **Nulos de Flex Fare.** 140.162 viajes con `payment_type = 0` (Flex Fare, según el diccionario de
  2024) traen `RatecodeID`, `passenger_count` y `store_and_fwd_flag` nulos. Son viajes reales y
  ninguna de esas columnas entra al modelo. Descartarlos borraría el 4,7 % de los datos sin motivo.
- **`passenger_count = 0` y `RatecodeID = 99`.** Son errores de captura en campos que no usamos.
- **Duplicados exactos.** Verificamos que no hay (0 en 2024-01), así que no hace falta una regla.
- **Outliers "legítimos"** (un viaje largo a Newark, una tarifa negociada alta). Las reglas quitan
  lo imposible, no lo inusual. Los extremos plausibles se amortiguan en gold con escala log.

## 4. Verificación

1. **Tests en los bordes** (`tests/test_rules.py`): para cada regla, el valor justo en el umbral se
   queda y el siguiente se va, sobre viajes con el esquema completo de 19 columnas.
2. **Auditoría independiente**: DuckDB re-implementa las 7 reglas en SQL y cuenta violaciones.
   Sobre silver, las 7 dan **0**. Si Polars y DuckDB discreparan, una de las dos implementaciones
   estaría mal.
3. **Procedencia**: el reporte guarda el sha256 del Parquet de bronze. Otra persona que corra el
   pipeline puede comprobar que partió del mismo archivo.

## 5. Features para K-means (gold, provisionales)

| Feature | Construcción | Por qué |
|---|---|---|
| `hora_sin`, `hora_cos` | Hora del pickup (con minutos) llevada al círculo de 24 h | Con la hora cruda, las 23:00 y la 01:00 quedarían a 22 h de distancia; en el círculo quedan a 2 h. |
| `dia_sin`, `dia_cos` | Día de la semana (lunes = 0) en el círculo de 7 días | Mismo motivo: domingo y lunes son vecinos. |
| `log_duracion_z` | z-score de `log1p(duración en min)` | La duración tiene cola larga. Sin escalar, dominaría la distancia euclídea por su unidad. |
| `log_distancia_z` | z-score de `log1p(millas)` | Igual que la duración. |

`PULocationID` y `DOLocationID` viajan en gold **pero no son features**, porque un ID de zona no es
una coordenada. Sirven para agregar las asignaciones de cluster por zona. `viaje_id` es la posición
del viaje en silver, para volver a los datos originales.

Estas features son una propuesta de PC1 y se revisan en PC2 junto con la implementación del K-means.

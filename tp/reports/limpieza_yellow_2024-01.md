# Limpieza NYC TLC — yellow 2024-01

Generado por `uv run nyc-tlc all`. No editar a mano: se regenera en cada corrida.

## Procedencia

| Archivo | Bytes | sha256 |
|---|---:|---|
| [yellow_tripdata_2024-01.parquet](https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet) | 49,961,641 | `c4d59da7bbc8abaeeeb1727947ee93d9891a71acb42854bd80db1571b2030510` |
| [taxi_zone_lookup.csv](https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv) | 12,331 | `1a99e105092230f8620f301edcca7f80d3080642ff404d28ed957d3fa222c8ed` |

## Reglas (en cascada)

Cada viaje descartado se atribuye a la **primera** regla que falla, así las filas suman.

| Regla | Condición para quedarse | Descartados | % de bronze | Restantes |
|---|---|---:|---:|---:|
| **bronze** | archivo original | | | 2,964,624 |
| `requeridos` | Sin nulos en las columnas que usa el pipeline | 0 | 0.00 % | 2,964,624 |
| `mes` | El viaje empieza dentro de 2024-01 (el archivo trae fechas sueltas de otros meses) | 18 | 0.00 % | 2,964,606 |
| `duracion` | Duración entre 60 s y 21600 s | 36,893 | 1.24 % | 2,927,713 |
| `distancia` | Distancia en (0, 100] millas | 36,284 | 1.22 % | 2,891,429 |
| `velocidad` | Velocidad media ≤ 80 mph | 100 | 0.00 % | 2,891,329 |
| `montos` | Tarifa y total positivos (los negativos son reembolsos o anulaciones) | 32,272 | 1.09 % | 2,859,057 |
| `zonas` | Origen y destino son zonas conocidas de NYC (sin 'Unknown' ni 'Outside of NYC') | 27,571 | 0.93 % | 2,831,486 |
| **silver** | | 133,138 | 4.49 % | **2,831,486** |

Mínimo del enunciado: 1,000,000 registros limpios → **cumple**.

## Auditoría independiente (DuckDB)

Las mismas reglas reescritas en SQL. En bronze el conteo no es exclusivo (un viaje puede
violar varias); en silver todas deben dar 0.

| Regla | Violaciones en bronze | Violaciones en silver |
|---|---:|---:|
| `requeridos` | 0 | 0 |
| `mes` | 18 | 0 |
| `duracion` | 36,893 | 0 |
| `distancia` | 60,430 | 0 |
| `velocidad` | 1,921 | 0 |
| `montos` | 38,341 | 0 |
| `zonas` | 31,527 | 0 |

## Escalado de features (gold)

| Feature | Media | Desv. (poblacional) |
|---|---:|---:|
| `log_duracion` | 2.558154 | 0.638942 |
| `log_distancia` | 1.170440 | 0.656089 |

# tp — Trabajo Parcial CC65: K-means concurrente sobre NYC TLC

Raíz independiente dentro de `concurrente` (como `labs/go`): tiene su propio toolchain (uv) y su
propio CI. Las tareas se siguen en los beads del repo padre: `concurrente-41o` (PC1), `concurrente-3r8` (PC2) y `concurrente-r0p` (TB1), con sus hijos.

## Domain / Scientific Context

- **Problem**: el TP pide un algoritmo de ML concurrente en Go (sin librerías de terceros) sobre un
  dataset de más de 1M de registros, ligado a un ODS. El equipo eligió K-means sobre viajes de taxi
  para estudiar patrones de movilidad urbana (ODS 11). La decisión y su diseño están en
  `concurrente-41o.1`; la discusión, en la PR #4 y en la issue #5.
- **Outcome / target**: aprendizaje no supervisado, sin variable objetivo. El producto de esta
  etapa es un **dataset limpio y documentado** (rúbrica de PC1: 3 pts por el procedimiento de
  limpieza y el dataset limpio) y las features que consume el K-means en Go.
- **Data provenance**: datos públicos de la NYC Taxi & Limousine Commission,
  [TLC Trip Record Data](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page),
  servidos por su CDN en CloudFront. Flota **yellow**, mes **2024-01** (`configs/limpieza.toml`).
  No son datos propios ni peruanos. TLC re-publica meses corregidos, así que cada corrida registra
  el sha256 del archivo en `reports/`. El diccionario de datos define los timestamps como hora local
  de NYC sin zona horaria.

## Architecture

```bash
uv sync --extra dev
uv run nyc-tlc all      # bronze → silver → gold + reports/
uv run pytest -q        # reglas, features y pipeline completo (sin red)
```

| Capa | Qué contiene | Dónde |
|---|---|---|
| bronze | Archivos de TLC tal cual: Parquet del mes + `taxi_zone_lookup.csv`. Inmutables: no se re-descargan si existen. | `data/bronze/` |
| silver | Viajes que pasan las 7 reglas, con las **columnas originales** del Parquet. | `data/silver/<flota>_<mes>.parquet` |
| gold | CSV para Go: `viaje_id`, zonas (no son features) y 6 features estandarizadas. | `data/gold/<flota>_<mes>_features.csv` |
| reports | Evidencia versionada: procedencia, conteo por regla, auditoría y escalado. | `reports/limpieza_<flota>_<mes>.{json,md}` |

Polars aplica las reglas en cascada. **DuckDB las re-verifica en SQL** como auditoría
independiente: en silver todas deben dar 0 violaciones. Si las dos implementaciones discrepan, hay
un bug en una de ellas.

## Key Files

| File | Purpose |
|------|---------|
| `configs/limpieza.toml` | Mes, flota, URLs y umbrales de las reglas. Cambiarlo regenera todo. |
| `src/nyc_tlc/rules.py` | Las 7 reglas bronze → silver y la cascada con conteo por regla. |
| `src/nyc_tlc/audit.py` | Las mismas reglas en SQL (DuckDB), como verificación independiente. |
| `src/nyc_tlc/features.py` | silver → gold: hora y día en el círculo, log + z-score de duración y distancia. |
| `src/nyc_tlc/pipeline.py` | Orquesta las capas y escribe el reporte. |
| `docs/limpieza.md` | El porqué de cada regla, para el informe de PC1. |
| `reports/limpieza_yellow_2024-01.md` | Los números de la última corrida. Se genera, no se edita. |
| `kmeans/` | Módulo Go del K-means (PC2): secuencial, concurrente con worker pool, `cmd/kmeans` y `cmd/benchmark`. Su diseño está en `docs/kmeans.md`; el análisis, en `docs/analisis-pc2.md`. |
| `scripts/tablas_informe.py` | Genera las tablas y cifras del informe de la PC2 desde `reports/benchmark_*.json`. |
| `scripts/kmeans_gpu.py` | Lloyd en GPU con PyTorch, mismo contrato que `kmeans/`, para el contraste del TB1. Se corre en `ssh gpu` con `scripts/gpu/correr_remoto.sh`; cómo y por qué, en `docs/kmeans-gpu.md`. |
| `scripts/analisis_gpu.py` | Tablas del contraste GPU vs CPU desde `reports/gpu_*.json` y el benchmark de Go de la misma máquina. |

## Data Conventions

- **Layers**: raw → `data/bronze/`, cleaned → `data/silver/`, analytic → `data/gold/`. Todo
  gitignoreado; `reports/` sí se versiona.
- **Polars en vez de pandas**; DuckDB para SQL sobre Parquet (auditoría y exploración).
- **Nombres reales del Parquet** en bronze y silver (`tpep_pickup_datetime`, `PULocationID`, ...).
  Los nombres en español aparecen recién en gold.
- **Los timestamps quedan naive** (hora local de NYC por especificación). Por eso ruff ignora `DTZ`.

## Conventions

- **TDD**: cada regla tiene tests en sus bordes (el valor del umbral se queda, el siguiente se va),
  con fixtures del esquema completo de 19 columnas. El pipeline se prueba de punta a punta con un
  bronze en miniatura servido por `file://`.
- **Un nulo solo descarta el viaje si está en una columna que usamos.** Las 140 mil filas de Flex
  Fare (`payment_type = 0`) traen nulos en `RatecodeID`/`passenger_count` y se conservan.
- **Los notebooks se versionan SIN salidas.** Un `.ipynb` ejecutado pesa megas por las imágenes
  embebidas, hace ilegible el diff y nada garantiza que sus salidas correspondan al código.
  `tests/test_notebooks.py` lo verifica en CI. Antes de commitear:
  `uv run jupyter nbconvert --clear-output --inplace notebooks/*.ipynb`.
  Las figuras que van al informe se exportan como archivos aparte (`reports/figuras/`).
- **Los IDs de zona nunca entran a la distancia euclídea**: van en gold solo para agregar por zona
  después del clustering.
- **Las features de gold son provisionales** (PC1). Se revisan en PC2 junto con el K-means en Go;
  si cambian, se cambia `features.py` con su test primero.
- **Memoria**: el mes completo usa ~1.8 GB de RSS y tarda ~2 min, casi todo en la descarga. Corre
  bien en la laptop. Para varios meses, ver la memoria `gorgo-specs-y-reparto-de-carga` antes de
  mover la carga (gorgo tiene menos RAM).

"""Features silver → gold para K-means sobre viajes.

- Hora del día y día de la semana van al círculo (seno, coseno): así las 23:00 y la 01:00 quedan
  a 2 h de distancia y no a 22 h, que es lo que haría la distancia euclídea sobre la hora cruda.
- Duración y distancia tienen colas largas: se pasan a log1p y se estandarizan (z-score con
  desviación poblacional) para que ninguna domine la distancia euclídea por su unidad.
- Los IDs de zona NO son features (un ID no es una coordenada). Viajan en gold solo para
  agregar las asignaciones por zona después del clustering; `viaje_id` es la fila de silver.
"""

import math

import polars as pl

FEATURES = ("hora_sin", "hora_cos", "dia_sin", "dia_cos", "log_duracion_z", "log_distancia_z")
COLUMNAS_GOLD = ("viaje_id", "PULocationID", "DOLocationID", *FEATURES)

_TAU = 2 * math.pi


def construir_features(silver: pl.DataFrame) -> tuple[pl.DataFrame, dict]:
    pickup = pl.col("tpep_pickup_datetime")
    hora = pickup.dt.hour() + pickup.dt.minute() / 60 + pickup.dt.second() / 3600
    dia = pickup.dt.weekday() - 1  # polars: lunes=1 … domingo=7 → 0…6
    duracion_min = (pl.col("tpep_dropoff_datetime") - pickup).dt.total_seconds() / 60

    base = silver.select(
        pl.int_range(pl.len(), dtype=pl.Int64).alias("viaje_id"),
        pl.col("PULocationID"),
        pl.col("DOLocationID"),
        (hora * _TAU / 24).sin().alias("hora_sin"),
        (hora * _TAU / 24).cos().alias("hora_cos"),
        (dia * _TAU / 7).sin().alias("dia_sin"),
        (dia * _TAU / 7).cos().alias("dia_cos"),
        duracion_min.log1p().alias("log_duracion"),
        pl.col("trip_distance").log1p().alias("log_distancia"),
    )

    escalado = {}
    for col in ("log_duracion", "log_distancia"):
        media = base[col].mean()
        desv = base[col].std(ddof=0)
        escalado[col] = {"media": media, "desv": desv}
        # sin variación no hay nada que estandarizar; dividir por 0 metería NaN al CSV de Go
        z = (pl.col(col) - media) / desv if desv > 0 else pl.lit(0.0)
        base = base.with_columns(z.alias(f"{col}_z"))

    return base.select(COLUMNAS_GOLD), escalado

"""Fixtures con el esquema real de yellow_tripdata (19 columnas, mismos tipos que el Parquet de TLC)."""

from datetime import datetime, timedelta

import polars as pl
import pytest

ESQUEMA_TLC = {
    "VendorID": pl.Int32,
    "tpep_pickup_datetime": pl.Datetime("us"),
    "tpep_dropoff_datetime": pl.Datetime("us"),
    "passenger_count": pl.Int64,
    "trip_distance": pl.Float64,
    "RatecodeID": pl.Int64,
    "store_and_fwd_flag": pl.String,
    "PULocationID": pl.Int32,
    "DOLocationID": pl.Int32,
    "payment_type": pl.Int64,
    "fare_amount": pl.Float64,
    "extra": pl.Float64,
    "mta_tax": pl.Float64,
    "tip_amount": pl.Float64,
    "tolls_amount": pl.Float64,
    "improvement_surcharge": pl.Float64,
    "total_amount": pl.Float64,
    "congestion_surcharge": pl.Float64,
    "Airport_fee": pl.Float64,
}

INICIO = datetime(2024, 1, 15, 8, 0, 0)


def viaje(**cambios):
    """Un viaje válido de 12 min y 2 mi dentro de Manhattan; `cambios` pisa campos puntuales.

    `duracion_s` es un atajo para fijar el dropoff relativo al pickup.
    """
    duracion_s = cambios.pop("duracion_s", 12 * 60)
    pickup = cambios.get("tpep_pickup_datetime", INICIO)
    fila = {
        "VendorID": 2,
        "tpep_pickup_datetime": pickup,
        "tpep_dropoff_datetime": (pickup or INICIO) + timedelta(seconds=duracion_s),
        "passenger_count": 1,
        "trip_distance": 2.0,
        "RatecodeID": 1,
        "store_and_fwd_flag": "N",
        "PULocationID": 161,
        "DOLocationID": 237,
        "payment_type": 1,
        "fare_amount": 14.2,
        "extra": 1.0,
        "mta_tax": 0.5,
        "tip_amount": 3.0,
        "tolls_amount": 0.0,
        "improvement_surcharge": 1.0,
        "total_amount": 22.2,
        "congestion_surcharge": 2.5,
        "Airport_fee": 0.0,
    }
    fila.update(cambios)
    return fila


def viajes(*filas):
    return pl.DataFrame(list(filas), schema=ESQUEMA_TLC)


@pytest.fixture
def params():
    from nyc_tlc.rules import ParametrosLimpieza

    return ParametrosLimpieza(
        mes="2024-01",
        duracion_min_s=60,
        duracion_max_s=21600,
        distancia_max_mi=100,
        velocidad_max_mph=80,
        zonas_validas=frozenset(range(1, 264)),
    )

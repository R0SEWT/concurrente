"""Reglas de limpieza bronze → silver.

Cada regla es una condición de *permanencia*: el viaje se queda si la cumple. Se aplican en
cascada y cada viaje descartado se atribuye a la primera regla que falla, así el reporte suma
exactamente lo que se perdió entre bronze y silver.
"""

from dataclasses import dataclass
from datetime import datetime

import polars as pl

# Columnas que usa el pipeline (limpieza, features y análisis por zona). Un nulo en ellas deja
# al viaje sin información; los nulos en el resto (p. ej. Flex Fare) no justifican descartarlo.
COLUMNAS_REQUERIDAS = (
    "tpep_pickup_datetime",
    "tpep_dropoff_datetime",
    "trip_distance",
    "PULocationID",
    "DOLocationID",
    "fare_amount",
    "total_amount",
)


@dataclass(frozen=True)
class ParametrosLimpieza:
    mes: str  # "AAAA-MM"
    duracion_min_s: int
    duracion_max_s: int
    distancia_max_mi: float
    velocidad_max_mph: float
    zonas_validas: frozenset[int]


@dataclass(frozen=True)
class Regla:
    id: str
    descripcion: str
    condicion: pl.Expr


def limites_del_mes(mes: str) -> tuple[datetime, datetime]:
    anio, m = (int(x) for x in mes.split("-"))
    inicio = datetime(anio, m, 1)
    fin = datetime(anio + 1, 1, 1) if m == 12 else datetime(anio, m + 1, 1)
    return inicio, fin


def construir_reglas(p: ParametrosLimpieza) -> list[Regla]:
    pickup = pl.col("tpep_pickup_datetime")
    duracion_s = (pl.col("tpep_dropoff_datetime") - pickup).dt.total_seconds()
    distancia = pl.col("trip_distance")
    inicio, fin = limites_del_mes(p.mes)
    zonas = list(p.zonas_validas)

    return [
        Regla(
            "requeridos",
            "Sin nulos en las columnas que usa el pipeline",
            pl.all_horizontal(pl.col(c).is_not_null() for c in COLUMNAS_REQUERIDAS),
        ),
        Regla(
            "mes",
            f"El viaje empieza dentro de {p.mes} (el archivo trae fechas sueltas de otros meses)",
            (pickup >= inicio) & (pickup < fin),
        ),
        Regla(
            "duracion",
            f"Duración entre {p.duracion_min_s} s y {p.duracion_max_s} s",
            duracion_s.is_between(p.duracion_min_s, p.duracion_max_s),
        ),
        Regla(
            "distancia",
            f"Distancia en (0, {p.distancia_max_mi}] millas",
            (distancia > 0) & (distancia <= p.distancia_max_mi),
        ),
        Regla(
            "velocidad",
            f"Velocidad media ≤ {p.velocidad_max_mph} mph",
            distancia / (duracion_s / 3600) <= p.velocidad_max_mph,
        ),
        Regla(
            "montos",
            "Tarifa y total positivos (los negativos son reembolsos o anulaciones)",
            (pl.col("fare_amount") > 0) & (pl.col("total_amount") > 0),
        ),
        Regla(
            "zonas",
            "Origen y destino son zonas conocidas de NYC (sin 'Unknown' ni 'Outside of NYC')",
            pl.col("PULocationID").is_in(zonas) & pl.col("DOLocationID").is_in(zonas),
        ),
    ]


def aplicar_reglas(df: pl.DataFrame, reglas: list[Regla]) -> tuple[pl.DataFrame, list[dict]]:
    conteos = []
    for regla in reglas:
        antes = df.height
        df = df.filter(regla.condicion)
        conteos.append(
            {
                "regla": regla.id,
                "descripcion": regla.descripcion,
                "descartados": antes - df.height,
                "restantes": df.height,
            }
        )
    return df, conteos

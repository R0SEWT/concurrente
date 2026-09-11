"""Auditoría independiente en DuckDB.

Las mismas reglas de `rules.py`, reescritas en SQL con otro motor. Sobre bronze cuenta cuántos
viajes viola cada regla (conteo no exclusivo: un viaje puede violar varias); sobre silver todo
debe dar 0. Si una regla de Polars estuviera mal escrita, las dos implementaciones discreparían.
"""

from pathlib import Path

import duckdb

from nyc_tlc.rules import COLUMNAS_REQUERIDAS, ParametrosLimpieza, limites_del_mes


def auditar(parquet: Path, p: ParametrosLimpieza) -> dict[str, int]:
    inicio, fin = limites_del_mes(p.mes)
    dur = "(epoch(tpep_dropoff_datetime) - epoch(tpep_pickup_datetime))"
    condiciones = {
        "requeridos": " and ".join(f"{c} is not null" for c in COLUMNAS_REQUERIDAS),
        "mes": f"tpep_pickup_datetime >= '{inicio}' and tpep_pickup_datetime < '{fin}'",
        "duracion": f"{dur} between {p.duracion_min_s} and {p.duracion_max_s}",
        "distancia": f"trip_distance > 0 and trip_distance <= {p.distancia_max_mi}",
        "velocidad": f"trip_distance / ({dur} / 3600.0) <= {p.velocidad_max_mph}",
        "montos": "fare_amount > 0 and total_amount > 0",
        "zonas": "list_contains($zonas, PULocationID) and list_contains($zonas, DOLocationID)",
    }
    # un nulo en la condición cuenta como violación, igual que en el filtro de Polars
    columnas = ", ".join(
        f"count(*) filter (where not coalesce({cond}, false)) as {regla}"
        for regla, cond in condiciones.items()
    )
    fila = duckdb.execute(
        f"select {columnas} from read_parquet($ruta)",
        {"ruta": str(parquet), "zonas": sorted(p.zonas_validas)},
    ).fetchone()
    return dict(zip(condiciones, fila, strict=True))

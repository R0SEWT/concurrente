"""Auditoría independiente en DuckDB.

Las mismas reglas de `rules.py`, reescritas en SQL con otro motor. Sobre bronze cuenta cuántos
viajes viola cada regla (conteo no exclusivo: un viaje puede violar varias); sobre silver todo
debe dar 0. Si una regla de Polars estuviera mal escrita, las dos implementaciones discreparían.
"""

from pathlib import Path

import duckdb

from nyc_tlc.rules import COLUMNAS_REQUERIDAS, ParametrosLimpieza, limites_del_mes

_DURACION = "(epoch(tpep_dropoff_datetime) - epoch(tpep_pickup_datetime))"

# El SQL solo contiene nombres de columnas (constantes de este módulo). Todo valor que venga de
# la configuración entra como parámetro de DuckDB, con su tipo forzado por el cast.
_CONDICIONES = {
    "requeridos": " and ".join(f"{c} is not null" for c in COLUMNAS_REQUERIDAS),
    "mes": "tpep_pickup_datetime >= $inicio::TIMESTAMP and tpep_pickup_datetime < $fin::TIMESTAMP",
    "duracion": f"{_DURACION} between $dmin::DOUBLE and $dmax::DOUBLE",
    "distancia": "trip_distance > 0 and trip_distance <= $distmax::DOUBLE",
    "velocidad": f"trip_distance / ({_DURACION} / 3600.0) <= $vmax::DOUBLE",
    "montos": "fare_amount > 0 and total_amount > 0",
    "zonas": "list_contains($zonas::INTEGER[], PULocationID)"
    " and list_contains($zonas::INTEGER[], DOLocationID)",
}
# un nulo en la condición cuenta como violación, igual que en el filtro de Polars
_SQL = "select {} from read_parquet($ruta)".format(
    ", ".join(
        f"count(*) filter (where not coalesce({cond}, false)) as {regla}"
        for regla, cond in _CONDICIONES.items()
    )
)


def auditar(parquet: Path, p: ParametrosLimpieza) -> dict[str, int]:
    inicio, fin = limites_del_mes(p.mes)
    # nosemgrep va sin ID porque semgrep y opengrep nombran distinto la regla que silencia:
    # python.sqlalchemy.security.sqlalchemy-execute-raw-query. Dispara por la forma
    # execute(<no literal>), pero _SQL es constante (solo nombres de columnas) y los valores van
    # como parámetros; test_audit.py lo verifica. Discusión en la PR #6.
    fila = duckdb.execute(  # nosemgrep
        _SQL,
        {
            "ruta": str(parquet),
            "inicio": inicio,
            "fin": fin,
            "dmin": p.duracion_min_s,
            "dmax": p.duracion_max_s,
            "distmax": p.distancia_max_mi,
            "vmax": p.velocidad_max_mph,
            "zonas": sorted(p.zonas_validas),
        },
    ).fetchone()
    return dict(zip(_CONDICIONES, fila, strict=True))

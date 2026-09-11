"""La auditoría en DuckDB recibe los umbrales como parámetros, nunca como texto dentro del SQL."""

from dataclasses import replace

import duckdb
import pytest
from conftest import viaje, viajes

from nyc_tlc.audit import auditar


@pytest.fixture
def parquet(tmp_path):
    ruta = tmp_path / "viajes.parquet"
    # 8.1 mi en 6 min = 81 mph: viola la regla de velocidad
    viajes(viaje(), viaje(trip_distance=8.1, duracion_s=360)).write_parquet(ruta)
    return ruta


def test_cuenta_la_violacion_de_velocidad(params, parquet):
    assert auditar(parquet, params)["velocidad"] == 1


def test_un_umbral_que_no_es_numero_no_puede_reescribir_la_consulta(params, parquet):
    # interpolado en el SQL quedaría "<= 80 or true" y la regla dejaría de contar en silencio
    malicioso = replace(params, velocidad_max_mph="80 or true")
    with pytest.raises(duckdb.Error):
        auditar(parquet, malicioso)

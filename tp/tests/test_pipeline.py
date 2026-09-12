"""Pipeline completo sobre un bronze en miniatura servido por file:// (sin red)."""

import csv
import hashlib
import json
from datetime import datetime

import polars as pl
import pytest
from conftest import viaje, viajes

from nyc_tlc.cli import main
from nyc_tlc.features import COLUMNAS_GOLD

ZONAS_CSV = (
    '"LocationID","Borough","Zone","service_zone"\n'
    '48,"Manhattan","Clinton East","Yellow Zone"\n'
    '132,"Queens","JFK Airport","Airports"\n'
    '161,"Manhattan","Midtown Center","Yellow Zone"\n'
    '237,"Manhattan","Upper East Side South","Yellow Zone"\n'
    '264,"Unknown","N/A","N/A"\n'
    '265,"N/A","Outside of NYC","N/A"\n'
)


@pytest.fixture
def entorno(tmp_path):
    remoto = tmp_path / "remoto"
    remoto.mkdir()
    viajes(
        viaje(),
        viaje(PULocationID=132, DOLocationID=48, trip_distance=17.0, duracion_s=45 * 60),
        viaje(tpep_pickup_datetime=datetime(2023, 12, 31, 23)),  # mes
        viaje(duracion_s=-60),  # duración
        viaje(fare_amount=-14.2, total_amount=-22.2),  # montos
        viaje(DOLocationID=265),  # zona fuera de NYC aunque figure en el lookup
        viaje(payment_type=0, RatecodeID=None, passenger_count=None, store_and_fwd_flag=None),
    ).write_parquet(remoto / "yellow_tripdata_2024-01.parquet")
    (remoto / "taxi_zone_lookup.csv").write_text(ZONAS_CSV)

    config = tmp_path / "limpieza.toml"
    config.write_text(
        f"""
[fuente]
flota = "yellow"
mes = "2024-01"
url_viajes = "file://{remoto}/{{flota}}_tripdata_{{mes}}.parquet"
url_zonas = "file://{remoto}/taxi_zone_lookup.csv"

[reglas]
duracion_min_s = 60
duracion_max_s = 21600
distancia_max_mi = 100
velocidad_max_mph = 80
"""
    )
    raiz = tmp_path / "proyecto"
    raiz.mkdir()
    return {"remoto": remoto, "config": config, "raiz": raiz}


def correr(entorno):
    main(["all", "--config", str(entorno["config"]), "--raiz", str(entorno["raiz"])])
    return json.loads((entorno["raiz"] / "reports/limpieza_yellow_2024-01.json").read_text())


def test_de_bronze_a_gold_quedan_solo_los_viajes_validos(entorno):
    reporte = correr(entorno)

    assert reporte["filas"] == {"bronze": 7, "silver": 3, "gold": 3}
    silver = pl.read_parquet(entorno["raiz"] / "data/silver/yellow_2024-01.parquet")
    assert silver.height == 3
    assert sorted(silver["PULocationID"].to_list()) == [132, 161, 161]


def test_el_reporte_suma_exactamente_lo_que_se_perdio(entorno):
    reporte = correr(entorno)

    por_regla = {r["regla"]: r["descartados"] for r in reporte["reglas"]}
    assert por_regla == {
        "requeridos": 0,
        "mes": 1,
        "duracion": 1,
        "distancia": 0,
        "velocidad": 0,
        "montos": 1,
        "zonas": 1,
    }


def test_gold_es_un_csv_con_el_contrato_que_lee_go(entorno):
    correr(entorno)

    with open(entorno["raiz"] / "data/gold/yellow_2024-01_features.csv", newline="") as f:
        filas = list(csv.reader(f))
    assert filas[0] == list(COLUMNAS_GOLD)
    assert len(filas) == 1 + 3
    assert all(celda not in ("", "NaN", "inf") for fila in filas[1:] for celda in fila)


def test_el_reporte_registra_la_procedencia_con_sha256(entorno):
    reporte = correr(entorno)

    esperado = hashlib.sha256(
        (entorno["remoto"] / "yellow_tripdata_2024-01.parquet").read_bytes()
    ).hexdigest()
    assert reporte["fuente"]["viajes"]["sha256"] == esperado
    assert reporte["fuente"]["viajes"]["url"].endswith("yellow_tripdata_2024-01.parquet")
    assert reporte["parametros"]["velocidad_max_mph"] == 80


def test_la_auditoria_independiente_en_duckdb_no_encuentra_violaciones_en_silver(entorno):
    reporte = correr(entorno)

    assert reporte["auditoria"]["bronze"]["mes"] == 1
    assert reporte["auditoria"]["bronze"]["zonas"] == 1
    assert set(reporte["auditoria"]["silver"].values()) == {0}


def test_con_pocas_filas_el_reporte_marca_que_no_cumple_el_minimo_del_enunciado(entorno):
    reporte = correr(entorno)

    assert reporte["minimo_requerido"] == 1_000_000
    assert reporte["cumple_minimo"] is False


def test_el_reporte_markdown_lista_cada_regla_con_su_conteo(entorno):
    correr(entorno)

    md = (entorno["raiz"] / "reports/limpieza_yellow_2024-01.md").read_text()
    for regla in ("requeridos", "mes", "duracion", "distancia", "velocidad", "montos", "zonas"):
        assert f"| `{regla}` |" in md
    assert "| **silver** |" in md


def test_una_segunda_corrida_no_vuelve_a_descargar_lo_que_ya_esta_en_bronze(entorno):
    primero = correr(entorno)
    # si el pipeline re-descargara, tomaría este archivo cambiado y el sha256 sería otro
    viajes(viaje()).write_parquet(entorno["remoto"] / "yellow_tripdata_2024-01.parquet")
    segundo = correr(entorno)

    assert segundo["fuente"]["viajes"]["sha256"] == primero["fuente"]["viajes"]["sha256"]
    assert segundo["filas"]["bronze"] == 7


def test_si_ninguna_fila_sobrevive_el_pipeline_igual_deja_gold_y_reporte(entorno):
    viajes(viaje(fare_amount=-1.0), viaje(DOLocationID=264)).write_parquet(
        entorno["remoto"] / "yellow_tripdata_2024-01.parquet"
    )
    reporte = correr(entorno)

    assert reporte["filas"] == {"bronze": 2, "silver": 0, "gold": 0}
    with open(entorno["raiz"] / "data/gold/yellow_2024-01_features.csv", newline="") as f:
        assert list(csv.reader(f)) == [list(COLUMNAS_GOLD)]
    md = (entorno["raiz"] / "reports/limpieza_yellow_2024-01.md").read_text()
    assert "NO cumple" in md

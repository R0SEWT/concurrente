"""Features de gold: lo que lee K-means en Go. Valores esperados calculados a mano."""

from datetime import datetime

import pytest
from conftest import viaje, viajes

from nyc_tlc.features import COLUMNAS_GOLD, construir_features


def fila_gold(**cambios):
    gold, _ = construir_features(viajes(viaje(**cambios)))
    return gold.row(0, named=True)


@pytest.mark.parametrize(
    ("hora", "minuto", "sin", "cos"),
    [
        (0, 0, 0.0, 1.0),
        (6, 0, 1.0, 0.0),
        (12, 0, 0.0, -1.0),
        (23, 0, -0.258819, 0.965926),  # 2π·23/24
        (1, 30, 0.382683, 0.923880),  # 1.5 h → 2π·1.5/24 = π/8
    ],
)
def test_la_hora_se_codifica_en_el_circulo(hora, minuto, sin, cos):
    f = fila_gold(tpep_pickup_datetime=datetime(2024, 1, 15, hora, minuto))
    assert f["hora_sin"] == pytest.approx(sin, abs=1e-6)
    assert f["hora_cos"] == pytest.approx(cos, abs=1e-6)


def test_las_23h_y_la_01h_quedan_cerca_aunque_sus_numeros_esten_lejos():
    g, _ = construir_features(
        viajes(
            viaje(tpep_pickup_datetime=datetime(2024, 1, 15, 23)),
            viaje(tpep_pickup_datetime=datetime(2024, 1, 16, 1)),
            viaje(tpep_pickup_datetime=datetime(2024, 1, 16, 12)),
        )
    )
    s, c = g["hora_sin"].to_list(), g["hora_cos"].to_list()

    def d(i, j):
        return ((s[i] - s[j]) ** 2 + (c[i] - c[j]) ** 2) ** 0.5

    assert d(0, 1) == pytest.approx(0.517638, abs=1e-6)  # cuerda de 2 h: 2·sin(π/12)
    assert d(0, 2) > 1.9


@pytest.mark.parametrize(
    ("fecha", "sin", "cos"),
    [
        (datetime(2024, 1, 15, 8), 0.0, 1.0),  # lunes → 0
        (datetime(2024, 1, 21, 8), -0.781831, 0.623490),  # domingo → 6: 2π·6/7
    ],
)
def test_el_dia_de_la_semana_se_codifica_en_el_circulo(fecha, sin, cos):
    f = fila_gold(tpep_pickup_datetime=fecha)
    assert f["dia_sin"] == pytest.approx(sin, abs=1e-6)
    assert f["dia_cos"] == pytest.approx(cos, abs=1e-6)


def test_duracion_y_distancia_se_estandarizan_en_escala_log():
    # duraciones de 3, 12 y 48 min; distancias de 1, 2 y 3 mi
    g, escalado = construir_features(
        viajes(
            viaje(duracion_s=180, trip_distance=1.0),
            viaje(duracion_s=720, trip_distance=2.0),
            viaje(duracion_s=2880, trip_distance=3.0),
        )
    )
    # log1p(3)=1.386294, log1p(12)=2.564949, log1p(48)=3.891820 → media 2.614355
    assert escalado["log_duracion"]["media"] == pytest.approx(2.614355, abs=1e-6)
    # desviación poblacional (ddof=0): 1.023473
    assert escalado["log_duracion"]["desv"] == pytest.approx(1.023473, abs=1e-6)
    assert g["log_duracion_z"].to_list() == pytest.approx(
        [-1.199895, -0.048272, 1.248167], abs=1e-6
    )
    assert g["log_distancia_z"].mean() == pytest.approx(0.0, abs=1e-12)


def test_sin_variacion_el_z_score_es_cero_y_no_nan():
    f = fila_gold()
    assert f["log_duracion_z"] == 0.0
    assert f["log_distancia_z"] == 0.0


def test_gold_trae_ids_para_volver_a_silver_y_solo_features_numericas():
    g, _ = construir_features(viajes(viaje(PULocationID=132, DOLocationID=48), viaje()))
    assert g.columns == list(COLUMNAS_GOLD)
    assert g["viaje_id"].to_list() == [0, 1]
    assert g.row(0, named=True)["PULocationID"] == 132
    assert g.row(0, named=True)["DOLocationID"] == 48

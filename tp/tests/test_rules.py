"""Cada regla de limpieza en sus bordes: el valor justo en el umbral se queda, el siguiente se va."""

from datetime import datetime

import pytest
from conftest import viaje, viajes

from nyc_tlc.rules import aplicar_reglas, construir_reglas


def sobrevive(params, **cambios) -> bool:
    limpio, _ = aplicar_reglas(viajes(viaje(**cambios)), construir_reglas(params))
    return limpio.height == 1


def test_un_viaje_valido_sobrevive_a_todas_las_reglas(params):
    assert sobrevive(params)


@pytest.mark.parametrize(
    ("pickup", "queda"),
    [
        (datetime(2023, 12, 31, 23, 59, 59), False),
        (datetime(2024, 1, 1, 0, 0, 0), True),
        (datetime(2024, 1, 31, 23, 59, 59), True),
        (datetime(2024, 2, 1, 0, 0, 0), False),
        (datetime(2009, 1, 1, 0, 0, 0), False),
    ],
)
def test_solo_quedan_viajes_que_empiezan_dentro_del_mes(params, pickup, queda):
    assert sobrevive(params, tpep_pickup_datetime=pickup) is queda


@pytest.mark.parametrize(
    ("duracion_s", "queda"),
    [(-120, False), (0, False), (59, False), (60, True), (21600, True), (21601, False)],
)
def test_duracion_entre_un_minuto_y_seis_horas(params, duracion_s, queda):
    # distancia corta para que la regla de velocidad no interfiera en los bordes
    assert sobrevive(params, duracion_s=duracion_s, trip_distance=0.5) is queda


@pytest.mark.parametrize(
    ("distancia", "queda"),
    [(0.0, False), (-1.0, False), (0.01, True), (100.0, True), (100.01, False)],
)
def test_distancia_positiva_y_acotada(params, distancia, queda):
    # 6 h de viaje: 100 mi / 6 h ≈ 16.7 mph, así la velocidad no decide el caso
    assert sobrevive(params, trip_distance=distancia, duracion_s=21600) is queda


@pytest.mark.parametrize(
    ("distancia", "duracion_s", "queda"),
    [(8.0, 360, True), (8.1, 360, False), (10.0, 360, False)],  # 8 mi en 6 min = 80 mph
)
def test_velocidad_media_implausible_se_descarta(params, distancia, duracion_s, queda):
    assert sobrevive(params, trip_distance=distancia, duracion_s=duracion_s) is queda


@pytest.mark.parametrize(
    ("tarifa", "total", "queda"),
    [(14.2, 22.2, True), (0.0, 8.0, False), (-14.2, -22.2, False), (14.2, 0.0, False)],
)
def test_montos_positivos(params, tarifa, total, queda):
    assert sobrevive(params, fare_amount=tarifa, total_amount=total) is queda


@pytest.mark.parametrize(
    ("origen", "destino", "queda"),
    [(1, 263, True), (264, 161, False), (161, 265, False), (0, 161, False)],
)
def test_origen_y_destino_deben_ser_zonas_conocidas(params, origen, destino, queda):
    assert sobrevive(params, PULocationID=origen, DOLocationID=destino) is queda


@pytest.mark.parametrize(
    "columna",
    [
        "tpep_pickup_datetime",
        "tpep_dropoff_datetime",
        "trip_distance",
        "PULocationID",
        "DOLocationID",
        "fare_amount",
        "total_amount",
    ],
)
def test_nulo_en_una_columna_que_usamos_descarta_el_viaje(params, columna):
    assert sobrevive(params, **{columna: None}) is False


def test_nulos_de_flex_fare_en_columnas_que_no_usamos_no_descartan(params):
    # payment_type 0 (Flex Fare) trae RatecodeID, passenger_count y store_and_fwd_flag nulos
    assert sobrevive(
        params, payment_type=0, RatecodeID=None, passenger_count=None, store_and_fwd_flag=None
    )


def test_el_reporte_atribuye_cada_viaje_descartado_a_la_primera_regla_que_falla(params):
    df = viajes(
        viaje(),
        viaje(tpep_pickup_datetime=datetime(2023, 12, 31, 12)),  # fuera del mes
        viaje(tpep_pickup_datetime=datetime(2023, 12, 31, 12), fare_amount=-1.0),  # dos fallas
        viaje(fare_amount=-5.0, total_amount=-5.0),  # montos
        viaje(PULocationID=264),  # zona
    )
    limpio, conteos = aplicar_reglas(df, construir_reglas(params))

    assert limpio.height == 1
    por_regla = {c["regla"]: c["descartados"] for c in conteos}
    assert por_regla["mes"] == 2
    assert por_regla["montos"] == 1
    assert por_regla["zonas"] == 1
    assert sum(por_regla.values()) == 4
    assert [c["restantes"] for c in conteos][-1] == 1


def test_las_columnas_del_parquet_se_conservan_sin_renombrar(params):
    limpio, _ = aplicar_reglas(viajes(viaje()), construir_reglas(params))
    assert limpio.columns == viajes(viaje()).columns


def test_diciembre_cierra_en_enero_del_anio_siguiente(params):
    from dataclasses import replace

    diciembre = replace(params, mes="2024-12")
    assert sobrevive(diciembre, tpep_pickup_datetime=datetime(2024, 12, 31, 23, 50))
    assert not sobrevive(diciembre, tpep_pickup_datetime=datetime(2025, 1, 1, 0, 0))

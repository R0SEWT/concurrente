"""bronze → silver → gold, más el reporte que deja constancia de cada paso."""

import json
import tomllib
from pathlib import Path

import polars as pl

from nyc_tlc.audit import auditar
from nyc_tlc.features import construir_features
from nyc_tlc.ingest import descargar
from nyc_tlc.report import render_markdown
from nyc_tlc.rules import ParametrosLimpieza, aplicar_reglas, construir_reglas

MINIMO_ENUNCIADO = 1_000_000  # "dataset con más de 1MM de registros" (CC65_PCs_TP-202620)

# En el lookup de TLC, 264 es Borough "Unknown" y 265 es "N/A" (Outside of NYC).
BOROUGHS_NO_UBICABLES = ("Unknown", "N/A")


def zonas_validas(lookup_csv: Path) -> frozenset[int]:
    zonas = pl.read_csv(lookup_csv).filter(~pl.col("Borough").is_in(BOROUGHS_NO_UBICABLES))
    return frozenset(zonas["LocationID"].to_list())


def ejecutar(config_path: Path, raiz: Path) -> dict:
    cfg = tomllib.loads(Path(config_path).read_text())
    flota, mes = cfg["fuente"]["flota"], cfg["fuente"]["mes"]
    nombre = f"{flota}_{mes}"
    bronze_dir, silver_dir, gold_dir = (
        raiz / "data" / capa for capa in ("bronze", "silver", "gold")
    )
    reports_dir = raiz / "reports"

    # bronze: los archivos de TLC sin tocar
    url_viajes = cfg["fuente"]["url_viajes"].format(flota=flota, mes=mes)
    viajes_bronze = bronze_dir / url_viajes.rsplit("/", 1)[-1]
    fuente = {
        "flota": flota,
        "mes": mes,
        "viajes": descargar(url_viajes, viajes_bronze),
        "zonas": descargar(cfg["fuente"]["url_zonas"], bronze_dir / "taxi_zone_lookup.csv"),
    }

    # silver: viajes que pasan todas las reglas, con las columnas originales del Parquet
    params = ParametrosLimpieza(
        mes=mes, **cfg["reglas"], zonas_validas=zonas_validas(bronze_dir / "taxi_zone_lookup.csv")
    )
    bronze = pl.read_parquet(viajes_bronze)
    silver, conteos = aplicar_reglas(bronze, construir_reglas(params))
    silver_dir.mkdir(parents=True, exist_ok=True)
    silver_path = silver_dir / f"{nombre}.parquet"
    silver.write_parquet(silver_path)

    # gold: features para K-means en Go (CSV legible con encoding/csv de la stdlib)
    gold, escalado = construir_features(silver)
    gold_dir.mkdir(parents=True, exist_ok=True)
    gold.write_csv(gold_dir / f"{nombre}_features.csv", float_precision=6)

    reporte = {
        "fuente": fuente,
        "parametros": {"mes": mes, **cfg["reglas"], "zonas_validas": len(params.zonas_validas)},
        "filas": {"bronze": bronze.height, "silver": silver.height, "gold": gold.height},
        "reglas": conteos,
        "auditoria": {
            "bronze": auditar(viajes_bronze, params),
            "silver": auditar(silver_path, params),
        },
        "escalado": escalado,
        "minimo_requerido": MINIMO_ENUNCIADO,
        "cumple_minimo": silver.height > MINIMO_ENUNCIADO,
    }
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / f"limpieza_{nombre}.json").write_text(
        json.dumps(reporte, indent=2, ensure_ascii=False) + "\n"
    )
    (reports_dir / f"limpieza_{nombre}.md").write_text(render_markdown(reporte))
    return reporte

import argparse
from pathlib import Path

from nyc_tlc.pipeline import ejecutar


def main(argv=None):
    parser = argparse.ArgumentParser(prog="nyc-tlc", description=__doc__)
    sub = parser.add_subparsers(dest="comando", required=True)
    todo = sub.add_parser("all", help="bronze → silver → gold + reporte")
    todo.add_argument("--config", type=Path, default=Path("configs/limpieza.toml"))
    todo.add_argument("--raiz", type=Path, default=Path("."))
    args = parser.parse_args(argv)

    r = ejecutar(args.config, args.raiz)
    f = r["filas"]
    print(
        f"bronze {f['bronze']:,} → silver {f['silver']:,} → gold {f['gold']:,} "
        f"({'cumple' if r['cumple_minimo'] else 'NO cumple'} el mínimo de "
        f"{r['minimo_requerido']:,})"
    )

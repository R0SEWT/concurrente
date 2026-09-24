#!/usr/bin/env python3
"""Convierte el JSON del benchmark en las tablas y series del informe.

Nada se transcribe a mano: las tablas de la PC2 salen de acá, y si se vuelve a
medir, se vuelven a generar. Usa solo la biblioteca estándar.

    python3 analisis_benchmark.py ../reports/benchmark_gorgo.json --formato md
    python3 analisis_benchmark.py ../reports/benchmark_gorgo.json --formato tex
    python3 analisis_benchmark.py ../reports/benchmark_gorgo.json --formato csv
"""

import argparse
import json
import sys
from pathlib import Path


def karp_flatt(speedup: float, p: int) -> float | None:
    """Fracción serial efectiva.

    Absorbe overhead de sincronización, desbalance y efectos de memoria: no es
    el porcentaje de líneas secuenciales del programa. Con p = 1 no está
    definida.
    """
    if p <= 1 or speedup <= 0:
        return None
    return (1 / speedup - 1 / p) / (1 - 1 / p)


def techo_amdahl(e: float | None) -> float | None:
    """Speedup máximo con infinitos workers, si la fracción serial fuera e."""
    if e is None or e <= 0:
        return None
    return 1 / e


def cargar(ruta: Path) -> dict:
    with ruta.open(encoding="utf-8") as f:
        return json.load(f)


def filas(inf: dict, experimento: str) -> list[dict]:
    out = []
    for r in inf["resumen"]:
        if r["experimento"] != experimento:
            continue
        p = r.get("workers", 0)
        sp = r.get("speedup")
        e = karp_flatt(sp["punto"], p) if sp and p > 1 else None
        out.append(
            {
                "n": r["tamano"],
                "modo": r["modo"],
                "p": p,
                "recortada_ms": r["media_recortada_ms"],
                "mediana_ms": r["mediana_ms"],
                "desv_ms": r["desviacion_ms"],
                "reps": r["repeticiones"],
                "speedup": sp["punto"] if sp else None,
                "ic_inf": sp["inferior"] if sp else None,
                "ic_sup": sp["superior"] if sp else None,
                "eficiencia": r.get("eficiencia_por_worker"),
                "karp_flatt": e,
                "techo": techo_amdahl(e),
                "iteraciones": r["iteraciones"],
                "inercia": r["inercia"],
            }
        )
    out.sort(key=lambda f: (f["n"], f["modo"] == "conc", f["p"]))
    return out


def fmt(v, dec=2, vacio="—"):
    return vacio if v is None else f"{v:.{dec}f}"


def tabla_md(fs: list[dict]) -> str:
    sal = [
        "| n | modo | P | media recortada | desv | speedup [IC 95%] | eficiencia | Karp–Flatt | techo |",
        "|---:|:--|---:|---:|---:|:--|---:|---:|---:|",
    ]
    for f in fs:
        ic = (
            f"{f['speedup']:.2f}x [{f['ic_inf']:.2f}, {f['ic_sup']:.2f}]"
            if f["speedup"]
            else "—"
        )
        efi = f"{100 * f['eficiencia']:.0f}%" if f["eficiencia"] else "—"
        sal.append(
            f"| {f['n']:,} | {f['modo']} | {f['p'] or '—'} | {f['recortada_ms']:.1f} ms "
            f"| {f['desv_ms']:.1f} ms | {ic} | {efi} | {fmt(f['karp_flatt'], 3)} | {fmt(f['techo'], 1)} |"
        )
    return "\n".join(sal)


def tabla_tex(fs: list[dict]) -> str:
    sal = [
        r"\begin{tabular}{rlrrrlrr}",
        r"\toprule",
        r"$n$ & modo & $P$ & recortada (ms) & desv. & speedup [IC 95\%] & eficiencia & Karp--Flatt \\",
        r"\midrule",
    ]
    for f in fs:
        ic = (
            f"{f['speedup']:.2f}$\\times$ [{f['ic_inf']:.2f}, {f['ic_sup']:.2f}]"
            if f["speedup"]
            else "---"
        )
        efi = f"{100 * f['eficiencia']:.0f}\\%" if f["eficiencia"] else "---"
        sal.append(
            f"{f['n']} & {f['modo']} & {f['p'] or '---'} & {f['recortada_ms']:.1f} & "
            f"{f['desv_ms']:.1f} & {ic} & {efi} & {fmt(f['karp_flatt'], 3, '---')} \\\\"
        )
    sal += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(sal)


def tabla_csv(fs: list[dict]) -> str:
    cols = [
        "n", "modo", "p", "recortada_ms", "mediana_ms", "desv_ms", "reps",
        "speedup", "ic_inf", "ic_sup", "eficiencia", "karp_flatt", "iteraciones", "inercia",
    ]
    lineas = [",".join(cols)]
    for f in fs:
        lineas.append(",".join("" if f[c] is None else str(f[c]) for c in cols))
    return "\n".join(lineas)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("json", type=Path)
    ap.add_argument("--experimento", default="fijas", choices=["fijas", "convergencia"])
    ap.add_argument("--formato", default="md", choices=["md", "tex", "csv"])
    args = ap.parse_args()

    inf = cargar(args.json)
    fs = filas(inf, args.experimento)
    if not fs:
        print(f"no hay filas del experimento {args.experimento}", file=sys.stderr)
        return 1

    m = inf["metadatos"]
    if args.formato != "csv":
        print(
            f"% {args.experimento} · {m['maquina']} · {m['version_go']} · "
            f"{m['cpus_logicas']} CPUs lógicas · commit {m.get('commit', '?')[:8]} · "
            f"{inf['protocolo']['repeticiones_medidas']} repeticiones, "
            f"recorte {inf['protocolo']['recorte_por_extremo']}"
        )
    print({"md": tabla_md, "tex": tabla_tex, "csv": tabla_csv}[args.formato](fs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

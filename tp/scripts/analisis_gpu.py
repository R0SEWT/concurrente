#!/usr/bin/env python3
"""Tablas del contraste GPU (PyTorch) contra CPU (Go) desde los JSON de tp/reports.

Junta el JSON de kmeans_gpu.py con el del benchmark de Go corrido en la MISMA
máquina y escribe, en Markdown o LaTeX:

  1. la tabla de configuraciones completas sobre el dataset completo (CPU
     secuencial, CPU concurrente por P, GPU fp64, GPU fp32), con speedup frente
     al secuencial y diferencia relativa de inercia;
  2. el barrido por tamaño: cuánto tarda cada plataforma según n y dónde la GPU
     empieza a pagar frente a la mejor CPU concurrente.

Como el resto del TP, ninguna cifra se transcribe a mano.

    python3 analisis_gpu.py reports/gpu_wsl4060_fijas.json --cpu reports/benchmark_wsl4060.json
    python3 analisis_gpu.py reports/gpu_wsl4060_fijas.json --cpu ... --formato tex
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cargar(ruta: Path) -> dict:
    return json.loads(ruta.read_text(encoding="utf-8"))


def fmt_sp(sp, dec=2) -> str:
    if not sp:
        return "—"
    return f"{sp['punto']:.{dec}f}x [{sp['inferior']:.{dec}f}, {sp['superior']:.{dec}f}]"


def cpu_filas(cpu: dict, exper: str, n: int) -> tuple[dict, list[dict]]:
    seq = next(
        r
        for r in cpu["resumen"]
        if r["experimento"] == exper and r["tamano"] == n and r["modo"] == "seq"
    )
    concs = sorted(
        (
            r
            for r in cpu["resumen"]
            if r["experimento"] == exper and r["tamano"] == n and r["modo"] == "conc"
        ),
        key=lambda r: r["workers"],
    )
    return seq, concs


# ------------------------------------------------------------------ tabla 1 ---


def tabla_completa(gpu: dict, cpu: dict | None) -> tuple[list[dict], float | None]:
    exper = gpu["protocolo"]["experimento"]
    n = gpu["datos"]["n"]
    filas, ref = [], None
    if cpu:
        seq, concs = cpu_filas(cpu, exper, n)
        ref = seq["inercia"]
        filas.append(
            {
                "config": "CPU Go secuencial",
                "detalle": "1 hilo, float64",
                "ms": seq["media_recortada_ms"],
                "desv": seq["desviacion_ms"],
                "it": seq["iteraciones"],
                "speedup": None,
                "inercia": seq["inercia"],
            }
        )
        for r in concs:
            filas.append(
                {
                    "config": f"CPU Go concurrente P={r['workers']}",
                    "detalle": f"worker pool, chunk {cpu['protocolo']['chunk']:,}, float64",
                    "ms": r["media_recortada_ms"],
                    "desv": r["desviacion_ms"],
                    "it": r["iteraciones"],
                    "speedup": r["speedup"],
                    "inercia": r["inercia"],
                }
            )
    for r in (r for r in gpu["resumen"] if r["tamano"] == n):
        filas.append(
            {
                "config": f"GPU PyTorch {r['precision']}",
                "detalle": f"{gpu['metadatos']['gpu']}, más {r['ms_h2d']:.0f} ms de transferencia",
                "ms": r["media_recortada_ms"],
                "desv": r["desviacion_ms"],
                "it": r["iteraciones"],
                "speedup": r.get("speedup_vs_cpu_secuencial"),
                "inercia": r["inercia"],
                "inercia_fp64": r.get("inercia_sumada_fp64"),
                "vs_conc": r.get("speedup_vs_cpu_concurrente"),
                "asig_distintas": r.get("asignaciones_distintas_entre_precisiones"),
            }
        )
    return filas, ref


def md_completa(filas: list[dict], ref: float | None, gpu: dict) -> str:
    def dif(v):
        return "—" if ref is None or v is None else f"{abs(v - ref) / ref:.1e}"

    sal = [
        "| Configuración | Detalle | Media recortada | Desv. | Iter. | Speedup vs seq [IC 95%] | Δ rel. inercia vs seq |",
        "|---|---|---:|---:|---:|:--|---:|",
    ]
    for f in filas:
        d = dif(f["inercia"])
        if f.get("inercia_fp64") is not None and f["config"].endswith("fp32"):
            d += f" (sumada en fp64: {dif(f['inercia_fp64'])})"
        sal.append(
            f"| {f['config']} | {f['detalle']} | {f['ms']:.1f} ms | {f['desv']:.1f} ms | {f['it']} | "
            f"{fmt_sp(f['speedup'])} | {d} |"
        )
    m, p = gpu["metadatos"], gpu["protocolo"]
    trabajo = (
        f"trabajo fijo de {p['max_iter']} iteraciones"
        if p["experimento"] == "fijas"
        else f"hasta convergencia (tolerancia {p['tol_rel']:g}, tope {p['max_iter']} iteraciones)"
    )
    sal += [
        "",
        (
            f"Máquina {m['maquina']}: {m['gpu']} ({m['gpu_memoria_mb']} MB, {m['gpu_sms']} SMs), "
            f"torch {m['torch']}, CUDA {m['cuda']}. "
            f"{p['repeticiones_medidas']} repeticiones medidas + {p['rondas_calentamiento']} de calentamiento, "
            f"media recortada al {p['recorte_por_extremo']:.0%}, IC por bootstrap de "
            f"{p['replicas_bootstrap']:,} réplicas, {trabajo} sobre {gpu['datos']['n']:,} viajes, "
            f"k={gpu['centroides_iniciales']['k']}, mismos centroides iniciales que la CPU."
        ),
    ]
    for f in filas:
        if f.get("vs_conc"):
            c = f["vs_conc"]
            sal.append(
                f"- {f['config']} frente a la mejor CPU concurrente (P={c['workers']}): {fmt_sp(c)}."
            )
    distintas = next(
        (f["asig_distintas"] for f in filas if f.get("asig_distintas") is not None), None
    )
    if distintas is not None:
        sal.append(
            f"- Asignaciones distintas entre fp64 y fp32: {distintas:,} de {gpu['datos']['n']:,} "
            f"({100 * distintas / gpu['datos']['n']:.2f} %)."
        )
    return "\n".join(sal)


# ------------------------------------------------------------------ tabla 2 ---


def tabla_tamanos(gpu: dict, cpu: dict) -> list[dict]:
    exper = gpu["protocolo"]["experimento"]
    filas = []
    for n in gpu["protocolo"]["tamanos"]:
        try:
            seq, concs = cpu_filas(cpu, exper, n)
        except StopIteration:
            continue
        mejor = max(concs, key=lambda r: r["speedup"]["punto"]) if concs else None
        g = {r["precision"]: r for r in gpu["resumen"] if r["tamano"] == n}
        filas.append(
            {
                "n": n,
                "seq_ms": seq["media_recortada_ms"],
                "conc_p": mejor["workers"] if mejor else None,
                "conc_ms": mejor["media_recortada_ms"] if mejor else None,
                "fp64_ms": g["fp64"]["media_recortada_ms"] if "fp64" in g else None,
                "fp32_ms": g["fp32"]["media_recortada_ms"] if "fp32" in g else None,
                "fp32_vs_seq": g.get("fp32", {}).get("speedup_vs_cpu_secuencial"),
                "fp32_vs_conc": g.get("fp32", {}).get("speedup_vs_cpu_concurrente"),
                "fp64_vs_conc": g.get("fp64", {}).get("speedup_vs_cpu_concurrente"),
            }
        )
    return filas


def md_tamanos(filas: list[dict]) -> str:
    def ms(v):
        return "—" if v is None else f"{v:.1f}"

    sal = [
        (
            "| n (viajes) | CPU seq (ms) | Mejor CPU conc (ms) | GPU fp64 (ms) | GPU fp32 (ms) | "
            "fp32 vs seq | fp32 vs mejor conc | fp64 vs mejor conc |"
        ),
        "|---:|---:|---:|---:|---:|:--|:--|:--|",
    ]
    for f in filas:
        conc = "—" if f["conc_ms"] is None else f"{f['conc_ms']:.1f} (P={f['conc_p']})"
        sal.append(
            f"| {f['n']:,} | {ms(f['seq_ms'])} | {conc} | {ms(f['fp64_ms'])} | {ms(f['fp32_ms'])} | "
            f"{fmt_sp(f['fp32_vs_seq'], 1)} | {fmt_sp(f['fp32_vs_conc'])} | {fmt_sp(f['fp64_vs_conc'])} |"
        )
    return "\n".join(sal)


# --------------------------------------------------------------------- tex ----


def num(v, dec=1):
    if v is None:
        return "---"
    return f"{v:,.{dec}f}".replace(",", "\0").replace(".", ",").replace("\0", ".")


def cientifica(v):
    if v is None:
        return "---"
    mant, exp = f"{v:.1e}".split("e")
    return f"${mant.replace('.', '{,}')} \\cdot 10^{{{int(exp)}}}$"


def sp_tex(s, dec=2):
    if not s:
        return "---"
    return f"{num(s['punto'], dec)}$\\times$ [{num(s['inferior'], dec)}; {num(s['superior'], dec)}]"


def tex_completa(filas: list[dict], ref: float | None) -> str:
    sal = [
        "\\begin{tabular}{@{}llrrlr@{}}",
        "\\toprule",
        (
            "\\textbf{Configuración} & \\textbf{Detalle} & \\textbf{Media rec. (ms)} & \\textbf{Desv.} & "
            "\\textbf{Speedup vs seq [IC 95\\,\\%]} & \\textbf{$\\Delta$ rel. inercia} \\\\"
        ),
        "\\midrule",
    ]
    for f in filas:
        d = None if ref is None else abs(f["inercia"] - ref) / ref
        sal.append(
            f"{f['config']} & {f['detalle']} & {num(f['ms'])} & {num(f['desv'])} & "
            f"{sp_tex(f['speedup'])} & {cientifica(d)} \\\\"
        )
    sal += ["\\bottomrule", "\\end{tabular}"]
    return "\n".join(sal)


def tex_tamanos(filas: list[dict]) -> str:
    sal = [
        "\\begin{tabular}{@{}rrrrrll@{}}",
        "\\toprule",
        (
            "\\textbf{$n$} & \\textbf{CPU seq (ms)} & \\textbf{Mejor CPU conc (ms)} & \\textbf{GPU fp64 (ms)} & "
            "\\textbf{GPU fp32 (ms)} & \\textbf{fp32 vs seq} & \\textbf{fp32 vs conc} \\\\"
        ),
        "\\midrule",
    ]
    for f in filas:
        conc = "---" if f["conc_ms"] is None else f"{num(f['conc_ms'])} ($P={f['conc_p']}$)"
        sal.append(
            f"{num(f['n'], 0)} & {num(f['seq_ms'])} & {conc} & {num(f['fp64_ms'])} & {num(f['fp32_ms'])} & "
            f"{sp_tex(f['fp32_vs_seq'], 1)} & {sp_tex(f['fp32_vs_conc'])} \\\\"
        )
    sal += ["\\bottomrule", "\\end{tabular}"]
    return "\n".join(sal)


# -------------------------------------------------------------------- main ----


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("gpu", type=Path)
    ap.add_argument("--cpu", type=Path, help="JSON de tp/kmeans/cmd/benchmark de la misma máquina")
    ap.add_argument("--formato", choices=["md", "tex"], default="md")
    args = ap.parse_args()

    gpu = cargar(args.gpu)
    cpu = cargar(args.cpu) if args.cpu else None
    filas, ref = tabla_completa(gpu, cpu)
    varios = cpu is not None and len(gpu["protocolo"]["tamanos"]) > 1
    if args.formato == "md":
        print(md_completa(filas, ref, gpu))
        if varios:
            print("\n" + md_tamanos(tabla_tamanos(gpu, cpu)))
    else:
        print(tex_completa(filas, ref))
        if varios:
            print("\n" + tex_tamanos(tabla_tamanos(gpu, cpu)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

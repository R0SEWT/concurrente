#!/usr/bin/env python3
"""K-means de Lloyd en GPU con PyTorch, con el MISMO contrato que tp/kmeans (Go).

Es el contraste del TB1 (concurrente-3r8.7): la misma entrada, los mismos
centroides iniciales materializados por la CLI de Go, el mismo k, las mismas
iteraciones y el mismo criterio de parada, para que la comparación sea entre
implementaciones y no entre algoritmos. Lo que cambia es la plataforma
(GPU frente a CPU), el lenguaje y la precisión (fp64 y fp32).

Contrato replicado de tp/kmeans/secuencial.go:
  - distancia euclídea al cuadrado, calculada como suma de (x - c)^2 y NO por la
    expansión ||x||^2 - 2 x.c + ||c||^2, que redondea distinto;
  - desempate: gana el centroide de menor índice (torch.min devuelve el primero);
  - actualización: c = s * (1/n), como en Go; un cluster vacío conserva su
    centroide anterior;
  - parada: max_j ||c_j(t) - c_j(t-1)||_inf <= tol_abs + tol_rel * max_j ||c_j(t-1)||_inf
    o max_iter, lo que ocurra primero;
  - la inercia que se reporta se recalcula con los centroides finales. En fp32
    se reporta además sumada en fp64, para separar el error de ACUMULAR 2,8
    millones de términos en simple precisión del efecto de las asignaciones
    que cambian.

Protocolo de medición, el de tp/kmeans/cmd/benchmark: repeticiones medidas más
un calentamiento que se descarta, orden barajado por ronda, media recortada
simétrica y speedup como cociente de medias recortadas, con IC por bootstrap
cuando se pasa el JSON del benchmark de Go corrido en la MISMA máquina
(--referencia). Se mide solo el clustering, con torch.cuda.synchronize antes y
después; la carga y la transferencia a la GPU se reportan aparte.

Submuestras: --tamanos toma n viajes con paso fijo, igual que kmeans.Submuestra
en Go, para que el barrido por tamaño compare el mismo subconjunto. Los
centroides iniciales son los del archivo en todos los tamaños; la equivalencia
de inercia con Go solo se reporta para el dataset completo, que es el n del que
salió ese archivo.

    python kmeans_gpu.py --datos data/yellow_2024-01_features.csv \
        --centroides data/centroides_k8_s2024.txt --salida reports/gpu.json \
        --tamanos 1000,10000,100000,1000000,0 --referencia reports/benchmark_cpu.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import random
import socket
import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import torch

FEATURES = ["hora_sin", "hora_cos", "dia_sin", "dia_cos", "log_duracion_z", "log_distancia_z"]
DTYPES = {"fp64": torch.float64, "fp32": torch.float32}


# ------------------------------------------------------------------ entrada ---


def sha256_archivo(ruta: Path) -> str:
    h = hashlib.sha256()
    with ruta.open("rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def leer_gold(ruta: Path) -> np.ndarray:
    """Las 6 features como float64, N x 6. Cachea un .npy al lado para no
    reparsear 200 MB de CSV en cada corrida."""
    cache = ruta.with_suffix(".features.npy")
    if cache.exists() and cache.stat().st_mtime >= ruta.stat().st_mtime:
        return np.load(cache)
    try:
        import polars as pl

        x = pl.read_csv(ruta, columns=FEATURES).to_numpy().astype(np.float64)
    except ImportError:
        x = np.loadtxt(ruta, delimiter=",", skiprows=1, usecols=range(3, 9), dtype=np.float64)
    if not np.isfinite(x).all():
        sys.exit("el gold tiene NaN o Inf: el contrato los rechaza")
    np.save(cache, x)
    return x


def leer_centroides(ruta: Path) -> tuple[np.ndarray, int, int]:
    """El formato de kmeans.GuardarCentroides: 'k=K d=D' y K filas de D valores."""
    lineas = [l.strip() for l in ruta.read_text().splitlines() if l.strip()]
    cab = dict(p.split("=") for p in lineas[0].split())
    k, d = int(cab["k"]), int(cab["d"])
    c = np.array([[float(v) for v in l.split(",")] for l in lineas[1 : 1 + k]], dtype=np.float64)
    if c.shape != (k, d):
        sys.exit(f"centroides: se esperaban {k}x{d}, hay {c.shape}")
    return c, k, d


def submuestra(x: np.ndarray, n: int) -> np.ndarray:
    """Igual que kmeans.Submuestra: n filas con paso fijo N/n, índice floor(i*paso)."""
    total = x.shape[0]
    if n <= 0 or n >= total:
        return x
    paso = total / n
    idx = np.minimum((np.arange(n) * paso).astype(np.int64), total - 1)
    return np.ascontiguousarray(x[idx])


# ------------------------------------------------------------------- lloyd ---


def asignar(x: torch.Tensor, c: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Etiqueta y distancia^2 al centroide más cercano, por diferencias directas.
    Se trocea por filas para que el tensor N x k x d no pase de ~512 MB."""
    n, d = x.shape
    k = c.shape[0]
    filas = max(1, (512 << 20) // (k * d * x.element_size()))
    etiquetas = torch.empty(n, dtype=torch.int64, device=x.device)
    dist2 = torch.empty(n, dtype=x.dtype, device=x.device)
    for ini in range(0, n, filas):
        fin = min(n, ini + filas)
        dif = x[ini:fin, None, :] - c[None, :, :]
        dd = (dif * dif).sum(-1)
        m, j = dd.min(dim=1)  # primer mínimo: mismo desempate que Go
        etiquetas[ini:fin] = j
        dist2[ini:fin] = m
    return etiquetas, dist2


def lloyd(x: torch.Tensor, c0: torch.Tensor, max_iter: int, tol_abs: float, tol_rel: float) -> dict:
    k, d = c0.shape
    c = c0.clone()
    inercias = []
    paro = "max_iter"
    vacios = 0
    it = 0
    for it in range(1, max_iter + 1):
        etiquetas, dist2 = asignar(x, c)
        inercias.append(dist2.sum())
        sumas = torch.zeros(k, d, dtype=x.dtype, device=x.device).index_add_(0, etiquetas, x)
        conteos = torch.bincount(etiquetas, minlength=k)
        previos = c.clone()
        con = conteos > 0
        vacios = int((~con).sum())
        inv = torch.zeros(k, dtype=x.dtype, device=x.device)
        inv[con] = 1.0 / conteos[con].to(x.dtype)
        c = torch.where(con[:, None], sumas * inv[:, None], previos)
        desp = (c - previos).abs().max()
        escala = previos.abs().max()
        if desp <= tol_abs + tol_rel * escala:
            paro = "tolerancia"
            break
    # Pasada final con los centroides finales, como en Go.
    etiquetas, dist2 = asignar(x, c)
    return {
        "centroides": c,
        "asignaciones": etiquetas,
        "inercia": float(dist2.sum()),
        "inercia_sumada_fp64": float(dist2.double().sum()),
        "inercias": [float(v) for v in inercias],
        "iteraciones": it,
        "paro": paro,
        "vacios": vacios,
    }


# -------------------------------------------------------------- estadística ---


def media_recortada(xs: list[float], prop: float) -> float:
    xs = sorted(xs)
    r = int(len(xs) * prop)
    return statistics.fmean(xs[r : len(xs) - r])


def resumen_tiempos(ts: list[float], recorte: float) -> dict:
    return {
        "repeticiones": len(ts),
        "media_recortada_ms": media_recortada(ts, recorte),
        "mediana_ms": statistics.median(ts),
        "desviacion_ms": statistics.stdev(ts) if len(ts) > 1 else 0.0,
        "min_ms": min(ts),
        "max_ms": max(ts),
    }


def ic_bootstrap_cociente(
    sec: list[float], con: list[float], recorte: float, replicas: int, semilla: int
) -> dict:
    rng = random.Random(semilla)
    punto = media_recortada(sec, recorte) / media_recortada(con, recorte)
    coc = []
    for _ in range(replicas):
        s = [rng.choice(sec) for _ in sec]
        c = [rng.choice(con) for _ in con]
        coc.append(media_recortada(s, recorte) / media_recortada(c, recorte))
    coc.sort()
    return {
        "punto": punto,
        "inferior": coc[int(0.025 * replicas)],
        "superior": coc[min(replicas - 1, int(0.975 * replicas))],
        "nivel": 0.95,
    }


# ---------------------------------------------------------------- referencia --


def tiempos_cpu(
    ref: dict, experimento: str, n: int, modo: str, workers: int | None = None
) -> list[float]:
    return [
        c["ms_clustering"]
        for c in ref["corridas"]
        if c["experimento"] == experimento
        and c["tamano"] == n
        and c["modo"] == modo
        and (modo == "seq" or c.get("workers") == workers)
        and not c["calentamiento"]
    ]


def comparar_con_cpu(ref: dict, experimento: str, n: int, ts: list[float], args) -> dict:
    """Speedup de la GPU frente al secuencial y frente a la mejor configuración
    concurrente de Go con el mismo n; vacío si el benchmark de CPU no midió ese n."""
    seq = tiempos_cpu(ref, experimento, n, "seq")
    if not seq:
        return {}
    out = {
        "speedup_vs_cpu_secuencial": ic_bootstrap_cociente(
            seq, ts, args.recorte, args.bootstrap, args.semilla_orden
        )
    }
    concs = [
        r
        for r in ref["resumen"]
        if r["experimento"] == experimento and r["tamano"] == n and r["modo"] == "conc"
    ]
    if concs:
        mejor = max(concs, key=lambda r: r.get("speedup", {}).get("punto", 0))
        con = tiempos_cpu(ref, experimento, n, "conc", mejor["workers"])
        out["speedup_vs_cpu_concurrente"] = {
            "workers": mejor["workers"],
            **ic_bootstrap_cociente(con, ts, args.recorte, args.bootstrap, args.semilla_orden),
        }
    out["inercia_cpu_secuencial"] = next(
        r["inercia"]
        for r in ref["resumen"]
        if r["experimento"] == experimento and r["tamano"] == n and r["modo"] == "seq"
    )
    return out


# -------------------------------------------------------------------- main ----


def sincronizar(dev: torch.device) -> None:
    if dev.type == "cuda":
        torch.cuda.synchronize(dev)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--datos", type=Path, required=True)
    ap.add_argument(
        "--centroides", type=Path, required=True, help="archivo de kmeans.GuardarCentroides"
    )
    ap.add_argument("--salida", type=Path, required=True)
    ap.add_argument(
        "--experimento",
        choices=["fijas", "convergencia"],
        default="fijas",
        help="con qué experimento del benchmark de Go se compara",
    )
    ap.add_argument("--iter", type=int, default=10, help="tope de iteraciones")
    ap.add_argument("--tol-abs", type=float, default=0.0)
    ap.add_argument("--tol-rel", type=float, default=0.0)
    ap.add_argument(
        "--tamanos", default="0", help="tamaños n separados por coma; 0 = dataset completo"
    )
    ap.add_argument("--repes", type=int, default=20)
    ap.add_argument("--calentamiento", type=int, default=1)
    ap.add_argument("--recorte", type=float, default=0.10)
    ap.add_argument("--bootstrap", type=int, default=2000)
    ap.add_argument("--semilla-orden", type=int, default=7)
    ap.add_argument("--precisiones", default="fp64,fp32")
    ap.add_argument("--dispositivo", default="cuda")
    ap.add_argument(
        "--referencia", type=Path, help="JSON de tp/kmeans/cmd/benchmark corrido en ESTA máquina"
    )
    args = ap.parse_args()

    dev = torch.device(args.dispositivo)
    if dev.type == "cuda" and not torch.cuda.is_available():
        sys.exit("no hay CUDA disponible")

    t0 = time.perf_counter()
    x_np = leer_gold(args.datos)
    ms_carga = (time.perf_counter() - t0) * 1000
    c0_np, k, d = leer_centroides(args.centroides)
    if d != x_np.shape[1]:
        sys.exit(f"centroides con d={d}, gold con d={x_np.shape[1]}")
    n_total = x_np.shape[0]

    precisiones = [p.strip() for p in args.precisiones.split(",") if p.strip()]
    tamanos = sorted(
        {n_total if int(t) <= 0 else min(int(t), n_total) for t in args.tamanos.split(",")}
    )

    # Transferencia a la GPU, una vez por (tamaño, precisión), medida aparte.
    tensores, ms_h2d = {}, {}
    for n in tamanos:
        sub = submuestra(x_np, n)
        for p in precisiones:
            sincronizar(dev)
            t0 = time.perf_counter()
            tensores[n, p] = (
                torch.from_numpy(sub).to(dev, DTYPES[p]),
                torch.from_numpy(c0_np).to(dev, DTYPES[p]),
            )
            sincronizar(dev)
            ms_h2d[n, p] = (time.perf_counter() - t0) * 1000

    configs = [(n, p) for n in tamanos for p in precisiones]
    rng = random.Random(args.semilla_orden)
    corridas, resultado = [], {}
    total_rondas = args.calentamiento + args.repes
    for ronda in range(total_rondas):
        orden = configs[:]
        rng.shuffle(orden)
        for pos, (n, p) in enumerate(orden):
            xg, cg = tensores[n, p]
            sincronizar(dev)
            t0 = time.perf_counter()
            r = lloyd(xg, cg, args.iter, args.tol_abs, args.tol_rel)
            sincronizar(dev)
            ms = (time.perf_counter() - t0) * 1000
            corridas.append(
                {
                    "experimento": args.experimento,
                    "tamano": n,
                    "precision": p,
                    "ronda": ronda,
                    "orden_en_la_ronda": pos,
                    "calentamiento": ronda < args.calentamiento,
                    "ms_clustering": ms,
                    "iteraciones": r["iteraciones"],
                    "paro": r["paro"],
                    "inercia": r["inercia"],
                }
            )
            resultado[n, p] = r
        print(f"ronda {ronda + 1}/{total_rondas}", file=sys.stderr, end="\r")
    print(file=sys.stderr)

    referencia = json.loads(args.referencia.read_text()) if args.referencia else None

    resumen = []
    for n, p in configs:
        ts = [
            c["ms_clustering"]
            for c in corridas
            if c["tamano"] == n and c["precision"] == p and not c["calentamiento"]
        ]
        r = resultado[n, p]
        fila = {
            "experimento": args.experimento,
            "tamano": n,
            "precision": p,
            **resumen_tiempos(ts, args.recorte),
            "ms_por_iteracion": media_recortada(ts, args.recorte) / r["iteraciones"],
            "ms_h2d": ms_h2d[n, p],
            "iteraciones": r["iteraciones"],
            "paro": r["paro"],
            "clusters_vacios": r["vacios"],
            "inercia": r["inercia"],
            "inercia_sumada_fp64": r["inercia_sumada_fp64"],
        }
        if n == n_total:
            fila["centroides_finales"] = r["centroides"].double().cpu().numpy().tolist()
        if len(precisiones) == 2:
            a, b = (resultado[n, q]["asignaciones"] for q in precisiones)
            fila["asignaciones_distintas_entre_precisiones"] = int((a != b).sum())
        if referencia:
            cmp = comparar_con_cpu(referencia, args.experimento, n, ts, args)
            fila.update(cmp)
            # La equivalencia numérica solo tiene sentido donde los centroides
            # iniciales son los mismos que los de Go: el dataset completo.
            if "inercia_cpu_secuencial" in cmp and n == n_total:
                ref_i = cmp["inercia_cpu_secuencial"]
                fila["diferencia_relativa_inercia"] = abs(r["inercia"] - ref_i) / ref_i
                fila["diferencia_relativa_inercia_sumada_fp64"] = (
                    abs(r["inercia_sumada_fp64"] - ref_i) / ref_i
                )
        resumen.append(fila)

    props = torch.cuda.get_device_properties(dev) if dev.type == "cuda" else None
    informe = {
        "metadatos": {
            "momento": datetime.now(UTC).astimezone().isoformat(timespec="seconds"),
            "maquina": socket.gethostname(),
            "plataforma": platform.platform(),
            "python": platform.python_version(),
            "torch": torch.__version__,
            "cuda": torch.version.cuda,
            "gpu": props.name if props else None,
            "gpu_memoria_mb": round(props.total_memory / 2**20) if props else None,
            "gpu_sms": props.multi_processor_count if props else None,
        },
        "protocolo": {
            "experimento": args.experimento,
            "max_iter": args.iter,
            "tol_abs": args.tol_abs,
            "tol_rel": args.tol_rel,
            "tamanos": tamanos,
            "repeticiones_medidas": args.repes,
            "rondas_calentamiento": args.calentamiento,
            "recorte_por_extremo": args.recorte,
            "replicas_bootstrap": args.bootstrap,
            "orden": "aleatorizado por ronda entre (tamaño, precisión); se guarda el orden",
            "semilla_orden": args.semilla_orden,
            "se_mide": "solo el clustering, con cuda.synchronize antes y después; carga y H2D aparte",
            "distancia": "suma de (x-c)^2 por diferencias directas, troceada por filas",
            "submuestra": "sistemática con paso N/n, como kmeans.Submuestra",
        },
        "datos": {
            "ruta": str(args.datos),
            "sha256": sha256_archivo(args.datos),
            "n": n_total,
            "d": d,
            "ms_carga": ms_carga,
        },
        "centroides_iniciales": {
            "ruta": str(args.centroides),
            "sha256": sha256_archivo(args.centroides),
            "k": k,
        },
        "referencia_cpu": str(args.referencia) if args.referencia else None,
        "corridas": corridas,
        "resumen": resumen,
    }
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(json.dumps(informe, indent=2, ensure_ascii=False) + "\n")

    for f in resumen:
        linea = (
            f"n={f['tamano']:>9,} {f['precision']}: {f['media_recortada_ms']:8.1f} ms "
            f"({f['ms_por_iteracion']:.2f} ms/iter, {f['iteraciones']} it)"
        )
        if "speedup_vs_cpu_secuencial" in f:
            s = f["speedup_vs_cpu_secuencial"]
            linea += f" | vs seq {s['punto']:.2f}x [{s['inferior']:.2f}, {s['superior']:.2f}]"
        if "speedup_vs_cpu_concurrente" in f:
            c = f["speedup_vs_cpu_concurrente"]
            linea += f" | vs conc P={c['workers']} {c['punto']:.2f}x"
        if "diferencia_relativa_inercia" in f:
            linea += (
                f" | Δinercia {f['diferencia_relativa_inercia']:.1e}"
                f" (sumada en fp64: {f['diferencia_relativa_inercia_sumada_fp64']:.1e})"
            )
        print(linea)
    print(f"→ {args.salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

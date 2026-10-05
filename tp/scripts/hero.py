# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Hero del K-means concurrente: una iteración de Lloyd en un SVG autocontenido.

    uv run scripts/hero.py                      # → reports/figuras/hero.svg
    uv run scripts/hero.py -o /tmp/hero.svg

Una sola idea: el planificador decide QUIÉN procesa cada chunk; el índice decide DÓNDE se
suma. Por eso el resultado es idéntico bit a bit para cualquier cantidad de workers.

Las cifras salen del repo, no se escriben a mano:

  speedup        reports/benchmark_gorgo.json, experimento «fijas» sobre el dataset completo
  bit a bit      la misma inercia en todas las filas concurrentes de ese experimento; si
                 alguna difiere, el script falla en vez de dibujar una afirmación falsa
  Spin           informe/tp/generado/spin-casos.tsv (lo escribe spin/check.sh): un mutante
                 cuenta como atrapado si TODAS sus corridas dan errores > 0

El Gantt de la izquierda es ilustrativo: 4 workers, 8 chunks, con una planificación coherente
con un canal FIFO (cada worker libre recibe el chunk siguiente).

Las fuentes (Inter y JetBrains Mono, OFL) se bajan una vez de npm con sha256 fijo y se
incrustan en base64, así el SVG se ve igual en un <img> de GitHub que en el navegador.
"""

import argparse
import base64
import csv
import hashlib
import io
import json
import tarfile
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

TP = Path(__file__).resolve().parent.parent
CACHE = Path.home() / ".cache" / "concurrente-hero"

FUENTES = {
    # paquete npm: (sha256 del tarball, subsets)
    "inter": (
        "d26710dd38e7217484a1d47ee76c024977ec550548876f26d06ed1844af09a14",
        ["latin", "greek"],
    ),
    "jetbrains-mono": (
        "996fe6368a480c9ce15d4de22a2682b7c40b403718fee2b15e7272f244fd993f",
        ["latin"],
    ),
}
FAMILIA = {"inter": "Inter", "jetbrains-mono": "JetBrains Mono"}
VERSION_FUENTES = "5.3.0"

W, H = 2400, 1280
INK, MUTED, FAINT, LINE = "#1d2433", "#5b6474", "#9aa3b2", "#d7dce4"
RED, TEAL = "#d6334a", "#0f6b56"
SANS, MONO = "Inter, sans-serif", "'JetBrains Mono', monospace"

# Tono por índice de chunk, claro → oscuro: en parciales[c] el orden se lee como gradiente.
TONOS = ["#d3efe5", "#b3e3d3", "#8fd3bd", "#66bfa3", "#3fa688", "#238b6f", "#147459", "#0b5b46"]

# (chunk, inicio, fin) por worker. Canal FIFO: el primer worker libre recibe el siguiente.
CARRILES = [
    [(1, 0, 190), (5, 200, 400)],
    [(0, 10, 230), (6, 240, 450)],
    [(3, 20, 180), (4, 190, 420)],
    [(2, 30, 260), (7, 270, 380)],
]


# --- datos -------------------------------------------------------------------------------------


def cifras_benchmark(ruta: Path, workers: int) -> dict:
    d = json.loads(ruta.read_text())
    n = d["datos"]["n"]
    filas = [
        r
        for r in d["resumen"]
        if r["experimento"] == "fijas" and r["tamano"] == n and r["modo"] == "conc"
    ]
    inercias = {r["inercia"] for r in filas}
    if len(inercias) != 1:
        raise SystemExit(
            f"{ruta}: la inercia concurrente cambia con P ({inercias}); no es bit a bit"
        )
    fila = next((r for r in filas if r["workers"] == workers), None)
    if fila is None:
        raise SystemExit(f"{ruta}: no hay corrida concurrente con {workers} workers")
    return {
        "n": n,
        "k": d["protocolo"]["k"],
        "speedup": fila["speedup"]["punto"],
        "workers": workers,
        "ps": sorted(r["workers"] for r in filas),
    }


def cifras_spin(ruta: Path) -> dict:
    with ruta.open(newline="") as f:
        casos = list(csv.DictReader(f, delimiter="\t"))
    mutantes: dict[str, bool] = {}
    for c in casos:
        if c["variante"] != "correcto":
            mutantes[c["variante"]] = mutantes.get(c["variante"], True) and int(c["errores"]) > 0
    correctos = [c for c in casos if c["variante"] == "correcto"]
    if any(int(c["errores"]) for c in correctos):
        raise SystemExit(f"{ruta}: el modelo correcto tiene errores")
    return {"atrapados": sum(mutantes.values()), "mutantes": len(mutantes)}


def fuentes_css() -> str:
    reglas = []
    for paquete, (sha, subsets) in FUENTES.items():
        tgz = CACHE / f"{paquete}-{VERSION_FUENTES}.tgz"
        if not tgz.exists():
            url = f"https://registry.npmjs.org/@fontsource-variable/{paquete}/-/{tgz.name}"
            CACHE.mkdir(parents=True, exist_ok=True)
            tgz.write_bytes(urllib.request.urlopen(url, timeout=60).read())
        datos = tgz.read_bytes()
        if hashlib.sha256(datos).hexdigest() != sha:
            raise SystemExit(f"{tgz}: sha256 inesperado")
        with tarfile.open(fileobj=io.BytesIO(datos)) as tar:
            for s in subsets:
                woff2 = tar.extractfile(f"package/files/{paquete}-{s}-wght-normal.woff2").read()
                b64 = base64.b64encode(woff2).decode()
                reglas.append(
                    f'@font-face{{font-family:"{FAMILIA[paquete]}";font-weight:100 900;'
                    f'src:url(data:font/woff2;base64,{b64}) format("woff2")}}'
                )
    return "\n".join(reglas)


# --- dibujo ------------------------------------------------------------------------------------


def texto(x, y, s, size=34, weight=500, fill=INK, font=SANS, anchor="start", ls=0):
    return (
        f'<text x="{x:g}" y="{y:g}" font-family="{font}" font-size="{size}" font-weight="{weight}" '
        f'fill="{fill}" text-anchor="{anchor}" letter-spacing="{ls}">{escape(s)}</text>'
    )


def rect(x, y, w, h, fill, rx=12, stroke=None, sw=2):
    borde = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    return (
        f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{rx}" fill="{fill}"{borde}/>'
    )


def sobre(c):
    return "#0b3d30" if c < 4 else "#ffffff"


def dibujar(b: dict, spin: dict) -> list[str]:
    s: list[str] = []
    gx, gw, tmax = 470, 830, 450
    tx = lambda t: gx + t / tmax * gw
    ly0, lh, lg = 290, 92, 22
    ly = lambda i: ly0 + i * (lh + lg)
    bx = 1350  # barrera
    py, ph, pw, pp = 810, 92, 92, 104  # fila de parciales
    px = lambda c: gx + c * pp

    s.append(
        texto(80, 104, "ONE LLOYD ITERATION", size=30, weight=700, fill=MUTED, font=MONO, ls=3)
    )
    s.append(texto(80, 150, "tp/kmeans/concurrente.go", size=30, fill=FAINT, font=MONO))

    # Lo que los workers leen sin locks
    s.append(rect(gx, 180, gw, 74, "#f1f3f7", rx=14, stroke=LINE))
    s.append(texto(gx + 28, 230, "X · centroids", size=36, weight=700, font=MONO))
    s.append(texto(gx + gw - 28, 230, "read-only, no locks", size=32, fill=MUTED, anchor="end"))

    # Canal
    cx, cw, ct, ch = 90, 170, 56, 46
    s.append(texto(cx, 230, "chan", size=30, fill=MUTED, font=MONO))
    s.append(texto(cx, 266, "trabajos", size=36, weight=700, font=MONO))
    s.append(rect(cx - 14, ly0 - 14, cw + 28, 8 * ct + 18, "none", rx=18, stroke=LINE, sw=3))
    for c in range(8):
        y = ly0 + c * ct
        s.append(rect(cx, y, cw, ch, TONOS[c], rx=9))
        s.append(
            texto(
                cx + cw / 2,
                y + 34,
                f"c{c}",
                size=32,
                weight=700,
                font=MONO,
                fill=sobre(c),
                anchor="middle",
            )
        )
    ymid = ly0 + 8 * ct / 2 - 10
    s.append(
        f'<path d="M {cx + cw + 30} {ymid} L {gx - 110} {ymid}" stroke="{FAINT}" stroke-width="4" marker-end="url(#gris)"/>'
    )
    s.append(texto(cx + cw + 40, ymid + 64, "FIFO", size=30, fill=FAINT, font=MONO))

    # Workers
    for i, carril in enumerate(CARRILES):
        y = ly(i)
        s.append(
            texto(
                gx - 22,
                y + lh / 2 + 12,
                f"G{i + 1}",
                size=34,
                weight=700,
                font=MONO,
                fill=MUTED,
                anchor="end",
            )
        )
        s.append(
            f'<line x1="{gx}" y1="{y + lh / 2}" x2="{bx}" y2="{y + lh / 2}" stroke="{LINE}" stroke-width="2"/>'
        )
        fin = 0.0
        for c, a, z in carril:
            x0, x1 = tx(a), tx(z) - 6
            s.append(rect(x0, y, x1 - x0, lh, TONOS[c]))
            s.append(
                texto(
                    (x0 + x1) / 2,
                    y + lh / 2 + 13,
                    f"c{c}",
                    size=36,
                    weight=700,
                    font=MONO,
                    fill=sobre(c),
                    anchor="middle",
                )
            )
            fin = x1
        s.append(
            f'<line x1="{fin + 14:g}" y1="{y + lh / 2}" x2="{bx - 12}" y2="{y + lh / 2}" stroke="{RED}" '
            'stroke-width="4" stroke-dasharray="3 11" stroke-linecap="round"/>'
        )
        s.append(f'<circle cx="{fin + 2:g}" cy="{y + lh / 2}" r="9" fill="{RED}"/>')
    s.append(texto(gx, ly(3) + lh + 52, "workers take chunks in any order", size=32, fill=MUTED))
    s.append(texto(bx - 24, ly(3) + lh + 52, "Done()", size=30, fill=RED, font=MONO, anchor="end"))

    # Parciales, guardados por índice
    for c in range(8):
        s.append(rect(px(c), py, pw, ph, TONOS[c]))
        s.append(
            texto(
                px(c) + pw / 2,
                py + ph / 2 + 12,
                str(c),
                size=36,
                weight=700,
                font=MONO,
                fill=sobre(c),
                anchor="middle",
            )
        )
    s.append(texto(gx, py + ph + 50, "parciales[c]", size=34, weight=700, font=MONO))
    s.append(
        texto(gx + 262, py + ph + 50, "stored by index · one writer each", size=32, fill=MUTED)
    )

    # Barrera
    s.append(
        f'<line x1="{bx}" y1="180" x2="{bx}" y2="{py + ph + 24}" stroke="{RED}" stroke-width="6" stroke-dasharray="18 12"/>'
    )
    s.append(texto(bx, 160, "wg.Wait()", size=34, weight=700, font=MONO, fill=RED, anchor="middle"))

    # Reducción en orden de chunk → centroides nuevos
    ry, sx = py + ph / 2, 1490
    s.append(
        f'<path d="M {px(7) + pw + 16} {ry} L {sx - 62} {ry}" stroke="{TEAL}" stroke-width="6" marker-end="url(#verde)"/>'
    )
    s.append(f'<circle cx="{sx}" cy="{ry}" r="52" fill="{TEAL}"/>')
    s.append(texto(sx, ry + 22, "Σ", size=62, weight=700, fill="#fff", anchor="middle"))
    s.append(texto(sx, ry + 104, "in chunk order", size=32, weight=600, fill=TEAL, anchor="middle"))
    nx, nw = 1590, 270
    s.append(
        f'<path d="M {sx + 56} {ry} L {nx - 14} {ry}" stroke="{TEAL}" stroke-width="6" marker-end="url(#verde)"/>'
    )
    s.append(rect(nx, py, nw, ph, "#fff", rx=14, stroke=INK, sw=3))
    s.append(
        texto(
            nx + nw / 2,
            py + ph / 2 + 13,
            "centroids′",
            size=36,
            weight=700,
            font=MONO,
            anchor="middle",
        )
    )

    # Lazo a la siguiente iteración
    lx = nx + nw / 2
    s.append(
        f'<path d="M {lx} {py - 14} L {lx} 217 L {gx + gw + 22} 217" fill="none" stroke="{INK}" stroke-width="4" marker-end="url(#tinta)"/>'
    )
    s.append(texto(lx + 22, 520, "next", size=32, fill=MUTED))
    s.append(texto(lx + 22, 560, "iteration", size=32, fill=MUTED))

    # Resultados, del repo
    mx = 1980
    s.append(
        f'<line x1="{mx - 40}" y1="180" x2="{mx - 40}" y2="{py + ph + 60}" stroke="{LINE}" stroke-width="2"/>'
    )
    ps = ", ".join(map(str, b["ps"]))
    for y, grande, a, z in [
        (
            290,
            f"{b['speedup']:.2f}×",
            f"speedup, {b['workers']} workers",
            f"{b['n'] / 1e6:.2f}M trips · k={b['k']}",
        ),
        (560, "1 result", "bit-identical", f"for P = {ps}"),
        (
            830,
            f"{spin['atrapados']} / {spin['mutantes']}",
            "mutants caught",
            "by Spin, all interleavings",
        ),
    ]:
        s.append(texto(mx, y, grande, size=92, weight=800, ls=-1))
        s.append(texto(mx, y + 52, a, size=32, weight=600))
        s.append(texto(mx, y + 92, z, size=30, fill=MUTED))

    # Tesis
    s.append(f'<line x1="80" y1="1090" x2="{W - 80}" y2="1090" stroke="{LINE}" stroke-width="2"/>')
    s.append(
        f'<text x="80" y="1180" font-family="{SANS}" font-size="46" font-weight="500" fill="{INK}">'
        'Scheduling decides <tspan font-weight="800">who</tspan> computes a chunk; its index decides '
        '<tspan font-weight="800">where</tspan> it is summed.</text>'
    )
    return s


def marcador(id_, color):
    return (
        f'<marker id="{id_}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="4.2" markerHeight="4.2" '
        f'orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="{color}"/></marker>'
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("-o", "--salida", type=Path, default=TP / "reports" / "figuras" / "hero.svg")
    ap.add_argument("--benchmark", type=Path, default=TP / "reports" / "benchmark_gorgo.json")
    ap.add_argument(
        "--spin", type=Path, default=TP / "informe" / "tp" / "generado" / "spin-casos.tsv"
    )
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    cuerpo = "\n".join(
        dibujar(cifras_benchmark(args.benchmark, args.workers), cifras_spin(args.spin))
    )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">\n'
        f"<style>{fuentes_css()}</style>\n"
        f"<defs>{marcador('gris', FAINT)}{marcador('verde', TEAL)}{marcador('tinta', INK)}</defs>\n"
        f'<rect width="{W}" height="{H}" fill="#ffffff"/>\n'
        f'<g transform="translate(0 16)">\n{cuerpo}\n</g>\n</svg>\n'
    )
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(svg)
    print(f"{args.salida} ({len(svg) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()

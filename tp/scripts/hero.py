# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Figura hero del K-means concurrente, en estilo de figura de revista (Frontiers).

    uv run scripts/hero.py           # → reports/figuras/hero.svg, ancho completo (README)
    uv run scripts/hero.py card      # → reports/figuras/card.svg, solo B y C (card de ~470 px)

Tres paneles, una tesis: el orden de suma está fijado por el índice del chunk, así que el
resultado no depende de la planificación.

  A  el mecanismo: workers que toman chunks en cualquier orden, sumas parciales guardadas por
     índice, barrera y suma en orden de índice. Esquemático (4 workers, 8 chunks), y lo dice.
  B  escalamiento fuerte sobre el dataset completo, una curva por máquina con su IC 95 %.
  C  la evidencia del «bit a bit»: la inercia final de cada máquina × cada P, más los mutantes
     que Spin detecta.

Las cifras salen del repo y el script falla si contradicen el dibujo:

  B, C   reports/benchmark_<maquina>.json, experimento «fijas» con el dataset completo. Si dos
         corridas concurrentes dan inercias distintas, no hay figura.
  C      informe/tp/generado/spin-casos.tsv (lo escribe spin/check.sh): un mutante cuenta como
         detectado si todas sus corridas dan errores > 0.

Tipografía Arimo (métrica de Arial, la que pide Frontiers), bajada de npm con sha256 fijo e
incrustada en base64: el SVG se ve igual dentro de un <img> de GitHub que en el navegador.
"""

import argparse
import base64
import csv
import hashlib
import io
import json
import math
import tarfile
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

TP = Path(__file__).resolve().parent.parent
CACHE = Path.home() / ".cache" / "concurrente-hero"

ARIMO = ("5.3.0", "df44945077a74905969f15bba3b442f9fb6773818b2b59c970911deace01132f")

W, H = 2400, 1280
INK, MUTED, FAINT, RULE = "#111111", "#555555", "#9a9a9a", "#d0d0d0"
FONT = "Arimo, Arial, Helvetica, sans-serif"

# Máquinas en orden fijo; color Okabe–Ito y forma de marcador por máquina (la forma es la
# codificación secundaria para lectores con daltonismo). Núcleos: docs/analisis-pc2.md y
# docs/pixel.md.
MAQUINAS = [
    ("wsl4060", "i7 desktop", "#0072B2", "circulo"),
    ("gorgo", "Ryzen VM", "#E69F00", "cuadrado"),
    ("pixel9a", "Pixel 9a", "#009E73", "triangulo"),
    ("laptop_i5", "i5 laptop", "#CC79A7", "rombo"),
]

# Rampa secuencial de un tono para el índice del chunk (claro → oscuro).
TONOS = ["#d4ede4", "#b2dfcf", "#8dcfb8", "#64bb9f", "#3ea385", "#22876b", "#126e55", "#085641"]

# (chunk, inicio, fin) por worker, coherente con un canal FIFO: el primer worker libre
# recibe el chunk siguiente. Unidades arbitrarias.
CARRILES = [
    [(1, 0, 190), (5, 200, 400)],
    [(0, 10, 230), (6, 240, 450)],
    [(3, 20, 180), (4, 190, 420)],
    [(2, 30, 260), (7, 270, 380)],
]


# --- datos -------------------------------------------------------------------------------------


def benchmarks(reports: Path) -> list[dict]:
    salida, inercias = [], set()
    for clave, nombre, color, forma in MAQUINAS:
        d = json.loads((reports / f"benchmark_{clave}.json").read_text())
        n = d["datos"]["n"]
        filas = sorted(
            (
                r
                for r in d["resumen"]
                if r["experimento"] == "fijas" and r["tamano"] == n and r["modo"] == "conc"
            ),
            key=lambda r: r["workers"],
        )
        inercias |= {r["inercia"] for r in filas}
        salida.append(
            {
                "nombre": nombre,
                "color": color,
                "forma": forma,
                "n": n,
                "k": d["protocolo"]["k"],
                "puntos": [
                    (
                        r["workers"],
                        r["speedup"]["punto"],
                        r["speedup"]["inferior"],
                        r["speedup"]["superior"],
                    )
                    for r in filas
                ],
            }
        )
    if len(inercias) != 1:
        raise SystemExit(f"las corridas concurrentes no coinciden bit a bit: {sorted(inercias)}")
    if len({m["n"] for m in salida}) != 1:
        raise SystemExit("las máquinas no corrieron sobre el mismo dataset")
    for m in salida:
        m["inercia"] = inercias.copy().pop()
    return salida


def cifras_spin(ruta: Path) -> dict:
    with ruta.open(newline="") as f:
        casos = list(csv.DictReader(f, delimiter="\t"))
    if any(int(c["errores"]) for c in casos if c["variante"] == "correcto"):
        raise SystemExit(f"{ruta}: el modelo correcto tiene errores")
    mutantes: dict[str, bool] = {}
    for c in casos:
        if c["variante"] != "correcto":
            mutantes[c["variante"]] = mutantes.get(c["variante"], True) and int(c["errores"]) > 0
    return {"detectados": sum(mutantes.values()), "mutantes": len(mutantes)}


def fuentes_css() -> str:
    version, sha = ARIMO
    tgz = CACHE / f"arimo-{version}.tgz"
    if not tgz.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        url = f"https://registry.npmjs.org/@fontsource/arimo/-/{tgz.name}"
        tgz.write_bytes(urllib.request.urlopen(url, timeout=60).read())
    datos = tgz.read_bytes()
    if hashlib.sha256(datos).hexdigest() != sha:
        raise SystemExit(f"{tgz}: sha256 inesperado")
    reglas = []
    with tarfile.open(fileobj=io.BytesIO(datos)) as tar:
        for subset in ("latin", "greek"):  # greek: Σ
            for peso in (400, 700):
                woff2 = tar.extractfile(f"package/files/arimo-{subset}-{peso}-normal.woff2").read()
                b64 = base64.b64encode(woff2).decode()
                reglas.append(
                    f'@font-face{{font-family:"Arimo";font-weight:{peso};'
                    f'src:url(data:font/woff2;base64,{b64}) format("woff2")}}'
                )
    return "\n".join(reglas)


# --- primitivas --------------------------------------------------------------------------------


def texto(x, y, s, size=30, bold=False, fill=INK, anchor="start", extra=""):
    peso = 700 if bold else 400
    return (
        f'<text x="{x:g}" y="{y:g}" font-family="{FONT}" font-size="{size}" font-weight="{peso}" '
        f'fill="{fill}" text-anchor="{anchor}"{extra}>{escape(s)}</text>'
    )


def linea(x1, y1, x2, y2, color=INK, ancho=2, extra=""):
    return (
        f'<line x1="{x1:g}" y1="{y1:g}" x2="{x2:g}" y2="{y2:g}" stroke="{color}" '
        f'stroke-width="{ancho}"{extra}/>'
    )


def rect(x, y, w, h, fill, rx=6, stroke=None):
    borde = f' stroke="{stroke}" stroke-width="2"' if stroke else ""
    return (
        f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{rx}" fill="{fill}"{borde}/>'
    )


def marcador(forma, x, y, color, r=11):
    anillo = 'stroke="#ffffff" stroke-width="3"'
    if forma == "circulo":
        return f'<circle cx="{x:g}" cy="{y:g}" r="{r}" fill="{color}" {anillo}/>'
    if forma == "cuadrado":
        return f'<rect x="{x - r:g}" y="{y - r:g}" width="{2 * r}" height="{2 * r}" fill="{color}" {anillo}/>'
    if forma == "triangulo":
        q = r * 1.25
        return f'<path d="M {x:g} {y - q:g} L {x + q:g} {y + q * 0.8:g} L {x - q:g} {y + q * 0.8:g} Z" fill="{color}" {anillo}/>'
    q = r * 1.3
    return f'<path d="M {x:g} {y - q:g} L {x + q:g} {y:g} L {x:g} {y + q:g} L {x - q:g} {y:g} Z" fill="{color}" {anillo}/>'


def encabezado(x, y, letra, titulo, k=1.0):
    return texto(x, y, letra, size=round(60 * k), bold=True) + texto(
        x + round(62 * k), y - round(4 * k), titulo, size=round(38 * k), bold=True
    )


def sobre(c):
    return "#0b3328" if c < 4 else "#ffffff"


# --- paneles -----------------------------------------------------------------------------------


def panel_a() -> list[str]:
    s = [encabezado(70, 118, "A", "Scheduling varies, summation order does not")]
    s.append(texto(132, 168, "One Lloyd iteration · 4 workers, 8 chunks (schematic)", fill=MUTED))

    gx, gw, tmax = 270, 630, 450
    tx = lambda t: gx + t / tmax * gw
    y0, lh, lg = 232, 86, 22
    bx = 935  # barrera

    for i, carril in enumerate(CARRILES):
        y = y0 + i * (lh + lg)
        s.append(texto(gx - 22, y + lh / 2 + 11, f"Worker {i + 1}", anchor="end"))
        fin = gx
        for c, a, z in carril:
            x0, x1 = tx(a), tx(z) - 5
            s.append(rect(x0, y, x1 - x0, lh, TONOS[c]))
            s.append(
                texto(
                    (x0 + x1) / 2,
                    y + lh / 2 + 12,
                    str(c),
                    size=34,
                    bold=True,
                    fill=sobre(c),
                    anchor="middle",
                )
            )
            fin = x1
        s.append(
            linea(
                fin + 10,
                y + lh / 2,
                bx - 10,
                y + lh / 2,
                FAINT,
                3,
                ' stroke-dasharray="2 9" stroke-linecap="round"',
            )
        )

    s.append(linea(bx, 205, bx, 905, INK, 4, ' stroke-dasharray="14 10"'))
    s.append(texto(bx, 196, "barrier", bold=True, anchor="middle"))
    s.append(
        texto(gx, y0 + 4 * (lh + lg) + 22, "Each worker pulls the next free chunk", fill=MUTED)
    )

    # Sumas parciales, una por índice de chunk
    py, pw, pp = 760, 70, 79
    s.append(texto(gx - 22, py + 34, "Partial", anchor="end"))
    s.append(texto(gx - 22, py + 68, "sums", anchor="end"))
    for c in range(8):
        x = gx + c * pp
        s.append(rect(x, py, pw, 80, TONOS[c]))
        s.append(
            texto(x + pw / 2, py + 52, str(c), size=34, bold=True, fill=sobre(c), anchor="middle")
        )

    # Suma en orden de índice → centroides nuevos
    ay = py + 118
    s.append(
        f'<path d="M {gx} {ay} L {gx + 7 * pp + pw + 12} {ay}" stroke="{INK}" stroke-width="4" marker-end="url(#flecha)"/>'
    )
    s.append(texto(gx, ay + 46, "Σ in chunk-index order  →  new centroids", bold=True))

    s.append(
        texto(70, 1040, "Floating-point addition is not associative, so a fixed order", fill=MUTED)
    )
    s.append(texto(70, 1082, "of summation is what makes the result reproducible.", fill=MUTED))
    return s


def panel_b(
    maquinas: list[dict],
    ox: float,
    oy: float,
    ancho: float,
    alto: float,
    k: float = 1.0,
    letra: str = "B",
) -> list[str]:
    """Speedup contra P. (ox, oy): esquina del encabezado; alto: alto del área de datos."""
    m0 = maquinas[0]
    f = lambda v: round(v * k)
    s = [
        encabezado(ox, oy, letra, f"Strong scaling, {m0['n'] / 1e6:.2f} M trips, k = {m0['k']}", k)
    ]

    x0, x1 = ox + f(150), ox + ancho - f(300)
    y0, y1 = oy + f(72), oy + f(72) + alto
    ymax = 8
    px = lambda p: x0 + math.log2(p) / 4 * (x1 - x0)
    py = lambda v: y1 - v / ymax * (y1 - y0)

    # Ejes (solo izquierda y abajo), ticks hacia afuera
    s.append(linea(x0 - 20, y1, x1 + 20, y1))
    s.append(linea(x0 - 20, y0 - 10, x0 - 20, y1))
    for p in (1, 2, 4, 8, 16):
        s.append(linea(px(p), y1, px(p), y1 + 12))
        s.append(texto(px(p), y1 + f(46), str(p), size=f(30), anchor="middle"))
    for v in (0, 2, 4, 6, 8):
        s.append(linea(x0 - 32, py(v), x0 - 20, py(v)))
        s.append(texto(x0 - 42, py(v) + f(10), str(v), size=f(30), anchor="end"))
    s.append(texto((x0 + x1) / 2, y1 + f(92), "Workers (P)", size=f(30), anchor="middle"))
    yl, xl = (y0 + y1) / 2, x0 - f(92)
    s.append(
        texto(
            xl,
            yl,
            "Speedup",
            size=f(30),
            anchor="middle",
            extra=f' transform="rotate(-90 {xl} {yl})"',
        )
    )

    # Ideal lineal
    s.append(linea(px(1), py(1), px(8), py(8), FAINT, 3, ' stroke-dasharray="10 8"'))
    s.append(texto(px(8) - f(20), py(8) - f(6), "ideal", size=f(30), fill=MUTED, anchor="end"))

    etiquetas = []
    for m in maquinas:
        pts = m["puntos"]
        d = " ".join(
            f"{'M' if i == 0 else 'L'} {px(p):.1f} {py(v):.1f}"
            for i, (p, v, _, _) in enumerate(pts)
        )
        s.append(f'<path d="{d}" fill="none" stroke="{m["color"]}" stroke-width="{f(3)}"/>')
        for p, _, lo, hi in pts:
            s.append(linea(px(p), py(lo), px(p), py(hi), m["color"], f(3)))
        for p, v, _, _ in pts:
            s.append(marcador(m["forma"], px(p), py(v), m["color"], r=f(11)))
        p, v, _, _ = pts[-1]
        etiquetas.append([py(v), m, v])

    # Etiquetas directas al final de cada curva, sin solaparse
    etiquetas.sort(key=lambda e: e[0])
    for i in range(1, len(etiquetas)):
        etiquetas[i][0] = max(etiquetas[i][0], etiquetas[i - 1][0] + f(36))
    for y, m, v in etiquetas:
        s.append(texto(x1 + f(40), y + f(10), f"{m['nombre']} {v:.1f}×", size=f(30)))
    return s


def panel_c(
    maquinas: list[dict],
    spin: dict,
    ox: float,
    oy: float,
    cw: float,
    ch: float,
    k: float = 1.0,
    letra: str = "C",
) -> list[str]:
    """Matriz máquina × P: cada celda es una corrida con la inercia común."""
    f = lambda v: round(v * k)
    s = [encabezado(ox, oy, letra, "Same result on every machine and P", k)]
    ps = [p for p, *_ in maquinas[0]["puntos"]]
    cx0, gap = ox + f(290), f(8)
    y0 = oy + f(80)
    for j, p in enumerate(ps):
        s.append(
            texto(
                cx0 + j * (cw + gap) + cw / 2,
                y0 - f(16),
                f"P={p}",
                size=f(30),
                fill=MUTED,
                anchor="middle",
            )
        )
    for i, m in enumerate(maquinas):
        y = y0 + i * (ch + gap)
        s.append(marcador(m["forma"], ox + f(20), y + ch / 2, m["color"], r=f(10)))
        s.append(texto(ox + f(48), y + ch / 2 + f(10), m["nombre"], size=f(30)))
        for j, _ in enumerate(ps):
            x = cx0 + j * (cw + gap)
            s.append(rect(x, y, cw, ch, "#126e55", rx=4))
            s.append(
                f'<path d="M {x + cw / 2 - f(14)} {y + ch / 2} l {f(9)} {f(9)} l {f(18)} {-f(18)}" fill="none" '
                f'stroke="#ffffff" stroke-width="{f(5)}" stroke-linecap="round" stroke-linejoin="round"/>'
            )
    n = len(maquinas) * len(ps)
    yb = y0 + len(maquinas) * (ch + gap) + f(44)
    inercia = f"{maquinas[0]['inercia']:.9f}"
    s.append(
        texto(ox, yb, f"{n}/{n} runs end at inertia {inercia}, bit for bit.", size=f(30), bold=True)
    )
    s.append(
        texto(
            ox,
            yb + f(46),
            f"Spin: {spin['detectados']}/{spin['mutantes']} injected concurrency bugs detected.",
            size=f(30),
            fill=MUTED,
        )
    )
    return s


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("variante", nargs="?", choices=["hero", "card"], default="hero")
    ap.add_argument("-o", "--salida", type=Path)
    ap.add_argument("--reports", type=Path, default=TP / "reports")
    ap.add_argument(
        "--spin", type=Path, default=TP / "informe" / "tp" / "generado" / "spin-casos.tsv"
    )
    args = ap.parse_args()

    maquinas, spin = benchmarks(args.reports), cifras_spin(args.spin)
    if args.variante == "hero":
        # Ancho completo (README del repo): mecanismo, rendimiento y evidencia.
        cuerpo = [linea(1210, 70, 1210, 1210, RULE, 2)]
        cuerpo += panel_a() + panel_b(maquinas, 1270, 118, 1090, 370)
        cuerpo += panel_c(maquinas, spin, 1270, 760, 110, 54)
    else:
        # Card del perfil, vista a ~470 px: solo B y C, con el texto 1,3 veces más grande.
        cuerpo = [linea(1200, 70, 1200, 1210, RULE, 2)]
        cuerpo += panel_b(maquinas, 70, 130, 1090, 760, k=1.3, letra="A")
        cuerpo += panel_c(maquinas, spin, 1260, 130, 128, 150, k=1.3, letra="B")
    salida = args.salida or TP / "reports" / "figuras" / f"{args.variante}.svg"
    flecha = (
        '<marker id="flecha" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="4" markerHeight="4" '
        f'orient="auto"><path d="M0 0 L10 5 L0 10 z" fill="{INK}"/></marker>'
    )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">\n'
        f"<style>{fuentes_css()}</style>\n<defs>{flecha}</defs>\n"
        f'<rect width="{W}" height="{H}" fill="#ffffff"/>\n' + "\n".join(cuerpo) + "\n</svg>\n"
    )
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(svg)
    print(f"{salida} ({len(svg) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()

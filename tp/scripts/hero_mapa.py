# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Card del K-means concurrente: Nueva York en cuatro momentos, un SVG autocontenido.

    uv run scripts/hero_mapa.py          # → reports/figuras/mapa.svg

Cada zona de taxi se pinta con el arquetipo de viaje (cluster) que más viajes tiene a esa hora,
y su opacidad crece con el volumen: Manhattan resalta y las zonas casi sin viajes se apagan. Los
cuatro momentos se eligieron porque en cada uno domina un arquetipo distinto en Manhattan.

Datos: app/data/nyc_clusters_resumen.json (lo escribe kmeans/cmd/resumen_zonas a partir de las
2,83 M asignaciones) y app/data/nyc_taxi_zones.geojson. Las cifras del pie salen de
reports/benchmark_*.json y de spin-casos.tsv, con las mismas verificaciones que scripts/hero.py.
"""

import argparse
import json
import math
from pathlib import Path

from hero import FONT, benchmarks, cifras_spin, fuentes_css, texto

TP = Path(__file__).resolve().parent.parent
W, H = 2400, 1280
INK, MUTED = "#111111", "#5a5a5a"

# Nombres en inglés de los arquetipos del visor; el color es el mismo del visor (Okabe–Ito),
# salvo el amarillo, oscurecido para que se vea sobre blanco.
ARQUETIPOS = {
    0: ("After-work & dinner", "#0072B2"),
    1: ("Weekend nightlife", "#CC79A7"),
    2: ("Lunch short hops", "#009E73"),
    3: ("Business-district traffic", "#D55E00"),
    4: ("Late-night cross-borough", "#56B4E9"),
    5: ("Airports & highways", "#E69F00"),
    6: ("Weekend daytime", "#D9C21A"),
    7: ("Friday short hops", "#2DD4BF"),
}

MOMENTOS = [
    ("Weekday 8 AM", "semana", 8),
    ("Weekday 7 PM", "semana", 19),
    ("Weekend 3 PM", "finde", 15),
    ("Weekend 11 PM", "finde", 23),
]

FUERA = {"EWR", "Staten Island"}  # Newark y Staten Island casi no tienen viajes y estiran el mapa


def anillos(geom):
    if geom["type"] == "Polygon":
        return geom["coordinates"]
    return [anillo for poligono in geom["coordinates"] for anillo in poligono]


def proyector(features, ancho, alto):
    lons = [x for f in features for a in anillos(f["geometry"]) for x, _ in a]
    lats = [y for f in features for a in anillos(f["geometry"]) for _, y in a]
    k = math.cos(math.radians((min(lats) + max(lats)) / 2))
    w, h = (max(lons) - min(lons)) * k, max(lats) - min(lats)
    esc = min(ancho / w, alto / h)
    dx, dy = (ancho - w * esc) / 2, (alto - h * esc) / 2
    return lambda lon, lat: (dx + (lon - min(lons)) * k * esc, dy + (max(lats) - lat) * esc)


def caminos(features, proy):
    """Un path por zona, con las coordenadas redondeadas a 0,5 px y sin puntos repetidos."""
    salida = {}
    for f in features:
        partes = []
        for anillo in anillos(f["geometry"]):
            pts, previo = [], None
            for lon, lat in anillo:
                x, y = proy(lon, lat)
                p = (round(x * 2) / 2, round(y * 2) / 2)
                if p != previo:
                    pts.append(p)
                    previo = p
            if len(pts) > 2:
                partes.append("M" + "L".join(f"{x:g} {y:g}" for x, y in pts) + "Z")
        salida[str(f["properties"]["id"])] = "".join(partes)
    return salida


def mapa(zonas, geo, clave, hora, ox, oy, ancho, alto):
    proy = proyector(geo, ancho, alto)
    paths = caminos(geo, proy)
    totales = [z[clave][hora]["total"] for z in zonas.values()]
    tope = math.log1p(max(totales))
    s = [f'<g transform="translate({ox} {oy})">']
    for zid, d in paths.items():
        z = zonas.get(zid)
        celda = z[clave][hora] if z else {"total": 0}
        if celda["total"] == 0:
            s.append(f'<path d="{d}" fill="#ececec" stroke="#ffffff" stroke-width="1.5"/>')
            continue
        color = ARQUETIPOS[celda["dom"]][1]
        alfa = 0.18 + 0.82 * math.log1p(celda["total"]) / tope
        s.append(
            f'<path d="{d}" fill="{color}" fill-opacity="{alfa:.2f}" stroke="#ffffff" stroke-width="1.5"/>'
        )
    s.append("</g>")
    return s


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("-o", "--salida", type=Path, default=TP / "reports" / "figuras" / "mapa.svg")
    ap.add_argument("--reports", type=Path, default=TP / "reports")
    ap.add_argument(
        "--spin", type=Path, default=TP / "informe" / "tp" / "generado" / "spin-casos.tsv"
    )
    args = ap.parse_args()

    datos = json.loads((TP / "app" / "data" / "nyc_clusters_resumen.json").read_text())
    geo = [
        f
        for f in json.loads((TP / "app" / "data" / "nyc_taxi_zones.geojson").read_text())[
            "features"
        ]
        if f["properties"]["borough"] not in FUERA
    ]
    maquinas, spin = benchmarks(args.reports), cifras_spin(args.spin)
    if spin["detectados"] != spin["mutantes"]:
        raise SystemExit(f"Spin no detecta todos los mutantes: {spin}; el pie diría algo falso")
    gorgo = next(m for m in maquinas if m["nombre"] == "Ryzen VM")
    speedup8 = next(v for p, v, *_ in gorgo["puntos"] if p == 8)

    s = [
        texto(70, 118, "How New York moves by taxi", size=76, bold=True),
        texto(
            72,
            182,
            f"{datos['total_viajes'] / 1e6:.2f} M trips, January 2024, grouped into "
            f"{datos['k']} trip types. Each zone shows its most common type.",
            size=36,
            fill=MUTED,
        ),
    ]

    mw, mh, gap, my = 548, 720, 36, 340
    for i, (titulo, clave, hora) in enumerate(MOMENTOS):
        ox = 70 + i * (mw + gap)
        s.append(texto(ox, 262, titulo, size=40, bold=True))
        # El arquetipo con más viajes en ese momento, rotulado sobre su mapa
        conteos = [0] * datos["k"]
        for z in datos["zonas"].values():
            for c, n in enumerate(z[clave][hora]["counts"]):
                conteos[c] += n
        top = max(range(datos["k"]), key=conteos.__getitem__)
        nombre, color = ARQUETIPOS[top]
        s.append(f'<rect x="{ox}" y="{284}" width="30" height="30" rx="6" fill="{color}"/>')
        s.append(
            texto(ox + 42, 310, f"{nombre} · {100 * conteos[top] / sum(conteos):.0f}%", size=32)
        )
        s += mapa(datos["zonas"], geo, clave, hora, ox, my, mw, mh)

    # Los colores que no rotula ningún panel, y cómo leer la opacidad
    x, y = 70, my + mh + 66
    s.append(texto(x, y, "Also:", size=32, fill=MUTED))
    x += 96
    for c in (5, 4, 2):
        nombre, color = ARQUETIPOS[c]
        s.append(f'<rect x="{x}" y="{y - 26}" width="30" height="30" rx="6" fill="{color}"/>')
        s.append(texto(x + 42, y, nombre, size=32))
        x += 42 + len(nombre) * 16 + 44
    s.append(texto(x, y, "Paler zones have fewer trips", size=32, fill=MUTED))

    s.append(
        texto(
            70,
            H - 50,
            f"Clustered with a concurrent K-means in Go: {speedup8:.1f}× on 8 workers, identical "
            f"result on 4 machines, synchronization verified with Spin.",
            size=34,
            bold=True,
        )
    )

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'font-family="{FONT}">\n<style>{fuentes_css()}</style>\n'
        f'<rect width="{W}" height="{H}" fill="#ffffff"/>\n' + "\n".join(s) + "\n</svg>\n"
    )
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(svg)
    print(f"{args.salida} ({len(svg) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()

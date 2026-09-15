# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib>=3.8"]
# ///
"""Gráfico de la matriz de escenarios del ejercicio 8 (Ben-Ari, algoritmo 2.18).

Lee escenarios.csv, que exporta el mismo modelo que verifican los tests:

    go run ./week04/cmd/escenarios -csv > week04/grafico/escenarios.csv
    uv run week04/grafico/escenarios.py

Una fila por escenario: n después de cada instrucción, con la marca del proceso
que la ejecutó. Hueca = evaluó su guarda, rellena = hizo la asignación.
"""

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

AQUI = Path(__file__).parent

# Paleta categórica validada (slots 1 y 2): p azul, q naranja. La forma de la
# marca repite la identidad para que no dependa solo del color.
COLOR = {"p": "#2a78d6", "q": "#eb6834"}
MARCA = {"p": "o", "q": "s"}
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
REGLA = "#e4e3de"
SUPERFICIE = "#fcfcfb"
BANDA = "#f1f0ec"

TITULOS = {
    "8a": "8(a) · el bucle de p itera exactamente una vez",
    "8b": "8(b) · el bucle de p itera exactamente tres veces",
    "8c": "8(c) · la vuelta qqpp repetida: ninguno de los dos termina",
}
VUELTA_C = 4  # len("qqpp")


def leer(ruta: Path) -> dict[str, list[dict[str, str]]]:
    pasos: dict[str, list[dict[str, str]]] = {}
    with ruta.open(newline="", encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            pasos.setdefault(fila["escenario"], []).append(fila)
    return pasos


def dibujar(ax, nombre: str, pasos: list[dict[str, str]]) -> None:
    xs = [0] + [int(p["paso"]) for p in pasos]
    ns = [1] + [int(p["n"]) for p in pasos]

    if nombre == "8c":
        for i, inicio in enumerate(range(0, len(pasos), VUELTA_C)):
            if i % 2 == 0:
                ax.axvspan(inicio + 0.5, inicio + VUELTA_C + 0.5, color=BANDA, zorder=0, lw=0)
            ax.text(inicio + VUELTA_C / 2 + 0.5, 1.75, f"vuelta {i + 1}",
                    ha="center", va="center", fontsize=8, color=TINTA_2)
        ax.annotate("estado = inicial (n = 1, p1, q1)\n→ se repite para siempre",
                    xy=(len(pasos), 1), xytext=(len(pasos) + 0.8, 0.35),
                    fontsize=8.5, color=TINTA, va="center",
                    arrowprops=dict(arrowstyle="-", color=TINTA_2, lw=1))

    # n se mantiene entre instrucciones: escalón que cambia recién en la asignación.
    ax.step(xs, ns, where="post", color=TINTA_2, lw=2, zorder=1, solid_capstyle="round")
    ax.plot([0], [1], marker="o", ms=6, color=TINTA_2, zorder=2)
    ax.text(0, 1.32, "inicio", ha="center", fontsize=8, color=TINTA_2)

    terminados: set[str] = set()
    for p in pasos:
        x, n, proc, etiqueta = int(p["paso"]), int(p["n"]), p["proceso"], p["etiqueta"]
        es_guarda = etiqueta.endswith("1")
        ax.plot([x], [n], marker=MARCA[proc], ms=9, mew=2, zorder=3,
                color=COLOR[proc],
                markerfacecolor=SUPERFICIE if es_guarda else COLOR[proc],
                markeredgecolor=SUPERFICIE if not es_guarda else COLOR[proc])
        # Fondo del color de la superficie: el escalón vertical pasa justo por x.
        ax.text(x, n - 0.38, etiqueta, ha="center", va="top", fontsize=7.5, color=TINTA_2,
                zorder=4, bbox=dict(facecolor=SUPERFICIE, edgecolor="none", pad=0.6))
        if "falso" in p["detalle"] and proc not in terminados:
            terminados.add(proc)
            ax.text(x, n + 0.3, f"{proc} termina", ha="center", va="bottom",
                    fontsize=8.5, color=TINTA, fontweight="bold")

    ax.set_title(TITULOS[nombre], loc="left", fontsize=10.5, color=TINTA, pad=6)
    ax.set_ylim(-1.75, 2.05)
    ax.set_yticks([-1, 0, 1])
    ax.set_ylabel("n", color=TINTA_2, rotation=0, labelpad=10)
    ax.grid(axis="y", color=REGLA, lw=1)
    ax.set_axisbelow(True)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color(REGLA)
    ax.tick_params(colors=TINTA_2, labelsize=8.5)


def main() -> None:
    pasos = leer(AQUI / "escenarios.csv")
    orden = ["8a", "8b", "8c"]
    largo = max(len(pasos[e]) for e in orden)

    fig, ejes = plt.subplots(len(orden), 1, figsize=(11, 8.2), sharex=True, facecolor=SUPERFICIE)
    for ax, nombre in zip(ejes, orden):
        ax.set_facecolor(SUPERFICIE)
        dibujar(ax, nombre, pasos[nombre])
    ejes[-1].set_xlim(-0.6, largo + 0.6)
    ejes[-1].set_xticks(range(0, largo + 1, 2))
    ejes[-1].set_xlabel("paso del escenario (una instrucción por turno)", color=TINTA_2)

    leyenda = [
        Line2D([], [], ls="", marker=MARCA["p"], ms=9, color=COLOR["p"], label="proceso p"),
        Line2D([], [], ls="", marker=MARCA["q"], ms=9, color=COLOR["q"], label="proceso q"),
        Line2D([], [], ls="", marker="o", ms=9, mew=2, color=TINTA_2,
               markerfacecolor=SUPERFICIE, label="guarda (p1 / q1)"),
        Line2D([], [], ls="", marker="o", ms=9, color=TINTA_2, label="asignación (p2 / q2)"),
    ]
    fig.suptitle("Algoritmo C de Ben-Ari: valor de n después de cada instrucción",
                 x=0.01, y=0.995, ha="left", fontsize=12, color=TINTA, fontweight="bold")
    fig.legend(handles=leyenda, loc="upper left", ncol=4, frameon=False,
               fontsize=9, labelcolor=TINTA, bbox_to_anchor=(0.0, 0.965))
    fig.tight_layout(rect=(0, 0, 1, 0.93))

    for ext in ("png", "svg"):
        fig.savefig(AQUI / f"escenarios.{ext}", dpi=200, facecolor=SUPERFICIE)
    print(f"escrito {AQUI / 'escenarios.png'} y .svg")


if __name__ == "__main__":
    main()

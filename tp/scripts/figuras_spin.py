# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib>=3.8"]
# ///
"""Figuras del modelo Promela para el informe de la PC2.

Dibujan exactamente lo que devuelve Spin, sin retocar los datos:

    cd tp/spin && make figuras     # regenera las entradas con Spin y llama a este script

  automata-worker.pdf  el autómata del proctype worker, de `pan -D` (dot de Graphviz);
                       solo se abrevian las etiquetas: (4/2) → TAM, x = (x+1) → x++
  traza-mutante.pdf    compartido después de cada lectura y escritura en la ronda donde
                       falla el mutante, de `spin -t -p -l -g -DMUTANTE`

El estilo repite el de labs/spin/week05/grafico/trazas.py (incremento.svg), que dibuja el
mismo incremento perdido en el ejercicio de clase.
"""

import re
import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

INFORME = Path(__file__).resolve().parent.parent / "informe" / "pc2"
GENERADO = INFORME / "generado"
IMG = INFORME / "img"

# Paleta de trazas.py: slots 1 y 2 validados; la forma repite la identidad del worker.
COLOR = ["#2a78d6", "#eb6834"]
MARCA = ["o", "s"]
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
REGLA = "#e4e3de"
SUPERFICIE = "#fcfcfb"
BANDA = "#f1f0ec"

N = 4  # puntos por ronda en kmeans.pml; el assert del mutante es compartido == N


# --- autómata del worker ------------------------------------------------------

ABREVIAR = [
    (r"\(4/2\)", "TAM"),
    (r"\(\((\w+)<TAM\)\)", r"\1 < TAM"),
    (r"seen\[\(\(idx\*TAM\)\+i\)\] = \(seen\[\(\(idx\*TAM\)\+i\)\]\+1\)", "seen[idx*TAM+i]++"),
    (r"(\w+(?:\[\w+\])?) = \(\1\+1\)", r"\1++"),
    (r"(\w+(?:\[\w+\])?) = \(\1-1\)", r"\1--"),
    (r"assert\(\(escribiendo==0\)\)", "assert(escribiendo == 0)"),
]


def automata() -> None:
    dot = (GENERADO / "automatas.dot").read_text()
    m = re.search(r"digraph p_worker \{.*?\n\}", dot, re.DOTALL)
    if not m:
        sys.exit("automatas.dot no trae el digraph p_worker: ¿cambió el proctype?")
    worker = m[0]
    for patron, reemplazo in ABREVIAR:
        worker = re.sub(patron, reemplazo, worker)
    # Estilo del informe: tipografía sans, sin el size="8,10" de pan.
    worker = worker.replace(
        'size="8,10";',
        (
            "rankdir=TB; nodesep=0.25; ranksep=0.22;\n"
            f'node [fontname="Helvetica", fontsize=13, color="{TINTA_2}", shape=circle, width=0.5, fixedsize=true];\n'
            f'edge [fontname="Helvetica", fontsize=14, color="{TINTA_2}", fontcolor="{TINTA}"];'
        ),
    )
    worker = worker.replace(
        '[shape=box,style=dotted,label="worker"]',
        '[shape=plaintext,label="worker()",fixedsize=false]',
    )
    worker = worker.replace("color=blue,style=bold,shape=box", f'color="{COLOR[0]}",penwidth=2')
    (GENERADO / "automata-worker.dot").write_text(worker + "\n")
    subprocess.run(
        ["dot", "-Tpdf", "-o", str(IMG / "automata-worker.pdf")], input=worker.encode(), check=True
    )
    print(f"escrito {IMG / 'automata-worker.pdf'}")


# --- contraejemplo del mutante ------------------------------------------------

PASO = re.compile(r"^\s*\d+:\s+proc\s+(\d+) \((:init:|\w+):1\) \S+:\d+ \(state \d+\)\s+\[(.*)\]$")
VALOR = re.compile(r"^\s+compartido = (\d+)$")


def eventos() -> list[tuple[int, bool, int]]:
    """(worker, escribe, compartido después) en la última ronda: la que viola el assert.

    Se re-ejecutan los tres pasos del mutante con un tmp por worker, porque `spin -g` solo
    imprime `compartido = v` cuando el valor cambia: la escritura perdida (2 sobre 2) no deja
    línea. Las líneas que sí imprime se usan para comprobar la simulación.
    """
    lineas = (GENERADO / "traza-mutante.txt").read_text().splitlines()
    inicio = max(
        i
        for i, l in enumerate(lineas)
        if (m := PASO.match(l)) and m[2] == ":init:" and m[3] == "compartido = 0"
    )
    compartido, tmp, filas = 0, {}, []
    for linea in lineas[inicio + 1 :]:
        if m := VALOR.match(linea):
            assert int(m[1]) == compartido, (
                f"Spin dice compartido = {m[1]}, la simulación {compartido}"
            )
        elif (m := PASO.match(linea)) and m[2] == "worker":
            pid = int(m[1])
            if m[3] == "tmp = compartido":
                tmp[pid] = compartido
                filas.append((pid, False, compartido))
            elif m[3] == "tmp = (tmp+1)":
                tmp[pid] += 1
            elif m[3] == "compartido = tmp":
                compartido = tmp[pid]
                filas.append((pid, True, compartido))
        elif "assert((compartido==" in linea:
            break
    return filas


def traza() -> None:
    filas = eventos()
    workers = sorted({p for p, _, _ in filas})
    final = filas[-1][2]
    assert final != N, f"la traza termina en compartido = {final}: no es un contraejemplo"

    fig, ax = plt.subplots(figsize=(8.6, 3.5), facecolor=SUPERFICIE)
    ax.set_facecolor(SUPERFICIE)
    xs = list(range(len(filas) + 1))
    ys = [0] + [v for _, _, v in filas]
    ax.axhline(N, color=TINTA_2, lw=1, ls=(0, (4, 3)), zorder=1.5)
    ax.text(
        0.1, N + 0.12, f"esperado: compartido = N = {N}", fontsize=8, color=TINTA_2, va="bottom"
    )
    ax.step(xs, ys, where="post", color=TINTA_2, lw=2, zorder=1, solid_capstyle="round")
    ax.plot([0], [0], marker="o", ms=6, color=TINTA_2, zorder=2)

    leido: dict[int, int] = {}
    perdida = None
    for x, (pid, escribe, v) in enumerate(filas, start=1):
        k = workers.index(pid)
        ax.plot(
            [x],
            [v],
            marker=MARCA[k],
            ms=9,
            mew=2,
            zorder=3,
            color=COLOR[k],
            markerfacecolor=COLOR[k] if escribe else SUPERFICIE,
            markeredgecolor=SUPERFICIE if escribe else COLOR[k],
        )
        if escribe:
            txt = f"escribe {v}"
            if v == ys[x - 1]:
                perdida = (x, v, k)
        else:
            leido[pid] = v
            txt = f"lee {v}"
        ax.text(
            x,
            v + 0.3,
            txt,
            ha="center",
            va="bottom",
            fontsize=7.5,
            color=TINTA_2,
            zorder=4,
            bbox={"facecolor": SUPERFICIE, "edgecolor": "none", "pad": 0.6},
        )

    if perdida:
        x, v, k = perdida
        ax.axvspan(x - 0.5, x + 0.5, color=BANDA, zorder=0, lw=0)
        ax.annotate(
            f"worker {k + 1} escribe {v} sobre {v}:\nse pierde un incremento",
            xy=(x, v),
            xytext=(x - 2.3, -1.45),
            fontsize=8.5,
            color=TINTA,
            ha="center",
            arrowprops={"arrowstyle": "-", "color": TINTA_2, "lw": 1},
        )
    x = len(filas)
    ax.annotate(
        f"assert(compartido == {N}) falla\ncon compartido = {final}",
        xy=(x, final),
        xytext=(x - 0.1, -1.45),
        fontsize=8.5,
        color=TINTA,
        fontweight="bold",
        ha="right",
        arrowprops={"arrowstyle": "-", "color": TINTA_2, "lw": 1},
    )

    ax.set_xticks(xs)
    ax.set_xlim(-0.5, len(filas) + 0.5)
    ax.set_ylim(-1.9, N + 0.9)
    ax.set_yticks(range(N + 1))
    ax.set_xlabel("lectura o escritura de compartido, en el orden del contraejemplo", color=TINTA_2)
    ax.set_ylabel("compartido", color=TINTA_2)
    ax.grid(axis="y", color=REGLA, lw=1)
    ax.set_axisbelow(True)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color(REGLA)
    ax.tick_params(colors=TINTA_2, labelsize=8.5)

    leyenda = [
        Line2D([], [], ls="", marker=MARCA[k], ms=9, color=COLOR[k], label=f"worker {k + 1}")
        for k in range(len(workers))
    ]
    leyenda += [
        Line2D(
            [],
            [],
            ls="",
            marker="o",
            ms=9,
            mew=2,
            color=TINTA_2,
            markerfacecolor=SUPERFICIE,
            label="tmp = compartido (lee)",
        ),
        Line2D([], [], ls="", marker="o", ms=9, color=TINTA_2, label="compartido = tmp (escribe)"),
    ]
    ax.legend(
        handles=leyenda,
        loc="upper left",
        ncol=4,
        frameon=False,
        fontsize=8.5,
        labelcolor=TINTA,
        bbox_to_anchor=(0.0, 1.17),
    )
    fig.tight_layout()
    fig.savefig(IMG / "traza-mutante.pdf", facecolor=SUPERFICIE)
    plt.close(fig)
    print(f"escrito {IMG / 'traza-mutante.pdf'}")


if __name__ == "__main__":
    automata()
    traza()

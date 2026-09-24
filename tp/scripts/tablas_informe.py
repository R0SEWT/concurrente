#!/usr/bin/env python3
"""Genera las tablas y cifras del informe de la PC2 desde tp/reports/*.json.

Ninguna cifra del informe se transcribe a mano: este script escribe un .tex por
tabla en tp/informe/pc2/generado/ y un cifras.tex con las cantidades que el texto
cita en prosa (\\cifra{speedup-p4}, etc.). Si se vuelve a medir, se vuelve a
generar y el informe cambia solo.

    python3 tablas_informe.py --salida ../informe/pc2/generado

Solo usa la biblioteca estándar. El formato numérico sigue al informe: coma
decimal y punto de miles.
"""

import argparse
import json
import math
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
REPORTS = AQUI.parent / "reports"

PRINCIPAL = REPORTS / "benchmark_gorgo.json"
CRUCE = REPORTS / "benchmark_gorgo_cruce.json"
DEBIL = REPORTS / "benchmark_gorgo_debil.json"
CHUNKS = sorted(
    REPORTS.glob("benchmark_gorgo_chunk_*.json"), key=lambda p: int(p.stem.rsplit("_", 1)[1])
)
RECURSOS = REPORTS / "recursos_fedora_2026-09-17_2306.json"


# ----------------------------------------------------------------- formato ---


def num(v, dec=2):
    """3,80 · 1.106,3 · 2.831.486: coma decimal, punto de miles."""
    if v is None:
        return "---"
    s = f"{v:,.{dec}f}"
    return s.replace(",", "\0").replace(".", ",").replace("\0", ".")


def entero(v):
    return num(v, 0)


def pct(v):
    return "---" if v is None else f"{100 * v:.0f}\\,\\%"


def speedup_ic(sp):
    if not sp:
        return "---"
    return f"{num(sp['punto'])}$\\times$ [{num(sp['inferior'])}; {num(sp['superior'])}]"


def cientifica(v, dec=1):
    """$2{,}5 \\cdot 10^{-14}$, en modo matemático."""
    mant, exp = f"{v:.{dec}e}".split("e")
    return f"${mant.replace('.', '{,}')} \\cdot 10^{{{int(exp)}}}$"


def karp_flatt(speedup, p):
    """Fracción serial efectiva e = (1/S - 1/P) / (1 - 1/P). No definida con P = 1."""
    if p <= 1 or not speedup:
        return None
    return (1 / speedup - 1 / p) / (1 - 1 / p)


def cargar(ruta: Path) -> dict:
    with ruta.open(encoding="utf-8") as f:
        return json.load(f)


def resumen(inf, experimento, tamano, modo, workers=None):
    for r in inf["resumen"]:
        if (
            r["experimento"] == experimento
            and r["tamano"] == tamano
            and r["modo"] == modo
            and (modo == "seq" or r.get("workers") == workers)
        ):
            return r
    raise KeyError(f"no hay resumen para {experimento}/{tamano}/{modo}/{workers}")


def workers_de(inf, experimento, tamano):
    return sorted(
        {
            r["workers"]
            for r in inf["resumen"]
            if r["experimento"] == experimento and r["tamano"] == tamano and r["modo"] == "conc"
        }
    )


def nota_protocolo(inf):
    p, m = inf["protocolo"], inf["metadatos"]
    return (
        f"{m['maquina']} · {m['version_go']} · {m['cpus_logicas']} CPUs lógicas · "
        f"{p['repeticiones_medidas']} repeticiones medidas + {p['rondas_calentamiento']} de calentamiento · "
        f"media recortada al {p['recorte_por_extremo']:.0%} por extremo · "
        f"IC del speedup por bootstrap de {entero(p['replicas_bootstrap'])} réplicas · "
        f"$k={p['k']}$ · chunk {entero(p['chunk'])}"
    ).replace("%", "\\,\\%")


def tabla(cols, filas, caption, label, nota=None, tamano="\\small"):
    """Tabla booktabs. cols: lista de (encabezado, alineación)."""
    ali = "".join(a for _, a in cols)
    out = [
        "\\begin{table}[H]",
        f"\\caption{{{caption}}}\\label{{{label}}}",
        tamano,
        f"\\begin{{tabular}}{{@{{}}{ali}@{{}}}}",
        "\\toprule",
        " & ".join(f"\\textbf{{{h}}}" for h, _ in cols) + " \\\\",
        "\\midrule",
    ]
    out += [" & ".join(f) + " \\\\" for f in filas]
    out += ["\\bottomrule", "\\end{tabular}"]
    if nota:
        out += ["", f"{{\\footnotesize\\textit{{Nota.}} {nota}\\par}}"]
    out += ["\\end{table}", ""]
    return "\n".join(out)


# ------------------------------------------------------------------ tablas ---


def fuerte(inf, experimento, label, caption):
    n = inf["datos"]["n"]
    seq = resumen(inf, experimento, n, "seq")
    filas = [
        [
            "---",
            "secuencial",
            num(seq["media_recortada_ms"], 1),
            num(seq["desviacion_ms"], 1),
            "---",
            "---",
            "---",
        ]
    ]
    for p in workers_de(inf, experimento, n):
        r = resumen(inf, experimento, n, "conc", p)
        e = karp_flatt(r["speedup"]["punto"], p)
        filas.append(
            [
                str(p),
                "concurrente",
                num(r["media_recortada_ms"], 1),
                num(r["desviacion_ms"], 1),
                speedup_ic(r["speedup"]),
                pct(r["eficiencia_por_worker"]),
                "---" if e is None else num(e, 3),
            ]
        )
    it = seq["iteraciones"]
    extra = (
        f"trabajo fijo de {it} iteraciones"
        if experimento == "fijas"
        else f"hasta convergencia; ambas versiones pararon en {it} iteraciones (tope del protocolo)"
    )
    cols = [
        ("$P$", "r"),
        ("Versión", "l"),
        ("Media rec. (ms)", "r"),
        ("Desv. (ms)", "r"),
        ("Speedup [IC 95\\,\\%]", "l"),
        ("Efic.", "r"),
        ("Karp--Flatt", "r"),
    ]
    return tabla(
        cols,
        filas,
        caption,
        label,
        f"Dataset completo, {entero(n)} viajes, {extra}. {nota_protocolo(inf)}. "
        "Media rec. es la media recortada; la eficiencia es speedup/$P$. Karp--Flatt es la "
        "fracción serial efectiva $e = (1/S - 1/P)/(1 - 1/P)$; no está definida con $P = 1$.",
        tamano="\\footnotesize",
    )


def por_tamano(inf):
    tamanos = sorted({r["tamano"] for r in inf["resumen"] if r["experimento"] == "fijas"})
    ps = workers_de(inf, "fijas", tamanos[-1])
    filas = []
    for n in tamanos:
        seq = resumen(inf, "fijas", n, "seq")
        fila = [entero(n), num(seq["media_recortada_ms"], 1)]
        for p in ps:
            fila.append(num(resumen(inf, "fijas", n, "conc", p)["speedup"]["punto"]) + "$\\times$")
        filas.append(fila)
    cols = [("$n$ (viajes)", "r"), ("Secuencial (ms)", "r")] + [(f"$P={p}$", "r") for p in ps]
    return tabla(
        cols,
        filas,
        "Speedup según el tamaño del problema y la cantidad de workers",
        "tab:speedup-tamano",
        f"Trabajo fijo de {inf['protocolo']['iteraciones_fijas']} iteraciones. "
        "Cada celda es el speedup puntual de la media recortada; los intervalos de las "
        "filas del dataset completo están en la Tabla~\\ref{tab:speedup-fuerte}.",
    )


def cruce(principal, inf_cruce, p=4):
    filas_n = {}
    for inf in (principal, inf_cruce):
        for r in inf["resumen"]:
            if r["experimento"] == "fijas" and r["modo"] == "conc" and r.get("workers") == p:
                filas_n[r["tamano"]] = (inf, r)
    filas, primero = [], None
    for n in sorted(filas_n):
        inf, r = filas_n[n]
        if n > 200_000:
            continue
        seq = resumen(inf, "fijas", n, "seq")
        sp = r["speedup"]
        if sp["inferior"] > 1:
            gana = "sí"
            primero = primero or n
        elif sp["superior"] < 1:
            gana = "no, pierde"
        else:
            gana = "indistinguible"
        filas.append(
            [
                entero(n),
                num(seq["media_recortada_ms"], 2),
                num(r["media_recortada_ms"], 2),
                speedup_ic(sp),
                gana,
            ]
        )
    cols = [
        ("$n$ (viajes)", "r"),
        ("Secuencial (ms)", "r"),
        (f"Conc. $P={p}$ (ms)", "r"),
        ("Speedup [IC 95\\,\\%]", "l"),
        ("¿Gana?", "l"),
    ]
    return tabla(
        cols,
        filas,
        f"Punto de equilibrio: speedup con $P={p}$ según el tamaño del problema",
        "tab:equilibrio",
        "«Gana» cuando el intervalo de confianza queda entero por encima de 1; «pierde» cuando "
        "queda entero por debajo. Mismo protocolo que la Tabla~\\ref{tab:speedup-fuerte}.",
        tamano="\\footnotesize",
    ), primero


def debil(inf):
    filas_p = {}
    for r in inf["resumen"]:
        if r["modo"] == "conc":
            filas_p.setdefault(r["tamano"], {})[r["workers"]] = r
    tamanos = sorted(filas_p)
    base_n = tamanos[0]
    por_worker = base_n
    t_base = filas_p[base_n][1]["media_recortada_ms"]
    filas = []
    for n in tamanos:
        p = round(n / por_worker)
        r = filas_p[n][p]
        t1 = filas_p[n][1]["media_recortada_ms"]
        filas.append(
            [
                str(p),
                entero(n),
                num(r["media_recortada_ms"], 1),
                num(t1, 1),
                pct(t_base / r["media_recortada_ms"]),
            ]
        )
    cols = [
        ("$P$", "r"),
        ("$n$ (viajes)", "r"),
        ("Tiempo con $P$ (ms)", "r"),
        ("Mismo $n$ con $P=1$ (ms)", "r"),
        ("Eficiencia débil", "r"),
    ]
    return tabla(
        cols,
        filas,
        "Escalamiento débil: $n/P$ constante",
        "tab:debil",
        f"Se mantienen {entero(por_worker)} viajes por worker. La eficiencia débil es "
        "$T(P{=}1, n_1) / T(P, P \\cdot n_1)$: 100\\,\\% significa que el problema creció "
        "$P$ veces en el mismo tiempo. La cuarta columna muestra qué costaría el mismo "
        "$n$ sin paralelismo.",
    ), {"n-por-worker": entero(por_worker)}


def chunks(archivos):
    filas, mejor = [], None
    for ruta in archivos:
        inf = cargar(ruta)
        n = inf["datos"]["n"]
        c = inf["protocolo"]["chunk"]
        p = workers_de(inf, "fijas", n)[0]
        r = resumen(inf, "fijas", n, "conc", p)
        cant = math.ceil(n / c)
        filas.append(
            [entero(c), entero(cant), num(r["media_recortada_ms"], 1), speedup_ic(r["speedup"])]
        )
        if mejor is None or r["speedup"]["punto"] > mejor[1]:
            mejor = (c, r["speedup"]["punto"])
    cols = [
        ("Chunk (viajes)", "r"),
        ("Cantidad de chunks", "r"),
        ("Tiempo (ms)", "r"),
        ("Speedup [IC 95\\,\\%]", "l"),
    ]
    return (
        tabla(
            cols,
            filas,
            f"Barrido del tamaño de chunk con $P={p}$ sobre el dataset completo",
            "tab:chunk",
            "Mismo protocolo que la Tabla~\\ref{tab:speedup-fuerte}; solo cambia el tamaño de chunk. "
            "Con 3 chunks y 8 workers, cinco workers se quedan sin trabajo.",
        ),
        mejor,
        p,
    )


def recursos(lista):
    filas = []
    for r in lista:
        f = r["recursos_finales"]
        cpu = f["cpu_usuario_s"] + f["cpu_sistema_s"]
        pared = r["ms_total"] / 1000
        filas.append(
            [
                "seq" if r["modo"] == "seq" else "conc",
                "---" if r["modo"] == "seq" else str(r.get("workers", "")),
                num(r["ms_clustering"], 0),
                num(r["recursos_tras_carga"]["heap_mb"], 0),
                num(f["max_rss_mb"], 0),
                num(cpu, 2),
                num(cpu / pared, 1),
            ]
        )
    m = lista[0]
    cols = [
        ("Modo", "l"),
        ("$P$", "r"),
        ("Clust. (ms)", "r"),
        ("Heap (MB)", "r"),
        ("RSS (MB)", "r"),
        ("CPU (s)", "r"),
        ("Núcleos", "r"),
    ]
    return tabla(
        cols,
        filas,
        "Uso de recursos por configuración en la laptop",
        "tab:recursos",
        f"{m['maquina']} · {m['version_go']} · {m['cpus_logicas']} CPUs lógicas (4 núcleos físicos "
        f"con SMT) · dataset completo, $k={m['k']}$, {m['max_iter']} iteraciones. Una corrida por "
        "configuración: acá interesa el consumo, que es estable, no el tiempo. Clust. es el tiempo de "
        "clustering; Heap, el heap vivo tras cargar el CSV; RSS, el máximo del proceso. CPU es usuario "
        "más sistema del proceso completo, incluida la carga del CSV; Núcleos son los núcleos "
        "efectivos, CPU dividido por el tiempo de pared total.",
        tamano="\\footnotesize",
    )


def inercias(inf):
    n = inf["datos"]["n"]
    seq = resumen(inf, "fijas", n, "seq")
    filas = [["secuencial", "---", f"{seq['inercia']:.9f}".replace(".", ",")]]
    conc = [resumen(inf, "fijas", n, "conc", p) for p in workers_de(inf, "fijas", n)]
    valores = {f"{r['inercia']:.9f}" for r in conc}
    ps = ", ".join(str(r["workers"]) for r in conc)
    for v in sorted(valores):
        filas.append(["concurrente", ps, v.replace(".", ",")])
    rel = abs(conc[0]["inercia"] - seq["inercia"]) / seq["inercia"]
    cols = [("Versión", "l"), ("$P$", "l"), ("Inercia final", "r")]
    return tabla(
        cols,
        filas,
        "Inercia final sobre el dataset completo, $k=8$, 10 iteraciones",
        "tab:inercias",
        "La versión concurrente da el mismo valor para toda cantidad de workers porque reduce los "
        "parciales en orden de chunk. La diferencia con la secuencial es el redondeo de sumar en otro "
        f"orden: {cientifica(rel, 2)} en términos relativos.",
    ), rel


# ------------------------------------------------------------------- main ----


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--salida", type=Path, default=AQUI.parent / "informe" / "pc2" / "generado")
    args = ap.parse_args()
    args.salida.mkdir(parents=True, exist_ok=True)

    principal = cargar(PRINCIPAL)
    n = principal["datos"]["n"]
    cabecera = (
        "% Generado por tp/scripts/tablas_informe.py desde tp/reports/*.json. No editar a mano.\n"
    )

    salidas = {}
    salidas["tabla-speedup-fuerte.tex"] = fuerte(
        principal,
        "fijas",
        "tab:speedup-fuerte",
        "Escalamiento fuerte con trabajo fijo: dataset completo",
    )
    salidas["tabla-speedup-convergencia.tex"] = fuerte(
        principal,
        "convergencia",
        "tab:speedup-convergencia",
        "Escalamiento fuerte hasta convergencia: dataset completo",
    )
    salidas["tabla-speedup-tamano.tex"] = por_tamano(principal)
    salidas["tabla-equilibrio.tex"], n_equilibrio = cruce(principal, cargar(CRUCE))
    salidas["tabla-debil.tex"], c_debil = debil(cargar(DEBIL))
    salidas["tabla-chunk.tex"], mejor_chunk, p_chunk = chunks(CHUNKS)
    salidas["tabla-recursos.tex"] = recursos(cargar(RECURSOS))
    salidas["tabla-inercias.tex"], rel_inercia = inercias(principal)

    # Cifras que el texto cita en prosa.
    seq = resumen(principal, "fijas", n, "seq")
    cif = {
        "n": entero(n),
        "maquina": principal["metadatos"]["maquina"],
        "cpus-gorgo": str(principal["metadatos"]["cpus_logicas"]),
        "go": principal["metadatos"]["version_go"],
        "repeticiones": str(principal["protocolo"]["repeticiones_medidas"]),
        "bootstrap": entero(principal["protocolo"]["replicas_bootstrap"]),
        "recorte": f"{principal['protocolo']['recorte_por_extremo']:.0%}".replace("%", "\\,\\%"),
        "chunk": entero(principal["protocolo"]["chunk"]),
        "k": str(principal["protocolo"]["k"]),
        "iter-fijas": str(principal["protocolo"]["iteraciones_fijas"]),
        "seq-ms": num(seq["media_recortada_ms"], 0),
        "n-equilibrio": entero(n_equilibrio),
        "mejor-chunk": entero(mejor_chunk[0]),
        "p-chunk": str(p_chunk),
        "inercia-rel": cientifica(rel_inercia),
        "duracion-min": num(principal["duracion_total_min"], 0),
    }
    cif.update(c_debil)
    for p in workers_de(principal, "fijas", n):
        r = resumen(principal, "fijas", n, "conc", p)
        cif[f"speedup-p{p}"] = num(r["speedup"]["punto"])
        cif[f"eficiencia-p{p}"] = pct(r["eficiencia_por_worker"])
        cif[f"ms-p{p}"] = num(r["media_recortada_ms"], 0)
        e = karp_flatt(r["speedup"]["punto"], p)
        if e is not None:
            cif[f"kf-p{p}"] = num(e, 3)
        rc = resumen(principal, "convergencia", n, "conc", p)
        cif[f"speedup-conv-p{p}"] = num(rc["speedup"]["punto"])
    cif["sobrecosto-p1"] = pct(1 - resumen(principal, "fijas", n, "conc", 1)["speedup"]["punto"])
    lineas = [cabecera, "\\newcommand{\\cifra}[1]{\\csname cifra:#1\\endcsname}"]
    for k, v in sorted(cif.items()):
        lineas.append(f"\\expandafter\\def\\csname cifra:{k}\\endcsname{{{v}}}")
    salidas["cifras.tex"] = "\n".join(lineas) + "\n"

    for nombre, contenido in salidas.items():
        destino = args.salida / nombre
        destino.write_text(
            cabecera + contenido if not contenido.startswith("%") else contenido, encoding="utf-8"
        )
        print(f"→ {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

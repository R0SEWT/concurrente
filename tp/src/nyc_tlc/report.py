"""Reporte de limpieza en Markdown: la evidencia que va al informe de PC1 (3 pts de la rúbrica)."""


def _pct(n: int, total: int) -> str:
    return f"{100 * n / total:.2f} %" if total else "—"


def render_markdown(r: dict) -> str:
    f = r["fuente"]
    bronze = r["filas"]["bronze"]
    lineas = [
        f"# Limpieza NYC TLC — {f['flota']} {f['mes']}",
        "",
        "Generado por `uv run nyc-tlc all`. No editar a mano: se regenera en cada corrida.",
        "",
        "## Procedencia",
        "",
        "| Archivo | Bytes | sha256 |",
        "|---|---:|---|",
        *(
            f"| [{a['archivo']}]({a['url']}) | {a['bytes']:,} | `{a['sha256']}` |"
            for a in (f["viajes"], f["zonas"])
        ),
        "",
        "## Reglas (en cascada)",
        "",
        "Cada viaje descartado se atribuye a la **primera** regla que falla, así las filas suman.",
        "",
        "| Regla | Condición para quedarse | Descartados | % de bronze | Restantes |",
        "|---|---|---:|---:|---:|",
        f"| **bronze** | archivo original | | | {bronze:,} |",
        *(
            f"| `{x['regla']}` | {x['descripcion']} | {x['descartados']:,} | "
            f"{_pct(x['descartados'], bronze)} | {x['restantes']:,} |"
            for x in r["reglas"]
        ),
        (
            f"| **silver** | | {bronze - r['filas']['silver']:,} | "
            f"{_pct(bronze - r['filas']['silver'], bronze)} | **{r['filas']['silver']:,}** |"
        ),
        "",
        (
            f"Mínimo del enunciado: {r['minimo_requerido']:,} registros limpios → "
            f"**{'cumple' if r['cumple_minimo'] else 'NO cumple'}**."
        ),
        "",
        "## Auditoría independiente (DuckDB)",
        "",
        "Las mismas reglas reescritas en SQL. En bronze el conteo no es exclusivo (un viaje puede",
        "violar varias); en silver todas deben dar 0.",
        "",
        "| Regla | Violaciones en bronze | Violaciones en silver |",
        "|---|---:|---:|",
        *(
            f"| `{regla}` | {n:,} | {r['auditoria']['silver'][regla]:,} |"
            for regla, n in r["auditoria"]["bronze"].items()
        ),
        "",
        "## Escalado de features (gold)",
        "",
        "| Feature | Media | Desv. (poblacional) |",
        "|---|---:|---:|",
        *(f"| `{col}` | {e['media']:.6f} | {e['desv']:.6f} |" for col, e in r["escalado"].items()),
        "",
    ]
    return "\n".join(lineas)

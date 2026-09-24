"""Los notebooks se versionan sin salidas.

Un .ipynb ejecutado pesa megas por las imágenes embebidas, genera un diff ilegible en cada
corrida y nada garantiza que sus salidas correspondan al código. Las figuras que van al informe
se exportan como archivos aparte. Se limpia con:

    uv run jupyter nbconvert --clear-output --inplace notebooks/*.ipynb
"""

import json
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]


def celdas_ejecutadas(ruta: Path) -> list[int]:
    """Índices de las celdas que llegaron con salidas o con número de ejecución."""
    nb = json.loads(ruta.read_text())
    return [
        i
        for i, celda in enumerate(nb.get("cells", []))
        if celda.get("outputs") or celda.get("execution_count") is not None
    ]


def escribir_nb(ruta: Path, celdas: list[dict]) -> Path:
    ruta.write_text(json.dumps({"cells": celdas, "metadata": {}, "nbformat": 4}))
    return ruta


@pytest.fixture
def limpia():
    return {"cell_type": "code", "source": ["1 + 1"], "outputs": [], "execution_count": None}


def test_detecta_una_celda_con_salidas(tmp_path, limpia):
    ejecutada = {
        "cell_type": "code",
        "source": ["1 + 1"],
        "execution_count": 1,
        "outputs": [{"output_type": "execute_result", "data": {"text/plain": ["2"]}}],
    }
    nb = escribir_nb(tmp_path / "sucio.ipynb", [limpia, ejecutada])

    assert celdas_ejecutadas(nb) == [1]


def test_detecta_el_numero_de_ejecucion_aunque_no_haya_salidas(tmp_path, limpia):
    # `nbconvert --clear-output` borra outputs y deja execution_count en null; si quedó un
    # número, el notebook se guardó ejecutado
    contada = {**limpia, "execution_count": 7}
    nb = escribir_nb(tmp_path / "contada.ipynb", [limpia, contada])

    assert celdas_ejecutadas(nb) == [1]


def test_un_notebook_limpio_no_reporta_nada(tmp_path, limpia):
    markdown = {"cell_type": "markdown", "source": ["# Título"]}
    nb = escribir_nb(tmp_path / "limpio.ipynb", [markdown, limpia])

    assert celdas_ejecutadas(nb) == []


def test_los_notebooks_del_repo_estan_sin_salidas():
    sucios = {
        str(nb.relative_to(RAIZ)): celdas_ejecutadas(nb)
        for nb in sorted(RAIZ.rglob("*.ipynb"))
        if ".ipynb_checkpoints" not in nb.parts and ".venv" not in nb.parts
    }
    sucios = {ruta: celdas for ruta, celdas in sucios.items() if celdas}

    assert not sucios, (
        "Notebooks guardados con salidas: "
        + "; ".join(f"{r} (celdas {c})" for r, c in sucios.items())
        + ". Límpialos con `uv run jupyter nbconvert --clear-output --inplace <archivo>`."
    )

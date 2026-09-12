"""Bronze: bajar los archivos de TLC tal cual, sin tocarlos, y registrar su sha256."""

import hashlib
import shutil
import urllib.request
from pathlib import Path


def sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def descargar(url: str, destino: Path) -> dict:
    """Descarga `url` a `destino` si todavía no está. Bronze es inmutable: nunca se pisa.

    TLC re-publica meses corregidos de vez en cuando; si se quiere la versión nueva, se borra
    el archivo de bronze a mano y el sha256 del reporte deja constancia del cambio.
    """
    destino.parent.mkdir(parents=True, exist_ok=True)
    if not destino.exists():
        parcial = destino.with_name(destino.name + ".part")
        with urllib.request.urlopen(url) as respuesta, open(parcial, "wb") as f:
            shutil.copyfileobj(respuesta, f)
        parcial.rename(destino)
    return {
        "url": url,
        "archivo": destino.name,
        "bytes": destino.stat().st_size,
        "sha256": sha256(destino),
    }

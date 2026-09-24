#!/usr/bin/env python3
"""Convierte la salida de texto de la CLI en una imagen PNG para el informe.

La rúbrica pide «imágenes de evidencia del funcionamiento». Una captura de
pantalla hecha a mano no se puede regenerar; esta sí: el texto de origen queda
junto a la imagen (mismo nombre, extensión .txt) y cualquiera puede volver a
correr la CLI y rehacer la figura.

    python3 capturas_terminal.py salida.txt            # escribe salida.png
    python3 capturas_terminal.py a.txt b.txt --ancho 100

Solo usa Pillow, que ya está entre las dependencias de desarrollo de tp/.
"""

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FUENTES = [
    "/usr/share/fonts/jetbrains-mono-fonts/JetBrainsMono-Regular.ttf",
    str(
        Path.home() / ".local/share/fonts/JetBrainsMonoNerd/JetBrainsMonoNLNerdFontMono-Regular.ttf"
    ),
    "/usr/share/fonts/dejavu-sans-mono-fonts/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
]

FONDO = (30, 30, 34)
TEXTO = (222, 222, 216)
PROMPT = (120, 200, 130)
MARGEN = 22
ESCALA = 2  # se dibuja al doble y se reduce: bordes más limpios en el PDF


def fuente(tamano: int) -> ImageFont.FreeTypeFont:
    for ruta in FUENTES:
        if Path(ruta).exists():
            return ImageFont.truetype(ruta, tamano)
    sys.exit(
        "no se encontró una fuente monoespaciada; instalar jetbrains-mono-fonts o dejavu-sans-mono-fonts"
    )


def renderizar(texto: str, destino: Path, ancho_cols: int) -> None:
    lineas = texto.rstrip("\n").split("\n")
    f = fuente(15 * ESCALA)
    ancho_car = f.getlength("M")
    alto_lin = int(f.size * 1.45)
    ancho = int(ancho_car * ancho_cols) + 2 * MARGEN * ESCALA
    alto = alto_lin * len(lineas) + 2 * MARGEN * ESCALA

    img = Image.new("RGB", (ancho, alto), FONDO)
    d = ImageDraw.Draw(img)
    y = MARGEN * ESCALA
    for linea in lineas:
        color = PROMPT if linea.startswith("$ ") else TEXTO
        d.text((MARGEN * ESCALA, y), linea, font=f, fill=color)
        y += alto_lin

    img = img.resize((ancho // ESCALA, alto // ESCALA), Image.LANCZOS)
    img.save(destino, optimize=True)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("textos", nargs="+", type=Path)
    ap.add_argument("--ancho", type=int, default=0, help="columnas; 0 = la línea más larga")
    args = ap.parse_args()
    for ruta in args.textos:
        texto = ruta.read_text(encoding="utf-8")
        cols = args.ancho or max(len(l) for l in texto.splitlines()) + 1
        destino = ruta.with_suffix(".png")
        renderizar(texto, destino, cols)
        print(f"→ {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

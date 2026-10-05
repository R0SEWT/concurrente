#!/usr/bin/env bash
# Quita el fondo vacío bajo el último renglón de una captura de terminal, con un margen.
# No toca el contenido: solo corta filas de fondo al pie. El borde de la ventana se ignora al
# medir (por eso el -shave), porque sus esquinas tienen color.
#
#   tp/scripts/recortar_captura.sh img/ejec-go-test.png [más.png ...]
set -euo pipefail
for f in "$@"; do
	read -r w h < <(magick identify -format '%w %h\n' "$f")
	# caja del contenido dentro de la ventana: AnchoxAlto+X+Y
	caja=$(magick "$f" -shave 8x8 -fuzz 14% -format '%@' info:)
	alto_contenido=$(echo "$caja" | sed -E 's/^[0-9]+x([0-9]+)\+[0-9]+\+([0-9]+)$/\1 \2/' | awk '{print $1+$2+8}')
	nuevo=$((alto_contenido + 24))
	if [ "$nuevo" -lt "$h" ]; then
		magick "$f" -crop "${w}x${nuevo}+0+0" +repage "$f"
		echo "→ $f: ${h} → ${nuevo} px" >&2
	fi
done

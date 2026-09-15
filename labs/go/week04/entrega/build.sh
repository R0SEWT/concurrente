#!/usr/bin/env bash
# Arma la entrega de la semana 4, todo desde el mismo modelo Go:
#   tests → CSV → gráfico (matplotlib) → PDF (typst) + zip con el código.
#
#   ./week04/entrega/build.sh        # desde labs/go o desde cualquier lado
set -euo pipefail

cd "$(dirname "$0")/../.." # labs/go
salida=week04/entrega

go test -race ./week04/...
go vet ./week04/...
test -z "$(gofmt -l week04)" || { echo "gofmt: hay archivos sin formatear" >&2; exit 1; }

go run ./week04/cmd/escenarios >week04/ESCENARIOS.md
go run ./week04/cmd/escenarios -csv >week04/grafico/escenarios.csv
uv run --quiet week04/grafico/escenarios.py

# La demo termina con código distinto de cero cuando el detector encuentra la carrera.
go run -race ./week04/cmd/race >"$salida/race.txt" 2>&1 || true

typst compile --root week04 "$salida/matriz-escenarios.typ" "$salida/matriz-escenarios.pdf"

rm -f "$salida/week04-go.zip"
zip -q -r "$salida/week04-go.zip" go.mod week04 \
	-i 'go.mod' 'week04/*.go' 'week04/ESCENARIOS.md'

echo "listo:"
ls -lh "$salida/matriz-escenarios.pdf" "$salida/week04-go.zip"
unzip -l "$salida/week04-go.zip"

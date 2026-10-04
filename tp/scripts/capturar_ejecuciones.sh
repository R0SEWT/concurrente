#!/usr/bin/env bash
# Corre cada ejecución que cita el informe del TP y deja su captura en informe/tp/img/ejec-*.png.
#
# El docente pide una captura de cada ejecución: una que solo se nombra en el texto, o que aparece
# como listado, cuenta como no demostrada. Cada captura sale de la salida real del comando: el
# .txt queda junto al .png, su primera línea `$ ...` es el comando tal como se corrió, y este
# script los rehace todos.
#
#   tp/scripts/capturar_ejecuciones.sh            # todas
#   tp/scripts/capturar_ejecuciones.sh spin ci    # solo esos grupos
#
# Grupos: datos (nyc-tlc, pytest), go (vet + test -race), spin (make check y las salidas de pan
# que comenta el informe), benchmark (corrida reducida de demostración), ci (los checks de GitHub
# Actions sobre la PR del cierre del Entregable 3, que es el código que se entrega).
# Requiere uv, go, spin, cc y gh con sesión.
set -euo pipefail

TP=$(cd "$(dirname "$0")/.." && pwd)
IMG=$TP/informe/tp/img
GEN=$TP/informe/tp/generado

# capturar <nombre> <directorio> <comando> [columnas]: «$ comando» más su salida →
# img/ejec-<nombre>.txt. Si el comando falla, el script falla: una captura de un error no es
# evidencia de nada. De una línea de progreso que se reescribe con \r queda solo el último estado,
# como en la terminal; los tabuladores se expanden como en la terminal, salvo con «columnas», que
# alinea en columnas una salida tabular (la de gh).
capturar() {
	local nombre=$1 dir=$2 cmd=$3 modo=${4:-}
	local txt=$IMG/ejec-$nombre.txt
	echo "→ $nombre: $cmd" >&2
	{ echo "\$ $cmd"; (cd "$dir" && bash -o pipefail -c "$cmd") 2>&1; } > "$txt.tmp"
	if [ "$modo" = columnas ]; then
		sed 's/.*\r//' "$txt.tmp" | column -t -s $'\t' -L
	else
		sed 's/.*\r//' "$txt.tmp" | expand -t 8
	fi | sed 's/[[:space:]]*$//' > "$txt"
	rm "$txt.tmp"
}

# desde_generado <nombre> <comando> <archivo> <líneas>: las salidas de pan que deja
# `make informe` en generado/, con el comando que las produjo y recortadas como en el informe.
desde_generado() {
	local nombre=$1 cmd=$2 archivo=$3 lineas=$4
	{ echo "\$ $cmd"; head -n "$lineas" "$GEN/$archivo" | expand -t 8; } > "$IMG/ejec-$nombre.txt"
}

grupos=("$@")
[ ${#grupos[@]} -eq 0 ] && grupos=(datos go spin benchmark ci)

for g in "${grupos[@]}"; do
	case $g in
	datos)
		capturar pipeline "$TP" "uv run nyc-tlc all"
		capturar pytest "$TP" "uv run pytest -q"
		;;
	go)
		capturar go-test "$TP/kmeans" "go vet ./... && go test -race -count=1 ./..."
		;;
	spin)
		make -C "$TP/spin" informe >/dev/null
		capturar spin-check "$TP/spin" "make check"
		desde_generado spin-correcto \
			"spin -a kmeans.pml && cc -O2 -DNOCLAIM -o pan pan.c && ./pan" spin-correcto.txt 22
		desde_generado spin-mutante \
			"spin -DMUTANTE -a kmeans.pml && cc -O2 -DNOCLAIM -o pan-mutante pan.c && ./pan-mutante" \
			spin-mutante.txt 16
		desde_generado spin-termina \
			"spin -a kmeans.pml && cc -O2 -o pan-ltl pan.c && ./pan-ltl -a -f -N termina" spin-termina.txt 17
		desde_generado traza-deadlock \
			"spin -t -g -l -p -DMUTANTE_DEADLOCK kmeans.pml | sed -n '/trail ends/,\$p'" traza-deadlock.txt 26
		;;
	benchmark)
		# Corrida reducida, para mostrar el protocolo funcionando: las cifras del informe son de la
		# corrida oficial en gorgo (20 repeticiones, P hasta 16) y no salen de esta captura.
		capturar benchmark "$TP/kmeans" \
			"go run ./cmd/benchmark -repes 3 -workers 1,4,8 -experimentos fijas -bootstrap 200 -salida /tmp/benchmark-demo.json"
		;;
	ci)
		capturar ci "$TP/.." "gh pr checks 50" columnas
		;;
	*)
		echo "grupo desconocido: $g (datos, go, spin, benchmark, ci)" >&2
		exit 2
		;;
	esac
done

uv run --project "$TP" python "$TP/scripts/capturas_terminal.py" "$IMG"/ejec-*.txt

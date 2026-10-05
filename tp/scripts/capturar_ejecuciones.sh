#!/usr/bin/env bash
# Captura de pantalla real de cada ejecución que cita el informe del TP, en informe/tp/img/.
#
# El docente pide una captura de cada ejecución: una que solo se nombra en el texto, o que aparece
# como listado, cuenta como no demostrada. Por eso no se renderiza texto: el script abre una
# ventana de kitty flotante en Hyprland, teclea el comando en el shell de siempre (prompt, git,
# fastfetch), espera a que termine y fotografía la ventana con grim. Las pruebas van con -v, para
# que se vea cada caso y no solo un «ok».
#
#   tp/scripts/capturar_ejecuciones.sh            # todas
#   tp/scripts/capturar_ejecuciones.sh spin ci    # solo esos grupos
#
# Grupos: cli (secuencial y concurrente), datos (nyc-tlc, pytest), go (vet + test -race -v),
# spin (make check y las corridas de pan que comenta el informe), benchmark (corrida reducida de
# demostración), ci (checks de la PR #50, que cerró el Entregable 3).
# Requiere Hyprland (hyprctl eval), kitty, grim, uv, go, spin, cc y gh con sesión. Abre ventanas
# en el monitor activo: no tocar el teclado mientras corre.
set -euo pipefail

TP=$(cd "$(dirname "$0")/.." && pwd)
IMG=$TP/informe/tp/img
SOCK=${XDG_RUNTIME_DIR:-/tmp}/kitty-captura-$$.sock
KITTY=(kitty @ --to "unix:$SOCK")

# ¿Hay en la ventana algo distinto del shell en primer plano?
ocupado() {
	"${KITTY[@]}" ls | python3 -c '
import json, sys
procs = [p for o in json.load(sys.stdin) for t in o["tabs"] for w in t["windows"]
         for p in w["foreground_processes"]]
sys.exit(0 if any(not p["cmdline"][0].endswith("zsh") for p in procs) else 1)'
}

esperar() {
	sleep 1.5
	while ocupado; do sleep 1; done
	sleep 0.8 # el prompt se dibuja después de que termina el proceso
}

teclear() { "${KITTY[@]}" send-text -- "$1"$'\r'; }

# abrir <ancho> <alto> <fuente> <directorio>: kitty flotante bajo la barra, con el shell listo.
abrir() {
	local ancho=$1 alto=$2 fuente=$3 dir=$4
	rm -f "$SOCK"
	hyprctl eval "hl.exec_cmd(\"kitty --class captura-tp -o allow_remote_control=yes \
--listen-on unix:$SOCK -o env=GH_PAGER=cat -o env=PAGER=cat -o background_opacity=1 -o font_size=$fuente --directory $dir\", \
{ float = true, move = { 24, 52 }, size = { $ancho, $alto } })" >/dev/null
	for _ in $(seq 1 80); do [ -S "$SOCK" ] && break; sleep 0.25; done
	[ -S "$SOCK" ] || { echo "kitty no abrió la ventana de captura" >&2; exit 1; }
	esperar # fastfetch del .zshrc
}

foto() {
	local geo
	geo=$(hyprctl clients -j | python3 -c '
import json, sys
for c in json.load(sys.stdin):
    if c["class"] == "captura-tp":
        print("%d,%d %dx%d" % (*c["at"], *c["size"]))
        break')
	grim -g "$geo" "$IMG/$1.png"
	"$TP/scripts/recortar_captura.sh" "$IMG/$1.png" 2>/dev/null # fondo vacío bajo el prompt
	"${KITTY[@]}" close-window
	sleep 0.5
	echo "→ $IMG/$1.png" >&2
}

# capturar <nombre> <directorio> <ancho> <alto> <fuente> <limpiar: si|no> <comando>
# Con «si» se borra el fastfetch antes del comando, para las salidas largas.
capturar() {
	local nombre=$1 dir=$2 ancho=$3 alto=$4 fuente=$5 limpiar=$6 cmd=$7
	echo "· $nombre: $cmd" >&2
	abrir "$ancho" "$alto" "$fuente" "$dir"
	if [ "$limpiar" = si ]; then teclear clear; sleep 0.5; fi
	teclear "$cmd"
	esperar
	foto "$nombre"
}

grupos=("$@")
[ ${#grupos[@]} -eq 0 ] && grupos=(cli datos go spin benchmark ci)

for g in "${grupos[@]}"; do
	case $g in
	cli)
		# La secuencial genera los centroides iniciales y la concurrente los lee: mismo punto
		# de partida, y el «init 0 ms» de la segunda lo muestra.
		rm -f /tmp/centroides_k8.json
		capturar cli-secuencial "$TP/kmeans" 1000 640 10 no \
			"go run ./cmd/kmeans -modo seq -k 8 -iter 10 -centroides /tmp/centroides_k8.json"
		capturar cli-concurrente "$TP/kmeans" 1180 900 10 no \
			"go run ./cmd/kmeans -modo conc -workers 8 -chunk 16384 -k 8 -iter 10 -centroides /tmp/centroides_k8.json -progreso"
		;;
	datos)
		capturar ejec-pipeline "$TP" 1000 520 11 no "uv run nyc-tlc all"
		capturar ejec-pytest "$TP" 900 1020 8 si "uv run pytest -v --no-header"
		;;
	go)
		# -v imprime «=== RUN» y «--- PASS» por prueba; se filtran los RUN y los subtests (el padre
		# solo pasa si pasan todos sus subtests), y la suite se parte
		# en dos pantallas legibles: el núcleo (secuencial, concurrente y el piloto sobre el gold
		# real) y el resto. Entre las dos corren todas las pruebas, sin -short.
		capturar ejec-go-test "$TP/kmeans" 800 1020 8 si \
			"go vet ./... && go test -race -count=1 -v -run 'Concurrente|Secuencial|Piloto' ./... 2>&1 | grep -Ev '^(=== |    --- )'"
		capturar ejec-go-test-resto "$TP/kmeans" 800 1020 8 si \
			"go test -race -count=1 -v -skip 'Concurrente|Secuencial|Piloto' ./... 2>&1 | grep -Ev '^(=== |    --- )'"
		;;
	spin)
		capturar ejec-spin-check "$TP/spin" 1250 640 10 no "make check"
		capturar ejec-spin-correcto "$TP/spin" 1000 880 9 si "make verify"
		capturar ejec-spin-mutante "$TP/spin" 1000 700 9 si "make mutante"
		capturar ejec-spin-termina "$TP/spin" 1000 800 9 si \
			"spin -a kmeans.pml && cc -O2 -o pan-ltl pan.c && ./pan-ltl -a -f -N termina"
		capturar ejec-traza-deadlock "$TP/spin" 1300 680 9 si \
			"spin -DMUTANTE_DEADLOCK -a kmeans.pml && cc -O2 -DNOCLAIM -o pan-deadlock pan.c && ./pan-deadlock > /dev/null; spin -t -g -l -p -DMUTANTE_DEADLOCK kmeans.pml | sed -n '/trail ends/,\$p'"
		make -C "$TP/spin" clean >/dev/null
		;;
	benchmark)
		# Corrida reducida, para mostrar el protocolo funcionando: las cifras del informe son de la
		# corrida oficial en gorgo (20 repeticiones, P hasta 16) y no salen de esta captura.
		capturar ejec-benchmark "$TP/kmeans" 1250 680 10 no \
			"go run ./cmd/benchmark -repes 3 -workers 1,4,8 -experimentos fijas -bootstrap 200 -salida /tmp/benchmark-demo.json"
		;;
	ci)
		capturar ejec-ci "$TP/.." 1250 600 10 no "gh pr checks 50"
		;;
	*)
		echo "grupo desconocido: $g (cli, datos, go, spin, benchmark, ci)" >&2
		exit 2
		;;
	esac
done

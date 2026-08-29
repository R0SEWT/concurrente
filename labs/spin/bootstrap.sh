#!/usr/bin/env bash
# bootstrap.sh — instala Spin en ~/.local/bin sin sudo.
#
# Spin no está empaquetado en Fedora ni en Ubuntu, así que se compila desde
# fuente. Tarda ~10 s y el binario resultante pesa <1 MB con libc como única
# dependencia, así que también se puede copiar con scp a otra máquina.
#
#   ./bootstrap.sh          # instala si falta
#   ./bootstrap.sh --force  # recompila aunque ya exista
set -euo pipefail

PREFIX="${PREFIX:-$HOME/.local}"
SRC="${SPIN_SRC:-$HOME/Code/herramientas/spin}"
FORCE="${1:-}"

if [[ "$FORCE" != "--force" ]] && command -v spin >/dev/null 2>&1; then
	echo "spin ya está instalado: $(command -v spin) — $(spin -V)"
	exit 0
fi

# yacc no viene ni en Fedora ni en Ubuntu; bison lo emula con -y.
YACC="yacc"
command -v yacc >/dev/null 2>&1 || YACC="bison -y"

for t in gcc make; do
	command -v "$t" >/dev/null 2>&1 || { echo "falta $t" >&2; exit 1; }
done
command -v bison >/dev/null 2>&1 || command -v yacc >/dev/null 2>&1 || {
	echo "falta bison. Fedora: sudo dnf install bison flex" >&2
	echo "                Ubuntu: sudo apt install bison flex" >&2
	exit 1
}

if [[ -d "$SRC/.git" ]]; then
	git -C "$SRC" pull --ff-only -q
else
	mkdir -p "$(dirname "$SRC")"
	git clone -q https://github.com/nimble-code/Spin.git "$SRC"
fi

make -C "$SRC/Src" -s YACC="$YACC"
mkdir -p "$PREFIX/bin" "$PREFIX/share/man/man1"
make -C "$SRC/Src" install DESTDIR="$PREFIX" >/dev/null

echo "instalado: $PREFIX/bin/spin — $("$PREFIX/bin/spin" -V)"
case ":$PATH:" in
	*":$PREFIX/bin:"*) ;;
	*) echo "AVISO: $PREFIX/bin no está en tu PATH; agrégalo a tu shell rc." ;;
esac

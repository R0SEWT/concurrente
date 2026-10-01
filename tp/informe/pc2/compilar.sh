#!/usr/bin/env bash
# Compila el informe de la PC2: regenera lo generado y corre latexmk.
#
#   ./compilar.sh            # build/main.pdf
#   ./compilar.sh --open     # compila y abre el PDF
#   ./compilar.sh -c         # limpia (latexmk -c)
#
# En Fedora, latexmk y biber de TeX Live necesitan perl-sigtrap y libxcrypt-compat.
# Si no están instalados y no hay root, se descargan los RPM con `dnf download`,
# se extraen en build/deps/ y se usan por LD_LIBRARY_PATH y PERL5LIB. No toca el sistema.
set -euo pipefail
cd "$(dirname "$0")"

abrir=false
case "${1:-}" in
  "") ;;
  -c|--clean)
    latexmk -c
    exit 0
    ;;
  -o|--open) abrir=true ;;
  *)
    echo "uso: $0 [-c|--clean|-o|--open]" >&2
    exit 2
    ;;
esac

# Estas dependencias adicionales solo son necesarias en Fedora. En macOS se usa
# directamente la instalación local de MacTeX/TeX Live.
if [ "$(uname -s)" = "Linux" ]; then
  deps=build/deps
  export LD_LIBRARY_PATH="$PWD/$deps/usr/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
  export PERL5LIB="$PWD/$deps/usr/share/perl5${PERL5LIB:+:$PERL5LIB}"

  falta_sigtrap() { ! perl -e 'use sigtrap' 2>/dev/null; }
  falta_libcrypt() {
    ! command -v ldconfig >/dev/null 2>&1 ||
      { ! ldconfig -p | grep -q 'libcrypt\.so\.1 ' && [ ! -e "$deps/usr/lib64/libcrypt.so.1" ]; }
  }

  if falta_sigtrap || falta_libcrypt; then
    if [ ! -d "$deps/usr" ]; then
      if ! command -v dnf >/dev/null 2>&1; then
        echo "error: faltan dependencias de TeX Live y no está disponible dnf" >&2
        exit 1
      fi
      echo "→ faltan perl-sigtrap o libxcrypt-compat; se extraen en $deps (sin root)" >&2
      mkdir -p "$deps"
      ( cd "$deps" && dnf download -q perl-sigtrap libxcrypt-compat \
          && rm -f -- *.i686.rpm && for r in *.rpm; do rpm2cpio "$r" | cpio -idm --quiet; done && rm -f -- *.rpm )
    fi
  fi
fi

command -v latexmk >/dev/null 2>&1 || {
  echo "error: no se encontró latexmk; instala MacTeX o BasicTeX" >&2
  exit 1
}

if ! ./generar-historial.sh; then
  if [ -s generado/historial.tex ]; then
    echo "aviso: no se pudo actualizar el historial; se conserva generado/historial.tex" >&2
  else
    echo "error: no existe un historial anterior para continuar" >&2
    exit 1
  fi
fi
python3 ../../scripts/tablas_informe.py --salida generado
latexmk
echo "→ build/main.pdf"

if $abrir; then
  if [ "$(uname -s)" = "Darwin" ]; then
    open build/main.pdf
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open build/main.pdf
  else
    echo "aviso: abre manualmente $PWD/build/main.pdf" >&2
  fi
fi

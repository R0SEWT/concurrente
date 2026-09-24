#!/usr/bin/env bash
# Compila el informe de la PC2: regenera lo generado y corre latexmk.
#
#   ./compilar.sh            # build/main.pdf
#   ./compilar.sh -c         # limpia (latexmk -c)
#
# En Fedora, latexmk y biber de TeX Live necesitan perl-sigtrap y libxcrypt-compat.
# Si no están instalados y no hay root, se descargan los RPM con `dnf download`,
# se extraen en build/deps/ y se usan por LD_LIBRARY_PATH y PERL5LIB. No toca el sistema.
set -euo pipefail
cd "$(dirname "$0")"

deps=build/deps
export LD_LIBRARY_PATH="$PWD/$deps/usr/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export PERL5LIB="$PWD/$deps/usr/share/perl5${PERL5LIB:+:$PERL5LIB}"

falta_sigtrap() { ! perl -e 'use sigtrap' 2>/dev/null; }
falta_libcrypt() { ! ldconfig -p | grep -q 'libcrypt\.so\.1 ' && [ ! -e "$deps/usr/lib64/libcrypt.so.1" ]; }

if falta_sigtrap || falta_libcrypt; then
  if [ ! -d "$deps/usr" ]; then
    echo "→ faltan perl-sigtrap o libxcrypt-compat; se extraen en $deps (sin root)" >&2
    mkdir -p "$deps"
    ( cd "$deps" && dnf download -q perl-sigtrap libxcrypt-compat \
        && rm -f *.i686.rpm && for r in *.rpm; do rpm2cpio "$r" | cpio -idm --quiet; done && rm -f *.rpm )
  fi
fi

if [ "${1:-}" = "-c" ]; then
  latexmk -c
  exit 0
fi

./generar-historial.sh
python3 ../../scripts/tablas_informe.py --salida generado
latexmk
echo "→ build/main.pdf"

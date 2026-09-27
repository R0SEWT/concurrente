#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p build ../../../output/pdf
tectonic main.tex --outdir build --keep-logs
cp -f build/main.pdf ../../../output/pdf/CC65-Participacion-PC2-202620.pdf
echo "PDF: output/pdf/CC65-Participacion-PC2-202620.pdf"

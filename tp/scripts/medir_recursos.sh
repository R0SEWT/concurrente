#!/usr/bin/env bash
# Recolecta memoria y CPU por configuración, para el análisis de recursos.
#
#   ./medir_recursos.sh [salida.json]
#
# Corre la CLI una vez por configuración con -json y junta todo en un arreglo.
# No reemplaza al benchmark: acá interesa el consumo, no el tiempo, así que
# basta una corrida por configuración. Los tiempos del informe salen de
# cmd/benchmark, que sí repite y recorta.
set -euo pipefail

aqui=$(cd "$(dirname "$0")" && pwd)
cd "$aqui/../kmeans"

salida=${1:-../reports/recursos_$(hostname)_$(date +%F_%H%M).json}
# mktemp -u: solo el nombre. Si el archivo existe vacío, la CLI lo rechaza
# (y hace bien: un archivo de centroides corrupto no se ignora en silencio).
centroides=$(mktemp -u)
trap 'rm -f "$centroides" ./kmeans-recursos' EXIT

go build -o ./kmeans-recursos ./cmd/kmeans

# La primera corrida genera los centroides; las demás los leen, así todas
# parten de lo mismo.
tmp=$(mktemp)
echo "[" > "$tmp"
primera=1
for cfg in "seq 0" "conc 1" "conc 2" "conc 4" "conc 8" "conc 16"; do
  set -- $cfg
  modo=$1 workers=$2
  [ "$primera" = 1 ] || echo "," >> "$tmp"
  primera=0
  echo "  midiendo $modo ${workers:+P=$workers}" >&2
  ./kmeans-recursos -modo "$modo" -workers "${workers:-1}" -k 8 -iter 10 \
    -chunk 16384 -centroides "$centroides" -json >> "$tmp"
done
echo "]" >> "$tmp"

mkdir -p "$(dirname "$salida")"
mv "$tmp" "$salida"
echo "→ $salida" >&2

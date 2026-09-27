#!/usr/bin/env bash
# Corre el contraste completo en la caja con GPU (ssh gpu / ssh 4060), en orden:
#   1. benchmark de Go en CPU (misma máquina): trabajo fijo y hasta convergencia,
#      con el barrido de tamaños;
#   2. GPU con trabajo fijo, mismos tamaños, comparando contra 1;
#   3. GPU hasta convergencia sobre el dataset completo, comparando contra 1.
# La CPU va primero para que el benchmark de Go no compita con el host de la GPU.
#
# Se ejecuta EN el remoto, desde ~/proj/concurrente-gpu:
#   nohup ./correr_remoto.sh > logs/todo.log 2>&1 &
# Deja reports/benchmark_cpu.json, reports/gpu_fijas.json y reports/gpu_convergencia.json.
set -euo pipefail
cd "$(dirname "$0")"
export PATH="$HOME/go-sdk/bin:/usr/lib/wsl/lib:$PATH"

TAMANOS=${TAMANOS:-1000,10000,100000,1000000,0}
DATOS=data/yellow_2024-01_features.csv
CENT=data/centroides_k8_s2024.txt

echo "== $(date -Is) máquina $(hostname), $(nproc) CPUs, GPU: $(nvidia-smi --query-gpu=name,memory.used --format=csv,noheader)"

echo "== $(date -Is) 1/3 CPU Go: fijas + convergencia, tamaños $TAMANOS"
( cd kmeans && go run ./cmd/benchmark -datos "../$DATOS" -workers 1,2,4,8,16 \
    -tamanos "$TAMANOS" -experimentos fijas,convergencia -salida ../reports/benchmark_cpu.json )

echo "== $(date -Is) 2/3 GPU fijas, tamaños $TAMANOS"
.venv/bin/python kmeans_gpu.py --datos "$DATOS" --centroides "$CENT" --experimento fijas \
    --iter 10 --tamanos "$TAMANOS" --referencia reports/benchmark_cpu.json --salida reports/gpu_fijas.json

echo "== $(date -Is) 3/3 GPU convergencia, dataset completo"
.venv/bin/python kmeans_gpu.py --datos "$DATOS" --centroides "$CENT" --experimento convergencia \
    --iter 60 --tol-abs 1e-9 --tol-rel 1e-9 --tamanos 0 --referencia reports/benchmark_cpu.json \
    --salida reports/gpu_convergencia.json

echo "== $(date -Is) TODO-OK"

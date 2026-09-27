#!/data/data/com.termux/files/usr/bin/bash
# Replica la estructura del repo: ~/tp/kmeans (binarios) y ~/tp/data/gold (datos).
# Así la ruta por defecto ../data/gold/yellow_2024-01_features.csv resuelve sola.
set -e
O=/data/local/tmp/kmeans
mkdir -p ~/tp/kmeans ~/tp/data/gold
ln -sf $O/data/yellow_2024-01_features.csv ~/tp/data/gold/yellow_2024-01_features.csv
cp $O/data/centroides_k8_s2024.txt ~/tp/data/gold/
cp $O/kmeans $O/benchmark ~/tp/kmeans/
chmod +x ~/tp/kmeans/kmeans ~/tp/kmeans/benchmark
cat > ~/seq.sh <<'X'
cd ~/tp/kmeans && clear && ./kmeans -modo seq -k 8 -iter ${1:-10} -centroides ../data/gold/centroides_k8_s2024.txt -progreso
X
cat > ~/conc.sh <<'X'
cd ~/tp/kmeans && clear && ./kmeans -modo conc -workers ${1:-8} -k 8 -iter ${2:-10} -centroides ../data/gold/centroides_k8_s2024.txt -progreso
X
cat > ~/bench.sh <<'X'
cd ~/tp/kmeans && clear && ./benchmark -workers 1,2,4,8 -tamanos 0 -experimentos fijas -salida ~/benchmark_pixel9a.json
X
chmod +x ~/seq.sh ~/conc.sh ~/bench.sh
rm -f ~/kmeans ~/benchmark
echo "listo:"; ls -la ~/tp/data/gold ~/tp/kmeans

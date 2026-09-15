#!/usr/bin/env bash
# Genera generado/historial.tex: commits del Trabajo Parcial por integrante, desde las ramas
# publicadas en origin. Correr antes de compilar la versión que se entrega.
# Los alias de autor se unifican con el .mailmap de la raíz del repo.
set -euo pipefail
cd "$(dirname "$0")"

if ! git fetch --quiet origin; then
  echo "aviso: git fetch falló; se usan las refs de origin del último fetch" >&2
fi
# Sin refs de origin, git log no encuentra commits y la tabla saldría vacía: mejor abortar.
if [ -z "$(git for-each-ref --count=1 --format='%(refname)' refs/remotes/origin/)" ]; then
  echo "error: no hay refs de origin; haz git fetch origin antes de generar el historial" >&2
  exit 1
fi

out=generado/historial.tex
tmp="$(mktemp "${out}.XXXXXX")"
trap 'rm -f "$tmp"' EXIT
mkdir -p generado
rango=(--exclude='origin/__dolt*' --remotes=origin)
# ../../../docs es el docs/ de la raíz: ahí están las propuestas de caso (PR #3 y #4). No es tp/docs,
# que ya entra con ../../../tp. Con "--" delante, git no falla si la ruta no existe en alguna rama.
rutas=(-- ../../../tp ../../../docs)

escapar() { sed -e 's/\\/\//g' -e 's/[&%$#_{}]/\\&/g' -e 's/~/-/g' -e 's/\^/ /g'; }

commits="$(git log "${rango[@]}" --format='%ad|%aN|%h|%s' --date=short "${rutas[@]}")"
if [ -z "$commits" ]; then
  echo "error: git log no devolvió commits del Trabajo Parcial; no se sobrescribe $out" >&2
  exit 1
fi

{
  echo "% Generado por generar-historial.sh el $(date +%F). No editar a mano."
  echo '\begin{table}[H]'
  echo '\caption{Commits del Trabajo Parcial por integrante}\label{tab:commits-autor}'
  echo '\small'
  echo '\begin{tabular}{@{}lrrll@{}}'
  echo '\toprule'
  echo '\textbf{Integrante} & \textbf{Commits} & \textbf{Merges de PR} & \textbf{Primero} & \textbf{Último} \\'
  echo '\midrule'
  join -t '|' -a 1 -e 0 -o 1.1,1.2,2.2,1.3,1.4 \
    <(git log "${rango[@]}" --no-merges --format='%aN|%ad' --date=short "${rutas[@]}" \
        | awk -F'|' '{c[$1]++; if (!($1 in u)) u[$1]=$2; p[$1]=$2}
                     END {for (a in c) print a "|" c[a] "|" p[a] "|" u[a]}' | sort -t '|' -k1,1) \
    <(git log "${rango[@]}" --merges --grep='^Merge pull request' --format='%aN' | sort | uniq -c \
        | awk '{n=$1; $1=""; sub(/^ /, ""); print $0 "|" n}' | sort -t '|' -k1,1) \
    | escapar | awk -F'|' '{print $1 " & " $2 " & " $3 " & " $4 " & " $5 " \\\\"}'
  echo '\bottomrule'
  echo '\end{tabular}'
  echo
  echo '{\footnotesize\textit{Nota.} Todas las ramas publicadas en \texttt{origin}. Los merges de PR se cuentan aparte porque no tocan archivos por sí mismos.\par}'
  echo '\end{table}'
  echo
  echo '{\small'
  echo '\begin{xltabular}{\textwidth}{@{}L{2cm}L{2.9cm}L{1.5cm}Y@{}}'
  echo '\caption{Historial de commits del Trabajo Parcial, del más reciente al más antiguo}\label{tab:commits}\\'
  echo '\toprule'
  echo '\textbf{Fecha} & \textbf{Autor} & \textbf{Commit} & \textbf{Mensaje} \\'
  echo '\midrule'
  echo '\endfirsthead'
  echo '\toprule'
  echo '\textbf{Fecha} & \textbf{Autor} & \textbf{Commit} & \textbf{Mensaje} \\'
  echo '\midrule'
  echo '\endhead'
  echo '\bottomrule'
  echo '\endfoot'
  printf '%s\n' "$commits" | escapar | awk -F'|' '{print $1 " & " $2 " & \\texttt{" $3 "} & " $4 " \\\\"}'
  echo '\end{xltabular}'
  echo '}'
} > "$tmp"

mv "$tmp" "$out"
trap - EXIT
echo "escrito $out"

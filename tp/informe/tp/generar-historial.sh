#!/usr/bin/env bash
# Genera generado/historial.tex: commits del Trabajo Parcial por integrante y por entregable
# (tags pc1 y pc2 como cortes), desde las ramas publicadas en origin. Correr antes de compilar
# la versión que se entrega.
#
# Igual que el de la PC2, con una columna más:
#   - la tabla por integrante tiene una columna por entregable (PC1 | PC2 | TP);
#   - el listado de commits del TP (lo que no está en el tag pc2) marca cuáles ya están en
#     origin/main, o sea en la versión que se entrega, y cuáles siguen en una rama sin fusionar.
# Los alias de autor se unifican con el .mailmap de la raíz del repo.
set -euo pipefail
cd "$(dirname "$0")"

if ! git fetch --quiet origin; then
  echo "aviso: git fetch falló; se usan las refs de origin del último fetch" >&2
fi
if [ -z "$(git for-each-ref --count=1 --format='%(refname)' refs/remotes/origin/)" ]; then
  echo "error: no hay refs de origin; haz git fetch origin antes de generar el historial" >&2
  exit 1
fi
for t in pc1 pc2; do
  if ! git rev-parse -q --verify "$t" >/dev/null; then
    echo "error: no existe el tag $t; el historial del TP se define desde los tags pc1 y pc2" >&2
    exit 1
  fi
done

out=generado/historial.tex
tmp="$(mktemp "${out}.XXXXXX")"
trap 'rm -f "$tmp"' EXIT
mkdir -p generado

remotos=(--exclude='origin/__dolt*' --remotes=origin)
# ../../../docs es el docs/ de la raíz (propuestas de caso, PR #3 y #4). Con "--" delante, git no
# falla si la ruta no existe en alguna rama.
rutas=(-- ../../../tp ../../../docs)

escapar() { sed -e 's/\\/\//g' -e 's/[&%$#_{}]/\\&/g' -e 's/~/-/g' -e 's/\^/ /g'; }

# Conteo por autor en un rango. $1 = rango (p. ej. "pc1" o "pc1..").
conteo() {
  git log "$@" --no-merges --format='%aN' "${rutas[@]}" | sort | uniq -c \
    | awk '{n=$1; $1=""; sub(/^ /, ""); print $0 "|" n}' | sort -t '|' -k1,1
}

pc1="$(conteo pc1)"
pc2="$(conteo pc2 --not pc1)"
tp="$(conteo "${remotos[@]}" --not pc2)"
merges="$(git log "${remotos[@]}" --not pc2 --merges --grep='^Merge pull request' --format='%aN' \
  | sort | uniq -c | awk '{n=$1; $1=""; sub(/^ /, ""); print $0 "|" n}' | sort -t '|' -k1,1)"

autores="$( (printf '%s\n' "$pc1" "$pc2" "$tp" "$merges" | cut -d'|' -f1; git log pc1 --format='%aN' "${rutas[@]}") | grep -v '^$' | sort -u)"

buscar() { printf '%s\n' "$2" | awk -F'|' -v a="$1" '$1==a {print $2; f=1} END {if (!f) print 0}'; }

commits_tp="$(git log "${remotos[@]}" --not pc2 --no-merges --format='%H|%ad|%aN|%h|%s' --date=short "${rutas[@]}")"
if [ -z "$commits_tp" ]; then
  echo "error: git log no devolvió commits del TP (pc2..origin/*); no se sobrescribe $out" >&2
  exit 1
fi

{
  echo "% Generado por generar-historial.sh el $(date +%F). No editar a mano."
  echo '\begin{table}[H]'
  echo '\caption{Commits del Trabajo Parcial por integrante y entregable}\label{tab:commits-autor}'
  echo '\footnotesize'
  echo '\begin{tabular}{@{}lrrrr@{}}'
  echo '\toprule'
  echo '\textbf{Integrante} & \textbf{PC1} & \textbf{PC2} & \textbf{TP (nuevos)} & \textbf{Merges de PR (TP)} \\'
  echo '\midrule'
  while IFS= read -r a; do
    [ -n "$a" ] || continue
    printf '%s & %s & %s & %s & %s \\\\\n' "$(printf '%s' "$a" | escapar)" \
      "$(buscar "$a" "$pc1")" "$(buscar "$a" "$pc2")" "$(buscar "$a" "$tp")" "$(buscar "$a" "$merges")"
  done <<< "$autores"
  echo '\bottomrule'
  echo '\end{tabular}'
  echo
  echo '{\footnotesize\textit{Nota.} Commits que tocan \texttt{tp/} o \texttt{docs/}. PC1 cuenta hasta el tag \texttt{pc1} (entregado el 13 de septiembre); PC2, de \texttt{pc1} al tag \texttt{pc2} (entregado el 27 de septiembre); TP, lo que no está en \texttt{pc2}, en todas las ramas publicadas en \texttt{origin}. Los merges de PR se cuentan aparte porque no tocan archivos por sí mismos.\par}'
  echo '\end{table}'
  echo
  echo '{\small'
  echo '\begin{xltabular}{\textwidth}{@{}L{1.9cm}L{2.7cm}L{1.4cm}Yc@{}}'
  echo '\caption{Commits del Entregable 3, del más reciente al más antiguo}\label{tab:commits}\\'
  echo '\toprule'
  echo '\textbf{Fecha} & \textbf{Autor} & \textbf{Commit} & \textbf{Mensaje} & \textbf{En \texttt{main}} \\'
  echo '\midrule'
  echo '\endfirsthead'
  echo '\toprule'
  echo '\textbf{Fecha} & \textbf{Autor} & \textbf{Commit} & \textbf{Mensaje} & \textbf{En \texttt{main}} \\'
  echo '\midrule'
  echo '\endhead'
  echo '\bottomrule'
  echo '\endfoot'
  while IFS='|' read -r sha fecha autor corto msg; do
    if git merge-base --is-ancestor "$sha" origin/main 2>/dev/null; then en='sí'; else en='no'; fi
    printf '%s & %s & \\texttt{%s} & %s & %s \\\\\n' "$fecha" "$(printf '%s' "$autor" | escapar)" \
      "$corto" "$(printf '%s' "$msg" | escapar)" "$en"
  done <<< "$commits_tp"
  echo '\end{xltabular}'
  echo '}'
  echo
  echo '{\footnotesize\textit{Nota.} «En \texttt{main}» indica si el commit ya forma parte de \texttt{origin/main} al generar esta tabla; los que dicen «no» están en una rama publicada pendiente de fusión.\par}'
} > "$tmp"

mv "$tmp" "$out"
trap - EXIT
echo "escrito $out"

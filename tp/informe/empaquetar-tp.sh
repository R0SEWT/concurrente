#!/usr/bin/env bash
# Arma el paquete de entrega del TP (Entregable 3) con los nombres que pide el enunciado:
#
#   CC65-TP-202620-<código>.pdf      uno por alumno (el mismo informe); cada uno sube el suyo
#   CC65-Participación-202620.pdf    lo adjunta el coordinador
#   CC65-TP-202620-Datos.txt         enlace y sha256 de los datos (el CSV no entra en el Aula)
#   SHA256SUMS y ENTREGA.md          qué commit y qué tag produjeron cada archivo
#
#   ./empaquetar-tp.sh                 # en ~/Descargas/CC65-TP-202620/
#   ./empaquetar-tp.sh <directorio>
#
# Igual que empaquetar-pc2.sh. La versión final se arma desde el tag tp, después del release a
# main (por una rama release/tp, nunca con develop como rama de origen). Desde otra ref el paquete
# sale igual, pero marcado como preliminar en ENTREGA.md.
set -euo pipefail
cd "$(dirname "$0")"

destino="${1:-$HOME/Descargas/CC65-TP-202620}"
informe=tp
participacion=participacion-tp

# Los códigos salen de la misma fuente que la carátula del informe.
codigo() { sed -n "s/.*\\\\newcommand{\\\\codigo$1}{\\([^}]*\\)}.*/\\1/p" "$informe/preambulo/macros.tex"; }
codigos=("$(codigo Rody)" "$(codigo Dayana)" "$(codigo Tercero)")
for c in "${codigos[@]}"; do
  [[ "$c" =~ ^U[0-9]{9}$ ]] || { echo "código de alumno inválido en macros.tex: '$c'" >&2; exit 1; }
done

# Solo cuentan las marcas fuera de comentarios: las plantillas explican en un comentario qué reemplazar.
if grep -rnE '^[^%]*\\(pendiente|verificar)\{' "$informe/secciones/" "$participacion/main.tex"; then
  echo "quedan marcas \\pendiente o \\verificar: no se empaqueta" >&2; exit 1
fi
if grep -qi 'completar por el l' "$participacion/main.tex"; then
  echo "el comentario del team leader sigue sin completar" >&2; exit 1
fi
# Cada integrante tiene que tener marcado un nivel de cumplimiento en su primera fila.
for n in 2 3; do
  if grep -E "^$n & [^&]+ & [^&]+ & *& *& *\\\\" "$participacion/main.tex"; then
    echo "el integrante $n no tiene marcado su nivel de cumplimiento" >&2; exit 1
  fi
done

commit="$(git rev-parse HEAD)"
tag="$(git describe --tags --exact-match HEAD 2>/dev/null || true)"
sucio="$(git status --porcelain -- . ':!tp/generado/historial.tex' | head -1)"

echo "→ informe"
"./$informe/compilar.sh" >/dev/null
echo "→ reporte de participación"
( cd "$participacion" && mkdir -p build && tectonic main.tex --outdir build >/dev/null )

mkdir -p "$destino"
rm -f "$destino"/CC65-TP-202620-*.pdf "$destino"/CC65-Participación-202620.pdf
for c in "${codigos[@]}"; do
  cp "$informe/build/main.pdf" "$destino/CC65-TP-202620-$c.pdf"
done
cp "$participacion/build/main.pdf" "$destino/CC65-Participación-202620.pdf"
cp datos-entrega.txt "$destino/CC65-TP-202620-Datos.txt"

( cd "$destino" && sha256sum CC65-TP-202620-*.pdf CC65-Participación-202620.pdf CC65-TP-202620-Datos.txt > SHA256SUMS )

estado="final"
[[ "$tag" == "tp" ]] || estado="PRELIMINAR (HEAD no es el tag tp)"
[[ -z "$sucio" ]] || estado="$estado; hay cambios sin commitear en tp/informe"
paginas="$(pdfinfo "$informe/build/main.pdf" | sed -n 's/^Pages: *//p')"

cat > "$destino/ENTREGA.md" <<EOF
# Entrega TP · CC65 · 2026-20

- Estado: **$estado**
- Commit: \`$commit\`${tag:+ (tag \`$tag\`)}
- Generado: $(date '+%Y-%m-%d %H:%M %Z')
- Informe: $paginas páginas, el mismo PDF para los tres

| Archivo | Lo sube |
|---|---|
| \`CC65-TP-202620-${codigos[0]}.pdf\` | Rody (coordinador) |
| \`CC65-TP-202620-${codigos[1]}.pdf\` | Dayana |
| \`CC65-TP-202620-${codigos[2]}.pdf\` | Julio |
| \`CC65-Participación-202620.pdf\` | Rody, junto con su informe |
| \`CC65-TP-202620-Datos.txt\` | Rody, junto con su informe (enlace a los datos) |

Cada alumno sube su archivo al Aula Virtual: el enunciado no admite otro medio.
El video (Anexo A del informe) tiene que estar publicado y el tag \`tp\` en main antes de la hora
de entrega: el enunciado resta 5 puntos sin video y 10 si main se edita después.
Los sha256 están en \`SHA256SUMS\`.
EOF

echo
echo "paquete en $destino ($estado)"
ls -1 "$destino"

#!/usr/bin/env bash
# Arma el paquete de entrega de la PC2 con los nombres que pide el enunciado:
#
#   CC65-PC2-202620-<código>.pdf     uno por alumno (el mismo informe); cada uno sube el suyo
#   CC65-Participación-202620.pdf    lo adjunta el coordinador
#   SHA256SUMS y ENTREGA.md          qué commit y qué tag produjeron cada archivo
#
#   ./empaquetar-pc2.sh                # en ~/Descargas/CC65-PC2-202620/
#   ./empaquetar-pc2.sh <directorio>
#
# La versión final se arma desde el tag pc2, después del release a main: así la columna
# «En main» del historial dice sí. Desde otra ref el paquete sale igual, pero marcado como
# preliminar en ENTREGA.md.
set -euo pipefail
cd "$(dirname "$0")"

destino="${1:-$HOME/Descargas/CC65-PC2-202620}"
informe=pc2
participacion=participacion-pc2

# Los códigos salen de la misma fuente que la carátula del informe.
codigo() { sed -n "s/.*\\\\newcommand{\\\\codigo$1}{\\([^}]*\\)}.*/\\1/p" "$informe/preambulo/macros.tex"; }
codigos=("$(codigo Rody)" "$(codigo Dayana)" "$(codigo Tercero)")
for c in "${codigos[@]}"; do
  [[ "$c" =~ ^U[0-9]{9}$ ]] || { echo "código de alumno inválido en macros.tex: '$c'" >&2; exit 1; }
done

if grep -rn '\\pendiente{' "$informe/secciones/" "$participacion/main.tex"; then
  echo "quedan marcas \\pendiente: no se empaqueta" >&2; exit 1
fi
if grep -qi 'completar por el l' "$participacion/main.tex"; then
  echo "el comentario del team leader sigue sin completar" >&2; exit 1
fi

commit="$(git rev-parse HEAD)"
tag="$(git describe --tags --exact-match HEAD 2>/dev/null || true)"
sucio="$(git status --porcelain -- . ':!pc2/generado/historial.tex' | head -1)"

echo "→ informe"
"./$informe/compilar.sh" >/dev/null
echo "→ reporte de participación"
( cd "$participacion" && mkdir -p build && tectonic main.tex --outdir build >/dev/null )

mkdir -p "$destino"
rm -f "$destino"/CC65-PC2-202620-*.pdf "$destino"/CC65-Participación-202620.pdf
for c in "${codigos[@]}"; do
  cp "$informe/build/main.pdf" "$destino/CC65-PC2-202620-$c.pdf"
done
cp "$participacion/build/main.pdf" "$destino/CC65-Participación-202620.pdf"

( cd "$destino" && sha256sum CC65-PC2-202620-*.pdf CC65-Participación-202620.pdf > SHA256SUMS )

estado="final"
[[ "$tag" == "pc2" ]] || estado="PRELIMINAR (HEAD no es el tag pc2)"
[[ -z "$sucio" ]] || estado="$estado; hay cambios sin commitear en tp/informe"
paginas="$(pdfinfo "$informe/build/main.pdf" | sed -n 's/^Pages: *//p')"

cat > "$destino/ENTREGA.md" <<EOF
# Entrega PC2 · CC65 · 2026-20

- Estado: **$estado**
- Commit: \`$commit\`${tag:+ (tag \`$tag\`)}
- Generado: $(date '+%Y-%m-%d %H:%M %Z')
- Informe: $paginas páginas, el mismo PDF para los tres

| Archivo | Lo sube |
|---|---|
| \`CC65-PC2-202620-${codigos[0]}.pdf\` | Rody (coordinador) |
| \`CC65-PC2-202620-${codigos[1]}.pdf\` | Dayana |
| \`CC65-PC2-202620-${codigos[2]}.pdf\` | Julio |
| \`CC65-Participación-202620.pdf\` | Rody, junto con su informe |

Cada alumno sube su archivo al Aula Virtual: el enunciado no admite otro medio.
Los sha256 están en \`SHA256SUMS\`.
EOF

echo
echo "paquete en $destino ($estado)"
ls -1 "$destino"

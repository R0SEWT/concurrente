#!/usr/bin/env bash
# Regresión del modelo: cada caso fija qué debe responder pan, no solo que corra.
#
#   ./check.sh            # todos los casos
#   CC=gcc MEM="-m100000 -w26" ./check.sh
#   TSV=casos.tsv ./check.sh   # además deja una fila por caso (la tabla del informe sale de ahí)
#
# Un caso es: variante del modelo | corrida de pan | errores esperados | tipo de error | qué prueba.
# Las variantes -D son el mismo kmeans.pml con una línea distinta, para que la comparación sea
# justa. Un "errors: 0" solo convence si el mismo chequeo da "errors: 1" cuando el algoritmo
# está mal; por eso cada propiedad tiene su mutante.
#
# El tipo de error se compara con el texto de pan. Una fórmula de seguridad [] p se traduce a un
# never claim con un assert adentro, y su violación dice "assertion violated !( !( !((p)))".
# Por eso no se usa -A, que apagaría también ese assert, y el tipo esperado nombra la fórmula y no
# cualquier aserción del modelo.
#
# "sin-ltl" compila pan con -DNOCLAIM: con un never claim activo pan desactiva la búsqueda de
# estados finales inválidos, que es justamente como aparece un deadlock. (pan no tiene una opción
# de ejecución para ignorar las fórmulas: sin -N usa la primera, y -noclaim se ignora sin aviso.)
set -euo pipefail
cd "$(dirname "$0")"

CC="${CC:-cc}"
CFLAGS="${CFLAGS:--O2}"
MEM="${MEM:-}"
TSV="${TSV:-}"
[[ -z "$TSV" ]] || printf 'variante\tcorrida\terrores\testados\ttransiciones\tprofundidad\terror\tque\n' > "$TSV"

casos=(
  "correcto|sin-ltl|0||seguridad: aserciones y estados finales válidos (sin deadlock)"
  "correcto|-a -N exclusion|0||LTL: nadie publica centroides mientras hay lectores"
  "correcto|-a -f -N termina|0||LTL: las dos iteraciones terminan (weak fairness)"
  "MUTANTE|sin-ltl|1|assertion violated|acumulador compartido sin mutex: incremento perdido"
  "MUTANTE_DEADLOCK|sin-ltl|1|invalid end state|un worker pierde el wg.Done: deadlock en la barrera"
  "MUTANTE_DEADLOCK|-a -f -N termina|1|acceptance cycle|el mismo wg.Done perdido: la corrida nunca termina"
  "MUTANTE_SIN_BARRERA|-a -N exclusion|1|escribiendo&&(lectores>0)|el coordinador publica sin esperar la barrera"
)

compilado=""
fallas=0
for caso in "${casos[@]}"; do
  IFS='|' read -r variante corrida esperado tipo que <<< "$caso"
  flags="$corrida"; extra=""; bin="pan-$variante"
  if [[ "$corrida" == sin-ltl* ]]; then
    flags="${corrida#sin-ltl}"; extra="-DNOCLAIM"; bin="$bin-sin-ltl"
  fi
  if [[ " $compilado " != *" $bin "* ]]; then
    def=""; [[ "$variante" != correcto ]] && def="-D$variante"
    spin $def -a kmeans.pml > /dev/null
    # shellcheck disable=SC2086
    $CC $CFLAGS $extra -o "$bin" pan.c
    compilado="$compilado $bin"
  fi
  # shellcheck disable=SC2086
  salida="$(./"$bin" $flags $MEM 2>&1 || true)"
  # Sin fórmulas, la búsqueda tiene que incluir los estados finales inválidos.
  if [[ -n "$extra" && "$salida" != *"invalid end states"$'\t'"+"* ]]; then
    ok_sin=0
  else
    ok_sin=1
  fi
  n="$(sed -n 's/.*errors: \([0-9]*\).*/\1/p' <<< "$salida" | tail -1)"
  ok=$ok_sin
  (( ok )) || tipo="la búsqueda no incluyó los estados finales inválidos"
  [[ "$n" == "$esperado" ]] || ok=0
  [[ -z "$tipo" || "$salida" == *"$tipo"* ]] || ok=0
  # pan -N con un nombre que no existe no reclama nada y da 0 errores: exigir que la fórmula
  # figure como el never claim activo de la búsqueda.
  if [[ "$corrida" =~ -N\ ([a-z_]+) ]]; then
    [[ "$salida" == *"never claim"*"+ (${BASH_REMATCH[1]})"* ]] || { ok=0; tipo="sin la fórmula ${BASH_REMATCH[1]}"; }
  fi
  if [[ -n "$TSV" ]]; then
    estados="$(sed -n 's/^ *\([0-9]*\) states, stored.*/\1/p' <<< "$salida" | tail -1)"
    trans="$(sed -n 's/^ *\([0-9]*\) transitions.*/\1/p' <<< "$salida" | tail -1)"
    prof="$(sed -n 's/.*depth reached \([0-9]*\).*/\1/p' <<< "$salida" | tail -1)"
    error="$(grep -m1 -E '^pan:[0-9]+:' <<< "$salida" | sed 's/^pan:[0-9]*: *//' || true)"
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$variante" "$corrida" "$n" "$estados" "$trans" \
      "$prof" "$error" "$que" >> "$TSV"
  fi
  if (( ok )); then
    printf '  ok    %-20s %-20s errores: %s  %s\n' "$variante" "$corrida" "$n" "$que"
  else
    printf '  FALLA %-20s %-20s errores: %s (se esperaban %s%s)  %s\n' \
      "$variante" "$corrida" "${n:-?}" "$esperado" "${tipo:+, $tipo}" "$que"
    fallas=$((fallas + 1))
  fi
done
rm -f pan.? pan.[a-z][a-z] *.trail pan-* _spin_nvr.tmp

if (( fallas )); then
  echo "== $fallas caso(s) fallaron: el modelo dejó de probar lo que dice probar =="
  exit 1
fi
echo "== regresión OK: ${#casos[@]} casos =="

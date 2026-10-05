# Verificación del modelo de sincronización del K-means concurrente.
#
#   make verify     # el modelo correcto, sin fórmulas LTL: aserciones y deadlock, 0 errores
#   make ltl        # el modelo correcto contra cada fórmula LTL (exclusion, termina)
#   make mutante    # el modelo con la carrera: debe dar 1 error
#   make check      # regresión: 7 casos con el número y el tipo de error esperados (check.sh)
#   make trail      # reproduce el contraejemplo del mutante paso a paso
#   make figuras    # autómata del worker y contraejemplo del mutante para el informe
#   make informe    # figuras + salidas de pan + tabla de los 7 casos, en el informe del TP
#
# INFORME elige a qué informe van las salidas (tp/informe/$(INFORME)/). Por defecto el del TP:
# el de la PC2 quedó congelado en el tag pc2 y no se regenera desde acá.
#
# El modelo trae fórmulas LTL: sin -DNOCLAIM, pan usa la primera y desactiva la
# búsqueda de estados finales inválidos, que es como aparece un deadlock. Por eso
# las corridas de seguridad se compilan con -DNOCLAIM.
#
# A diferencia de labs/spin/Makefile, `check` compara el número de errores
# contra el esperado. Que aparezca una línea "errors: N" no dice nada si nadie
# mira N: un modelo que dejó de probar lo que decía probar sigue imprimiéndola.

CC     ?= cc
CFLAGS ?= -O2
MEM    ?=          # p. ej. MEM="-m100000 -w26" si pan se queda sin memoria

.PHONY: verify ltl mutante check trail figuras informe clean

verify: ## Búsqueda exhaustiva sobre el modelo correcto: aserciones y estados finales
	spin -a kmeans.pml
	$(CC) $(CFLAGS) -DNOCLAIM -o pan pan.c
	./pan $(MEM)

ltl: ## El modelo correcto contra cada fórmula LTL; termina con weak fairness
	spin -a kmeans.pml
	$(CC) $(CFLAGS) -o pan-ltl pan.c
	./pan-ltl -a -N exclusion $(MEM)
	./pan-ltl -a -f -N termina $(MEM)

mutante: ## El mismo modelo con un acumulador compartido sin exclusión mutua
	spin -DMUTANTE -a kmeans.pml
	$(CC) $(CFLAGS) -DNOCLAIM -o pan-mutante pan.c
	-./pan-mutante $(MEM)

check: ## Regresión: cada variante y fórmula con el resultado esperado
	@CC="$(CC)" CFLAGS="$(CFLAGS)" MEM="$(MEM)" ./check.sh

trail: ## Lee el contraejemplo que dejó el mutante
	spin -t -p -DMUTANTE kmeans.pml

INFORME  ?= tp
GENERADO := ../informe/$(INFORME)/generado

figuras: ## Figuras del informe: pan -D (autómatas) y la traza del mutante
	spin -a kmeans.pml >/dev/null && $(CC) $(CFLAGS) -DNOCLAIM -o pan pan.c
	./pan -D > $(GENERADO)/automatas.dot
	spin -DMUTANTE -a kmeans.pml >/dev/null && $(CC) $(CFLAGS) -DNOCLAIM -o pan-mutante pan.c
	-./pan-mutante $(MEM) >/dev/null
	spin -t -p -l -g -DMUTANTE kmeans.pml > $(GENERADO)/traza-mutante.txt
	uv run ../scripts/figuras_spin.py --informe $(INFORME)

# Cada salida de pan que cita el informe, con la misma compilación que check.sh.
# El informe del TP cita estos rangos de kmeans.pml (secciones/17-verificacion-formal.tex): si el
# modelo se mueve, fallar acá antes que mostrar las líneas equivocadas.
RANGOS := 80:lectores--  107:wg.Add  113:pendientes\ ==\ 0  134:Exclusión\ mutua

informe: figuras ## Salidas de pan y tabla de los 7 casos para el informe
	@for r in $(RANGOS); do l=$${r%%:*}; t=$${r#*:}; sed -n "$${l}p" kmeans.pml | grep -qF -- "$$t" \
	  || { echo "kmeans.pml:$$l ya no dice «$$t»: actualizar los rangos del informe del TP" >&2; exit 1; }; done
	@CC="$(CC)" CFLAGS="$(CFLAGS)" MEM="$(MEM)" TSV=$(GENERADO)/spin-casos.tsv ./check.sh
	spin -a kmeans.pml >/dev/null && $(CC) $(CFLAGS) -DNOCLAIM -o pan pan.c
	./pan $(MEM) > $(GENERADO)/spin-correcto.txt
	$(CC) $(CFLAGS) -o pan-ltl pan.c
	./pan-ltl -a -f -N termina $(MEM) > $(GENERADO)/spin-termina.txt
	spin -DMUTANTE -a kmeans.pml >/dev/null && $(CC) $(CFLAGS) -DNOCLAIM -o pan-mutante pan.c
	-./pan-mutante $(MEM) > $(GENERADO)/spin-mutante.txt
	spin -DMUTANTE_DEADLOCK -a kmeans.pml >/dev/null && $(CC) $(CFLAGS) -DNOCLAIM -o pan-deadlock pan.c
	-./pan-deadlock $(MEM) > $(GENERADO)/spin-deadlock.txt
	spin -t -g -l -p -DMUTANTE_DEADLOCK kmeans.pml | sed -n '/trail ends/,$$p' > $(GENERADO)/traza-deadlock.txt
	spin -DMUTANTE_SIN_BARRERA -a kmeans.pml >/dev/null && $(CC) $(CFLAGS) -o pan-sin-barrera pan.c
	-./pan-sin-barrera -a -N exclusion $(MEM) > $(GENERADO)/spin-sin-barrera.txt
	rm -f pan pan-* pan.? pan.[a-z][a-z] *.trail _spin_nvr.tmp
	uv run ../scripts/figuras_spin.py --informe $(INFORME) --solo-tabla

clean:
	rm -f pan pan-* pan.* *.trail _spin_nvr.tmp

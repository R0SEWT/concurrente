# Verificación del modelo de sincronización del K-means concurrente.
#
#   make verify     # el modelo correcto, sin fórmulas LTL: aserciones y deadlock, 0 errores
#   make ltl        # el modelo correcto contra cada fórmula LTL (exclusion, termina)
#   make mutante    # el modelo con la carrera: debe dar 1 error
#   make check      # regresión: 7 casos con el número y el tipo de error esperados (check.sh)
#   make trail      # reproduce el contraejemplo del mutante paso a paso
#   make figuras    # autómata del worker y contraejemplo del mutante para el informe
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

.PHONY: verify ltl mutante check trail figuras clean

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

GENERADO := ../informe/pc2/generado

figuras: ## Figuras del informe: pan -D (autómatas) y la traza del mutante
	spin -a kmeans.pml >/dev/null && $(CC) $(CFLAGS) -DNOCLAIM -o pan pan.c
	./pan -D > $(GENERADO)/automatas.dot
	spin -DMUTANTE -a kmeans.pml >/dev/null && $(CC) $(CFLAGS) -DNOCLAIM -o pan-mutante pan.c
	-./pan-mutante $(MEM) >/dev/null
	spin -t -p -l -g -DMUTANTE kmeans.pml > $(GENERADO)/traza-mutante.txt
	uv run ../scripts/figuras_spin.py

clean:
	rm -f pan pan-* pan.* *.trail _spin_nvr.tmp

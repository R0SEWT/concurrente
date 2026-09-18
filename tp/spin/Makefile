# Verificación del modelo de sincronización del K-means concurrente.
#
#   make verify     # el modelo correcto: debe dar 0 errores
#   make mutante    # el modelo con la carrera: debe dar 1 error
#   make check      # regresión: comprueba AMBOS números, no solo que corra
#   make trail      # reproduce el contraejemplo del mutante paso a paso
#
# A diferencia de labs/spin/Makefile, `check` compara el número de errores
# contra el esperado. Que aparezca una línea "errors: N" no dice nada si nadie
# mira N: un modelo que dejó de probar lo que decía probar sigue imprimiéndola.

CC     ?= cc
CFLAGS ?= -O2
MEM    ?=          # p. ej. MEM="-m100000 -w26" si pan se queda sin memoria

.PHONY: verify mutante check trail clean

verify: ## Búsqueda exhaustiva sobre el modelo correcto
	spin -a kmeans.pml
	$(CC) $(CFLAGS) -o pan pan.c
	./pan -a $(MEM)

mutante: ## El mismo modelo con un acumulador compartido sin exclusión mutua
	spin -DMUTANTE -a kmeans.pml
	$(CC) $(CFLAGS) -o pan-mutante pan.c
	-./pan-mutante -a $(MEM)

check: ## Regresión: 0 errores en el correcto, 1 en el mutante
	@echo "== modelo correcto: se esperan 0 errores =="
	@spin -a kmeans.pml >/dev/null && $(CC) $(CFLAGS) -o pan pan.c
	@n=$$(./pan -a $(MEM) 2>&1 | sed -n 's/.*errors: \([0-9]*\).*/\1/p' | tail -1); \
	  echo "   errores: $$n"; \
	  test "$$n" = "0" || { echo "   FALLA: se esperaban 0"; exit 1; }
	@echo "== mutante: se espera 1 error (incremento perdido) =="
	@spin -DMUTANTE -a kmeans.pml >/dev/null && $(CC) $(CFLAGS) -o pan-mutante pan.c
	@n=$$(./pan-mutante -a $(MEM) 2>&1 | sed -n 's/.*errors: \([0-9]*\).*/\1/p' | tail -1); \
	  echo "   errores: $$n"; \
	  test "$$n" = "1" || { echo "   FALLA: se esperaba 1; el modelo dejó de detectar la carrera"; exit 1; }
	@echo "== regresión OK =="

trail: ## Lee el contraejemplo que dejó el mutante
	spin -t -p -DMUTANTE kmeans.pml

clean:
	rm -f pan pan-mutante pan.* *.trail

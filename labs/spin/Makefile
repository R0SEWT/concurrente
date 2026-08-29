# Verificación de modelos Promela con Spin.
#
#   make verify MODEL=critical                    # safety (aserciones)
#   make verify MODEL=peterson CLAIM=exclusion    # una propiedad LTL nombrada
#   make fair   MODEL=peterson CLAIM=sin_inanicion  # liveness, con fairness débil
#   make trail  MODEL=critical                    # leer el contraejemplo
#
# OJO: el -N que elige la propiedad va en ./pan, NO en spin.
# `spin -N` espera un ARCHIVO con un never claim; con ltl inline no sirve.
# El propio pan lo dice al generarse: "choose which one with ./pan -a -N name".

MODEL ?= peterson
CLAIM ?=
CC    ?= cc
CFLAGS ?= -O2
FAIR  ?=            # -f para habilitar fairness débil (ver target `fair`)
MEM   ?=            # p.ej. MEM="-m100000 -w26" si pan se queda sin memoria

NFLAG = $(if $(CLAIM),-N $(CLAIM))

.PHONY: verify fair trail check clean

verify: ## Genera el verificador, lo compila y lo corre
	spin -a $(MODEL).pml
	$(CC) $(CFLAGS) -o pan pan.c
	./pan -a $(FAIR) $(NFLAG) $(MEM)

fair: ## Liveness bajo fairness débil (sin esto, todo claim de progreso "falla")
	$(MAKE) verify MODEL=$(MODEL) CLAIM=$(CLAIM) FAIR=-f

trail: ## Reproduce paso a paso el último contraejemplo
	spin -t -p $(MODEL).pml

check: ## Regresión: los tres resultados esperados del repo
	@echo "== critical: DEBE encontrar 1 error (incremento perdido) =="
	@$(MAKE) --no-print-directory verify MODEL=critical 2>&1 | grep -E "errors: [0-9]+"
	@echo "== peterson/exclusion: DEBE dar 0 errores =="
	@$(MAKE) --no-print-directory verify MODEL=peterson CLAIM=exclusion 2>&1 | grep -E "errors: [0-9]+"
	@echo "== peterson/sin_inanicion con -f: DEBE dar 0 errores =="
	@$(MAKE) --no-print-directory fair MODEL=peterson CLAIM=sin_inanicion 2>&1 | grep -E "errors: [0-9]+"

clean:
	rm -f pan pan.[bchmpt] pan.pre *.trail *.nvr

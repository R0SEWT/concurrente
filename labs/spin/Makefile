# Verificación de modelos Promela con Spin.
#   make verify MODEL=peterson CLAIM=exclusion
#   make trail  MODEL=peterson      # leer el contraejemplo del último fallo

MODEL ?= peterson
CLAIM ?=
CC    ?= cc
PANFLAGS ?= -a

ifdef CLAIM
SPINFLAGS = -a -N $(CLAIM)
else
SPINFLAGS = -a
endif

.PHONY: verify fair trail clean

verify: ## Verificación exhaustiva (safety)
	spin $(SPINFLAGS) $(MODEL).pml
	$(CC) -o pan pan.c
	./pan $(PANFLAGS)

fair: PANFLAGS = -a -f   ## Liveness bajo fairness débil
fair: verify

trail: ## Reproducir paso a paso el contraejemplo
	spin -t -p $(MODEL).pml

clean:
	rm -f pan pan.* *.trail _spin_nvr.tmp

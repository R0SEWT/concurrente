/*
 * peterson.pml — algoritmo de Peterson para dos procesos.
 *
 * Verifica las dos propiedades que un algoritmo de sección crítica debe cumplir:
 *   - exclusion (safety):    nunca hay dos procesos dentro a la vez.
 *   - sin_inanicion (liveness): quien quiere entrar, eventualmente entra.
 *
 * La liveness solo se sostiene bajo fairness débil — sin -f, Spin encuentra
 * un "contraejemplo" donde un proceso simplemente nunca es planificado, que
 * no dice nada del algoritmo. Ver README.
 */

bool want[2];      /* want[i]: P(i) quiere entrar          */
byte turn;         /* de quién es el turno si ambos quieren */
byte ncrit = 0;    /* cuántos procesos hay dentro           */
bool dentro[2];    /* dentro[i]: P(i) está en la SC         */

active [2] proctype P() {
	pid i = _pid;
	pid j = 1 - _pid;

	do
	:: true ->
		want[i] = true;
		turn = j;
		(!want[j] || turn == i);   /* espera bloqueante */

		ncrit++;
		dentro[i] = true;
		assert(ncrit == 1);        /* la propiedad, también como aserción local */
		dentro[i] = false;
		ncrit--;

		want[i] = false
	od
}

ltl exclusion      { [] (ncrit <= 1) }
ltl sin_inanicion  { [] (want[0] -> <> dentro[0]) }

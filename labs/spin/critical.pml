/*
 * critical.pml — la sección crítica sin proteger.
 *
 * Contraparte del contador Unsafe en labs/go/week01. Acá el model checker
 * no depende de la suerte del scheduler: explora TODOS los entrelazados y
 * encuentra el que pierde un incremento.
 *
 *   spin -a critical.pml && cc -o pan pan.c && ./pan
 *
 * Esperado: "assertion violated" con un contraejemplo. Léelo con
 *   spin -t -p critical.pml
 */

byte n = 0;

proctype P() {
	byte temp;
	temp = n;          /* leer  */
	n = temp + 1       /* escribir — entre ambos, el otro proceso puede correr */
}

init {
	atomic { run P(); run P() }
	(_nr_pr == 1);     /* espera a que ambos P terminen; solo queda init */
	assert(n == 2)
}

/*
 * Sincronización de una iteración de Lloyd con worker pool.
 *
 * Esto NO es el K-means: no hay distancias, ni centroides reales, ni punto
 * flotante. Es el esqueleto de sincronización de tp/kmeans/concurrente.go, con
 * un dominio chiquito, para que Spin pueda recorrer TODOS los entrelazados.
 *
 * Lo que se modela:
 *   - un canal de chunks que reparte el trabajo entre P workers persistentes;
 *   - acumuladores privados por chunk (conteo[c]);
 *   - la barrera del final de cada iteración (pendientes, o sea el WaitGroup);
 *   - la publicación de centroides nuevos, que solo puede ocurrir sin lectores.
 *
 * Lo que se verifica (ver README.md):
 *   1. Procesamiento exactamente una vez: seen[i] == 1 al final de cada iteración.
 *      Sumar los conteos NO alcanza: procesar A dos veces y omitir B da el mismo
 *      total. Por eso se cuenta por punto.
 *   2. Nadie escribe centroides mientras hay workers leyéndolos, ni al revés.
 *   3. Conservación: la reducción suma exactamente N puntos.
 *   4. Ausencia de deadlock (estados finales válidos, que pan chequea solo).
 *
 * Se modelan DOS iteraciones a propósito: los errores de reutilizar la barrera
 * o de no reiniciar los acumuladores solo aparecen en la segunda.
 *
 * Con -DMUTANTE se reemplaza el acumulador privado por uno compartido sin
 * exclusión mutua, con lectura y escritura separadas. Spin debe encontrar ahí
 * el contraejemplo; si no lo encuentra, el modelo no está probando nada.
 */

#define N     4          /* puntos */
#define C     2          /* chunks */
#define TAM   (N / C)    /* puntos por chunk */
#define ITERS 2          /* iteraciones */

byte seen[N];            /* veces que se procesó cada punto en esta iteración */
byte conteo[C];          /* acumulador privado de cada chunk */
byte pendientes;         /* WaitGroup: chunks que faltan terminar */
byte lectores;           /* workers dentro de la fase de asignación */
bit  escribiendo;        /* el coordinador está publicando centroides */
byte total;              /* resultado de la reducción */

chan trabajos = [C] of { byte };

#ifdef MUTANTE
byte compartido;         /* acumulador compartido, sin mutex */
#endif

proctype worker()
{
    byte idx, i, tmp;
end:                     /* bloquearse acá esperando trabajo es legítimo */
    do
    :: trabajos ? idx ->
        lectores++;
        assert(escribiendo == 0);     /* centroides de solo lectura */
        conteo[idx] = 0;              /* acumulador privado, reiniciado por iteración */
        i = 0;
        do
        :: i < TAM ->
            assert(escribiendo == 0);
            seen[idx * TAM + i]++;
            conteo[idx] = conteo[idx] + 1;
#ifdef MUTANTE
            tmp = compartido;         /* lectura  */
            tmp = tmp + 1;            /*   ...    */
            compartido = tmp;         /* escritura: acá se pierde el incremento */
#endif
            i++
        :: else -> break
        od;
        lectores--;
        pendientes--                  /* wg.Done() */
    od
}

init
{
    byte it, c, i;

    atomic { run worker(); run worker() }   /* P = 2 */

    it = 0;
    do
    :: it < ITERS ->
        i = 0;
        do :: i < N -> seen[i] = 0; i++ :: else -> break od;
        total = 0;
#ifdef MUTANTE
        compartido = 0;
#endif
        /* wg.Add antes de encolar: la tarea se registra antes de ejecutarse */
        pendientes = C;
        c = 0;
        do :: c < C -> trabajos ! c; c++ :: else -> break od;

        pendientes == 0;              /* barrera: wg.Wait() */
        assert(lectores == 0);        /* recién ahora se puede escribir */

        escribiendo = 1;
        c = 0;
        do :: c < C -> total = total + conteo[c]; c++ :: else -> break od;
        escribiendo = 0;

        i = 0;
        do :: i < N -> assert(seen[i] == 1); i++ :: else -> break od;
        assert(total == N);
#ifdef MUTANTE
        assert(compartido == N);
#endif
        it++
    :: else -> break
    od
}

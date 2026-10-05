# Guion del video de sustentación (TP, Entregable 3)

**Duración máxima:** 6:00.  
**Meta de grabación:** 5:30 (deja 30 segundos de margen de seguridad).  
**Exigencia de la rúbrica (5 pts):** Cada integrante demuestra dominio del tema, se exponen resultados experimentales y formales, se muestra el cierre del caso de uso y hay una discusión crítica de limitaciones, escalabilidad y mejoras.  
*(Penalidad del sílabo: -5 pts sin video; nota 00 al integrante que no aparezca en pantalla).*

---

## Instrucciones de grabación y ensamble

1. **Modalidad:** Cada integrante puede grabar su fragmento por separado (usando OBS Studio, Google Meet o Zoom en grabación local) o reunirse los tres en una llamada.
2. **Cámara obligatoria:** Rostro visible en una esquina superior o lateral durante toda la intervención.
3. **Compartir pantalla:**
   - PDF del informe: `tp/informe/tp/build/main.pdf` en la página/figura correspondiente.
   - Terminal para comandos en vivo (`make check` en Spin).
   - Navegador para la demo de la app móvil (`http://localhost:8080/` o capturas de la Sección 16).
4. **Edición:** Dayana une las tres pistas (acordado el sáb 3), verifica que el tiempo total no exceda los 6:00, sube el archivo a Google Drive o YouTube (acceso no listado / público) y coloca el enlace y los tiempos en el Anexo A del informe (`tp/informe/tp/secciones/19-anexos.tex`).

---

## Tabla de Tiempos y Estructura

| Parte | Integrante | Intervalo | Duración | Temas Clave |
|---|---|---|---|---|
| **1** | **Rody** | 0:00 – 2:00 | 2m 00s | Problema ODS 11, worker pool en Go, CLI, `go test -race` y benchmark en vivo, speedup fuerte |
| **2** | **Dayana** | 2:00 – 3:45 | 1m 45s | Verificación formal en Spin/Promela, LTL, mutantes y demo `make check` |
| **3** | **Julio** | 3:45 – 5:50 | 2m 05s | GAPs con IA, cierre de clusters ODS 11, demo de la App y discusión crítica |
| — | *Margen* | 5:50 – 6:00 | 10s | Colchón de seguridad para transiciones y cierre |

---

## Parte 1 · Rody · 0:00 – 2:00 · Caso, Algoritmo Concurrente y Speedup

*Las páginas son las impresas al pie del PDF (en Evince, `Ctrl+L` y el número).*

**Antes de grabar** (terminal en `~/Code/cursos/concurrente/tp/kmeans`, fuente grande con `Ctrl +`):
correr una vez cada comando para que el CSV quede en la caché del disco y `go run` ya esté compilado.
El docente pide ver cada ejecución en pantalla: las tres van en vivo, no en captura.

**En pantalla, en orden:**
1. Carátula del informe (`tp/informe/tp/build/main.pdf`, pág. 1).
2. Diagrama del worker pool (Sección 8, Figura 14, pág. 47).
3. **Terminal 1 · CLI en vivo** (secuencial y luego concurrente, mismos centroides):
   ```bash
   go run ./cmd/kmeans -modo seq -k 8 -iter 10 -centroides /tmp/centroides_k8.json
   go run ./cmd/kmeans -modo conc -workers 8 -chunk 16384 -k 8 -iter 10 -centroides /tmp/centroides_k8.json -progreso
   ```
   Señalar: `clustering` baja de ~3,4 s a ~0,8 s y la `inercia` es la misma (4,531799e+06). Con
   `-progreso` se ve cada iteración de Lloyd con la inercia J bajando.
4. **Terminal 1 · pruebas con el detector de carreras** (1 s):
   ```bash
   go test -race -short -count=1 -v -run Concurrente .
   ```
5. Tabla de speedup fuerte (Sección 9, Tabla 25, pág. 51).
6. **Terminal 2 · benchmark reducido** (~30 s; arrancarlo mientras se habla de la tabla):
   ```bash
   go run ./cmd/benchmark -repes 3 -workers 1,4,8 -experimentos fijas -bootstrap 200 -salida /tmp/benchmark-demo.json
   ```

**Texto sugerido:**
> **[Carátula]** «Buenos días, profesor. Somos el grupo 4. Nuestro caso analiza **2,83 millones de viajes limpios** del taxi amarillo de Nueva York, enero de 2024, con K-means, alineado con el **ODS 11**, ciudades sostenibles.
>
> **[Figura 14]** Implementamos Lloyd en Go, sin librerías externas, en dos versiones con el mismo contrato: secuencial y concurrente. La concurrente es un **worker pool persistente**: las goroutines se crean una sola vez, un canal reparte bloques de viajes, cada bloque acumula en su propia memoria sin contención, y una barrera con `sync.WaitGroup` cierra cada iteración. La reducción suma los bloques **siempre en el mismo orden**, por eso el resultado es idéntico con cualquier número de workers.
>
> **[CLI]** Acá lo corro sobre el dataset completo. La secuencial tarda unos 3,4 segundos en el clustering; la concurrente con 8 workers, menos de un segundo, y llega a la **misma inercia**: es la misma solución, más rápido. Con la barra se ve cada iteración.
>
> **[go test]** Las pruebas corren con el **detector de carreras**: verifican que la versión concurrente da lo mismo que la secuencial con cualquier número de workers.
>
> **[Tabla 25 + benchmark]** Para medir, el benchmark baraja las configuraciones, repite y usa media recortada. Esta es una corrida corta en la laptop; la oficial, con 20 repeticiones, da **3,80×** con 4 workers y **5,82×** con 8. El techo no lo pone una parte secuencial del algoritmo sino el **costo de coordinar la barrera**, y por debajo de unos **20 000 viajes** sincronizar cuesta más que calcular.
>
> Le doy el pase a Dayana para la verificación formal.»

---

## Parte 2 · Dayana · 2:00 – 3:45 · Verificación Formal en Spin y Mutantes

**En pantalla:**
1. Sección 14 del informe (`build/main.pdf`, pág. 61, Verificación formal); la regresión corriendo está en la Figura 16 (pág. 63).
2. Tabla 34 (`build/main.pdf`, pág. 64, modelo correcto y mutantes).
3. Terminal con la ejecución en vivo: `cd tp/spin && make check`.

**Texto sugerido:**
> «Gracias Rody. Mientras que las pruebas tradicionales solo observan un entrelazado por ejecución, en este proyecto utilizamos **Spin y Promela** para explorar de manera exhaustiva todo el espacio de estados de la sincronización.
>
> Modelamos la interacción entre un coordinador y dos workers con acumuladores privados, paso de mensajes por canal y barrera. Sobre este modelo verificamos tres propiedades formales:
> 1. **Ausencia de deadlock:** Ningún proceso queda bloqueado fuera de esperas legítimas.
> 2. **Exclusión mutua:** Especificada mediante la fórmula LTL $\Box \neg(\text{publicando} \land \text{leyendo})$, comprobando que el coordinador jamás actualiza centroides mientras un worker lee.
> 3. **Progreso:** La corrida completa todas las iteraciones bajo *weak fairness*.
>
> Sin embargo, un resultado de *cero errores* es engañoso si la prueba no tiene la capacidad de fallar. Por ello, adoptamos una **metodología de mutantes**:
> * En el mutante de deadlock, omitimos deliberadamente la señal `Done` de un worker, y Spin detecta el bloqueo en el paso 181.
> * En el mutante sin barrera, el coordinador publica centroides sin esperar a los workers, y Spin encuentra de inmediato el contraejemplo que viola la fórmula LTL.
>
> *(Mostrar terminal y ejecutar `make check`)*
>
> Como se observa en la terminal, los 7 casos —el modelo correcto y sus tres mutantes bajo aserciones, LTL y ciclo de progreso— se ejecutan automáticamente en nuestra integración continua, validando la solidez formal antes de tocar el código en producción.
>
> Ahora Julio explicará los hallazgos de IA, el cierre de los clusters y las conclusiones.»

---

## Parte 3 · Julio · 3:45 – 5:50 · GAPs con IA, Interpretación ODS 11, Demo App y Crítica

**En pantalla:**
1. Tabla 35 de GAPs con IA (`build/main.pdf`, Sección 15, pág. 69).
2. Tabla 36 de arquetipos y Figura 19 de la app móvil (`build/main.pdf`, Sección 16, págs. 71–73) o ventana del navegador con `http://localhost:8080/`.
3. Sección 18 (Conclusiones y recomendaciones, pág. 79).

**Texto sugerido:**
> «Gracias Dayana. En la implementación verificamos ausencia de carreras con `go test -race` y casos borde calculados a mano.
>
> Además, realizamos una auditoría de código asistida por IA mediante **Claude** con un prompt estructurado. El análisis confirmó la solidez de la concurrencia pero detectó un problema de arquitectura que ni Spin ni los tests observan: **false sharing**. Los contadores de bloques vecinos compartían la misma línea de caché L1/L2, lo que con $K=4$ generaba una penalidad del 12 %. También identificó que la GPU en PyTorch no es determinista en sumas flotantes, arrojando 8 valores de inercia distintos.
>
> **Cierre del caso de uso (ODS 11):**
> Resolvimos la interpretación de los 8 clusters con sus unidades reales. Los viajes se dividen en 3 regímenes: micro-saltos corporativos (23 %), saturación vial a menos de 10 mph (54 %) y corredores periféricos hacia aeropuertos (23 %).
>
> El hallazgo clave para el ODS 11.2 es que en **Midtown Center al mediodía**, el **41,2 % de los viajes mide 1 milla o menos**. En cuadrícula urbana, estos trayectos se cubren en 6 minutos en bicicleta o 12 a pie; esta evidencia cuantitativa respalda directamente políticas como el *Congestion Pricing* y nuevas ciclovías protegidas. Asimismo, a las 14:00 Manhattan genera más de 7 700 viajes que explican el pico de las 15:00 en JFK y LaGuardia.
>
> *(Mostrar brevemente la app en el navegador o la Fig. 8)*
> Desarrollamos un visor cartográfico ultraligero que corre sobre un resumen de 735 KB generado en Go, aplicando el principio de honestidad **InWatch**: las zonas sin taxis no se interpolan falsamente, sino que se identifican como servidas por la red de Metro MTA.
>
> **Discusión crítica y limitaciones:**
> Reconocemos como limitación haber trabajado con un único mes de datos y en memoria compartida. Como trabajo futuro para la Unidad 2, escalaremos el algoritmo a un entorno **distribuido entre varias máquinas** conectando nuestro servidor y la GPU mediante paso de bloques por red, y extenderemos el análisis a un año completo para medir la estabilidad estacional de los centroides.
>
> Con esto concluimos nuestra sustentación. Muchas gracias.»

---

## Checklist de Cierre para Rody (Coordinador)

- [ ] Compartir este guion con Dayana y Julio.
- [ ] Grabar las tres intervenciones asegurando la presencia de cámara y pantalla.
- [ ] Ensamblar el video final y verificar que dure entre **5:20 y 5:45** (nunca más de 6:00).
- [ ] Subir el video a Google Drive o YouTube (acceso público o con enlace).
- [ ] Colocar el enlace y los tiempos exactos en `tp/informe/tp/secciones/19-anexos.tex` (Anexo A):
  ```latex
  \begin{itemize}
    \item \textbf{URL:} \url{https://...}
    \item \textbf{Duración:} 05:32
    \item \textbf{Partes:} Rody Vilchez (0:00, Algoritmo y Speedup), Dayana Gómez (2:00, Spin y Mutantes), Julio Meza (3:45, IA, Clusters ODS 11 y Discusión Crítica).
  \end{itemize}
  ```
- [ ] Recompilar el informe con `./compilar.sh` y validar que el Anexo A quede sin marcas de `\pendiente`.

# Guion del video de sustentación (TP, Entregable 3)

**Duración máxima: 6:00.** El guion apunta a 5:30, para tener margen. Lo que exige el enunciado:
cada integrante demuestra conocimiento del tema, se presentan los resultados y hay una discusión
crítica de limitaciones, escalabilidad y posibles mejoras. Si alguien no aparece, su nota es 00.

- **Cómo grabar**: cada uno graba su parte por separado, compartiendo pantalla (Meet, Zoom u OBS),
  con la cámara encendida en una esquina. Rody une las tres partes y sube el video.
- **Qué mostrar**: el PDF del informe (`tp/informe/tp/build/main.pdf`) en la sección que se
  nombra, o la terminal cuando se indica.
- **El texto es una sugerencia**: se puede decir con otras palabras. Lo que no se cambia son las
  cifras, que salen del informe.

| Parte | Quién | Tiempo | Tema |
|---|---|---|---|
| 1 | Rody | 0:00–1:50 | El caso, el algoritmo concurrente y el speedup |
| 2 | Dayana | 1:50–3:40 | Verificación formal en Spin |
| 3 | Julio | 3:40–5:30 | Tests, análisis con IA y discusión crítica |

---

## Parte 1 · Rody · 0:00–1:50 · el caso, el algoritmo y el speedup

**En pantalla**: la carátula; después la figura del worker pool (Sección 8); después la tabla de
speedup fuerte (Sección 9).

> Somos el Equipo K-means NYC TLC. Nuestro caso es agrupar con K-means 2,8 millones de viajes del
> taxi amarillo de Nueva York, de enero de 2024, para encontrar patrones de movilidad urbana, en
> línea con el ODS 11.
>
> Implementamos el algoritmo de Lloyd en Go, sin librerías, en dos versiones con el mismo
> contrato numérico: una secuencial y una concurrente. La concurrente usa un worker pool: las
> goroutines viven toda la corrida, un canal les reparte bloques de viajes, cada bloque tiene sus
> propios acumuladores, y una barrera con `sync.WaitGroup` cierra cada iteración. Como la reducción
> suma los bloques siempre en el mismo orden, el resultado es idéntico con cualquier cantidad de
> workers.
>
> Medimos con 20 repeticiones por configuración, en orden aleatorio, con media recortada al 10 %.
> Con cuatro workers el speedup es 3,80 y con ocho, 5,82. Lo que limita la escalabilidad no es una
> parte secuencial del código: es el costo de coordinar, que crece con los workers. Y por debajo de
> unos 20 000 viajes la concurrencia no paga.

## Parte 2 · Dayana · 1:50–3:40 · verificación formal en Spin

**En pantalla**: la Sección 14 del PDF (verificación formal); la Tabla 33 con los siete casos; en
la terminal, `cd tp/spin && make check`.

> Los tests observan un entrelazado por corrida. Para el diseño usamos Spin, que recorre todos los
> entrelazados posibles de un modelo en Promela. El modelo es el esqueleto de sincronización del
> worker pool: el canal, los acumuladores por bloque, la barrera y la publicación de centroides,
> con cuatro puntos, dos bloques, dos workers y dos iteraciones.
>
> Verificamos tres propiedades. Ausencia de deadlock: ningún proceso queda bloqueado fuera de una
> espera legítima. Exclusión mutua: el coordinador nunca publica centroides mientras un worker los
> lee, escrito como fórmula LTL. Y progreso: la corrida termina, bajo weak fairness.
>
> Lo importante es que cada verificación puede fallar. Para cada propiedad hay un mutante: si un
> worker pierde su `wg.Done`, Spin encuentra el deadlock en la barrera; si el coordinador publica
> sin esperarla, se viola la exclusión. El modelo correcto da cero errores en los tres casos y cada
> mutante da exactamente su error. Son siete casos que corren en la integración continua.
>
> *(Mostrar `make check`: los siete «ok» y «regresión OK».)*

## Parte 3 · Julio · 3:40–5:30 · tests, IA y discusión crítica

**En pantalla**: `tp/kmeans/concurrente_test.go`; después la Sección 15 del PDF (GAPs, Tabla del
análisis por categoría); al final, las recomendaciones de la Sección 17.

> Spin verifica el diseño; la implementación la prueban los tests con `go test -race`. Agregué
> casos borde que se pueden calcular a mano: un cluster vacío conserva su centroide, un empate va al
> centroide de menor índice, con k = 1 el centroide es la media y con k = N la inercia es cero. Cada
> caso se prueba con 1, 2 y 4 workers.
>
> También analizamos el código con un modelo de IA, Claude Opus 5.5, con un prompt estructurado, y
> contrastamos cada hallazgo contra el código. No encontró errores de sincronización, lo que
> coincide con Spin y con `-race`. Pero sí encontró algo que ninguna de las dos herramientas ve:
> *false sharing*. Los contadores de dos bloques vecinos comparten una línea de caché, y con k = 4
> eso cuesta un 12 %; con nuestro k = 8 no pasa, por casualidad. Y encontró que el programa de
> benchmark, que produce todas nuestras cifras, no tiene tests y puede perder una sesión entera
> de medición si falla al final.
>
> Las limitaciones: la verificación en Spin vale para un modelo pequeño y bajo weak fairness, y no
> modela el cierre del pool. Medimos un solo mes de datos. Y todavía no interpretamos los clusters.
> Para escalar recomendamos más meses de datos, donde coordinar pesa menos frente al trabajo, elegir
> k con un criterio de validación y, para varias máquinas, repartir los bloques por red, que es el
> tema de la unidad 2.

---

## Checklist de Rody

- [ ] Mandar este guion al grupo el jueves 1/10.
- [ ] Unir las tres partes y comprobar que la duración total sea menor a 6:00.
- [ ] Subir el video con acceso por enlace y ponerlo en el Anexo A del informe
      (`secciones/19-anexos.tex`: URL, duración y minuto en que empieza cada parte).

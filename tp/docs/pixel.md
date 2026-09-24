# El K-means en un celular: Pixel 9a con Termux

El mismo binario de `tp/kmeans`, compilado para Android, corriendo sobre los 2 831 486 viajes del
gold en un Google Pixel 9a. Sirve para dos cosas: como tercera plataforma del análisis de speedup,
con un procesador de núcleos **heterogéneos**, y como demostración para el video del TP.

Datos en `tp/reports/benchmark_pixel9a.json` y `tp/reports/temperatura_pixel9a.csv`; capturas en
`tp/reports/figuras/pixel/`.

## El equipo

| | |
|---|---|
| Teléfono | Google Pixel 9a (`tegu`), Android 17 |
| SoC | Google Tensor G4: 1 núcleo a 3,1 GHz, 3 a 2,6 GHz y 4 a 1,95 GHz |
| RAM | 7,4 GB |
| Entorno | Termux 0.118.3 (build de GitHub), Go 1.26.7 compilado en la laptop |

Go ve 8 CPUs lógicas y las trata como iguales; Android decide en qué tipo de núcleo corre cada
goroutine.

## Resultados, mismo protocolo que la PC2

20 repeticiones más calentamiento, orden barajado, media recortada al 10 %, IC por bootstrap. Speedup
sobre el dataset completo, trabajo fijo de 10 iteraciones:

| Máquina | Secuencial | P=2 | P=4 | P=8 | P=16 | IC 95 % con P=8 | Variación del secuencial |
|---|---:|---:|---:|---:|---:|:--|---:|
| gorgo, 11 núcleos x86 | 1 106 ms | 1,93× | 3,80× | 5,82× | 6,25× | [5,73; 5,89] | 0,4 % |
| Caja 4060, i7-10700 de 16 hilos | 1 650 ms | 1,73× | 3,42× | 6,12× | 7,88× | [6,04; 6,20] | 0,3 % |
| Pixel 9a, Tensor G4 | 3 606 ms | 1,90× | 3,50× | 3,95× | 3,94× | [3,25; 4,79] | 28,8 % |

Hasta convergencia (60 iteraciones) el Pixel da 4,47× con P=8, con la misma forma.

La inercia final concurrente es **idéntica bit a bit en las tres máquinas**: 4531798,747970126 con
trabajo fijo y 4461447,055723991 hasta convergencia. Dos arquitecturas distintas (x86-64 y ARM64),
tres sistemas operativos, el mismo número. Es la consecuencia directa de reducir los parciales en
orden de bloque (Sección «Por qué la reducción va en orden de bloque» del informe de la PC2).

## Tres lecturas

**La curva se aplana en 4, no en 8.** Hasta P=4 el Pixel escala como las otras dos máquinas (3,50×).
De 4 a 8 gana casi nada: los cuatro núcleos que faltan son los pequeños, a 1,95 GHz y con mucha menos
capacidad por ciclo. Como el worker pool reparte bloques por un canal, los núcleos lentos toman menos
bloques y no frenan a los rápidos, pero tampoco aportan mucho. Es el mismo techo que en la laptop con
SMT: el procesador anuncia 8 CPUs y trabajan como unas 4.

**La dispersión es cien veces mayor.** El coeficiente de variación del secuencial pasa de 0,3 % en
las máquinas de escritorio a 29 % en el teléfono, y el intervalo del speedup con P=8 se abre de ±0,1
a ±0,8. La causa es el control térmico y de frecuencia del teléfono, que se ve en los datos crudos:

| Tramo | Secuencial, primeras 7 medidas | Últimas 7 | Cambio |
|---|---:|---:|---:|
| Trabajo fijo (primeros 5 min, batería subiendo a 38,5 °C) | 2 531 ms | 3 917 ms | +55 % |
| Hasta convergencia (batería bajando a 35 °C) | 17 165 ms | 12 977 ms | −24 % |

Mientras el teléfono se calienta, el gobernador baja la frecuencia y el mismo trabajo tarda más;
cuando se enfría, la vuelve a subir. Barajar el orden reparte esa deriva entre configuraciones, así
que el speedup sigue siendo comparable, pero la media recortada ya no describe una máquina estable:
describe un promedio sobre estados térmicos. En un celular hace falta enfriar entre rondas o fijar la
frecuencia (requiere root) para medir como en la PC2.

**Cabe sobrado.** 349 MB de heap para los datos y un RSS máximo de ~830 MB en un teléfono de 7,4 GB.
La carga del CSV tarda ~2,2 s, igual que en la laptop.

## Cómo se montó

Termux desde el APK de GitHub, instalado por `adb`. El gold y los centroides se suben con `adb push` a
`/data/local/tmp/kmeans/data/`, que Termux puede leer; `tp/scripts/pixel/setup.sh` arma dentro de
Termux la misma estructura que el repo (`~/tp/kmeans`, `~/tp/data/gold`) para que la ruta por defecto
de la CLI resuelva sola, y deja `~/seq.sh`, `~/conc.sh` y `~/bench.sh`.

```bash
cd tp/kmeans
CGO_ENABLED=0 GOOS=android GOARCH=arm64 go build -trimpath -o /tmp/kmeans ./cmd/kmeans
CGO_ENABLED=0 GOOS=android GOARCH=arm64 go build -trimpath -o /tmp/benchmark ./cmd/benchmark
adb push /tmp/kmeans /tmp/benchmark ../scripts/pixel/setup.sh /data/local/tmp/kmeans/
adb push ../data/gold/yellow_2024-01_features.csv /data/local/tmp/kmeans/data/
# en Termux:  bash /data/local/tmp/kmeans/setup.sh && ./seq.sh && ./conc.sh 8
```

En Termux, `./seq.sh` muestra la barra de progreso por iteración (`-progreso`, que escribe en stderr
y no toca la salida medible).

## Tres problemas que aparecieron, y qué enseñan

1. **`GOOS=linux` no sirve.** Un binario estático para `linux/arm64` falla en Android con «TLS segment
   is underaligned: alignment is 8, needs to be at least 64 for ARM64 Bionic». Android no es Linux con
   otra libc: su enlazador exige otra alineación. `GOOS=android` la respeta.
2. **Los flags se ignoraban en silencio.** Android lanza el binario a través de su enlazador y el
   programa recibe su propia ruta dos veces, primero como se escribió (`./kmeans`) y después absoluta
   (captura 06). El paquete `flag` deja de leer en el primer argumento que no empieza con guion, así
   que veía la ruta repetida y descartaba todo lo demás: la corrida «secuencial» salía concurrente,
   con 100 iteraciones, sin barra. `cmd/kmeans` y `cmd/benchmark` ahora descartan ese duplicado
   (`argumentos.go`, con test). El benchmark del teléfono corrió antes del arreglo, pero con los
   valores por defecto, que son exactamente el protocolo oficial; por eso sus números son válidos.
3. **Sacar archivos de Termux.** SELinux impide que Termux escriba en `/data/local/tmp` aunque tenga
   permisos Unix, y el build de GitHub no es depurable (`run-as` no funciona). El JSON se bajó por el
   mismo cable: `adb reverse tcp:9777 tcp:9777` y, en Termux, `cat archivo > /dev/tcp/127.0.0.1/9777`.

## Para el distribuido de la U2

El teléfono es el nodo lento y heterogéneo que hace interesante el problema (`concurrente-gsl.1`): va
a un tercio de la velocidad de las otras máquinas, con una varianza que cambia con la temperatura. El
reparto por demanda del worker pool ya tolera un nodo así dentro de una máquina; llevarlo a la red es
la pregunta.

# PR: Análisis concurrente de movilidad urbana usando NYC TLC Trip Record Data

## Objeto de estudio

El presente trabajo estudia el procesamiento concurrente de grandes
volúmenes de datos de movilidad urbana para identificar patrones de
tráfico, demanda de viajes y zonas con mayor congestión.

El análisis utiliza datos reales publicados por la New York City Taxi
and Limousine Commission (TLC), correspondientes a registros históricos
de viajes de taxis amarillos, verdes y vehículos de transporte privado.

El dataset contiene millones de registros de viajes reales. La fuente
oficial publica datos con información de fechas, ubicaciones de recogida
y destino, distancia recorrida, tarifas y características del viaje.

Fuente oficial:

https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page

https://learn.microsoft.com/en-us/azure/open-datasets/dataset-taxi-yellow 

------------------------------------------------------------------------

## Relación con ODS

### ODS 11: Ciudades y comunidades sostenibles

El proyecto busca analizar patrones de movilidad urbana para comprender
el comportamiento del transporte dentro de una ciudad.

El procesamiento eficiente de estos datos puede ayudar a:

-   identificar zonas con alta demanda de transporte
-   detectar horarios críticos de congestión
-   analizar distribución de viajes
-   mejorar planificación urbana

------------------------------------------------------------------------

## Dataset seleccionado

### NYC TLC Trip Record Data

Fuente:

New York City Taxi and Limousine Commission.

Características:

  Característica   Valor
  ---------------- --------------------
  Fuente           NYC TLC
  Tipo             Datos reales
  Registros        Millones de viajes
  Formato actual   Parquet
  Dominio          Transporte urbano

El dataset oficial contiene registros de viajes con campos como:

  Campo              Uso
  ------------------ -----------------------
  pickup_datetime    Inicio del viaje
  dropoff_datetime   Fin del viaje
  pickup_location    Zona origen
  dropoff_location   Zona destino
  trip_distance      Distancia recorrida
  fare_amount        Costo del viaje
  payment_type       Método de pago
  passenger_count    Cantidad de pasajeros

------------------------------------------------------------------------

## Problema computacional

El procesamiento de millones de viajes requiere realizar operaciones
repetitivas:

-   lectura de grandes archivos
-   limpieza de registros
-   generación de estadísticas
-   agrupación por zonas
-   extracción de características para modelos ML

Una ejecución secuencial procesa cada viaje individualmente, mientras
que una solución concurrente puede distribuir el trabajo utilizando
múltiples goroutines.

------------------------------------------------------------------------

## Modelo de Machine Learning

### Modelo seleccionado: K-means

El objetivo es agrupar zonas urbanas según patrones de movilidad.

Variables utilizadas:

    cantidad de viajes
    hora promedio
    duración promedio
    distancia promedio
    zona geográfica

Resultado esperado:

    Cluster 1:
    zonas de baja demanda

    Cluster 2:
    zonas de demanda media

    Cluster 3:
    zonas críticas de alta demanda

------------------------------------------------------------------------

## Arquitectura secuencial

    Archivo NYC TLC

          |

    Lectura registro por registro

          |

    Limpieza y transformación

          |

    Cálculo de métricas

          |

    Modelo ML

------------------------------------------------------------------------

## Arquitectura concurrente

Se utilizará un patrón Worker Pool.

                      Dataset NYC TLC
                            |
                         Reader
                            |
                         Channel
                            |
            +---------------+---------------+
            |               |               |
         Worker 1        Worker 2        Worker N
            |               |               |
            +---------------+---------------+
                            |
                        Reducer
                            |
                     Modelo clustering

Cada worker realizará:

1.  lectura de una sección del dataset
2.  limpieza del registro
3.  generación de variables
4.  cálculo de estadísticas parciales

------------------------------------------------------------------------

## Sincronización

Se utilizarán mecanismos de Go:

-   goroutines
-   channels
-   sync.WaitGroup
-   sync.Mutex

Objetivos:

-   evitar condiciones de carrera
-   asegurar consistencia de resultados
-   combinar correctamente resultados parciales

------------------------------------------------------------------------

## Fusión de resultados

Cada worker genera información parcial.

Ejemplo:

Worker 1:

    Zona Manhattan

    50000 viajes
    distancia promedio = 4.5 km

Worker 2:

    Zona Manhattan

    70000 viajes
    distancia promedio = 5.1 km

Los resultados deben fusionarse conservando:

-   cantidad total de viajes
-   sumatorias
-   promedios
-   valores máximos y mínimos

------------------------------------------------------------------------

## Línea base y experimentos

Se ejecutarán pruebas con diferentes cantidades de workers:

    1
    2
    4
    8
    16

Métricas:

-   tiempo de ejecución
-   speedup
-   uso de CPU
-   memoria

Fórmula:

    Speedup = Tiempo secuencial / Tiempo concurrente

------------------------------------------------------------------------

## Tests

Se implementarán pruebas para:

### Correctitud

Validar:

-   registros procesados correctamente
-   ausencia de pérdida de información
-   resultados equivalentes entre ejecución secuencial y concurrente

### Concurrencia

Probar múltiples goroutines accediendo a estructuras compartidas.

Validar:

-   ausencia de race conditions
-   resultados determinísticos

### Fusión

Comprobar que la unión de resultados parciales sea equivalente al
procesamiento completo.

------------------------------------------------------------------------

## Estructura propuesta

    nyc-mobility-analysis/

    ├── data/
    │   └── nyc_tlc/

    ├── cmd/
    │   └── analyzer/

    ├── internal/
    │
    │   ├── parser/
    │   ├── worker/
    │   ├── reducer/
    │   └── model/
    │
    ├── tests/
    │
    ├── README.md
    └── docs/

------------------------------------------------------------------------

## Plan de trabajo

### PC1

-   investigación bibliográfica
-   análisis del dataset
-   limpieza de datos
-   definición del caso de uso

### PC2

-   implementación secuencial
-   implementación concurrente
-   Worker Pool
-   medición de speedup

### TP

-   modelado en Promela
-   verificación de exclusión mutua
-   análisis de escalabilidad
-   revisión técnica del código

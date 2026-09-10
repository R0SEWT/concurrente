# PR: Análisis concurrente de calidad del aire en Lima Metropolitana usando datos reales de SENAMHI

## Objeto de estudio

El presente trabajo estudia el procesamiento concurrente de mediciones
de calidad del aire en Lima Metropolitana para identificar patrones de
contaminación atmosférica y clasificar niveles de riesgo ambiental.

El análisis utiliza datos reales publicados por el Servicio Nacional de
Meteorología e Hidrología del Perú (SENAMHI), correspondientes al
monitoreo de contaminantes atmosféricos en estaciones de Lima
Metropolitana.

El dataset contiene 577 794 registros reales, donde cada registro
representa una medición ambiental asociada a una estación, fecha y hora.

Pregunta principal:

> ¿Cuánto mejora el tiempo de procesamiento y análisis de grandes
> volúmenes de datos ambientales mediante una arquitectura concurrente
> frente a una implementación secuencial?

------------------------------------------------------------------------

## Relación con ODS

### ODS 13: Acción por el clima

El proyecto busca procesar información ambiental para analizar la
contaminación atmosférica en Lima Metropolitana.

El análisis permitirá:

-   detectar zonas con mayor contaminación
-   identificar patrones temporales
-   clasificar niveles de calidad del aire
-   apoyar la toma de decisiones ambientales

------------------------------------------------------------------------

## Dataset seleccionado

Fuente:

**Monitoreo de los contaminantes del aire en Lima Metropolitana -
SENAMHI**

https://www.datosabiertos.gob.pe/dataset/monitoreo-de-los-contaminantes-del-aire-en-lima-metropolitana-servicio-nacional-de

Características:

  Característica      Valor
  ------------------- --------------
  Fuente              SENAMHI
  Tipo                Datos reales
  Registros           577 794
  Formato             CSV
  Tamaño aproximado   68 MB

Variables principales:

  Campo              Uso
  ------------------ ---------------------------
  ESTACION           Punto de monitoreo
  FECHA              Fecha de medición
  HORA               Hora de medición
  PM10               Material particulado
  PM2_5              Material particulado fino
  NO2                Dióxido de nitrógeno
  LATITUD/LONGITUD   Ubicación
  DISTRITO           Zona geográfica

------------------------------------------------------------------------

## Problema computacional

El dataset requiere operaciones repetitivas:

-   limpieza de registros
-   transformación de variables
-   cálculo de estadísticas
-   generación de características
-   clasificación ambiental

La versión secuencial procesa cada registro individualmente, mientras
que la propuesta concurrente divide el trabajo entre múltiples
goroutines.

------------------------------------------------------------------------

## Modelo de Machine Learning

### Árbol de decisión

Se plantea clasificar la calidad del aire mediante una variable
objetivo:

    CALIDAD_AIRE

    0 - Bueno
    1 - Moderado
    2 - Malo
    3 - Muy malo

Variables de entrada:

    PM10
    PM2_5
    NO2
    hora
    estación

------------------------------------------------------------------------

## Arquitectura secuencial

    Archivo CSV

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

Se utilizará un patrón Worker Pool:

                     CSV SENAMHI
                         |
                      Reader
                         |
                     Channel
                         |
            +------------+------------+
            |            |            |
         Worker 1     Worker 2     Worker N
            |            |            |
            +------------+------------+
                         |
                      Reducer
                         |
                  Modelo clasificación

Cada worker realizará:

1.  lectura de registros
2.  limpieza
3.  transformación
4.  cálculo parcial

------------------------------------------------------------------------

## Sincronización

Se utilizarán:

-   goroutines
-   channels
-   sync.WaitGroup
-   sync.Mutex

El objetivo es garantizar:

-   ausencia de condiciones de carrera
-   resultados consistentes
-   correcta fusión de resultados parciales

------------------------------------------------------------------------

## Fusión de resultados

Cada worker genera resultados parciales.

Ejemplo:

Worker 1:

    Estación X
    1000 mediciones
    PM2.5 promedio = 25

Worker 2:

    Estación X
    800 mediciones
    PM2.5 promedio = 35

Los resultados deben combinarse mediante reducción manteniendo:

-   suma acumulada
-   cantidad de muestras
-   máximos y mínimos

------------------------------------------------------------------------

## Línea base y experimentos

Número de workers:

    1
    2
    4
    8
    16

Métricas:

-   tiempo de ejecución
-   speedup
-   uso de CPU
-   memoria utilizada

Fórmula:

    Speedup = Tiempo secuencial / Tiempo concurrente

------------------------------------------------------------------------

## Tests

Se implementarán pruebas para:

### Correctitud

Verificar:

-   registros leídos = registros procesados
-   ausencia de pérdida de datos
-   ausencia de duplicados

### Concurrencia

Probar múltiples goroutines sobre estructuras compartidas y validar
resultados.

### Fusión

Comprobar que la combinación de resultados parciales produce el mismo
resultado que una ejecución completa.

------------------------------------------------------------------------

## Estructura propuesta

    senamhi-air-analysis/

    ├── data/
    │   └── senamhi.csv

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
-   selección y limpieza del dataset
-   definición del caso de uso

### PC2

-   implementación secuencial
-   implementación concurrente
-   Worker Pool
-   medición de speedup

### TP

-   modelado en Promela
-   verificación de deadlocks
-   análisis de escalabilidad
-   revisión técnica del código

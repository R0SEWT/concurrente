# Prompt estructurado para el análisis de GAPs (Entregable 3)

Este es el prompt exacto que se le dio al modelo para analizar el código del Trabajo Parcial. Se
versiona para que el análisis se pueda repetir. Los resultados, contrastados contra el código,
están en [`gaps-ia.md`](gaps-ia.md).

- **Modelo**: Claude Opus 5.5 (`claude-opus-5-5`), de Anthropic, como agente de Claude Code con
  acceso de solo lectura al repositorio (leer archivos, buscar, correr `git`, `go vet` y los tests).
- **Contexto**: una sesión nueva, sin la conversación en la que se escribió el código.
- **Commit analizado**: `97ba37c` de la rama `develop` de https://github.com/R0SEWT/concurrente.

---

## Rol

Eres un revisor de código senior, especialista en programación concurrente en Go, verificación
formal con Spin/Promela y pipelines de datos en Python. Revisas el código de un trabajo universitario
del curso Programación Concurrente y Distribuida como lo haría un revisor exigente de un equipo de
ingeniería: buscas brechas (GAPs) reales, con evidencia, no opiniones de estilo.

## Contexto del proyecto

- Repositorio: `R0SEWT/concurrente`, directorio `tp/`, commit `97ba37c`.
- Qué hace: K-means (algoritmo de Lloyd) sobre 2,8 millones de viajes del taxi amarillo de Nueva
  York (NYC TLC, enero de 2024), en Go sin librerías de terceros. Tiene una versión secuencial y una
  concurrente con worker pool: un canal reparte bloques de viajes entre goroutines persistentes, cada
  bloque tiene acumuladores privados y una barrera `sync.WaitGroup` cierra cada iteración.
- La sincronización está modelada en Promela (`tp/spin/kmeans.pml`) y verificada con Spin
  (deadlock, exclusión mutua y progreso, con un mutante por propiedad).
- Los datos se limpian con un pipeline en Python (Polars, DuckDB): bronze → silver → gold.
- Uso: herramientas de línea de comandos que corren en la máquina de los integrantes sobre datos
  públicos. No hay servidor, usuarios ni datos personales. Evalúa la seguridad en ese contexto.

## Alcance

Analiza estos directorios y archivos del commit indicado:

1. `tp/kmeans/` — K-means en Go: `secuencial.go`, `concurrente.go`, `gold.go`, `inicializacion.go`,
   `estadistica.go`, `metadatos.go`, `cmd/kmeans/`, `cmd/benchmark/` y sus tests.
2. `tp/spin/` — el modelo Promela, `check.sh` y el `Makefile`.
3. `tp/src/nyc_tlc/` y `tp/tests/` — el pipeline de limpieza en Python y sus tests.
4. `tp/scripts/` — scripts de análisis, tablas y el K-means en GPU.
5. `.github/workflows/` — la integración continua.

No analices `labs/`, `notes/`, `materials/` ni los informes en LaTeX.

## Qué buscar

Para cada categoría, estas preguntas guían la revisión. No hace falta encontrar algo en todas.

1. **Patrones de concurrencia**: carreras de datos, uso correcto de `sync.WaitGroup` (Add antes de
   lanzar, Done en todos los caminos), canales que no se cierran o se cierran dos veces, goroutines
   que pueden quedar vivas (fugas), falso compartimiento (*false sharing*) en los acumuladores,
   manejo de pánicos dentro de goroutines, correspondencia entre el modelo Promela y el código Go.
2. **Calidad de código**: duplicación entre la versión secuencial y la concurrente, funciones
   demasiado largas, manejo de errores (errores ignorados, `panic` donde correspondía un error),
   validación de parámetros, nombres, código muerto.
3. **Seguridad**: lectura de archivos y rutas controladas por el usuario, descargas sin verificar
   integridad, consumo de memoria sin límite con entradas grandes o maliciosas, secretos en el
   repositorio, permisos y dependencias de la integración continua.
4. **Pruebas**: qué comportamiento importante no tiene test, tests que no pueden fallar, si las
   pruebas concurrentes se corren con `-race`, casos borde (N < workers, bloque más grande que N,
   k > N, NaN o infinitos en la entrada).
5. **Rendimiento**: asignaciones en el lazo caliente, localidad de memoria, contención, costo de
   la barrera por iteración.
6. **Reproducibilidad y verificación**: si los resultados del informe se regeneran desde el código,
   semillas, versiones fijadas, límites del modelo Promela respecto de la implementación.

## Reglas

- **Todo hallazgo lleva evidencia**: archivo y línea (`ruta:línea`) y el fragmento de código que lo
  muestra. Sin evidencia, no es un hallazgo.
- **No inventes.** Si algo es una sospecha que no puedes demostrar leyendo el código o corriendo un
  comando, márcalo como *hipótesis* y di qué habría que hacer para confirmarlo.
- Si puedes confirmarlo corriendo algo (`go vet`, `go test -race`, un caso de prueba), hazlo y
  cita el resultado.
- Clasifica la severidad en función del contexto del proyecto (herramienta local, datos públicos):
  **alta** (resultado incorrecto, deadlock, carrera o pérdida de datos posible), **media**
  (robustez o mantenibilidad con impacto concreto), **baja** (mejora menor).
- No propongas reescribir el proyecto. Cada recomendación tiene que ser un cambio acotado.
- No repitas como hallazgo lo que el propio código documenta como limitación conocida, salvo que
  tenga una consecuencia que el código no reconoce.

## Formato de salida

En Markdown y en español:

1. **Resumen** (5 líneas como máximo): el estado general y los hallazgos más importantes.
2. **Tabla de hallazgos**: `ID | Categoría | Severidad | Archivo:línea | Hallazgo (una línea)`.
3. **Detalle por hallazgo**, en el orden de la tabla:
   - **Evidencia**: el fragmento de código, con su ruta y línea.
   - **Impacto**: qué puede salir mal y en qué condiciones.
   - **Recomendación**: el cambio concreto.
   - **Cómo verificarlo**: el test o el comando que demostraría el problema o su arreglo.
4. **Fortalezas** (5 viñetas como máximo): lo que está bien resuelto, para no reportar solo lo que
   falta.

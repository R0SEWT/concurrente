# concurrente

Cuaderno de trabajo del curso **Programación Concurrente y Distribuida** (1ACC0065, NRC 8809),
UPC, Ciencias de la Computación, ciclo 2026-20. Docente: Carlos Alberto Jara García.

Apuntes por sesión, el índice del material del Aula Virtual, los laboratorios de Go y de Spin, y el
Trabajo Parcial: un K-means concurrente en Go sobre los viajes de taxi de Nueva York.

## Mapa

| Ruta | Qué hay |
|------|---------|
| `notes/` | Apuntes por sesión, en español. `_template.md` es la plantilla. |
| `materials/` | Material del Aula Virtual, por semana. **No se versiona** (es del profesor y el remoto es público); el sílabo es la excepción. |
| `manifest.json` | Inventario canónico del curso: unidades, cronograma de evaluación, bibliografía y, por cada adjunto, nombre, ruta, tamaño y sha256. Es la fuente de verdad de qué material existe. |
| `labs/go/` | Go, un paquete por semana. `go test -race` como red de seguridad. |
| `labs/spin/` | Promela: modelos verificados exhaustivamente con Spin. |
| `tp/` | Trabajo Parcial (PC1 + PC2 + TB1): pipeline de datos, K-means secuencial y concurrente, benchmark, modelo Promela e informes en LaTeX. |
| `docs/` | Propuestas de caso de uso del TP. |

Cada raíz tiene su propio toolchain y su README con los comandos.

## Empezar

```bash
bd ready                                        # qué toca hacer: el cronograma vivo del curso
cd labs/go   && go test -race ./...             # Go 1.26 (dnf install golang)
cd labs/spin && make check                      # Spin 6.5.2 (./bootstrap.sh lo compila sin sudo)
cd tp        && uv sync --extra dev && uv run pytest -q
```

## El curso

| Unidad | Semanas | Tema |
|--------|---------|------|
| 1 | 1 a 8  | Construcción y verificación de aplicaciones concurrentes: Go, sección crítica, semáforos, patrones, model checking con Spin/Promela |
| 2 | 9 a 16 | Computación distribuida: canales, servicios y algoritmos distribuidos, exclusión mutua distribuida, consenso, tiempo real |

| Evaluación | Semana | Peso |
|------------|--------|------|
| PC1, PC2 | 3, 5 | 10 % cada una |
| TB1 | 7 | 5 % |
| EA1 | 8 | 10 % |
| PC3, PC4 | 11, 13 | 10 % cada una |
| TB2, DD1 | 15 | 15 % cada una |
| EB1 | 16 | 15 % |

Ninguna evaluación es recuperable. El cronograma completo está en `manifest.json` y cada evaluación
tiene su issue en beads.

## Trabajo Parcial

K-means sobre los 2,8 millones de viajes del taxi amarillo de Nueva York de enero de 2024 (datos
abiertos de la TLC), para caracterizar patrones de movilidad urbana en línea con el ODS 11.

- **PC1**: caso de uso, revisión bibliográfica y pipeline de limpieza bronze → silver → gold, con
  auditoría independiente en SQL. Informe en `tp/informe/pc1/`.
- **PC2**: K-means secuencial y concurrente en Go sin librerías de terceros (worker pool, canal de
  bloques, barrera con `sync.WaitGroup`), sincronización verificada en Promela, speedup con media
  recortada e intervalos bootstrap. Informe en `tp/informe/pc2/`; todas sus tablas se generan desde
  `tp/reports/*.json`.
- **TB1**: pendiente. Contraste en GPU, elección de k y la interpretación de los clusters.

Contexto, procedencia de los datos y arquitectura en [`tp/CLAUDE.md`](tp/CLAUDE.md).

## Convenciones

- **Verificar y probar son cosas distintas, y hacen falta las dos.** Spin verifica el algoritmo
  sobre todos los entrelazados de un modelo reducido; `go test -race` prueba la implementación. Un
  test que pasa sin `-race` no demuestra nada sobre una sección crítica.
- **Los labs se escriben con TDD**: el test antes que la goroutine o el modelo.
- **Git Flow**: nada entra directo a `develop` ni a `main`. Una rama por unidad de trabajo, PR
  revisada, y una fusión de `develop` a `main` por entregable, con tag (`pc1`, `pc2`, …). GitHub
  borra la rama al fusionar.
- **Tareas en beads**, no en TODOs sueltos: `bd ready`, `bd show <id>`, `bd close <id>`.
- **IA como herramienta del curso.** El sílabo incorpora prompt engineering para diseñar algoritmos
  concurrentes e interpretar Spin, siempre contrastando contra la teoría; el uso se registra en el TP.

Las reglas completas para personas y agentes están en [`CLAUDE.md`](CLAUDE.md).

## Equipo del TP

Rody Sebastian Vilchez Marin (coordinador), Dayana Kety Gómez Rodriguez y Julio Cesar Meza Alfaro.

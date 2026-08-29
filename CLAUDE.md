# concurrente — AI Agent Instructions

Repo del curso **Programación Concurrente y Distribuida (1ACC0065)**, UPC, ciclo 2026-20, NRC 8809.
No es un proyecto de software con usuarios: es el cuaderno de trabajo de un ciclo.
Repo hermano y mismo patrón: `../cs-topics`.

## Contexto

- **Qué es**: apuntes por sesión + material del Aula Virtual + código de las PCs, trabajos y el proyecto final.
- **Temario**: U1 (semanas 1-8) construcción y verificación de concurrencia — Go, sección crítica,
  semáforos, patrones, model checking con Spin/Promela. U2 (semanas 9-16) computación distribuida —
  canales, servicios y algoritmos distribuidos, exclusión mutua distribuida, consenso, tiempo real.
- **Logro del curso**: construir aplicaciones concurrentes y distribuidas de alto rendimiento.
- **Docente**: Carlos Alberto Jara Garcia. 3 créditos, 16 semanas, presencial en laboratorio.
- **Procedencia del material**: sílabo oficial en `materials/silabo-1ACC0065.pdf`; el resto sale del
  Aula Virtual UPC. `manifest.json` es la fuente canónica de qué existe y qué falta. Material del
  profesor: si se sube algo suyo, **el remoto debería ser privado**.
- **Nota sobre IA**: el sílabo incorpora explícitamente prompt engineering como herramienta del curso
  (U1 para diseño de algoritmos concurrentes e interpretación de Spin; U2 para algoritmos distribuidos
  y consenso), siempre contrastando contra la teoría. Usar IA aquí es parte de la metodología, no un atajo.

## Arquitectura

Estructura por tipo, no por semana — las unidades pueden reordenarse, los labs no.

```bash
notes/         # apuntes .md por sesión (_template.md es la plantilla)
materials/     # PDFs y slides, carpeta por semana (week-NN/) + el sílabo
labs/go/       # Go — un paquete por semana, go test como red de seguridad
labs/spin/     # Promela — modelos .pml verificados con spin/ispin
```

Cada lab es una raíz independiente con su propio toolchain:

```bash
cd labs/go   && go test ./...                 # requiere Go (ver Convenciones)
cd labs/spin && spin -a mutex.pml && gcc -o pan pan.c && ./pan   # verificación exhaustiva
```

## Archivos clave

| Archivo | Propósito |
|------|---------|
| `manifest.json` | Inventario canónico del curso: unidades, cronograma de evaluación, material del Aula Virtual. Fuente de verdad para saber qué falta. |
| `materials/silabo-1ACC0065.pdf` | Sílabo oficial. Pesos y semanas de evaluación salen de acá. |
| `notes/_template.md` | Plantilla de apunte de sesión. |
| `labs/go/go.mod` | Módulo Go del curso (`upc.edu.pe/concurrente`). Un paquete por semana. |
| `labs/go/week01/critical_test.go` | Ejemplo de referencia: carrera de datos detectada con `-race`, luego corregida. |
| `labs/spin/README.md` | Cómo correr Spin sobre un `.pml` y leer el contraejemplo. |

## Evaluación

`NF = 0.10·PC1 + 0.10·PC2 + 0.05·TB1 + 0.10·EA1 + 0.10·PC3 + 0.10·PC4 + 0.15·TB2 + 0.15·DD1 + 0.15·EB1`

Cada evaluación tiene su issue en beads con la semana en el título. `bd ready` es el cronograma vivo;
`manifest.json` guarda la tabla completa. Ninguna evaluación figura como recuperable en el sílabo.

## Convenciones

- **Apuntes en español**, nombrados `week-NN-<tema-en-kebab>.md`. Copia `_template.md`.
- **Material versionado**: `materials/` SÍ se commitea (misma decisión que en `cs-topics`).
- **Los labs se escriben con TDD**: test primero, luego la goroutine o el modelo Promela.
- **Toolchain**: Go 1.26.7 (`dnf`) y Spin 6.5.2 (compilado, `labs/spin/bootstrap.sh`) ya están
  instalados. Spin vive en `~/.local/bin`, su fuente en `~/Code/herramientas/spin`.
- **Concurrencia en Go se prueba con `go test -race`**, siempre. Un test que pasa sin `-race` no
  demuestra nada sobre una sección crítica.
- **Spin no reemplaza al test ni al revés**: el modelo `.pml` verifica el *algoritmo* (safety y
  liveness sobre todos los entrelazados); el test en Go verifica la *implementación*. El curso pide ambos.
- Los binarios que genera Spin (`pan`, `pan.*`) están gitignoreados — son artefactos, se regeneran.
- **Verificar es local; ejecutar pesado es en gorgo.** Spin es memory-bound y esta laptop tiene
  15 GB contra los 9.1 GB de gorgo. gorgo (11 núcleos, RTX 4060 Ti, `/home` al 97%) es para los
  benchmarks de Go de la U2 y la investigación con GPU, no para `pan`.

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:6cd5cc61 -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

**Architecture in one line:** issues live in a local Dolt DB; sync uses `refs/dolt/data` on your git remote; `.beads/issues.jsonl` is a passive export. See https://github.com/gastownhall/beads/blob/main/docs/SYNC_CONCEPTS.md for details and anti-patterns.

## Agent Context Profiles

The managed Beads block is task-tracking guidance, not permission to override repository, user, or orchestrator instructions.

- **Conservative (default)**: Use `bd` for task tracking. Do not run git commits, git pushes, or Dolt remote sync unless explicitly asked. At handoff, report changed files, validation, and suggested next commands.
- **Minimal**: Keep tool instruction files as pointers to `bd prime`; use the same conservative git policy unless active instructions say otherwise.
- **Team-maintainer**: Only when the repository explicitly opts in, agents may close beads, run quality gates, commit, and push as part of session close. A current "do not commit" or "do not push" instruction still wins.

## Session Completion

This protocol applies when ending a Beads implementation workflow. It is subordinate to explicit user, repository, and orchestrator instructions.

1. **File issues for remaining work** - Create beads for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **Handle git/sync by active profile**:
   ```bash
   # Conservative/minimal/default: report status and proposed commands; wait for approval.
   git status

   # Team-maintainer opt-in only, unless current instructions forbid it:
   git pull --rebase
   git push
   git status
   ```
5. **Hand off** - Summarize changes, validation, issue status, and any blocked sync/commit/push step

**Critical rules:**
- Explicit user or orchestrator instructions override this Beads block.
- Do not commit or push without clear authority from the active profile or the current user request.
- If a required sync or push is blocked, stop and report the exact command and error.
<!-- END BEADS INTEGRATION -->

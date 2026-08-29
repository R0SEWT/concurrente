# concurrente

Cuaderno de trabajo del curso **Programación Concurrente y Distribuida** (1ACC0065, NRC 8809),
UPC — Ciencias de la Computación, ciclo 2026-20. 

Apuntes, material del curso y los labs de Go y Spin. 

## Estructura

```
notes/         apuntes por sesión (_template.md es la plantilla)
materials/     PDFs y slides — el sílabo vive en materials/silabo-1ACC0065.pdf
labs/go/       Go: un paquete por semana, go test -race
labs/spin/     Promela: modelos verificados con Spin
manifest.json  inventario canónico: unidades, temario, cronograma, bibliografía
```

## Empezar

```bash
bd ready                          # qué toca hacer (issues del curso)
cd labs/go   && go test -race ./...
cd labs/spin && make verify MODEL=peterson CLAIM=exclusion
```

`go` y `spin` no vienen instalados por defecto; ver `labs/*/README.md`.

## Cómo está organizado el curso

| Unidad | Semanas | Tema |
|--------|---------|------|
| 1 | 1-8  | Construcción y verificación de aplicaciones concurrentes (Go, sección crítica, semáforos, Spin/Promela) |
| 2 | 9-16 | Computación distribuida (canales, algoritmos distribuidos, exclusión mutua distribuida, consenso, tiempo real) |

`NF = 0.10·PC1 + 0.10·PC2 + 0.05·TB1 + 0.10·EA1 + 0.10·PC3 + 0.10·PC4 + 0.15·TB2 + 0.15·DD1 + 0.15·EB1`

El cronograma completo está en `manifest.json` y como issues en `bd ready`.

## Convenciones

Ver [`CLAUDE.md`](CLAUDE.md) — es la fuente para agentes y para mí. Lo esencial:
apuntes en español, `materials/` sí se commitea, los labs se escriben con TDD,
y la concurrencia se prueba **siempre** con `-race` (Go) o exhaustivamente (Spin).

# Informe del TP (LaTeX)

Informe del Entregable 3 del Trabajo Parcial, el final. Salió del de la PC2 (`../pc2/`, congelado
en el tag `pc2`), como pide el enunciado: empieza con los Entregables 1 y 2 y sus correcciones
(Partes I y II) y sigue con lo del Entregable 3 (Parte III): verificación formal en Spin
(deadlock, exclusión mutua y progreso), análisis del código con IA (GAPs), GitHub, conclusiones
del grupo y de cada integrante, y los anexos (video, informe de GAPs en `.md`, declaración de uso
de IA).

```bash
./compilar.sh            # historial + tablas + latexmk → build/main.pdf
./compilar.sh -c         # limpia
```

`compilar.sh` hace tres cosas, que también se pueden correr a mano:

```bash
./generar-historial.sh                                   # generado/historial.tex, desde origin
python3 ../../scripts/tablas_informe.py --salida generado   # tablas y cifras, desde tp/reports/*.json
latexmk                                                  # pdflatex + biber, APA
```

## Nada se transcribe a mano

- **Tablas de tiempos, speedup, recursos e inercias**: `generado/tabla-*.tex`, generadas desde
  `tp/reports/*.json` por `tp/scripts/tablas_informe.py`.
- **Cifras en prosa**: `generado/cifras.tex` define `\cifra{speedup-p4}`, `\cifra{n-equilibrio}`,
  etc. Si se vuelve a medir, el texto cambia solo.
- **Capturas de la CLI**: `img/cli-*.txt` es la salida real de `tp/kmeans/cmd/kmeans`;
  `img/cli-*.png` se renderiza con `tp/scripts/capturas_terminal.py`. Para rehacerlas:

  ```bash
  cd ../../kmeans && go build -o /tmp/kmeans ./cmd/kmeans
  /tmp/kmeans -modo seq  -k 8 -iter 10 -centroides /tmp/c.json | tee ../informe/pc2/img/cli-secuencial.txt
  /tmp/kmeans -modo conc -workers 8 -chunk 16384 -k 8 -iter 10 -centroides /tmp/c.json | tee ../informe/pc2/img/cli-concurrente.txt
  uv run python ../scripts/capturas_terminal.py ../informe/pc2/img/cli-*.txt
  ```

  (la primera línea `$ ...` de cada `.txt` es el comando, agregada a mano para la figura).
- **Capturas de cada ejecución** (`img/ejec-*.png`): el docente pide una captura de cada
  ejecución, no un listado ni una mención. `tp/scripts/capturar_ejecuciones.sh` corre el pipeline,
  `pytest`, `go vet` + `go test -race`, la regresión de Spin, un benchmark reducido y los checks de
  CI, guarda la salida real en `img/ejec-*.txt` (primera línea: el comando) y la renderiza. Se
  puede rehacer un solo grupo: `capturar_ejecuciones.sh spin`.
- **Todo lo de Spin**: `cd tp/spin && make informe`. Deja en `generado/` las salidas de `pan`
  (`spin-*.txt`), el estado final del contraejemplo de deadlock (`traza-deadlock.txt`), la tabla
  de los siete casos de la regresión (`spin-casos.tsv` → `tabla-spin-casos.tex`) y las figuras
  `img/automata-worker.pdf` e `img/traza-mutante.pdf`, vía `tp/scripts/figuras_spin.py`. Falla si
  `kmeans.pml` se movió y los rangos de líneas que cita la Sección 17 ya no apuntan a lo que dicen.
- **Historial de commits**: `generado/historial.tex`, desde las ramas de `origin` y los tags `pc1`
  y `pc2`.

La bibliografía es `../../docs/referencias.bib`: un solo `.bib` para todo el TP.

## Dependencias del sistema

En Fedora, `latexmk` y `biber` de TeX Live necesitan `perl-sigtrap` y `libxcrypt-compat`:

```bash
sudo dnf install perl-sigtrap libxcrypt-compat
```

Sin root, `compilar.sh` los descarga con `dnf download`, los extrae en `build/deps/` y los usa
por `LD_LIBRARY_PATH` y `PERL5LIB`. No toca el sistema.

## Antes de entregar

- Buscar `\pendiente` y `\verificar` en `secciones/`: el PDF final no debe tener ninguna marca
  roja ni naranja.
- Regenerar el historial con las ramas ya fusionadas y `main` con el tag `tp`. El release va por
  una rama `release/tp` y nunca con `develop` como rama de origen: el repositorio borra la rama de
  origen al fusionar.
- El video (Anexo A) y `tp/docs/gaps-ia.md` (Anexo B) tienen que estar publicados antes: el
  enunciado resta 5 puntos sin video y 10 si `main` se edita después de la fecha de entrega.
- El enunciado pide Word, pero el docente aceptó `.tex` y `.pdf`. Cada integrante sube el PDF como
  `CC65-TP-202620-[código]`; el coordinador sube además `CC65-Participación-202620`.

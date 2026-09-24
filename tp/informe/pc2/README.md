# Informe PC2 (LaTeX)

Informe del Entregable 2 del Trabajo Parcial. Empieza con el Entregable 1 y sus correcciones
(Parte I) y sigue el orden de la rúbrica de la PC2 (Parte II): algoritmo y modelo en Promela,
implementación en Go con capturas, explicación de la sincronización, speedup con media recortada,
análisis de escalabilidad y trade-offs, recursos de cómputo y punto de equilibrio, antecedente,
GitHub y conclusiones.

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
- **Salida de Spin**: `generado/spin-correcto.txt` y `generado/spin-mutante.txt` salen de
  `tp/spin` con `spin -a kmeans.pml && cc -O2 -o pan pan.c && ./pan` (y `-DMUTANTE`).
- **Historial de commits**: `generado/historial.tex`, desde las ramas de `origin` y el tag `pc1`.

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
- Regenerar el historial con las ramas ya fusionadas y `main` con el tag `pc2`.
- El enunciado pide Word, pero el docente aceptó `.tex` y `.pdf`. Cada integrante sube el PDF como
  `CC65-PC2-202620-[código]`; el coordinador sube además `CC65-Participación-202620`.

# Informe PC1 (LaTeX)

Informe del Entregable 1 del Trabajo Parcial. El orden de secciones es el que pide el enunciado:
carátula, índice, resumen, objetivos, temas con una ficha por paper, caso de uso, limpieza y
GitHub.

```bash
./generar-historial.sh   # regenera la tabla de commits desde origin
latexmk                  # build/main.pdf (pdflatex + biber, APA)
```

La bibliografía es `../../docs/referencias.bib`: se mantiene un solo `.bib` para todo el TP.

En Fedora, `latexmk` y `biber` de TeX Live necesitan dos paquetes del sistema:

```bash
sudo dnf install perl-sigtrap libxcrypt-compat
```

Sin ellos, se puede compilar a mano (sin biber, las citas salen como claves y no hay referencias):

```bash
mkdir -p build
pdflatex -output-directory=build main.tex
biber --input-directory build --output-directory build main
pdflatex -output-directory=build main.tex && pdflatex -output-directory=build main.tex
```

## Antes de entregar

- Buscar `\pendiente` y `\verificar` en `secciones/` y `preambulo/`: el PDF no debe tener
  ninguna marca roja ni naranja.
- **La opinión crítica de cada paper y las conclusiones individuales las escribe cada integrante.**
  Valen 10 de los 20 pts y el curso usa un detector de plagio.
- Completar los códigos en `preambulo/macros.tex`. El coordinador es Rody: sube además el reporte
  de participación (`CC65-Participación-202620`).
- El enunciado pide Word, pero el docente aceptó `.tex` y `.pdf` en clase. Cada integrante sube
  el PDF como `CC65-PC1-202620-[código]`.

#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["playwright"]
# ///
"""Captura las vistas móviles de tp/app que van en la figura fig:app-movil del informe.

Igual que capturas_terminal.py: una captura hecha a mano no se puede regenerar;
esta sí. Cada vista es un deep link de la app (?hour, ?day, ?zone, ?filter), así
que lo que muestra la figura es exactamente el estado que dice el pie.

    uv run tp/scripts/capturas_app.py                    # escribe en tp/informe/tp/img/
    uv run tp/scripts/capturas_app.py --chrome /usr/bin/google-chrome

Sirve tp/app con http.server en un puerto libre. Las teselas del mapa base salen
de internet, así que necesita red.
"""

import argparse
import functools
import http.server
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

TP = Path(__file__).resolve().parent.parent
VISTAS = {
    # Midtown Center a las 12:00 entre semana, con el detalle expandido desde el asa.
    "app-movil-midtown.png": ("?hour=12&day=semana&zone=161&min", True),
    # Cluster 5 (aeropuertos) aislado a las 15:00 entre semana.
    "app-movil-aeropuertos.png": ("?hour=15&day=semana&filter=5", False),
}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--salida", type=Path, default=TP / "informe/tp/img")
    p.add_argument("--chrome", help="ejecutable de Chrome si no hay navegadores de Playwright")
    args = p.parse_args()

    class Silencioso(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *_):
            pass

    manejador = functools.partial(Silencioso, directory=TP / "app")
    servidor = http.server.ThreadingHTTPServer(("127.0.0.1", 0), manejador)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{servidor.server_port}/index.html"

    with sync_playwright() as pw:
        nav = pw.chromium.launch(executable_path=args.chrome)
        # 412x915: el mismo viewport de las capturas originales (un Android de gama media).
        ctx = nav.new_context(
            viewport={"width": 412, "height": 915},
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True,
        )
        ctx.add_init_script(
            "try{localStorage.setItem('nyc_taxi_pulse_tour_seen','true')}catch(e){}"
        )
        for nombre, (query, expandir) in VISTAS.items():
            pag = ctx.new_page()
            errores: list[str] = []
            pag.on("pageerror", lambda e, errores=errores: errores.append(str(e)))
            pag.goto(base + query, wait_until="networkidle")
            pag.wait_for_timeout(2500)  # transiciones del bottom sheet y teselas
            if expandir:
                pag.click("#sheetHandle")
                pag.wait_for_timeout(900)
            if errores:
                raise SystemExit(f"{nombre}: errores de JavaScript: {errores}")
            pag.screenshot(path=args.salida / nombre)
            print(f"→ {args.salida / nombre}")
        nav.close()
    servidor.shutdown()


if __name__ == "__main__":
    main()

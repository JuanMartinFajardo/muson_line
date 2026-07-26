# ==========================================================================
# hoja.py — Lámina de contactos del tema entero. Fuera de Blender.
# --------------------------------------------------------------------------
#   python3 tools/decks/hoja.py --tema quijote [--fuente build] [--tamano 1]
#
# Las 11 cartas en fila sobre el tapete verde, que es donde se van a ver. Es
# lo primero que hay que mirar después de cada pasada: casi todos los fallos
# de un tema (una figura que no se distingue de otra, una carta que no se
# cuenta, un valor que no encaja con el resto) saltan a la vista aquí y no
# mirando las cartas de una en una.
# ==========================================================================

import argparse
import os
import sys

from PIL import Image

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import spec   # noqa: E402


def hoja(slug, fuente='dist', escala=1, fondo=None, salida=None):
    carpeta = os.path.join(AQUI, fuente, slug, 'raw' if fuente == 'build' else '')
    extension = 'png' if fuente == 'build' else 'webp'

    imagenes = []
    for pieza in spec.PIEZAS:
        ruta = os.path.join(carpeta, f'{pieza}.{extension}')
        if not os.path.exists(ruta):
            continue
        img = Image.open(ruta).convert('RGBA')
        if escala != 1:
            img = img.resize((int(img.width * escala), int(img.height * escala)),
                             Image.LANCZOS)
        imagenes.append(img)

    if not imagenes:
        raise SystemExit(f'no hay imágenes en {carpeta}')

    hueco = 10
    ancho = sum(i.width for i in imagenes) + hueco * (len(imagenes) + 1)
    alto = max(i.height for i in imagenes) + hueco * 2
    color = tuple(int(c * 255) for c in spec.hex_a_srgb(fondo or spec.FELT_VERDE))
    lienzo = Image.new('RGB', (ancho, alto), color)

    x = hueco
    for img in imagenes:
        lienzo.paste(img, (x, hueco), img)
        x += img.width + hueco

    salida = salida or os.path.join(AQUI, 'build', slug, 'hoja.png')
    os.makedirs(os.path.dirname(salida), exist_ok=True)
    lienzo.save(salida)
    return salida


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--tema', required=True)
    p.add_argument('--fuente', default='build', choices=['build', 'dist'])
    p.add_argument('--tamano', type=float, default=1.0)
    p.add_argument('--fondo', default=None)
    p.add_argument('--salida', default=None)
    args = p.parse_args()
    print(hoja(args.tema, args.fuente, args.tamano, args.fondo, args.salida))


if __name__ == '__main__':
    main()

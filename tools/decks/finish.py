# ==========================================================================
# finish.py — Reducción y codificación. Se ejecuta FUERA de Blender.
# --------------------------------------------------------------------------
#   python3 tools/decks/finish.py --tema ducks
#
# Coge los PNG a 4x de build/<slug>/raw/ y saca lo que consume el juego:
#
#   dist/<slug>/NN.webp        208 × 319   (§2)
#   dist/<slug>/NN@2x.webp     416 × 638   (por si se sirve retina)
#   dist/<slug>/back.webp
#   dist/<slug>/thumb.webp     104 × 160   (del as, que es el cartel del tema)
#   dist/<slug>/<slug>.zip     lo que se sube por el panel de administración
#
# El DECK_SPEC pide `cwebp -q 82 -m 6 -sharp_yuv`. Si el binario está, se usa;
# si no, se codifica con Pillow, que da un tamaño muy parecido. Lo que no se
# negocia es el orden: reducir con Lanczos ANTES de codificar.
# ==========================================================================

import argparse
import os
import shutil
import subprocess
import sys
import zipfile

from PIL import Image

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import spec   # noqa: E402


def _cwebp():
    return shutil.which('cwebp')


def codificar(img, destino, calidad=None):
    """PNG/RGBA → webp con alfa intacto."""
    calidad = calidad or spec.WEBP['quality']
    binario = _cwebp()
    if binario:
        temporal = destino + '.tmp.png'
        img.save(temporal, 'PNG')
        subprocess.run([binario, '-q', str(calidad), '-alpha_q', '100',
                        '-m', str(spec.WEBP['method']), '-sharp_yuv',
                        temporal, '-o', destino],
                       check=True, capture_output=True)
        os.remove(temporal)
    else:
        img.save(destino, 'WEBP', quality=calidad,
                 method=spec.WEBP['method'], exact=True)
    return os.path.getsize(destino)


def reducir(img, tamano):
    return img.resize(tamano, Image.LANCZOS)


def acabar(slug, crudo=None, destino=None, calidad=None):
    crudo = crudo or os.path.join(AQUI, 'build', slug, 'raw')
    destino = destino or os.path.join(AQUI, 'dist', slug)
    os.makedirs(destino, exist_ok=True)

    pesos, total = {}, 0
    for pieza in spec.PIEZAS:
        origen = os.path.join(crudo, f'{pieza}.png')
        if not os.path.exists(origen):
            print(f"  · falta {pieza}.png — sin renderizar")
            continue
        with Image.open(origen) as img:
            img = img.convert('RGBA')
            uno = reducir(img, (spec.ANCHO_PX, spec.ALTO_PX))
            dos = reducir(img, (spec.ANCHO_PX * 2, spec.ALTO_PX * 2))

            peso = codificar(uno, os.path.join(destino, f'{pieza}.webp'), calidad)
            codificar(dos, os.path.join(destino, f'{pieza}@2x.webp'), calidad)
            pesos[pieza] = peso
            total += peso

            if pieza == '01':      # el as es el cartel del tema (§4.1)
                codificar(reducir(img, spec.TAMANO_THUMB),
                          os.path.join(destino, 'thumb.webp'), calidad)

    # El zip que se sube por el panel: sólo lo que el juego necesita a @1x.
    ruta_zip = os.path.join(destino, f'{slug}.zip')
    with zipfile.ZipFile(ruta_zip, 'w', zipfile.ZIP_DEFLATED) as z:
        for pieza in list(spec.PIEZAS) + ['thumb']:
            archivo = os.path.join(destino, f'{pieza}.webp')
            if os.path.exists(archivo):
                z.write(archivo, f'{pieza}.webp')

    return pesos, total, destino


def informe(pesos, total):
    """Aviso de presupuesto del §6. No bloquea: un tema pesado se ve igual,
    sólo tarda más en llegar por una conexión mala."""
    print('\n  peso @1x por carta')
    for pieza, peso in sorted(pesos.items()):
        techo = spec.PRESUPUESTO['dorso_1x_techo'] if pieza == 'back' \
            else spec.PRESUPUESTO['cara_1x_techo']
        objetivo = spec.PRESUPUESTO['dorso_1x'] if pieza == 'back' \
            else spec.PRESUPUESTO['cara_1x']
        marca = 'TECHO' if peso > techo else ('alto' if peso > objetivo else 'ok')
        print(f"    {pieza:>5}  {peso / 1024:6.1f} KB  {marca}")
    print(f"\n  tema entero: {total / 1024:.1f} KB "
          f"(objetivo {spec.PRESUPUESTO['tema_1x'] / 1024:.0f} KB, "
          f"techo {spec.PRESUPUESTO['tema_1x_techo'] / 1024:.0f} KB)")
    if total > spec.PRESUPUESTO['tema_1x_techo']:
        print("  ⚠️  por encima del techo: baja PRIMERO la complejidad del fondo, "
              "el detalle del sujeto el último (§6).")


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--tema', required=True)
    p.add_argument('--calidad', type=int, default=None)
    p.add_argument('--crudo', default=None)
    p.add_argument('--salida', default=None)
    args = p.parse_args()

    pesos, total, destino = acabar(args.tema, args.crudo, args.salida, args.calidad)
    print(f"\n=== {args.tema} → {destino}")
    informe(pesos, total)


if __name__ == '__main__':
    main()

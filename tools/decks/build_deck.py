# ==========================================================================
# build_deck.py — Construye y renderiza un tema. Se ejecuta DENTRO de Blender.
# --------------------------------------------------------------------------
#   blender --background --factory-startup --python tools/decks/build_deck.py -- \
#           --tema ducks [--cartas 01,05,12] [--muestras 16] [--salida ...]
#
# Una escena por carta, siempre desde cero: así una carta mal construida no
# puede contaminar a la siguiente, y se puede rehacer una sola sin recompilar
# el tema entero (que es como se trabaja de verdad, ver DECK_PIPELINE.md).
#
# Deja PNG RGBA a 4x en `tools/decks/build/<slug>/raw/`. Reducir, codificar en
# webp y pasar la puerta de legibilidad es cosa de finish.py y qa.py, que
# corren fuera de Blender.
# ==========================================================================

import argparse
import importlib
import os
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.join(AQUI, 'themes'))

import spec   # noqa: E402
import rig    # noqa: E402


def parsear():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    p = argparse.ArgumentParser(prog='build_deck')
    p.add_argument('--tema', required=True, help='slug del tema (ducks, coffee…)')
    p.add_argument('--cartas', default='todas',
                   help="'todas' o lista: 01,02,12,back")
    p.add_argument('--muestras', type=int, default=None,
                   help='sobrescribe las muestras del spec (borradores rápidos)')
    p.add_argument('--escala', type=int, default=None,
                   help='factor de render; 4 = calidad final, 1 = vistazo')
    p.add_argument('--salida', default=None)
    p.add_argument('--semilla', type=int, default=7,
                   help='fija el jitter: el mismo número da la misma carta')
    return p.parse_args(argv)


def main():
    args = parsear()

    modulo = importlib.import_module(f'themes.{args.tema.replace("-", "_")}')
    tema = modulo.TEMA

    piezas = list(spec.PIEZAS) if args.cartas == 'todas' else \
        [c.strip() for c in args.cartas.split(',') if c.strip()]

    salida = args.salida or os.path.join(AQUI, 'build', tema.slug, 'raw')
    os.makedirs(salida, exist_ok=True)

    if args.escala:
        spec.ANCHO_RENDER = spec.ANCHO_PX * args.escala
        spec.ALTO_RENDER = spec.ALTO_PX * args.escala
    if args.muestras:
        spec.RENDER['muestras'] = args.muestras

    print(f"\n=== {tema.slug} · {len(piezas)} piezas · "
          f"{spec.ANCHO_RENDER}×{spec.ALTO_RENDER} · "
          f"{spec.RENDER['muestras']} muestras ===")

    for pieza in piezas:
        t0 = time.time()
        escena, colecciones = rig.escena_limpia()
        rig.camara(escena, colecciones['CAM'])
        rig.luces(colecciones['LIGHTS'], tema.potencia_luces)

        # La semilla depende de la carta: el jitter es distinto en cada una
        # pero reproducible, así que rehacer la 6 no cambia la 7.
        ctx = rig.Contexto(escena, colecciones, pieza,
                           semilla=args.semilla * 1000 + sum(map(ord, pieza)))
        tema.construir(ctx)

        ruta = rig.render(escena, os.path.join(salida, f'{pieza}.png'))
        print(f"  {pieza}  {time.time() - t0:5.1f}s  {ruta}")

    print(f"=== listo: {salida}\n")


if __name__ == '__main__':
    main()

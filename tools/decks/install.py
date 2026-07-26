# ==========================================================================
# install.py — Mete un tema ya acabado en el juego. Fuera de Blender.
# --------------------------------------------------------------------------
#   python3 tools/decks/install.py --tema ducks [--acceso todos] [--orden 20]
#
# Pasa por exactamente el mismo camino que una subida del panel de
# administración (`decks.instalar_pieza`): se reabre cada imagen, se reescala a
# 208×319 y se recodifica. Un solo camino de entrada significa que lo que se ve
# en producción es lo mismo que probó el diseñador, y que este script no puede
# colar en `static/` nada que el panel rechazaría.
# ==========================================================================

import argparse
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)
sys.path.insert(0, AQUI)

import base_datos   # noqa: E402
import decks        # noqa: E402
import spec         # noqa: E402


def _leer_metadatos(slug):
    """Saca nombre, nombre_en y descripcion del módulo del tema leyéndolo como
    texto. Es a propósito: importarlo arrastraría `bpy`, que sólo existe dentro
    de Blender."""
    ruta = os.path.join(AQUI, 'themes', slug.replace('-', '_') + '.py')
    if not os.path.exists(ruta):
        return {}
    with open(ruta, encoding='utf-8') as f:
        fuente = f.read()
    salida = {}
    for clave in ('nombre_en', 'nombre', 'descripcion'):
        if clave in salida:
            continue
        # `clave = 'x'` o `clave = ('x' 'y')` partido en varias líneas.
        m = re.search(rf"^    {clave} = (\(?)(.+?)(?=^    \w+ =|^$)",
                      fuente, re.M | re.S)
        if not m:
            continue
        trozos = re.findall(r"'([^']*)'|\"([^\"]*)\"", m.group(2))
        texto = ''.join(a or b for a, b in trozos).strip()
        if texto:
            salida[clave] = texto
    return salida


def instalar(slug, nombre, nombre_en=None, descripcion=None, acceso='todos',
             orden=100, origen=None, por='pipeline'):
    origen = origen or os.path.join(AQUI, 'dist', slug)
    if not os.path.isdir(origen):
        raise SystemExit(f"no existe {origen}: ¿has pasado por finish.py?")

    slug = decks.validar_slug(slug)
    escritas = []
    for pieza in list(spec.PIEZAS) + ['thumb']:
        archivo = os.path.join(origen, f'{pieza}.webp')
        if not os.path.exists(archivo):
            continue
        with open(archivo, 'rb') as f:
            decks.instalar_pieza(slug, pieza, f.read())
        escritas.append(pieza)

    if not escritas:
        raise SystemExit(f"{origen} no tiene ninguna imagen que instalar")

    existente = base_datos.deck_por_slug(slug)
    if existente:
        base_datos.deck_actualizar(existente['id'], nombre=nombre,
                                   nombre_en=nombre_en, descripcion=descripcion,
                                   acceso=acceso, orden=orden, activo=1)
        deck_id = existente['id']
        accion = 'actualizado'
    else:
        deck_id = base_datos.deck_crear(slug, nombre, nombre_en, descripcion,
                                        acceso, orden, creado_por=por)
        accion = 'creado'

    faltan = decks.piezas_presentes(base_datos.deck_por_slug(slug))
    return deck_id, accion, escritas, faltan


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--tema', required=True)
    p.add_argument('--nombre', default=None)
    p.add_argument('--nombre-en', default=None)
    p.add_argument('--descripcion', default=None)
    p.add_argument('--acceso', default='todos',
                   choices=['todos', 'cuenta', 'restringido'])
    p.add_argument('--orden', type=int, default=100)
    p.add_argument('--origen', default=None)
    args = p.parse_args()

    # Si no se dan a mano, los textos salen del propio módulo del tema. Se leen
    # del código fuente en vez de importarlo: el módulo de un tema hace
    # `import bpy` y sólo se puede importar dentro de Blender, y este script
    # corre fuera. Así el nombre sigue teniendo una única fuente de verdad.
    nombre, nombre_en, descripcion = args.nombre, args.nombre_en, args.descripcion
    if not (nombre and nombre_en and descripcion):
        leidos = _leer_metadatos(args.tema)
        nombre = nombre or leidos.get('nombre') or args.tema
        nombre_en = nombre_en or leidos.get('nombre_en')
        descripcion = descripcion or leidos.get('descripcion')

    deck_id, accion, escritas, faltan = instalar(
        args.tema, nombre, nombre_en, descripcion, args.acceso, args.orden,
        args.origen)

    print(f"=== {args.tema} {accion} (id {deck_id}) con {len(escritas)} imágenes")
    print(f"    acceso: {args.acceso} · orden: {args.orden}")
    if faltan:
        print(f"    ⚠️  faltan por subir: {', '.join(faltan)}")
    print(f"    peso en disco: {decks.peso_en_disco(args.tema) / 1024:.1f} KB")


if __name__ == '__main__':
    main()

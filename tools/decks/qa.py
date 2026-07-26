# ==========================================================================
# qa.py — La puerta de legibilidad del DECK_SPEC §7. Fuera de Blender.
# --------------------------------------------------------------------------
#   python3 tools/decks/qa.py --tema ducks
#
# Las cinco pruebas del spec, automatizadas hasta donde tiene sentido:
#
#   1. Miniatura   83×128 — ¿se sigue leyendo? (medida: contraste local)
#   2. Silueta     10/11/12 en negro puro, ¿son distinguibles entre sí?
#                  (medida: distancia entre siluetas, 0 = idénticas)
#   3. Mesa mixta  el as junto a ases de otros temas — se genera la lámina
#   4. Daltonismo  simulación de deuteranopia y protanopia — se genera la lámina
#   5. Tapete      compuesto sobre verde y sobre oscuro; ¿el borde se define?
#
# Lo que la máquina puede medir, lo mide y lo aprueba o lo suspende. Lo que
# hay que MIRAR, lo deja en `qa/` como una lámina de contactos, porque el §7
# es una puerta para un ojo humano, no un test unitario. El informe dice
# claramente cuál es cuál.
# ==========================================================================

import argparse
import os
import sys

from PIL import Image, ImageChops, ImageStat

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import spec   # noqa: E402


# --- utilidades ------------------------------------------------------------

def _abrir(destino, pieza):
    ruta = os.path.join(destino, f'{pieza}.webp')
    return Image.open(ruta).convert('RGBA') if os.path.exists(ruta) else None


def _sobre(fondo_hex, img):
    lienzo = Image.new('RGBA', img.size, tuple(
        int(c * 255) for c in spec.hex_a_srgb(fondo_hex)) + (255,))
    lienzo.alpha_composite(img)
    return lienzo.convert('RGB')


def _ventana(img):
    """La ventana interior de la carta: se quita el marco, que es idéntico en
    todas y sólo serviría para diluir cualquier comparación."""
    w, h = img.size
    m = int(spec.VENTANA_PX / spec.ANCHO_PX * w)
    return img.convert('RGB').crop((m, m, w - m, h - m))


def _referencia(imagenes):
    """Fondo del tema, deducido de las tres figuras: la mediana píxel a píxel.

    No hace falta saber cómo es el fondo de cada tema — basta con que sea el
    MISMO en las tres cartas, que es justamente lo que exige el spec. Donde una
    figura tiene sujeto y las otras dos no, la mediana devuelve el fondo. Así el
    recorte funciona igual con un degradado de agua que con papel cuadriculado,
    sin adivinar nada.
    """
    ventanas = [_ventana(i) for i in imagenes]
    base = ventanas[0].size
    ventanas = [v if v.size == base else v.resize(base) for v in ventanas]
    pixeles = [v.load() for v in ventanas]
    fondo = Image.new('RGB', base)
    destino = fondo.load()
    for y in range(base[1]):
        for x in range(base[0]):
            canales = [[p[x, y][c] for p in pixeles] for c in range(3)]
            destino[x, y] = tuple(sorted(c)[len(c) // 2] for c in canales)
    return fondo


def _mascara(img, fondo, umbral=40):
    """Dónde hay sujeto: los píxeles que se separan del fondo de referencia."""
    ventana = _ventana(img)
    if ventana.size != fondo.size:
        ventana = ventana.resize(fondo.size)
    dif = ImageChops.difference(ventana, fondo).convert('L')
    return dif.point(lambda p: 255 if p > umbral // 3 else 0)


def _distancia_siluetas(mascara_a, mascara_b):
    """Distancia de Jaccard entre dos siluetas: 0 = la misma mancha, 1 = no se
    pisan en ningún sitio.

    Se normaliza por la UNIÓN de las dos siluetas, y no por el tamaño de la
    carta, porque si no el test castiga a los temas despejados: dos dibujos de
    línea sobre papel en blanco sólo pueden diferir en el 10 % de los píxeles
    de la carta por mucho que no se parezcan en nada, y suspendían siempre.
    Medido contra lo que ocupan, la comparación vale igual para una figura
    maciza que para cuatro rayas.
    """
    interseccion = ImageStat.Stat(ImageChops.darker(mascara_a, mascara_b)).sum[0]
    union = ImageStat.Stat(ImageChops.lighter(mascara_a, mascara_b)).sum[0]
    if union <= 0:
        return 0.0
    return 1.0 - interseccion / union


def _contraste_medio(img):
    """Desviación típica de la luminancia: cuánta información visual queda."""
    return ImageStat.Stat(img.convert('L')).stddev[0] / 255.0


#: Matrices de simulación de dicromacia (Viénot, Brettel & Mollon 1999).
_DALTONISMO = {
    'deuteranopia': ((0.625, 0.375, 0.0), (0.700, 0.300, 0.0), (0.0, 0.300, 0.700)),
    'protanopia':   ((0.567, 0.433, 0.0), (0.558, 0.442, 0.0), (0.0, 0.242, 0.758)),
}


def _simular_daltonismo(img, tipo):
    m = _DALTONISMO[tipo]
    return img.convert('RGB').convert('RGB', (
        m[0][0], m[0][1], m[0][2], 0,
        m[1][0], m[1][1], m[1][2], 0,
        m[2][0], m[2][1], m[2][2], 0))


def _tira(imagenes, fondo_hex, separacion=8):
    """Lámina de contactos horizontal sobre un fondo dado."""
    imagenes = [i for i in imagenes if i]
    if not imagenes:
        return None
    ancho = sum(i.width for i in imagenes) + separacion * (len(imagenes) + 1)
    alto = max(i.height for i in imagenes) + separacion * 2
    color = tuple(int(c * 255) for c in spec.hex_a_srgb(fondo_hex))
    lienzo = Image.new('RGB', (ancho, alto), color)
    x = separacion
    for img in imagenes:
        lienzo.paste(img, (x, separacion), img if img.mode == 'RGBA' else None)
        x += img.width + separacion
    return lienzo


# --- las cinco pruebas -----------------------------------------------------

def revisar(slug, destino=None, otros=()):
    destino = destino or os.path.join(AQUI, 'dist', slug)
    carpeta_qa = os.path.join(destino, 'qa')
    os.makedirs(carpeta_qa, exist_ok=True)

    cartas = {p: _abrir(destino, p) for p in spec.PIEZAS}
    faltan = [p for p, img in cartas.items() if img is None]
    lineas, fallos, avisos = [], [], []

    lineas.append(f'# Puerta de legibilidad — {slug}\n')
    if faltan:
        fallos.append(f"faltan piezas: {', '.join(faltan)}")

    # 1 · Miniatura ---------------------------------------------------------
    lineas.append('\n## 1 · Miniatura 83×128\n')
    lineas.append('| carta | contraste | veredicto |\n|---|---|---|')
    for pieza in spec.VALORES:
        img = cartas.get(pieza)
        if not img:
            continue
        mini = img.resize(spec.THUMB_TEST, Image.LANCZOS)
        mini.save(os.path.join(carpeta_qa, f'thumb_{pieza}.png'))
        c = _contraste_medio(_sobre(spec.FELT_VERDE, mini))
        ok = c >= 0.075
        if not ok:
            fallos.append(f'{pieza}: se apaga a tamaño miniatura (contraste {c:.3f})')
        lineas.append(f'| {pieza} | {c:.3f} | {"ok" if ok else "SUSPENDE"} |')
    lineas.append('\nContraste = desviación típica de la luminancia sobre el tapete. Es un '
                  'detector de humo — dice si la carta se ha convertido en una mancha — no una '
                  'prueba de legibilidad. Un tema muy despejado (líneas finas sobre mucho blanco) '
                  'puntúa bajo por diseño y aun así se lee: para eso está la lámina de la prueba 3.')

    # 2 · Siluetas de las figuras ------------------------------------------
    lineas.append('\n## 2 · Siluetas 10 / 11 / 12\n')
    figuras = [p for p in spec.FIGURAS if cartas.get(p)]
    if len(figuras) == 3:
        fondo = _referencia([cartas[p] for p in figuras])
        mascaras = {}
        for pieza in figuras:
            mascaras[pieza] = _mascara(cartas[pieza], fondo)
            mascaras[pieza].save(os.path.join(carpeta_qa, f'silueta_{pieza}.png'))

        lineas.append('| par | distancia | veredicto |\n|---|---|---|')
        for i in range(len(figuras)):
            for j in range(i + 1, len(figuras)):
                d = _distancia_siluetas(mascaras[figuras[i]], mascaras[figuras[j]])
                ok = d >= 0.55
                if not ok:
                    fallos.append(f'{figuras[i]} y {figuras[j]} ocupan casi la misma '
                                  f'mancha (distancia {d:.3f})')
                lineas.append(f'| {figuras[i]} vs {figuras[j]} | {d:.3f} | '
                              f'{"ok" if ok else "SUSPENDE"} |')
        lineas.append('\nDistancia de Jaccard entre las dos siluetas, normalizada por lo que '
                      'ocupan. Es el fallo más común del spec (§4.2): por debajo de 0.55 las '
                      'dos figuras se pisan tanto que son la misma carta con otro dibujo. '
                      '`qa/silueta_NN.png` enseña qué recortó el test de cada una.')
    else:
        lineas.append('_Faltan figuras: la prueba necesita las tres._')

    # 3 · Mesa mixta --------------------------------------------------------
    ases = [cartas.get('01')]
    for otro in otros:
        ases.append(_abrir(otro, '01'))
    tira = _tira(ases, spec.FELT_VERDE)
    if tira:
        tira.save(os.path.join(carpeta_qa, 'mesa_mixta.png'))
    lineas.append('\n## 3 · Mesa mixta\n')
    lineas.append('`qa/mesa_mixta.png` — el as de este tema junto a los de otros. '
                  '**A ojo:** ¿los sigue atando el marco? ¿hay alguna que grite '
                  'más que las demás? Eso no lo puede medir una máquina.')

    # 4 · Daltonismo --------------------------------------------------------
    lineas.append('\n## 4 · Daltonismo\n')
    for tipo in _DALTONISMO:
        muestras = [_simular_daltonismo(_sobre(spec.FELT_VERDE, cartas[p]), tipo)
                    for p in ('01', '05', '07', '12') if cartas.get(p)]
        lamina = _tira(muestras, spec.FELT_VERDE)
        if lamina:
            lamina.save(os.path.join(carpeta_qa, f'{tipo}.png'))
    lineas.append('`qa/deuteranopia.png` y `qa/protanopia.png` — **a ojo:** '
                  'el recuento de pintas no puede depender de un rojo contra un '
                  'verde, porque contar es la única señal real que hay.')

    # 5 · Tapete ------------------------------------------------------------
    lineas.append('\n## 5 · Tapete\n')
    lineas.append('| fondo | definición del borde | veredicto |\n|---|---|---|')
    for nombre, fondo in (('verde', spec.FELT_VERDE), ('oscuro', spec.FELT_OSCURO)):
        img = cartas.get('01')
        if not img:
            continue
        compuesta = _sobre(fondo, img)
        compuesta.save(os.path.join(carpeta_qa, f'tapete_{nombre}.png'))
        # El borde se mide en la franja de 4 px que rodea la carta.
        w, h = compuesta.size
        marco_ext = compuesta.crop((0, 0, w, 6)).convert('L')
        banda = compuesta.crop((0, 6, w, 16)).convert('L')
        delta = abs(ImageStat.Stat(marco_ext).mean[0] - ImageStat.Stat(banda).mean[0]) / 255.0
        ok = delta >= 0.05
        if not ok:
            avisos.append(f'sobre {nombre}, el borde de la carta casi no se separa '
                          f'del fondo (Δ {delta:.3f})')
        lineas.append(f'| {nombre} | {delta:.3f} | {"ok" if ok else "revisar"} |')

    # Veredicto -------------------------------------------------------------
    lineas.insert(1, '\n**{}**\n'.format(
        'SUSPENDE — ' + '; '.join(fallos) if fallos else
        ('PASA con avisos — ' + '; '.join(avisos) if avisos else 'PASA')))
    lineas.append('\n---\n\nLas pruebas 3 y 4 son de ojo: el informe sólo prepara '
                  'las láminas. Míralas antes de dar el tema por bueno.\n')

    informe = os.path.join(destino, 'QA.md')
    with open(informe, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lineas))
    return informe, fallos, avisos


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--tema', required=True)
    p.add_argument('--salida', default=None)
    p.add_argument('--comparar', default='',
                   help='slugs separados por comas para la prueba de mesa mixta')
    args = p.parse_args()

    otros = [os.path.join(AQUI, 'dist', s.strip())
             for s in args.comparar.split(',') if s.strip()]
    informe, fallos, avisos = revisar(args.tema, args.salida, otros)

    print(f"\n=== {args.tema}: {informe}")
    for f in fallos:
        print(f"  SUSPENDE  {f}")
    for a in avisos:
        print(f"  aviso     {a}")
    if not fallos and not avisos:
        print("  todo lo medible pasa. Mira las láminas de qa/ antes de darlo por bueno.")
    return 1 if fallos else 0


if __name__ == '__main__':
    sys.exit(main())

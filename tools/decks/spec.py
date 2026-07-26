# ==========================================================================
# spec.py — DECK_SPEC.md convertido en números
# --------------------------------------------------------------------------
# Este archivo es la única fuente de la geometría, la cámara, las luces y el
# presupuesto de peso. Si el DECK_SPEC cambia, se cambia AQUÍ y todos los temas
# se recompilan alineados; un tema nunca redefine estas constantes, sólo las usa.
#
# No importa `bpy`: lo usan tanto los scripts que corren dentro de Blender como
# los que corren fuera (acabado, control de calidad, instalación).
#
# Convenio de unidades del DECK_SPEC §2: **1 BU = 100 px**. Todas las
# coordenadas son BU relativas al centro de la carta, que está en el origen.
# ==========================================================================

PX = 100.0                       # px por unidad de Blender

# --- Lienzo (§2) -----------------------------------------------------------
ANCHO_PX, ALTO_PX = 208, 319     # exportación @1x
ESCALA_RENDER = 4                # se renderiza a 4x y se reduce
ANCHO_RENDER = ANCHO_PX * ESCALA_RENDER      # 832
ALTO_RENDER = ALTO_PX * ESCALA_RENDER        # 1276

ANCHO = ANCHO_PX / PX            # 2.08 BU
ALTO = ALTO_PX / PX              # 3.19 BU
MEDIO_X = ANCHO / 2              # 1.04
MEDIO_Y = ALTO / 2               # 1.595
RADIO_ESQUINA = 0.11             # 11 px

# --- Capas en Z (§2) -------------------------------------------------------
Z_BG = 0.000                     # fondo: 0.000 – 0.010
Z_BG_TECHO = 0.010
Z_INTERIOR = 0.012               # el sujeto: 0.012 – 0.250
Z_INTERIOR_TECHO = 0.250
Z_MARCO = 0.255                  # banda del marco: 0.255 – 0.290
Z_NUMERAL = 0.290

PROFUNDIDAD_MAX = 0.25           # presupuesto de relieve: 25 px

# --- Esqueleto del marco (§3) ---------------------------------------------
# Medidas en px desde el borde, tal cual están escritas en el DECK_SPEC.
SANGRADO_PX = 3                  # borde transparente
BANDA_DE_PX = 3                  # la banda empieza aquí
BANDA_A_PX = 20                  # y acaba aquí  → 17 px de ancho
VENTANA_PX = 22                  # el interior empieza a 22 px de cada borde

BANDA_DE = BANDA_DE_PX / PX      # 0.03
BANDA_A = BANDA_A_PX / PX        # 0.20
RADIO_BANDA_EXT = 0.08
RADIO_BANDA_INT = 0.05

RELIEVE_MARCO = 0.035            # extrusión de la banda
BISEL_MARCO = 0.008              # bisel a ambos lados
RELIEVE_PATRON_MAX = 0.006       # patrón embosado que un tema puede añadir

# Ventana interior: 164 × 275 px, centrada.
VENTANA_MEDIO_X = (ANCHO_PX - 2 * VENTANA_PX) / 2 / PX     # 0.82
VENTANA_MEDIO_Y = (ALTO_PX - 2 * VENTANA_PX) / 2 / PX      # 1.375

# Cajas de los numerales: 8..46 px, simétricas respecto al centro.
NUM_CAJA_DE_PX, NUM_CAJA_A_PX = 8, 46
NUM_ALTURA_MAYUSCULA = 20 / PX   # 0.20 BU de altura de caja tipográfica

def caja_numeral(esquina='sup-izq'):
    """Centro (x, y) en BU de una de las dos cajas de numeral."""
    centro = (NUM_CAJA_DE_PX + NUM_CAJA_A_PX) / 2 / PX      # 0.27 desde el borde
    x = -MEDIO_X + centro
    y = MEDIO_Y - centro
    return (x, y) if esquina == 'sup-izq' else (-x, -y)


# --- Patrones de pintas (§4.1) --------------------------------------------
# Para cada carta: centros de las instancias en BU y caja máxima de cada una.
# `escala_centro` sólo lo usa el 5 (quincunce), donde el centro va a ×1.15.
PATRONES = {
    1:  {'centros': [(0.0, 0.0)],
         'caja': (1.30, 1.70)},
    2:  {'centros': [(0.0, 0.68), (0.0, -0.68)],
         'caja': (0.90, 1.10), 'espejo_inferior': True},
    3:  {'centros': [(0.0, 0.88), (-0.44, -0.42), (0.44, -0.42)],
         'caja': (0.78, 0.90)},
    4:  {'centros': [(-0.40, 0.78), (0.40, 0.78), (-0.40, -0.78), (0.40, -0.78)],
         'caja': (0.70, 0.82)},
    5:  {'centros': [(-0.42, 0.86), (0.42, 0.86), (0.0, 0.0),
                     (-0.42, -0.86), (0.42, -0.86)],
         'caja': (0.66, 0.78), 'escala_centro': 1.15},
    6:  {'centros': [(-0.42, 0.98), (0.42, 0.98), (-0.42, 0.0), (0.42, 0.0),
                     (-0.42, -0.98), (0.42, -0.98)],
         'caja': (0.64, 0.72)},
    7:  {'centros': [(-0.40, 0.99), (0.40, 0.99),
                     (-0.60, 0.0), (0.0, 0.0), (0.60, 0.0),
                     (-0.40, -0.99), (0.40, -0.99)],
         'caja': (0.58, 0.66)},
}

SEPARACION_MINIMA = 0.06         # hueco mínimo entre siluetas (§4.1)
JITTER_ROTACION = 6.0            # ±6° por instancia
JITTER_ESCALA = 0.03             # ±3 %
BORDE_INSTANCIA = 0.015          # el "rim" que separa la pinta del fondo

# --- Figuras (§4.2) --------------------------------------------------------
FIGURA_ALTURA_MIN = 0.72         # fracción de la altura de la ventana
FIGURA_ALTURA_MAX = 0.90

# --- Cámara y luces (§5) ---------------------------------------------------
CAMARA = {'tipo': 'ORTHO', 'ortho_scale': 3.19, 'loc': (0.0, 0.0, 6.0),
          'rot': (0.0, 0.0, 0.0)}

# Las proporciones son fijas; el vataje absoluto lo ajusta cada tema con
# `potencia_luces` para que su fondo caiga en el hex que ha declarado.
LUCES = {
    'KEY':  {'loc': (-2.2, 2.4, 3.2),  'tamano': 3.0, 'factor': 1.00},
    'FILL': {'loc': (2.4, -1.4, 2.8),  'tamano': 4.0, 'factor': 0.28},
    'RIM':  {'loc': (0.0, -0.6, -1.2), 'tamano': 2.5, 'factor': 0.35},
}
POTENCIA_BASE = 220.0            # W de KEY con factor 1.00

RENDER = {
    'muestras': 64,
    'ao_distancia': 0.20,
    'ao_factor': 0.40,
    'view_transform': 'Standard',   # OBLIGATORIO (§5): los hex son literales
    'look': 'None',
    'exposicion': 0.0,
    'gamma': 1.0,
}

# --- Cartas y exportación (§1, §6) ----------------------------------------
VALORES = ('01', '02', '03', '04', '05', '06', '07', '10', '11', '12')
NUMEROS = ('01', '02', '03', '04', '05', '06', '07')
FIGURAS = ('10', '11', '12')
PIEZAS = VALORES + ('back',)
NOMBRE_FIGURA = {'10': 'sota', '11': 'caballo', '12': 'rey'}

TAMANO_THUMB = (104, 160)

PRESUPUESTO = {
    'cara_1x': 14 * 1024, 'cara_1x_techo': 18 * 1024,
    'cara_2x': 38 * 1024, 'cara_2x_techo': 48 * 1024,
    'dorso_1x': 10 * 1024, 'dorso_1x_techo': 14 * 1024,
    'tema_1x': 150 * 1024, 'tema_1x_techo': 190 * 1024,
}
WEBP = {'quality': 82, 'method': 6}

# --- Puerta de legibilidad (§7) -------------------------------------------
THUMB_TEST = (83, 128)           # tamaño al que hay que seguir leyendo la carta
FELT_VERDE = '#0b6b3a'           # tapete
FELT_OSCURO = '#1a1a1e'          # tema oscuro
CONTRASTE_NUMERAL_MIN = 4.5      # ratio de luminancia numeral / banda


# --- Utilidades de color ---------------------------------------------------

def hex_a_srgb(codigo):
    """'#F0E3C8' → (0.94, 0.89, 0.78) en sRGB 0-1."""
    codigo = codigo.lstrip('#')
    return tuple(int(codigo[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def srgb_a_lineal(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_a_lineal(codigo, alfa=None):
    """Color listo para meter en un nodo de Blender, que trabaja en lineal.
    Con `view_transform = Standard`, un shader de emisión con este valor sale
    del render exactamente con el hex pedido."""
    rgb = tuple(srgb_a_lineal(c) for c in hex_a_srgb(codigo))
    return rgb + (alfa,) if alfa is not None else rgb


def luminancia(codigo):
    """Luminancia relativa WCAG de un hex."""
    r, g, b = (srgb_a_lineal(c) for c in hex_a_srgb(codigo))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(hex_a, hex_b):
    """Ratio de contraste WCAG entre dos hex (siempre ≥ 1)."""
    la, lb = luminancia(hex_a), luminancia(hex_b)
    claro, oscuro = max(la, lb), min(la, lb)
    return (claro + 0.05) / (oscuro + 0.05)

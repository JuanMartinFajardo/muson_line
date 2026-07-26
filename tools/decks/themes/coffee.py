# ==========================================================================
# themes/coffee.py — 04 · Temática Café
# --------------------------------------------------------------------------
# Fuente: wiki/decks/04-coffee.md. Una cafetería vista desde arriba: granos
# sobre mármol en las cartas de número, tazas sobre el mismo mármol en las
# figuras. Misma cámara, misma luz, mismo plano cenital en las once cartas —
# ese es el gesto del tema, y es lo que hace que la escalada se lea antes de
# mirar el numeral: se ve cuánta leche lleva la taza.
#
# Prohibido el vapor (bonito en un render, un borrón a 208 px) y prohibida la
# textura de mármol (una sola veta ancha; el ruido fino se come 6 KB).
# ==========================================================================

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bpy     # noqa: E402
import spec    # noqa: E402
import rig     # noqa: E402
from base import Tema   # noqa: E402


class Coffee(Tema):
    slug = 'coffee'
    nombre = 'Café'
    nombre_en = 'Coffee'
    descripcion = ('Una cafetería de especialidad vista desde arriba: granos '
                   'sobre mármol, remolinos de crema y cerámica a la luz de la '
                   'mañana.')

    paleta = {
        'bean': '#5A3A22', 'bean-hi': '#8B5E3C', 'crema': '#C9A06B',
        'milk': '#F5EDE1', 'marble': '#EDE9E3', 'marble-vein': '#CFC8BE',
        'ceramic': '#FFFFFF', 'frame': '#4A3428', 'gold': '#C9A06B',
    }

    # Serif didone de contraste alto: el único sitio de la colección donde una
    # tipografía preciosista es lo correcto. Bodoni y no Didot: el "1" de Didot
    # es un asta con serifas que a 20 px se lee como una "I", y "10" acababa
    # pareciendo "IO" — justo lo que prohíbe el §3.
    fuente_numerales = '/System/Library/Fonts/Supplemental/Bodoni 72.ttc'
    hex_numeral = '#C9A06B'
    hex_banda = '#4A3428'
    rugosidad_banda = 0.45          # satinado: madera teñida o cuero de carta
    hex_filete = '#C9A06B'
    potencia_luces = 1.15
    eje_escalada = 'tamaño del recipiente y complejidad de la leche: espresso → macchiato → mocha'

    #: Un grano de café no tiene arriba: la mitad de abajo del 2 no se gira.
    pip_tiene_arriba = False

    # ------------------------------------------------------------------
    # Fondo — el mármol de la barra, cenital
    # ------------------------------------------------------------------

    def fondo(self, ctx):
        rig.carta_base(ctx, rig.material_plano('coffee_marmol', self.color('marble')))

        # Tres vetas anchas y suaves en diagonal. GRANDES: una veta cruza la
        # carta entera. Si aquí aparece una textura de ruido, se han perdido
        # 6 KB y el tema se ha salido del presupuesto (§6).
        vetas = [(-1.4, -1.9, 0.9, 1.9, 0.16),
                 (-0.4, -1.9, 1.6, 1.5, 0.09),
                 (-1.5, 0.2, 0.6, 1.9, 0.06)]
        for i, (x1, y1, x2, y2, ancho) in enumerate(vetas):
            self.plana(ctx, f'veta{i}',
                       self.barra(x1, y1, x2, y2, ancho, ancho * 0.35),
                       'marble-vein', spec.Z_BG + 0.002 + i * 0.001, alfa=0.18)

        # El único indicio de que el mármol es una superficie y no una pared:
        # una sombra elíptica muy suave bajo el centro de masas.
        self.plana(ctx, 'poso', self.elipse(0.0, -0.10, 0.80, 1.05, 40),
                   'marble-vein', spec.Z_BG + 0.006, alfa=0.13, suave=True)

    # ------------------------------------------------------------------
    # Marco — grano dorado detrás del numeral
    # ------------------------------------------------------------------

    def ornamento_esquina(self, ctx, x, y):
        grano = rig.forma('FRAME_grano', self._contorno_grano(0.18),
                          spec.Z_NUMERAL + 0.001, 0.0, 0.0, True, ctx.col['FRAME'])
        rig.poner_material(grano, rig.material_plano(
            'coffee_grano_esq', self.color('gold'), 0.40))
        rig.centrar_en(grano, x, y)
        return grano

    # ------------------------------------------------------------------
    # Pinta — el grano de café
    # ------------------------------------------------------------------

    #: Proporción del grano: alargado, no redondo. Un grano ancho se lee como
    #: un huevo o como un guijarro, y ahí se pierde el tema entero.
    GRANO_RX, GRANO_RY = 0.19, 0.30

    @classmethod
    def _contorno_grano(cls, escala=1.0, mitad=None, hueco=0.028):
        """Silueta del grano, o de uno de sus dos lóbulos.

        `mitad = -1 | +1` devuelve medio grano, retranqueado `hueco` del eje.
        Los dos lóbulos con el hueco entre medias SON el surco: dibujarlo como
        una raya encima daba un grano partido por una barra; dibujarlo como
        ausencia de material deja que el bisel de cada lóbulo capte la KEY por
        su canto interior, que es exactamente lo que hace que se lea como café.
        """
        rx, ry = cls.GRANO_RX * escala, cls.GRANO_RY * escala
        puntos = []
        for i in range(29):
            a = -math.pi / 2 + math.pi * i / 28          # medio contorno
            x, y = rx * math.cos(a), ry * math.sin(a)
            # El surco no es recto: se curva un poco, como en el grano real.
            desvio = hueco * escala * (0.60 + 0.40 * math.cos(a * 1.5))
            puntos.append((x if mitad is None else abs(x) * mitad, y))
            if mitad is not None:
                puntos[-1] = (puntos[-1][0] + desvio * mitad, y)
        if mitad is None:
            for i in range(27, 0, -1):
                a = -math.pi / 2 + math.pi * i / 28
                puntos.append((-rx * math.cos(a), ry * math.sin(a)))
        else:
            # Se cierra por el eje, con la curva suave del surco.
            for i in range(28, -1, -1):
                a = -math.pi / 2 + math.pi * i / 28
                desvio = hueco * escala * (0.60 + 0.40 * math.cos(a * 1.5))
                puntos.append((desvio * mitad, ry * math.sin(a) * 0.985))
        return puntos

    def pip(self, ctx):
        """Los dos lóbulos del grano sobre una sombra oscura del mismo
        contorno: la sombra sólo asoma por el surco y por el canto."""
        base = self.silueta(ctx, 'grano_base', self._contorno_grano(1.03),
                            'bean', grosor=0.02, bisel=0.004, suave=True,
                            rugosidad=0.55)
        rig.poner_material(base, rig.material_pbr('coffee_grano_base_m',
                                                  '#3A2415', 0.7))

        lobulos = [self.silueta(ctx, f'grano_lobulo{m}',
                                self._contorno_grano(1.0, m), 'bean',
                                spec.Z_INTERIOR + 0.018, grosor=0.085,
                                bisel=0.022, suave=True, rugosidad=0.35)
                   for m in (-1, 1)]
        return rig.unir([base] + lobulos, 'pip_grano')

    def cartas_de_numero(self, ctx, n):
        """Los granos giran libremente (no tienen arriba) y el 4 forma molinillo:
        cada grano a 90° del anterior."""
        if n == 4:
            return self._molinillo(ctx)
        return super().cartas_de_numero(ctx, n)

    def _molinillo(self, ctx):
        patron = spec.PATRONES[4]
        maestro = self.pip(ctx)
        rig.encajar_en(maestro, *patron['caja'])
        maestro = rig.a_malla(maestro)
        creados = []
        for i, (cx, cy) in enumerate(patron['centros']):
            creados.append(rig.instancia(maestro, f'grano_{i}', (cx, cy),
                                         90.0 * i, 1.0, ctx.col['INTERIOR']))
        bpy.data.objects.remove(maestro, do_unlink=True)
        return creados

    # ------------------------------------------------------------------
    # Figuras — tres tazas, siempre desde arriba
    # ------------------------------------------------------------------

    def figura(self, ctx, pieza):
        return {'10': self._espresso, '11': self._macchiato,
                '12': self._mocha}[pieza](ctx)

    def _plato(self, ctx, radio, nombre):
        """El platillo: un disco de cerámica con un canto biselado. Lo comparten
        las tres figuras, que es de donde sale parte del presupuesto."""
        return self.silueta(ctx, f'{nombre}_plato', self.circulo(0, 0, radio, 56),
                            'ceramic', spec.Z_INTERIOR, grosor=0.05, bisel=0.014,
                            rugosidad=0.30)

    def _liquido(self, ctx, radio, rol, nombre, z=0.06):
        return self.silueta(ctx, f'{nombre}_liquido', self.circulo(0, 0, radio, 48),
                            rol, spec.Z_INTERIOR + z, grosor=0.02, bisel=0.004,
                            rugosidad=0.22)

    def _cuchara(self, ctx, nombre, angulo, largo, ancho=0.045):
        """Cucharilla dorada: mango recto y cazo ovalado. Cruza el plato y
        rompe el círculo, que es lo que separa las siluetas del 10 y del 11."""
        a = math.radians(angulo)
        x1, y1 = 0.10 * math.cos(a), 0.10 * math.sin(a)
        x2, y2 = largo * math.cos(a), largo * math.sin(a)
        mango = self.silueta(ctx, f'{nombre}_mango',
                             self.barra(x1, y1, x2, y2, ancho, ancho * 0.7),
                             'gold', spec.Z_INTERIOR + 0.11, grosor=0.02,
                             bisel=0.004, rugosidad=0.25)
        cazo = self.silueta(ctx, f'{nombre}_cazo',
                            self.elipse(x1, y1, 0.075, 0.05, 20, angulo),
                            'gold', spec.Z_INTERIOR + 0.11, grosor=0.02,
                            bisel=0.004, suave=True, rugosidad=0.25)
        return rig.unir([mango, cazo], f'{nombre}_cuchara')

    def _espresso(self, ctx):
        """Taza pequeña de pared gruesa. El disco de líquido es oscuro con un
        anillo de crema y un remolino moteado por encima. Silueta: dos círculos
        concéntricos apretados."""
        radio_plato = 0.55 * spec.VENTANA_MEDIO_X * 2 / 2
        self._plato(ctx, radio_plato, 'espresso')
        self.silueta(ctx, 'espresso_taza', self.circulo(0, 0, radio_plato * 0.68, 48),
                     'ceramic', spec.Z_INTERIOR + 0.05, grosor=0.05, bisel=0.012,
                     rugosidad=0.28)
        self._liquido(ctx, radio_plato * 0.52, 'crema', 'espresso', 0.10)
        self.silueta(ctx, 'espresso_cafe', self.circulo(0, 0, radio_plato * 0.44, 40),
                     'bean', spec.Z_INTERIOR + 0.12, grosor=0.01, bisel=0.003,
                     rugosidad=0.20)
        # El remolino de crema: dos arcos que se persiguen, moteados y opacos.
        for i, (r, de, a) in enumerate(((0.30, 20, 220), (0.19, 200, 380))):
            self.silueta(ctx, f'espresso_swirl{i}',
                         self.arco(0.0, 0.0, radio_plato * r, 0.035, de, a, 24),
                         'crema', spec.Z_INTERIOR + 0.13, grosor=0.006,
                         bisel=0.002, suave=True, rugosidad=0.30)
        self._cuchara(ctx, 'espresso', -35, radio_plato * 0.95, 0.038)
        return None

    def _macchiato(self, ctx):
        """Vaso alto: desde arriba se lee la pared del cilindro, con las capas
        asomando por el borde. Silueta: un círculo cruzado por una diagonal —
        la cucharilla larga — que lo separa del 10 y del 12 de un vistazo."""
        radio = 0.62 * spec.VENTANA_MEDIO_X
        # Pared del vaso: dos aros concéntricos que sugieren el espesor.
        self.silueta(ctx, 'macchiato_vaso', self.aro(0, 0, radio, 0.10),
                     'ceramic', spec.Z_INTERIOR, grosor=0.09, bisel=0.02,
                     rugosidad=0.14)
        # Capas vistas a través del cristal, de fuera a dentro.
        for i, (r, rol) in enumerate(((0.94, 'bean'), (0.80, 'crema'))):
            self.silueta(ctx, f'macchiato_capa{i}',
                         self.circulo(0, 0, radio * r, 44), rol,
                         spec.Z_INTERIOR + 0.02 + i * 0.01, grosor=0.01,
                         bisel=0.003, rugosidad=0.25)
        self._liquido(ctx, radio * 0.72, 'milk', 'macchiato', 0.05)

        # El corazón vertido: descentrado y ligeramente torcido, a propósito.
        corazon = [(0.0, -0.20), (0.16, -0.02), (0.17, 0.10), (0.09, 0.16),
                   (0.01, 0.09), (-0.08, 0.16), (-0.16, 0.09), (-0.15, -0.03)]
        pieza = self.silueta(ctx, 'macchiato_corazon',
                             self.escalar(corazon, radio * 2.1), 'crema',
                             spec.Z_INTERIOR + 0.08, grosor=0.008, bisel=0.002,
                             suave=True, rugosidad=0.30)
        pieza.rotation_euler[2] = math.radians(-14)
        rig.centrar_en(pieza, radio * 0.10, radio * 0.06)

        self._cuchara(ctx, 'macchiato', 62, radio * 1.35, 0.05)
        return None

    def _mocha(self, ctx):
        """El recipiente más ancho: un tazón. Encima, una roseta entera de
        once hojas. La única corona de la baraja, y está hecha de cacao.
        Silueta: el disco más grande, con satélites."""
        radio = 0.78 * spec.VENTANA_MEDIO_X
        self._plato(ctx, radio * 1.12, 'mocha')
        self.silueta(ctx, 'mocha_tazon', self.circulo(0, 0, radio, 56),
                     'ceramic', spec.Z_INTERIOR + 0.05, grosor=0.05, bisel=0.016,
                     rugosidad=0.26)
        self._liquido(ctx, radio * 0.88, 'bean', 'mocha', 0.10)

        # La roseta: once hojas vertidas, de la ancha de arriba a la punta de
        # abajo. Cada hoja es un GALÓN, no un rombo: dos brazos que bajan desde
        # el eje. Con rombos macizos las once se funden en un disco blanco y la
        # roseta desaparece — lo que la hace legible son los huecos oscuros que
        # quedan entre galón y galón.
        #
        # Es geometría a 0.02 sobre el líquido: ese labio es lo que le da
        # cuerpo a la espuma, y es el detalle que hace que la carta parezca cara.
        hojas = 11
        for i in range(hojas):
            t = i / (hojas - 1.0)
            # Todo el dibujo se queda dentro del disco de líquido (0.88 r):
            # una roseta que se sale del tazón deja de leerse como vertida.
            y = radio * (0.58 - 1.20 * t)
            ancho = radio * (0.62 - 0.48 * t) * math.sin(math.pi * (0.30 + 0.66 * t))
            caida = radio * 0.17
            grueso = radio * 0.10
            galon = [
                (-ancho, y + caida), (0.0, y),
                (ancho, y + caida),
                (ancho * 0.80, y + caida + grueso * 0.55),
                (0.0, y + grueso),
                (-ancho * 0.80, y + caida + grueso * 0.55),
            ]
            self.silueta(ctx, f'mocha_hoja{i}', galon, 'milk',
                         spec.Z_INTERIOR + 0.13 + i * 0.0009, grosor=0.008,
                         bisel=0.002, suave=True, rugosidad=0.32)
        # El tallo, que cose los galones y remata en punta.
        self.silueta(ctx, 'mocha_tallo',
                     self.barra(0.0, radio * 0.68, 0.0, -radio * 0.76, 0.026, 0.010),
                     'milk', spec.Z_INTERIOR + 0.145, grosor=0.006, bisel=0.002,
                     rugosidad=0.32)

        # Cacao espolvoreado en corona, sólo en el borde superior del disco.
        for i in range(9):
            a = math.radians(59 + 62 * i / 8)     # corona en el borde de arriba
            r = radio * 0.93
            self.silueta(ctx, f'mocha_cacao{i}',
                         self.circulo(r * math.cos(a), r * math.sin(a),
                                      radio * 0.045, 12),
                         'bean', spec.Z_INTERIOR + 0.15, grosor=0.004,
                         bisel=0.001, alfa=0.55)

        # Satélites en el plato: dos granos y la jarrita de leche.
        for i, (x, y) in enumerate(((-radio * 0.95, -radio * 0.72),
                                    (-radio * 1.12, -radio * 0.52))):
            grano = self.pip(ctx)
            rig.encajar_en(grano, radio * 0.34, radio * 0.44)
            grano.rotation_euler[2] = math.radians(28 + 55 * i)
            rig.centrar_en(grano, x, y)
        jarra = self.silueta(ctx, 'mocha_jarra', [
            (-0.13, -0.16), (0.13, -0.16), (0.15, 0.10),
            (0.06, 0.20), (-0.06, 0.18), (-0.15, 0.08),
        ], 'milk', spec.Z_INTERIOR + 0.06, grosor=0.05, bisel=0.012, suave=True,
            rugosidad=0.25)
        rig.centrar_en(jarra, radio * 0.96, -radio * 0.86)
        return None

    # ------------------------------------------------------------------
    # Dorso — tarjeta de visita de una buena cafetería
    # ------------------------------------------------------------------

    def dorso(self, ctx):
        rig.carta_base(ctx, rig.material_plano('coffee_dorso', self.color('frame')))

        maestro = rig.forma('dorso_grano', self._contorno_grano(0.23),
                            spec.Z_INTERIOR, 0.0, 0.0, True, ctx.col['INTERIOR'])
        rig.poner_material(maestro, rig.material_plano(
            'coffee_dorso_grano', self.color('gold'), 0.06))
        maestro = rig.a_malla(maestro)
        for fila in range(16):
            y = -1.50 + fila * 0.20
            desfase = 0.10 if fila % 2 else 0.0
            for columna in range(7):
                rig.instancia(maestro, f'dorso_{fila}_{columna}',
                              (-0.95 + columna * 0.30 + desfase, y),
                              30.0, 1.0, ctx.col['INTERIOR'])
        bpy.data.objects.remove(maestro, do_unlink=True)

        # Centro: un aro dorado con un grano dentro, girado 30°. Nada más.
        self.silueta(ctx, 'dorso_aro', self.aro(0, 0, 0.25, 0.02, 56), 'gold',
                     spec.Z_INTERIOR + 0.10, grosor=0.02, bisel=0.005,
                     rugosidad=0.30)
        grano = self.silueta(ctx, 'dorso_centro', self._contorno_grano(0.52),
                             'gold', spec.Z_INTERIOR + 0.12, grosor=0.03,
                             bisel=0.008, suave=True, rugosidad=0.30)
        grano.rotation_euler[2] = math.radians(30)
        return None


TEMA = Coffee()

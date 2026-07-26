# ==========================================================================
# themes/ducks.py — 01 · Patos
# --------------------------------------------------------------------------
# Fuente: wiki/decks/01-ducks.md. Amarillo de pato de goma sobre agua de
# estanque en calma: juguetes mates y blandos flotando en una superficie
# quieta y soleada. Gracioso sin ser una caricatura.
#
# Dos reglas del archivo del tema que no se tocan:
#   · El OJO es toda la personalidad. Ni se quita ni se agranda.
#   · Cada pato va cortado por la LÍNEA DE FLOTACIÓN y apoyado en una elipse
#     de onda. Un pato con las patas en el aire rompe el tema entero.
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


class Ducks(Tema):
    slug = 'ducks'
    nombre = 'Patos'
    nombre_en = 'Ducks'
    descripcion = ('Amarillo de pato de goma sobre agua de estanque: juguetes '
                   'mates flotando en una superficie quieta y soleada.')

    paleta = {
        'duck': '#F5C518', 'duck-shade': '#D99A0B', 'bill': '#F0733A',
        'water-top': '#BFE3E8', 'water-bot': '#7FBFCB', 'ripple': '#E8F6F8',
        'frame': '#F3EDE0', 'ink': '#2C3A44',
    }

    # Sans humanista geométrica, de peso fuerte.
    fuente_numerales = '/System/Library/Fonts/Avenir Next.ttc'
    hex_numeral = '#2C3A44'
    hex_banda = '#F3EDE0'
    rugosidad_banda = 0.55          # satinado: la KEY deja brillo por la izquierda
    hex_filete = '#7FBFCB'
    potencia_luces = 0.92
    eje_escalada = ('altura sobre el agua y alboroto: cría → zampullida → '
                    'ánade en el momento previo al aleteo')

    # ------------------------------------------------------------------
    # Fondo — el estanque visto desde arriba. Ni horizonte ni cielo.
    # ------------------------------------------------------------------

    def fondo(self, ctx, centro=(0.0, 0.0), anillos=3):
        rig.carta_base(ctx, rig.material_gradiente(
            'ducks_agua', self.color('water-top'), self.color('water-bot')))

        # Tres aros concéntricos centrados en el centro de masas de la carta.
        # Son el único detalle del fondo: no cuestan casi nada y hacen que las
        # once cartas parezcan el mismo estanque.
        #
        # RIESGO DE PESO del archivo del tema: aros finos y contrastados son
        # justo lo que revienta el webp. Se quedan al 14 % y a 0.02 de ancho.
        for i in range(anillos):
            radio = 0.34 + i * 0.30
            self.plana(ctx, f'onda{i}', self.aro(centro[0], centro[1], radio, 0.02, 64),
                       'ripple', spec.Z_BG + 0.002 + i * 0.001, alfa=0.14)

    # ------------------------------------------------------------------
    # Marco — un aro de onda detrás del numeral
    # ------------------------------------------------------------------

    def ornamento_esquina(self, ctx, x, y):
        aro = rig.forma('FRAME_onda', self.aro(x, y, 0.055, 0.012, 32),
                        spec.Z_NUMERAL + 0.001, 0.0, 0.0, False, ctx.col['FRAME'])
        rig.poner_material(aro, rig.material_plano(
            'ducks_onda_esq', self.color('water-bot'), 0.30))
        return aro

    # ------------------------------------------------------------------
    # Pinta — el pato
    # ------------------------------------------------------------------

    #: Altura local del corte de flotación. Por debajo de esto no hay pato:
    #: hay onda.
    FLOTACION = -0.30

    def _pato(self, ctx, nombre, escala=1.0, cria=False, z=0.0):
        """El pato, de tres cuartos por detrás y ladeado 8° hacia la cámara.

        Ese ángulo es lo que evita que parezca un juguete de baño fotografiado
        de perfil: se le ve el lomo redondo y el pico de canto a la vez.
        """
        piezas = []

        # Cuerpo: un huevo más ancho por la cola que por el pecho, cortado
        # plano por la línea de flotación.
        cuerpo = [
            (-0.42, -0.02), (-0.38, 0.18), (-0.24, 0.30),      # cola y lomo
            (-0.02, 0.34), (0.16, 0.28), (0.26, 0.14),         # hacia el cuello
            (0.30, -0.02),
            (0.28, self.FLOTACION), (-0.40, self.FLOTACION),   # el corte, recto
        ]
        piezas.append(self.silueta(ctx, f'{nombre}_cuerpo', cuerpo, 'duck',
                                   spec.Z_INTERIOR + z, grosor=0.16, bisel=0.05,
                                   suave=True, rugosidad=0.62))

        # Cabeza: una bola. En la cría es proporcionalmente mayor y más redonda.
        radio_cabeza = 0.21 if cria else 0.185
        cx, cy = (0.22, 0.46) if cria else (0.26, 0.50)
        piezas.append(self.silueta(ctx, f'{nombre}_cabeza',
                                   self.circulo(cx, cy, radio_cabeza, 30), 'duck',
                                   spec.Z_INTERIOR + z + 0.02, grosor=0.15,
                                   bisel=0.05, rugosidad=0.62))
        # Cuello, que cose la cabeza al cuerpo.
        piezas.append(self.silueta(ctx, f'{nombre}_cuello',
                                   self.barra(0.16, 0.20, cx, cy, 0.20, 0.24),
                                   'duck', spec.Z_INTERIOR + z + 0.01, grosor=0.14,
                                   bisel=0.045, rugosidad=0.62))

        # Pico: una cuña. En la cría es un pico romo y corto, sin cuña.
        if cria:
            pico = self.elipse(cx + radio_cabeza * 0.85, cy - 0.02, 0.075, 0.055, 18)
        else:
            pico = [(cx + 0.10, cy + 0.04), (cx + 0.34, cy - 0.01),
                    (cx + 0.33, cy - 0.07), (cx + 0.09, cy - 0.08)]
        piezas.append(self.silueta(ctx, f'{nombre}_pico', pico, 'bill',
                                   spec.Z_INTERIOR + z + 0.10, grosor=0.07,
                                   bisel=0.024, suave=cria, rugosidad=0.50))

        # El pliegue del ala: un arco poco profundo, no un ala modelada.
        piezas.append(self.silueta(
            ctx, f'{nombre}_ala',
            self.arco(-0.10, 0.02, 0.20, 0.035, -30, 130, 20), 'duck-shade',
            spec.Z_INTERIOR + z + 0.14, grosor=0.02, bisel=0.008, suave=True,
            rugosidad=0.62))

        grupo = rig.unir(piezas, nombre)

        # El OJO va aparte y siempre el último: es lo único que no se funde con
        # el resto, y es toda la personalidad del pato.
        ojo = self.silueta(ctx, f'{nombre}_ojo',
                           self.circulo(cx + 0.06, cy + 0.04, 0.032, 16), 'ink',
                           spec.Z_INTERIOR + z + 0.20, grosor=0.02, bisel=0.006,
                           rugosidad=0.4)
        return grupo, ojo

    def _flotar(self, ctx, nombre, x, y, ancho=0.44):
        """La elipse de onda sobre la que se apoya el pato. Sin esto el pato
        no flota: levita, y el tema se cae."""
        return self.silueta(ctx, f'{nombre}_flota',
                            self.elipse(x, y, ancho, ancho * 0.30, 28), 'ripple',
                            spec.Z_INTERIOR - 0.004, grosor=0.01, bisel=0.003,
                            suave=True, alfa=0.55)

    def pip(self, ctx):
        grupo, ojo = self._pato(ctx, f'pato_{ctx.rnd.randint(0, 10 ** 6)}')
        return rig.unir([grupo, ojo], 'pip_pato')

    def cartas_de_numero(self, ctx, n):
        """Los patos se colocan con el patrón del spec, pero cada uno se apoya
        en su propia elipse de onda, y las ondas se dibujan ANTES para que
        queden por debajo de todos los patos."""
        patron = spec.PATRONES[n]
        ancho_max, alto_max = patron['caja']

        # Primero, todas las ondas.
        for i, (cx, cy) in enumerate(patron['centros']):
            escala = patron.get('escala_centro', 1.0) if (n == 5 and i == 2) else 1.0
            self._flotar(ctx, f'onda_pip{i}', cx,
                         cy - alto_max * 0.30 * escala, ancho_max * 0.52 * escala)

        creados = super().cartas_de_numero(ctx, n)

        # El fondo lleva sus aros centrados en el centro de masas; en las
        # cartas de número eso es el centro de la carta, así que no hay nada
        # que recolocar.
        return creados

    # ------------------------------------------------------------------
    # Figuras
    # ------------------------------------------------------------------

    def figura(self, ctx, pieza):
        return {'10': self._cria, '11': self._zampullida,
                '12': self._anade}[pieza](ctx)

    def _cria(self, ctx):
        """Un solo patito, plumón, a 0.55 del pato grande y BAJO en el encuadre:
        el agua se queda con la mitad de arriba. Silueta: pequeño, redondo,
        abajo. Inconfundiblemente el más chico de los tres."""
        self._flotar(ctx, 'cria', 0.0, -0.62, 0.42)
        grupo, ojo = self._pato(ctx, 'cria_pato', cria=True)
        conjunto = rig.unir([grupo, ojo], 'fig_cria')
        rig.escalar_a_alto(conjunto, 0.55 * 2 * spec.VENTANA_MEDIO_Y * 0.80)
        rig.centrar_en(conjunto, 0.0, -0.44)
        return conjunto

    def _zampullida(self, ctx):
        """El pato volcado hacia delante, cola arriba: la postura clásica de
        cuando se alimenta. La cabeza está bajo el agua y por tanto NO ESTÁ —
        la silueta es una cuña amarilla con una corona de salpicadura donde el
        cuello entra en el agua. Se lee distinta del 10 y del 12 al instante.

        Escalada: es la que alborota el agua, seis aros rotos y descentrados."""
        # Aros rotos y desplazados: el agua revuelta.
        for i in range(6):
            radio = 0.22 + i * 0.16
            de = ctx.rnd.uniform(0, 120)
            self.plana(ctx, f'zamp_onda{i}',
                       self.arco(ctx.rnd.uniform(-0.10, 0.10) - 0.05,
                                 -0.42 + ctx.rnd.uniform(-0.05, 0.05),
                                 radio, 0.022, de, de + ctx.rnd.uniform(190, 320), 40),
                       'ripple', spec.Z_BG + 0.006 + i * 0.001, alfa=0.20)

        piezas = []
        # El cuerpo, volcado 40°: ancho abajo, estrechándose hacia la cola.
        cuerpo = [(-0.30, -0.52), (0.26, -0.44), (0.34, -0.06),
                  (0.22, 0.34), (-0.02, 0.42), (-0.22, 0.16), (-0.34, -0.20)]
        piezas.append(self.silueta(ctx, 'zamp_cuerpo', cuerpo, 'duck',
                                   grosor=0.16, bisel=0.05, suave=True,
                                   rugosidad=0.62))
        # Tres plumas de cola, como cuñas planas abiertas en abanico.
        for i, ang in enumerate((62, 88, 114)):
            a = math.radians(ang)
            base = (0.02 + 0.10 * math.cos(a), 0.34 + 0.06 * math.sin(a))
            punta = (base[0] + 0.34 * math.cos(a), base[1] + 0.34 * math.sin(a))
            piezas.append(self.silueta(
                ctx, f'zamp_pluma{i}',
                self.barra(base[0], base[1], punta[0], punta[1], 0.13, 0.045),
                'duck', spec.Z_INTERIOR + 0.02, grosor=0.10, bisel=0.03,
                rugosidad=0.62))
        # El pliegue del ala.
        piezas.append(self.silueta(
            ctx, 'zamp_ala', self.arco(0.0, -0.06, 0.20, 0.035, -60, 100, 20),
            'duck-shade', spec.Z_INTERIOR + 0.14, grosor=0.02, bisel=0.008,
            suave=True, rugosidad=0.62))

        conjunto = rig.unir(piezas, 'fig_zampullida')
        rig.escalar_a_alto(conjunto, 0.78 * 2 * spec.VENTANA_MEDIO_Y)
        rig.centrar_en(conjunto, 0.0, 0.10)

        # La corona de salpicadura, donde entra el cuello. Va después, en
        # coordenadas ya finales.
        for i in range(7):
            a = math.radians(200 + 140 * i / 6)
            r = 0.20 + 0.05 * (i % 3)
            self.silueta(ctx, f'zamp_salpica{i}',
                         self.barra(-0.02 + 0.13 * math.cos(a),
                                    -0.62 + 0.07 * math.sin(a),
                                    -0.02 + r * math.cos(a),
                                    -0.62 + r * 0.55 * math.sin(a), 0.045, 0.02),
                         'ripple', spec.Z_INTERIOR + 0.22, grosor=0.02,
                         bisel=0.006, alfa=0.85)
        return conjunto

    def _anade(self, ctx):
        """El ánade a tamaño completo, de perfil: pecho alzado, cuello estirado
        y alas a medio levantar, en el instante anterior al aleteo. Es la única
        carta con alas modeladas. La cresta es una arista de plumas en color de
        pico — una corona insinuada, nunca una corona de verdad.

        El agua debajo está como un cristal: un solo aro perfecto, ancho y
        centrado. Escalada: el más alto, el más ancho y el agua más tranquila
        — maestría, no esfuerzo."""
        piezas = []

        # Las alas van PRIMERO y por detrás: dos formas levantadas que salen
        # por encima de la línea del lomo. Si van encima del cuerpo se funden
        # con él y el ánade se convierte en un bulto.
        for lado, (px, py, ang, z) in enumerate((
                (-0.30, 0.16, 24, -0.006), (-0.10, 0.12, 8, -0.003))):
            ala = [(0.0, 0.0), (0.16, 0.18), (0.20, 0.44),
                   (0.10, 0.56), (-0.06, 0.44), (-0.14, 0.20)]
            piezas.append(self.silueta(
                ctx, f'anade_ala{lado}',
                self.mover(self.girar(ala, ang), px, py), 'duck',
                spec.Z_INTERIOR + z, grosor=0.09, bisel=0.03, suave=True,
                rugosidad=0.62))

        # Cuerpo: bajo, largo, con la cola levantada a la izquierda y el pecho
        # alzado a la derecha.
        piezas.append(self.silueta(ctx, 'anade_cuerpo', [
            (-0.72, 0.06), (-0.60, 0.20), (-0.34, 0.22),
            (-0.04, 0.20), (0.22, 0.14), (0.38, -0.02),
            (0.40, -0.20), (0.30, -0.34), (-0.62, -0.34), (-0.74, -0.16),
        ], 'duck', grosor=0.17, bisel=0.055, suave=True, rugosidad=0.62))

        # Cuello estirado hacia arriba y a la derecha, y cabeza alta.
        piezas.append(self.silueta(ctx, 'anade_cuello',
                                   self.barra(0.24, 0.06, 0.42, 0.62, 0.24, 0.17),
                                   'duck', spec.Z_INTERIOR + 0.01, grosor=0.15,
                                   bisel=0.05, rugosidad=0.62))
        piezas.append(self.silueta(ctx, 'anade_cabeza',
                                   self.circulo(0.44, 0.72, 0.185, 30), 'duck',
                                   spec.Z_INTERIOR + 0.02, grosor=0.15, bisel=0.05,
                                   rugosidad=0.62))
        # Pico, saliendo de la cabeza hacia la derecha.
        piezas.append(self.silueta(ctx, 'anade_pico', [
            (0.56, 0.75), (0.84, 0.70), (0.83, 0.62), (0.55, 0.63),
        ], 'bill', spec.Z_INTERIOR + 0.12, grosor=0.07, bisel=0.024,
            rugosidad=0.50))
        # La cresta: tres plumas cortas arqueadas sobre la cabeza. Una corona
        # insinuada por las plumas, nunca una corona de verdad.
        for i in range(3):
            a = math.radians(104 + 24 * i)
            piezas.append(self.silueta(
                ctx, f'anade_cresta{i}',
                self.barra(0.44 + 0.16 * math.cos(a), 0.72 + 0.16 * math.sin(a),
                           0.44 + 0.30 * math.cos(a), 0.72 + 0.30 * math.sin(a),
                           0.055, 0.02),
                'bill', spec.Z_INTERIOR + 0.05, grosor=0.04, bisel=0.012,
                rugosidad=0.55))
        # El pliegue del ala sobre el costado.
        piezas.append(self.silueta(
            ctx, 'anade_pliegue', self.arco(-0.18, -0.06, 0.20, 0.035, -40, 120, 20),
            'duck-shade', spec.Z_INTERIOR + 0.14, grosor=0.02, bisel=0.008,
            suave=True, rugosidad=0.62))
        # El ojo entra en la unión: al fundir mallas cada cara conserva su
        # material, así que sigue siendo negro y viaja con la figura al escalar.
        piezas.append(self.silueta(ctx, 'anade_ojo',
                                   self.circulo(0.50, 0.76, 0.033, 16), 'ink',
                                   spec.Z_INTERIOR + 0.20, grosor=0.02, bisel=0.006,
                                   rugosidad=0.4))

        # Se encaja por ANCHO Y ALTO: el ánade con las alas abiertas y el
        # cuello estirado es la figura más ancha de la baraja, y escalándolo
        # sólo por la altura se salía de la ventana por los dos lados.
        conjunto = rig.unir(piezas, 'fig_anade')
        rig.encajar_en(conjunto, 2 * spec.VENTANA_MEDIO_X * 0.96,
                       0.88 * 2 * spec.VENTANA_MEDIO_Y)
        rig.centrar_en(conjunto, -0.02, 0.04)

        # Un solo aro, ancho, perfecto y centrado: el agua en calma absoluta.
        self.plana(ctx, 'anade_onda', self.aro(0.0, -1.02, 0.74, 0.026, 72),
                   'ripple', spec.Z_BG + 0.008, alfa=0.28)
        return conjunto

    # ------------------------------------------------------------------
    # Dorso
    # ------------------------------------------------------------------

    def dorso(self, ctx):
        rig.carta_base(ctx, rig.material_plano('ducks_dorso', self.color('water-bot')))

        # Retícula hexagonal de aritos diminutos al 10 %.
        maestro = rig.forma('dorso_onda', self.aro(0, 0, 0.08, 0.014, 26),
                            spec.Z_INTERIOR, 0.0, 0.0, False, ctx.col['INTERIOR'])
        rig.poner_material(maestro, rig.material_plano(
            'ducks_dorso_onda', self.color('ripple'), 0.10))
        maestro = rig.a_malla(maestro)
        paso_x, paso_y = 0.26, 0.225
        for fila in range(15):
            y = -1.55 + fila * paso_y
            desfase = paso_x / 2 if fila % 2 else 0.0
            for columna in range(9):
                rig.instancia(maestro, f'dorso_{fila}_{columna}',
                              (-1.04 + columna * paso_x + desfase, y),
                              0.0, 1.0, ctx.col['INTERIOR'])
        bpy.data.objects.remove(maestro, do_unlink=True)

        # En el centro, la silueta de un pato, plana y sin relieve, mirando a
        # la izquierda. Lo bastante simétrica para que girar la carta no diga
        # nada (§ dorso).
        silueta = self.plana(ctx, 'dorso_pato', [
            (0.40, -0.26), (0.16, -0.32), (-0.16, -0.28),    # panza
            (-0.38, -0.10), (-0.44, 0.10), (-0.34, 0.16),    # cola levantada
            (-0.14, 0.06), (0.10, 0.06),                     # lomo
            (0.20, 0.26), (0.16, 0.44),                      # cuello
            (0.28, 0.56), (0.44, 0.52), (0.48, 0.38),        # cabeza
            (0.62, 0.36), (0.62, 0.28), (0.46, 0.26),        # pico
            (0.44, 0.10), (0.46, -0.10),
        ], 'duck', spec.Z_INTERIOR + 0.10, suave=True, capa='INTERIOR')
        # A malla antes de medir: la caja envolvente de una curva incluye los
        # manejadores de las bezier, así que centrarla sin convertir la deja
        # descolocada.
        silueta = rig.a_malla(silueta)
        rig.escalar_a_alto(silueta, 0.62)   # 0.4 BU de ANCHO, que es lo que pide el tema
        rig.centrar_en(silueta, 0.0, 0.0)
        return silueta


TEMA = Ducks()

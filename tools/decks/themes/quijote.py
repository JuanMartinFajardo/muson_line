# ==========================================================================
# themes/quijote.py — 05 · Don Quijote
# --------------------------------------------------------------------------
# Fuente: wiki/decks/05-quijote.md. Un teatro de sombras: TODO menos el marco
# es una silueta plana extruida 0.02 con bisel 0.004, y nada se sale del plano
# XY. Cualquier escorzo mata el tema al instante, así que aquí no se rota nada
# fuera de XY ni se añade desenfoque atmosférico: la profundidad es sólo valor
# (`ink` cerca, `ink-soft` lejos, `ink-soft` al 55 % para lo imaginado).
#
# La línea del horizonte cae exactamente a la misma altura en las 11 cartas
# (HORIZONTE), que es lo que hace que la baraja se lea como un solo paisaje.
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


#: El horizonte: la banda de tierra ocupa el 22 % inferior de la ventana.
HORIZONTE = -spec.VENTANA_MEDIO_Y + 0.22 * (2 * spec.VENTANA_MEDIO_Y)


class Quijote(Tema):
    slug = 'quijote'
    nombre = 'Don Quijote'
    nombre_en = 'Don Quixote'
    descripcion = ('La Mancha a mediodía en tres colores: cielo blanqueado, '
                   'tierra ocre y siluetas negras que podrían ser gigantes.')

    paleta = {
        'sky': '#F0E3C8', 'sky-lo': '#E2CDA4', 'earth': '#C98F4A',
        'ink': '#241E1A', 'ink-soft': '#5C4E42', 'rust': '#9E3B22',
        'frame': '#3A2E23', 'parchment': '#F5EBD6',
    }

    # Serif humanista de proporciones garaldas, generosamente espaciado.
    fuente_numerales = '/System/Library/Fonts/Supplemental/Baskerville.ttc'
    hex_numeral = '#F5EBD6'
    hex_banda = '#3A2E23'
    rugosidad_banda = 0.75          # mate, como el canto de una página
    potencia_luces = 1.0
    eje_escalada = ('distancia al suelo: Dulcinea imaginada, Sancho plantado, '
                    'Quijote por los aires')

    # ------------------------------------------------------------------
    # Fondo — dos zonas y nada más. Sin nubes, sin sol, sin textura.
    # ------------------------------------------------------------------

    def fondo(self, ctx):
        rig.carta_base(ctx, rig.material_gradiente(
            'quijote_cielo', self.color('sky'), self.color('sky-lo')))

        # Banda de tierra, borde superior recto: el horizonte. Idéntico en las
        # once cartas, que es lo que las convierte en un solo paisaje.
        self.plana(ctx, 'tierra', [
            (-spec.MEDIO_X, -spec.MEDIO_Y), (spec.MEDIO_X, -spec.MEDIO_Y),
            (spec.MEDIO_X, HORIZONTE), (-spec.MEDIO_X, HORIZONTE),
        ], 'earth', spec.Z_BG + 0.002)

        # Niebla de calor: una banda horizontal justo encima del suelo.
        self.plana(ctx, 'calor', [
            (-spec.MEDIO_X, HORIZONTE + 0.03), (spec.MEDIO_X, HORIZONTE + 0.03),
            (spec.MEDIO_X, HORIZONTE + 0.16), (-spec.MEDIO_X, HORIZONTE + 0.16),
        ], 'parchment', spec.Z_BG + 0.004, alfa=0.15)

        # Cuatro matojos en la tierra. Nada más: el fondo se acaba aquí.
        for i in range(4):
            x = -0.75 + i * 0.5 + ctx.rnd.uniform(-0.08, 0.08)
            self.plana(ctx, f'mata{i}', self.barra(
                x, HORIZONTE - 0.34, x + ctx.rnd.uniform(-0.05, 0.05),
                HORIZONTE - 0.34 + ctx.rnd.uniform(0.10, 0.20), 0.020, 0.004),
                'ink-soft', spec.Z_BG + 0.006, alfa=0.20)

    # ------------------------------------------------------------------
    # Marco — voluta capitular en `rust`, detrás del numeral
    # ------------------------------------------------------------------

    def ornamento_esquina(self, ctx, x, y):
        """Un solo trazo que se enrosca, a la manera de una capitular
        iluminada. Se hace con `arco` de grosor decreciente."""
        trazo = []
        pasos = 22
        for i in range(pasos + 1):
            t = i / pasos
            ang = math.radians(-30 + 300 * t)
            r = 0.055 - 0.026 * t
            trazo.append((x + r * math.cos(ang), y + r * math.sin(ang)))
        for i in range(pasos, -1, -1):
            t = i / pasos
            ang = math.radians(-30 + 300 * t)
            r = 0.055 - 0.026 * t - (0.013 - 0.009 * t)
            trazo.append((x + r * math.cos(ang), y + r * math.sin(ang)))

        obj = rig.forma('FRAME_voluta', trazo, spec.Z_NUMERAL + 0.001,
                        0.0, 0.0, True, ctx.col['FRAME'])
        rig.poner_material(obj, rig.material_plano(
            'quijote_voluta', self.color('rust')))
        return obj

    # ------------------------------------------------------------------
    # Pinta — el molino, visto de frente, como recorte de papel
    # ------------------------------------------------------------------

    def _molino(self, ctx, nombre, angulo, rol='ink', alfa=1.0, aspa=0.52):
        """Torre troncocónica con capucha y cuatro aspas en X dura.

        Se construye por partes que se funden en una sola malla: así la
        silueta se lee como un contorno continuo y el patrón puede duplicarla
        en enlazado.

        `aspa` es el radio de las aspas. Se acorta en las cartas de fila (4 y
        7), donde siete cruces desplegadas se comen unas a otras: lo que hay
        que poder contar son las TORRES, y para eso tienen que quedar francas.
        """
        partes = []

        # Torre + capucha, en un contorno cerrado.
        partes.append(self.silueta(ctx, f'{nombre}_torre', [
            (-0.21, -0.46), (0.21, -0.46),
            (0.14, 0.16), (0.17, 0.19), (0.0, 0.40), (-0.17, 0.19), (-0.14, 0.16),
        ], rol, alfa=alfa))

        # Las cuatro aspas: barras ahusadas hacia la punta.
        for k in range(4):
            a = math.radians(angulo + 90 * k)
            dx, dy = math.cos(a) * aspa, math.sin(a) * aspa
            partes.append(self.silueta(
                ctx, f'{nombre}_aspa{k}',
                self.barra(0.0, 0.28, dx, 0.28 + dy, 0.085, 0.045),
                rol, spec.Z_INTERIOR + 0.004, alfa=alfa))

        return rig.unir(partes, nombre)

    def pip(self, ctx):
        return self._molino(ctx, 'molino', ctx.rnd.uniform(0, 45))

    pip_tiene_arriba = True

    # ------------------------------------------------------------------
    # Cartas 1–7 — el archivo del tema desvía cinco de ellas
    # ------------------------------------------------------------------

    def cartas_de_numero(self, ctx, n):
        if n == 1:
            return self._as(ctx)
        if n == 2:
            return self._dos(ctx)
        if n in (4, 7):
            return self._fila_en_horizonte(ctx, n)
        if n in (3, 5, 6):
            return self._patron_con_valor(ctx, n)
        return super().cartas_de_numero(ctx, n)

    def _as(self, ctx):
        """Un molino enorme, aspas a 22°, tan cerca que las puntas las recorta
        el marco. Carta cartel del tema."""
        molino = self._molino(ctx, 'molino_as', 22.0)
        rig.encajar_en(molino, 1.30, 1.70)
        molino.scale = tuple(s * 1.5 for s in molino.scale)   # se sale a propósito
        rig.centrar_en(molino, 0.0, -0.05)

        # Uso de `rust` nº 1 de los tres de la baraja: una puertecita.
        self.silueta(ctx, 'as_puerta', [
            (-0.05, -0.72), (0.05, -0.72), (0.05, -0.50),
            (0.03, -0.46), (-0.03, -0.46), (-0.05, -0.50),
        ], 'rust', spec.Z_INTERIOR + 0.06, grosor=0.01, bisel=0.002)
        return molino

    def _dos(self, ctx):
        """Los dos de pie sobre el horizonte, uno grande delante y otro más
        pequeño y en `ink-soft` detrás: profundidad por valor, no por escorzo."""
        cerca = self._molino(ctx, 'dos_cerca', ctx.rnd.uniform(0, 45))
        rig.encajar_en(cerca, 0.92, 1.12)
        rig.centrar_en(cerca, -0.18, HORIZONTE + 0.46)

        lejos = self._molino(ctx, 'dos_lejos', ctx.rnd.uniform(0, 45), 'ink-soft')
        rig.encajar_en(lejos, 0.62, 0.76)
        rig.centrar_en(lejos, 0.40, HORIZONTE + 0.32)
        return [cerca, lejos]

    def _patron_con_valor(self, ctx, n):
        """3, 5 y 6 mantienen el patrón del spec, pero reparten los dos valores
        de tinta como dice el archivo del tema: lo alto y lo lejano, en
        `ink-soft`."""
        patron = spec.PATRONES[n]
        ancho_max, alto_max = patron['caja']
        lejanos = {3: {0}, 5: {0, 1, 3, 4}, 6: {2, 3}}[n]

        creados = []
        for i, (cx, cy) in enumerate(patron['centros']):
            rol = 'ink-soft' if i in lejanos else 'ink'
            molino = self._molino(ctx, f'p{n}_{i}', ctx.rnd.uniform(0, 45), rol)
            escala = 1.0 + ctx.rnd.uniform(-spec.JITTER_ESCALA, spec.JITTER_ESCALA)
            if n == 5:
                escala *= patron['escala_centro'] if i == 2 else 0.86
            rig.encajar_en(molino, ancho_max * escala, alto_max * escala)
            # En el 6 la fila lejana se levanta: se lee como una segunda cresta.
            rig.centrar_en(molino, cx, cy + (0.26 if (n == 6 and i in lejanos) else 0.0))
            creados.append(molino)
        return creados

    def _fila_en_horizonte(self, ctx, n):
        """4 y 7 ignoran la rejilla: una sola fila sobre el horizonte, que es
        como se ve de verdad la cresta de Campo de Criptana. La condición del
        §4.1 sigue en pie — se tienen que contar de un vistazo — así que las
        alturas son generosas y los huecos, francos."""
        creados = []
        if n == 4:
            # Cuatro en fila, decreciendo de izquierda a derecha.
            xs = [-0.62, -0.21, 0.20, 0.60]
            escalas = [1.00, 0.86, 0.73, 0.61]
            roles = ['ink'] * 4
            base, aspa = 0.62, 0.34
        else:
            # Siete: la cresta más larga de la baraja. Las aspas se recogen y
            # las alturas se alternan para que cada torre tenga su hueco. Sale
            # una cresta lejana con mucho cielo encima, que es exactamente el
            # aire de este tema.
            xs = [-0.72, -0.48, -0.24, 0.00, 0.24, 0.48, 0.72]
            escalas = [0.86, 1.00, 0.80, 0.96, 0.82, 1.00, 0.88]
            roles = ['ink' if i % 2 == 0 else 'ink-soft' for i in range(7)]
            base, aspa = 0.44, 0.28

        # Se escala por ALTURA, no encajando en una caja: un molino con las
        # aspas desplegadas es mucho más ancho que alto, y encajarlo por ancho
        # deja siete miniaturas ilegibles pegadas al suelo.
        for i, (x, escala, rol) in enumerate(zip(xs, escalas, roles)):
            molino = self._molino(ctx, f'fila{n}_{i}',
                                  ctx.rnd.uniform(12, 38), rol, aspa=aspa)
            rig.escalar_a_alto(molino, base * escala)
            rig.centrar_en(molino, x, HORIZONTE + base * escala * 0.40)
            creados.append(molino)
        return creados

    # ------------------------------------------------------------------
    # Figuras
    # ------------------------------------------------------------------

    def figura(self, ctx, pieza):
        return {'10': self._dulcinea, '11': self._sancho,
                '12': self._quijote}[pieza](ctx)

    def _dulcinea(self, ctx):
        """Nunca es real, así que nunca es sólida: `ink-soft` al 55 %, y la
        niebla de calor le pasa por encima. Es la única figura por la que se ve
        el fondo, y esa es toda la idea. Silueta: una columna estrecha, blanda
        e incompleta."""
        # Se dibuja de UN SOLO trazo cerrado, no juntando piezas. Con alfa
        # 0.55, dos siluetas superpuestas suman opacidad y la figura sale a
        # manchas: la única forma de que una figura translúcida tenga un valor
        # uniforme es que no se solape consigo misma.
        #
        # Proporciones deliberadamente estrechas. La prueba de silueta del §7
        # la tiene que separar de Sancho (bajo y ancho) y del Quijote (largo y
        # horizontal) en negro puro.
        cuerpo = self.silueta(ctx, 'dulcinea', [
            (0.00, 0.70),                       # alto de la cabeza
            (0.10, 0.62), (0.11, 0.50),         # sien y mandíbula
            (0.04, 0.44),                       # cuello, lado derecho
            (0.14, 0.36), (0.15, 0.24),         # hombro derecho
            (0.11, 0.08), (0.09, -0.06),        # costado y talle
            (0.16, -0.34), (0.26, -0.74),       # falda abriéndose
            (0.10, -0.70), (-0.04, -0.75),      # bajo deshilachado
            (-0.20, -0.70), (-0.26, -0.74),
            (-0.17, -0.32), (-0.11, -0.06),     # el otro costado
            (-0.14, 0.10), (-0.20, 0.22),       # hombro izquierdo…
            (-0.32, 0.42), (-0.37, 0.55),       # …y el brazo levantado
            (-0.30, 0.58), (-0.22, 0.46),
            (-0.13, 0.36),                      # vuelta al cuello
            (-0.05, 0.44),
            (-0.11, 0.50), (-0.10, 0.62),
        ], 'ink-soft', suave=True, alfa=0.55)

        grupo = rig.unir([cuerpo], 'fig_dulcinea')
        rig.escalar_a_alto(grupo, 0.80 * 2 * spec.VENTANA_MEDIO_Y)
        rig.centrar_en(grupo, 0.02, -0.06)

        # Uso de `rust` nº 2: la cinta del pelo. Lo único definido de ella. Va
        # después de escalar la figura, con la carta ya en coordenadas finales.
        rig.centrar_en(
            self.silueta(ctx, 'cinta',
                         self.barra(-0.09, 0.02, 0.09, -0.02, 0.045, 0.02),
                         'rust', spec.Z_INTERIOR + 0.08, grosor=0.01, bisel=0.002),
            0.13, 0.86)
        return grupo

    def _sancho(self, ctx):
        """Todo `ink`, de canto duro, absolutamente sólido. Ancho y bajo, con
        los pies en la tierra: es el contrapeso del 12 en todos los sentidos."""
        partes = [
            # Cuerpo redondo, de perfil mirando a la izquierda.
            self.silueta(ctx, 'sancho_cuerpo', [
                (-0.34, -0.26), (-0.36, 0.04), (-0.28, 0.24),
                (-0.14, 0.34), (0.10, 0.34), (0.26, 0.22),
                (0.32, 0.00), (0.28, -0.26),
            ], 'ink', suave=True),
            # El sombrero de ala ancha: es media silueta él solo.
            self.silueta(ctx, 'sancho_sombrero', [
                (-0.46, 0.36), (0.34, 0.36), (0.30, 0.42),
                (0.16, 0.44), (0.12, 0.58), (-0.10, 0.58), (-0.14, 0.44),
                (-0.42, 0.42),
            ], 'ink', spec.Z_INTERIOR + 0.003),
            # Dos piernas cortas y separadas.
            self.silueta(ctx, 'sancho_p1', self.barra(-0.16, -0.24, -0.18, -0.66, 0.16),
                         'ink'),
            self.silueta(ctx, 'sancho_p2', self.barra(0.12, -0.24, 0.15, -0.66, 0.16),
                         'ink'),
            # La bota de vino, colgada de la cadera.
            self.silueta(ctx, 'sancho_bota',
                         self.elipse(0.40, -0.10, 0.11, 0.15, 20, 20), 'ink'),
        ]
        # La cabeza del burro, a la altura de la rodilla.
        partes.append(self.silueta(ctx, 'sancho_burro', [
            (-0.68, -0.34), (-0.50, -0.30), (-0.42, -0.14), (-0.44, 0.00),
            (-0.49, -0.04), (-0.53, 0.06), (-0.57, -0.05), (-0.62, -0.12),
            (-0.70, -0.22),
        ], 'ink', suave=True))

        grupo = rig.unir(partes, 'fig_sancho')
        rig.encajar_en(grupo, 1.34, 0.68 * 2 * spec.VENTANA_MEDIO_Y)
        rig.centrar_en(grupo, 0.0, HORIZONTE + 0.52)
        return grupo

    def _quijote(self, ctx):
        """A caballo, lanza en ristre, cargando a la izquierda. Caballo y
        jinete son una sola silueta continua; la lanza cruza la carta entera y
        el marco la recorta por los dos lados."""
        # El molino, ahora como antagonista, al 12 % y por detrás de todo.
        molino = self._molino(ctx, 'rey_molino', 30.0, 'ink-soft', alfa=0.12)
        rig.encajar_en(molino, 0.86, 1.10)
        rig.centrar_en(molino, 0.34, 0.34)

        partes = [
            # Rocinante: escuálido, todas las patas en el aire a media zancada.
            self.silueta(ctx, 'rey_tronco', [
                (-0.54, 0.02), (-0.34, 0.12), (-0.06, 0.10),
                (0.20, 0.14), (0.34, 0.06), (0.30, -0.10),
                (0.04, -0.16), (-0.24, -0.14), (-0.50, -0.08),
            ], 'ink', suave=True),
            # Cuello y cabeza, estirados hacia delante.
            self.silueta(ctx, 'rey_cuello', [
                (-0.50, -0.04), (-0.44, 0.10), (-0.62, 0.22),
                (-0.78, 0.26), (-0.82, 0.18), (-0.70, 0.12), (-0.58, 0.00),
            ], 'ink', suave=True),
            # Grupa y cola.
            self.silueta(ctx, 'rey_grupa', [
                (0.26, 0.12), (0.44, 0.18), (0.50, 0.04),
                (0.42, -0.06), (0.28, -0.08),
            ], 'ink', suave=True),
        ]
        # Cuatro patas en zancada, ninguna tocando el suelo.
        for x0, y0, x1, y1, x2, y2 in (
            (-0.36, -0.10, -0.48, -0.34, -0.62, -0.42),
            (-0.22, -0.12, -0.16, -0.36, -0.02, -0.44),
            (0.16, -0.12, 0.24, -0.34, 0.14, -0.46),
            (0.30, -0.08, 0.44, -0.28, 0.52, -0.40),
        ):
            partes.append(self.silueta(ctx, f'rey_pata{x0}',
                                       self.barra(x0, y0, x1, y1, 0.075, 0.05), 'ink'))
            partes.append(self.silueta(ctx, f'rey_casco{x0}',
                                       self.barra(x1, y1, x2, y2, 0.05, 0.035), 'ink'))

        # El jinete, echado muy hacia delante sobre el cuello del caballo.
        partes += [
            # Torso inclinado, del sillín al hombro.
            self.silueta(ctx, 'rey_torso',
                         self.barra(0.02, 0.10, -0.20, 0.44, 0.17, 0.13), 'ink',
                         spec.Z_INTERIOR + 0.004),
            # El brazo que empuña, siguiendo la línea de la lanza.
            self.silueta(ctx, 'rey_brazo',
                         self.barra(-0.18, 0.42, -0.42, 0.52, 0.07, 0.05), 'ink',
                         spec.Z_INTERIOR + 0.006),
            # La pierna, doblada contra la panza del caballo.
            self.silueta(ctx, 'rey_pierna',
                         self.barra(0.04, 0.10, 0.06, -0.14, 0.075, 0.05), 'ink',
                         spec.Z_INTERIOR + 0.004),
            # Cuello y yelmo de bacía: media esfera boca abajo.
            self.silueta(ctx, 'rey_cuello_j',
                         self.barra(-0.22, 0.44, -0.24, 0.52, 0.055), 'ink',
                         spec.Z_INTERIOR + 0.006),
            self.silueta(ctx, 'rey_yelmo', [
                (-0.36, 0.55), (-0.12, 0.55), (-0.14, 0.63),
                (-0.24, 0.68), (-0.34, 0.62),
            ], 'ink', spec.Z_INTERIOR + 0.008, suave=True),
            # La lanza, de borde a borde, cruzando por encima de todo.
            self.silueta(ctx, 'rey_lanza',
                         self.barra(-1.16, 0.66, 0.66, 0.30, 0.032, 0.018), 'ink',
                         spec.Z_INTERIOR + 0.010),
        ]

        grupo = rig.unir(partes, 'fig_rey')
        rig.encajar_en(grupo, 2 * spec.VENTANA_MEDIO_X,
                       0.90 * 2 * spec.VENTANA_MEDIO_Y)
        rig.centrar_en(grupo, 0.0, -0.06)

        # Uso de `rust` nº 3: la punta de la lanza. El único punto saturado y
        # afilado de las 40 cartas.
        rig.centrar_en(self.silueta(ctx, 'rey_punta', [
            (-0.06, 0.03), (0.06, 0.0), (-0.06, -0.03),
        ], 'rust', spec.Z_INTERIOR + 0.10, grosor=0.01, bisel=0.002),
            -0.86, 0.62)
        return grupo

    # ------------------------------------------------------------------
    # Dorso — sello de lacre sobre teselado de molinos
    # ------------------------------------------------------------------

    def dorso(self, ctx):
        rig.carta_base(ctx, rig.material_plano('quijote_dorso', self.color('earth')))

        # Retícula al tresbolillo de molinos al 7 %, cada uno con otro ángulo.
        maestro = self._molino(ctx, 'dorso_molino', 0.0, 'ink', alfa=0.07)
        rig.encajar_en(maestro, 0.28, 0.34)
        maestro = rig.a_malla(maestro)
        for fila in range(10):
            y = -1.48 + fila * 0.34
            desfase = 0.18 if fila % 2 else 0.0
            for columna in range(4):
                rig.instancia(maestro, f'dorso_{fila}_{columna}',
                              (-0.84 + columna * 0.48 + desfase, y),
                              ctx.rnd.uniform(0, 45), 1.0, ctx.col['INTERIOR'])
        bpy.data.objects.remove(maestro, do_unlink=True)

        # El sello: un disco `rust` con el molino en negativo dentro.
        sello = self.silueta(ctx, 'dorso_sello', self.circulo(0, 0, 0.44, 48),
                             'rust', spec.Z_INTERIOR + 0.10, grosor=0.03,
                             bisel=0.006, rugosidad=0.55)
        negativo = self._molino(ctx, 'dorso_negativo', 22.0, 'earth')
        rig.encajar_en(negativo, 0.50, 0.60)
        negativo.location.z = spec.Z_INTERIOR + 0.16
        rig.centrar_en(negativo, 0.0, 0.0)
        return [sello, negativo]


TEMA = Quijote()

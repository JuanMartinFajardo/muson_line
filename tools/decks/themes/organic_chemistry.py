# ==========================================================================
# themes/organic_chemistry.py — 16 · Química Orgánica
# --------------------------------------------------------------------------
# Fuente: wiki/decks/16-organic-chemistry.md. Fórmulas esqueléticas como diseño
# gráfico puro: hexágonos, ángulos de enlace y pares libres sobre papel
# cuadriculado de laboratorio. **El recuento es el número de carbonos**, y es
# químicamente cierto — eso es todo el tema.
#
# Los ángulos son exactos: 109.5° para sp³, 120° para sp², 180° para sp. Un
# químico ve un ángulo mal al instante y deja la baraja por descuidada.
#
# Cada estructura tiene que ser una molécula REAL y CORRECTA. El encanto del
# tema es enteramente que sea verdad; si una estructura está mal, la carta no
# vale nada precisamente para quien más la disfrutaría.
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


class OrganicChemistry(Tema):
    slug = 'organic-chemistry'
    nombre = 'Química orgánica'
    nombre_en = 'Organic chemistry'
    descripcion = ('Fórmulas esqueléticas sobre papel cuadriculado. El número '
                   'de la carta es el número de carbonos, y es cierto.')

    paleta = {
        'notebook': '#F2EEE2', 'grid': '#C9D9C4', 'carbon': '#2A2A2E',
        'oxygen': '#D93B2B', 'nitrogen': '#2B5BD9', 'sulfur': '#E8C020',
        'halogen': '#3EB56B', 'frame': '#1E2622', 'chalk': '#F2EEE2',
    }

    # Sans técnica con cero barrado y uno de asta plana: la letra de un frasco
    # de reactivo.
    fuente_numerales = '/System/Library/Fonts/Menlo.ttc'
    hex_numeral = '#F2EEE2'
    hex_banda = '#1E2622'
    rugosidad_banda = 0.85          # mate
    potencia_luces = 1.05
    eje_escalada = 'complejidad molecular: disolvente → fármaco → macromolécula'

    #: Grosor del enlace (§ pinta): cilindros de 0.014 con las puntas redondas.
    ENLACE = 0.030
    #: Longitud canónica de un enlace en el dibujo.
    LARGO = 0.30

    # ------------------------------------------------------------------
    # Fondo — papel de cuaderno de laboratorio
    # ------------------------------------------------------------------

    def fondo(self, ctx):
        rig.carta_base(ctx, rig.material_plano('quim_papel', self.color('notebook')))

        # La misma cuadrícula en todas las cartas: paso 0.11 BU, al 22 %.
        paso, mitad = 0.11, 0.0035
        n_v = int(spec.MEDIO_X / paso) + 1
        for i in range(-n_v, n_v + 1):
            x = i * paso
            self.plana(ctx, f'gridv{i}', [
                (x - mitad, -spec.MEDIO_Y), (x + mitad, -spec.MEDIO_Y),
                (x + mitad, spec.MEDIO_Y), (x - mitad, spec.MEDIO_Y),
            ], 'grid', spec.Z_BG + 0.002, alfa=0.22)
        n_h = int(spec.MEDIO_Y / paso) + 1
        for i in range(-n_h, n_h + 1):
            y = i * paso
            self.plana(ctx, f'gridh{i}', [
                (-spec.MEDIO_X, y - mitad), (spec.MEDIO_X, y - mitad),
                (spec.MEDIO_X, y + mitad), (-spec.MEDIO_X, y + mitad),
            ], 'grid', spec.Z_BG + 0.002, alfa=0.22)

        # Marginalia arriba a la derecha: trazos y una flecha, al 18 %. Tiene
        # que parecer una anotación al margen y ser DEMASIADO pequeña para
        # leerse como texto — si se lee, se convierte en una etiqueta y estorba.
        anotacion = ctx.rnd.randint(3, 5)
        for i in range(anotacion):
            x0 = 0.24 + ctx.rnd.uniform(-0.02, 0.02)
            y0 = 1.10 - i * 0.055
            largo = ctx.rnd.uniform(0.12, 0.34)
            self.plana(ctx, f'nota{i}', self.barra(x0, y0, x0 + largo, y0, 0.012),
                       'carbon', spec.Z_BG + 0.004, alfa=0.18)
        self.plana(ctx, 'nota_flecha',
                   self.barra(0.24, 1.10 - anotacion * 0.055 - 0.05,
                              0.62, 1.10 - anotacion * 0.055 - 0.05, 0.010),
                   'carbon', spec.Z_BG + 0.004, alfa=0.18)
        self.plana(ctx, 'nota_punta', [
            (0.62, 1.10 - anotacion * 0.055 - 0.015),
            (0.68, 1.10 - anotacion * 0.055 - 0.05),
            (0.62, 1.10 - anotacion * 0.055 - 0.085),
        ], 'carbon', spec.Z_BG + 0.004, alfa=0.18)

    # ------------------------------------------------------------------
    # Marco — hexágeno verde detrás del numeral
    # ------------------------------------------------------------------

    def ornamento_esquina(self, ctx, x, y):
        hexa = rig.forma('FRAME_hexa',
                         [self.poligono_regular(x, y, 0.062, 6, 30),
                          self.poligono_regular(x, y, 0.050, 6, 30)],
                         spec.Z_NUMERAL + 0.001, 0.0, 0.0, False, ctx.col['FRAME'])
        rig.poner_material(hexa, rig.material_plano(
            'quim_hexa_esq', self.color('halogen'), 0.45))
        return hexa

    # ------------------------------------------------------------------
    # Dibujo de estructuras
    # ------------------------------------------------------------------

    def _enlace(self, ctx, nombre, p1, p2, rol='carbon', orden=1, z=0.0,
                separacion=0.055):
        """Un enlace. Doble = dos paralelas, triple = tres.

        El enlace es geometría de verdad con 0.02 de relieve y el canto
        superior suave: la KEY le deja un filo de luz por arriba y ese pelín de
        volumen es justo lo que separa el dibujo de un clipart."""
        (x1, y1), (x2, y2) = p1, p2
        dx, dy = x2 - x1, y2 - y1
        largo = math.hypot(dx, dy) or 1e-6
        nx, ny = -dy / largo, dx / largo

        desfases = {1: (0.0,), 2: (-0.5, 0.5), 3: (-1.0, 0.0, 1.0)}[orden]
        piezas = []
        for i, d in enumerate(desfases):
            ox, oy = nx * d * separacion, ny * d * separacion
            piezas.append(self.silueta(
                ctx, f'{nombre}_{i}',
                self.barra(x1 + ox, y1 + oy, x2 + ox, y2 + oy, self.ENLACE),
                rol, spec.Z_INTERIOR + z, grosor=0.020, bisel=0.006,
                rugosidad=0.55))
        return piezas

    def _cadena(self, ctx, nombre, vertices, ordenes=None, rol='carbon', z=0.0):
        """Enlaza una lista de vértices en orden. `ordenes` permite dar el
        orden de cada enlace."""
        piezas = []
        for i in range(len(vertices) - 1):
            orden = 1 if ordenes is None else ordenes[i]
            piezas += self._enlace(ctx, f'{nombre}_{i}', vertices[i],
                                   vertices[i + 1], rol, orden, z)
        return piezas

    @staticmethod
    def _zigzag(n, largo=0.30, angulo=109.5, x0=0.0, y0=0.0):
        """Los `n` vértices de una cadena en zigzag con el ángulo de enlace
        pedido. n vértices = n carbonos = el número de la carta."""
        media = math.radians(180 - angulo) / 2.0
        puntos, x, y, arriba = [], x0, y0, True
        for i in range(n):
            puntos.append((x, y))
            x += largo * math.cos(media)
            y += largo * math.sin(media) * (1 if arriba else -1)
            arriba = not arriba
        return puntos

    def _letra(self, ctx, texto, x, y, rol, alto=0.20):
        """Heteroátomo: el glifo en su color CPK, con un halo del color del
        papel por detrás. El halo es la convención tipográfica de siempre —
        hace que las líneas de enlace parezcan detenerse limpiamente en la
        letra — y sin él el dibujo parece mal hecho."""
        halo = self.silueta(ctx, f'halo_{texto}_{x:.2f}_{y:.2f}',
                            self.circulo(x, y, alto * 0.62, 20), 'notebook',
                            spec.Z_INTERIOR + 0.05, grosor=0.008, bisel=0.002)
        rig.poner_material(halo, rig.material_plano(
            f'quim_halo_{texto}_{x:.2f}', self.color('notebook')))

        glifo = rig.texto(f'glifo_{texto}_{x:.2f}_{y:.2f}', texto,
                          self.fuente_numerales, alto, spec.Z_INTERIOR + 0.07,
                          col=ctx.col['INTERIOR'])
        rig.poner_material(glifo, rig.material_plano(
            f'quim_letra_{texto}_{x:.2f}_{y:.2f}', self.color(rol)))
        rig.centrar_en(glifo, x, y)
        return [halo, glifo]

    def _anillo(self, ctx, nombre, cx, cy, radio, lados, giro=0.0, aromatico=False,
                rol='carbon'):
        """Un ciclo regular. Con `aromatico` lleva dentro el círculo del
        sexteto en vez de dobles enlaces alternos."""
        vertices = self.poligono_regular(cx, cy, radio, lados, giro)
        piezas = []
        for i in range(lados):
            piezas += self._enlace(ctx, f'{nombre}_{i}', vertices[i],
                                   vertices[(i + 1) % lados], rol)
        if aromatico:
            piezas.append(self.silueta(
                ctx, f'{nombre}_sexteto',
                self.aro(cx, cy, radio * 0.55, self.ENLACE * 0.85, 40),
                rol, grosor=0.020, bisel=0.006, rugosidad=0.55))
        return piezas, vertices

    # ------------------------------------------------------------------
    # Pinta — el vértice de carbono
    # ------------------------------------------------------------------

    def pip(self, ctx):
        """En notación esquelética el carbono no se dibuja: se sobreentiende en
        el vértice. La pinta es, por tanto, un ÁNGULO DE ENLACE: dos segmentos
        que se encuentran a 109.5°."""
        media = math.radians(180 - 109.5) / 2.0
        brazo = self.LARGO * 0.9
        piezas = self._enlace(ctx, 'ang_a', (0.0, 0.0),
                              (-brazo * math.cos(media), -brazo * math.sin(media)))
        piezas += self._enlace(ctx, 'ang_b', (0.0, 0.0),
                               (brazo * math.cos(media), -brazo * math.sin(media)))
        return rig.unir(piezas, 'pip_vertice')

    # ------------------------------------------------------------------
    # Cartas 1–7 — N carbonos, químicamente exacto
    # ------------------------------------------------------------------

    def cartas_de_numero(self, ctx, n):
        return {
            1: self._metano, 2: self._etanol, 3: self._acetona, 4: self._butano,
            5: self._ciclopentano, 6: self._benceno, 7: self._tolueno,
        }[n](ctx)

    def _centrar_grupo(self, ctx, piezas, nombre, ancho, alto, x=0.0, y=0.0):
        grupo = rig.unir([p for p in piezas if p], nombre)
        rig.encajar_en(grupo, ancho, alto)
        rig.centrar_en(grupo, x, y)
        return grupo

    def _metano(self, ctx):
        """CH₄. **Desviación de la notación esquelética**, y con razón: con un
        solo carbono no hay cadena que dibujar. Se enseña la geometría real en
        bolas y varillas — un carbono con cuatro hidrógenos a los ángulos
        tetraédricos exactos, dos en el plano, uno en cuña hacia el lector y
        otro en trazos hacia atrás. Carta cartel del tema."""
        r = 0.52
        piezas = []
        # Los dos enlaces en el plano.
        for ang in (150, 30):
            a = math.radians(ang)
            piezas += self._enlace(ctx, f'met_{ang}', (0, 0),
                                   (r * math.cos(a), r * math.sin(a)))
        # La cuña hacia el lector: un triángulo que se ensancha.
        piezas.append(self.silueta(ctx, 'met_cuna',
                                   self.barra(0.0, 0.0, 0.0, -r, 0.02, 0.16),
                                   'carbon', grosor=0.024, bisel=0.006))
        # El enlace hacia atrás: cinco trazos que se acortan.
        for i in range(5):
            t = (i + 1) / 5.0
            largo = 0.05 + 0.055 * (1 - t)
            piezas.append(self.silueta(
                ctx, f'met_trazo{i}',
                self.barra(-largo, r * 0.30 + t * 0.34 - 0.30,
                           largo, r * 0.30 + t * 0.34 - 0.30, 0.030),
                'carbon', grosor=0.018, bisel=0.005))
        # Las bolas: el carbono central, oscuro; los cuatro hidrógenos, claros.
        piezas.append(self.silueta(ctx, 'met_C', self.circulo(0, 0, 0.15, 32),
                                   'carbon', spec.Z_INTERIOR + 0.03,
                                   grosor=0.09, bisel=0.03, rugosidad=0.40))
        posiciones = [(r * math.cos(math.radians(150)), r * math.sin(math.radians(150))),
                      (r * math.cos(math.radians(30)), r * math.sin(math.radians(30))),
                      (0.0, -r), (0.0, r * 0.64)]
        for i, (x, y) in enumerate(posiciones):
            bola = self.silueta(ctx, f'met_H{i}', self.circulo(x, y, 0.105, 28),
                                'notebook', spec.Z_INTERIOR + 0.03, grosor=0.07,
                                bisel=0.024, rugosidad=0.35)
            rig.poner_material(bola, rig.material_pbr('quim_H', '#FFFFFF', 0.35))
            piezas.append(bola)

        return self._centrar_grupo(ctx, piezas, 'metano', 1.30, 1.70)

    def _etanol(self, ctx):
        """CH₃CH₂OH. Dos vértices y un OH rojo al final."""
        v = self._zigzag(2, self.LARGO)
        piezas = self._cadena(ctx, 'eta', v)
        fin = (v[-1][0] + self.LARGO * math.cos(math.radians(35.25)),
               v[-1][1] - self.LARGO * math.sin(math.radians(35.25)))
        piezas += self._enlace(ctx, 'eta_o', v[-1], fin)
        piezas += self._letra(ctx, 'OH', fin[0] + 0.12, fin[1] - 0.02, 'oxygen', 0.17)
        return self._centrar_grupo(ctx, piezas, 'etanol', 0.92, 1.14)

    def _acetona(self, ctx):
        """(CH₃)₂CO. Tres carbonos y un carbonilo en el del medio. La carta
        pequeña más satisfactoria: es perfectamente simétrica."""
        v = self._zigzag(3, self.LARGO)
        piezas = self._cadena(ctx, 'ace', v)
        centro = v[1]
        piezas += self._enlace(ctx, 'ace_co', centro,
                               (centro[0], centro[1] + self.LARGO), orden=2)
        piezas += self._letra(ctx, 'O', centro[0], centro[1] + self.LARGO + 0.11,
                              'oxygen', 0.19)
        return self._centrar_grupo(ctx, piezas, 'acetona', 0.84, 1.02)

    def _butano(self, ctx):
        """C₄H₁₀. Cuatro vértices, en horizontal y sin nada más. La expresión
        más pura de la notación esquelética de toda la baraja."""
        v = self._zigzag(4, self.LARGO)
        piezas = self._cadena(ctx, 'but', v)
        return self._centrar_grupo(ctx, piezas, 'butano', 1.10, 0.70)

    def _ciclopentano(self, ctx):
        """C₅H₁₀. El primer ciclo. Se cuenta por las esquinas."""
        piezas, _ = self._anillo(ctx, 'ciclo', 0, 0, 0.46, 5, 90)
        return self._centrar_grupo(ctx, piezas, 'ciclopentano', 0.98, 1.02)

    def _benceno(self, ctx):
        """C₆H₆. El hexágono, con el círculo aromático dentro. La forma más
        famosa de la química, sola en medio de una página de cuaderno."""
        piezas, _ = self._anillo(ctx, 'benc', 0, 0, 0.48, 6, 30, aromatico=True)
        return self._centrar_grupo(ctx, piezas, 'benceno', 1.02, 1.02)

    def _tolueno(self, ctx):
        """C₇H₈. Benceno más un metilo. Cuenta = seis vértices del anillo más
        la punta de la rama."""
        piezas, v = self._anillo(ctx, 'tol', 0, 0, 0.46, 6, 30, aromatico=True)
        origen = v[0]
        rama = (origen[0] + self.LARGO * math.cos(math.radians(30)),
                origen[1] + self.LARGO * math.sin(math.radians(30)))
        piezas += self._enlace(ctx, 'tol_metilo', origen, rama)
        return self._centrar_grupo(ctx, piezas, 'tolueno', 1.10, 1.10)

    # ------------------------------------------------------------------
    # Figuras
    # ------------------------------------------------------------------

    def figura(self, ctx, pieza):
        return {'10': self._cafeina, '11': self._penicilina,
                '12': self._proteina}[pieza](ctx)

    @staticmethod
    def _purina(lado=0.34):
        """Los nueve átomos del núcleo de purina, colocados de verdad.

        Un hexágono y un pentágono regulares COMPARTIENDO una arista, con la
        numeración canónica. No vale poner dos anillos regulares cerca y unir
        lo que caiga: sale una fusión torcida y dos nitrógenos adyacentes que
        no existen en ninguna purina. Aquí la geometría se calcula: el centro
        del pentágono está a su apotema de la arista compartida, y la arista
        compartida es C4–C5.
        """
        cx6, r6 = -lado * 0.9, lado
        seis = {n: (cx6 + r6 * math.cos(math.radians(a)),
                    r6 * math.sin(math.radians(a)))
                for n, a in (('C5', 30), ('C6', 90), ('N1', 150),
                             ('C2', 210), ('N3', 270), ('C4', 330))}

        r5 = lado / (2 * math.sin(math.radians(36)))       # circunradio del pentágono
        apotema = r5 * math.cos(math.radians(36))
        cx5 = seis['C4'][0] + apotema
        cinco = {n: (cx5 + r5 * math.cos(math.radians(a)),
                     r5 * math.sin(math.radians(a)))
                 for n, a in (('N7', 72), ('C8', 0), ('N9', 288))}
        return {**seis, **cinco}

    def _cafeina(self, ctx):
        """1,3,7-trimetilxantina. Núcleo de purina: pirimidindiona fusionada a
        imidazol, con carbonilos en C2 y C6, metilos en N1, N3 y N7, y el doble
        enlace C8=N9. Un guiño al jugador: esto es una baraja, y la cafeína es
        lo que se juega a las dos de la mañana."""
        a = self._purina(0.34)
        piezas = []

        # Los enlaces del esqueleto, con sus órdenes reales.
        aristas = [('N1', 'C2', 1), ('C2', 'N3', 1), ('N3', 'C4', 1),
                   ('C4', 'C5', 2), ('C5', 'C6', 1), ('C6', 'N1', 1),
                   ('C5', 'N7', 1), ('N7', 'C8', 1), ('C8', 'N9', 2),
                   ('N9', 'C4', 1)]
        for de, hasta, orden in aristas:
            piezas += self._enlace(ctx, f'caf_{de}{hasta}', a[de], a[hasta],
                                   orden=orden, separacion=0.045)

        # Los dos carbonilos, apuntando hacia fuera del anillo.
        for carbono, angulo in (('C6', 90), ('C2', 210)):
            base = a[carbono]
            ang = math.radians(angulo)
            fin = (base[0] + 0.28 * math.cos(ang), base[1] + 0.28 * math.sin(ang))
            piezas += self._enlace(ctx, f'caf_co{carbono}', base, fin, orden=2,
                                   separacion=0.045)
            piezas += self._letra(ctx, 'O', fin[0] + 0.05 * math.cos(ang),
                                  fin[1] + 0.05 * math.sin(ang), 'oxygen', 0.15)

        # Los tres metilos: un enlace corto que no lleva letra (es la
        # convención — el extremo suelto ya es un CH₃).
        for nitrogeno, angulo in (('N1', 150), ('N3', 270), ('N7', 72)):
            base = a[nitrogeno]
            ang = math.radians(angulo)
            piezas += self._enlace(
                ctx, f'caf_me{nitrogeno}', base,
                (base[0] + 0.26 * math.cos(ang), base[1] + 0.26 * math.sin(ang)))

        # Las letras de los cuatro nitrógenos, al final para quedar por encima.
        for nitrogeno in ('N1', 'N3', 'N7', 'N9'):
            piezas += self._letra(ctx, 'N', a[nitrogeno][0], a[nitrogeno][1],
                                  'nitrogen', 0.15)

        # Compacta y centrada. La prueba 2 del §7 la suspendía contra la
        # penicilina: las dos son dibujos de línea de tamaño parecido, así que
        # la cafeína se recoge y la penicilina se estira hasta el ancho de la
        # ventana. Es además lo que dice el archivo del tema (0.72 contra 0.82
        # de alto, "y casi todo el ancho").
        return self._centrar_grupo(ctx, piezas, 'cafeina',
                                   1.16, 0.66 * 2 * spec.VENTANA_MEDIO_Y)

    def _penicilina(self, ctx):
        """El beta-lactámico: un ciclo de cuatro muy tenso fusionado a una
        tiazolidina de cinco con su azufre, más una cadena lateral que sale
        hasta un benceno. Tres centros estereogénicos marcados con cuña y con
        trazos, que es lo que mete la tercera dimensión en la notación.

        Escalada: es la molécula que cambió cuánto vive la gente, y es la
        primera carta con estereoquímica."""
        piezas = []
        # Lactama de cuatro.
        cuatro, v4 = self._anillo(ctx, 'pen4', -0.10, 0.20, 0.24, 4, 45)
        # Tiazolidina de cinco, fusionada por la arista de abajo.
        cinco, v5 = self._anillo(ctx, 'pen5', 0.22, -0.14, 0.28, 5, 200)
        piezas += cuatro + cinco
        piezas += self._enlace(ctx, 'pen_fus', v4[2], v5[0])
        piezas += self._letra(ctx, 'S', v5[2][0], v5[2][1], 'sulfur', 0.16)
        piezas += self._letra(ctx, 'N', v4[3][0], v4[3][1], 'nitrogen', 0.15)

        # El carbonilo de la lactama.
        base = v4[1]
        piezas += self._enlace(ctx, 'pen_co', base, (base[0] + 0.06, base[1] + 0.26),
                               orden=2)
        piezas += self._letra(ctx, 'O', base[0] + 0.06, base[1] + 0.38, 'oxygen', 0.14)

        # Cadena lateral hacia la izquierda, hasta un benceno.
        amida = [(-0.34, 0.34), (-0.62, 0.20), (-0.90, 0.34)]
        piezas += self._enlace(ctx, 'pen_am0', v4[0], amida[0])
        piezas += self._cadena(ctx, 'pen_am', amida)
        piezas += self._letra(ctx, 'N', amida[0][0], amida[0][1], 'nitrogen', 0.14)
        piezas += self._enlace(ctx, 'pen_amco', amida[1],
                               (amida[1][0], amida[1][1] - 0.24), orden=2)
        piezas += self._letra(ctx, 'O', amida[1][0], amida[1][1] - 0.34, 'oxygen', 0.13)
        anillo, _ = self._anillo(ctx, 'pen_benc', -1.24, 0.24, 0.26, 6, 30,
                                 aromatico=True)
        piezas += anillo

        # Estereoquímica: una cuña maciza y dos enlaces en trazos.
        piezas.append(self.silueta(ctx, 'pen_cuna',
                                   self.barra(v5[1][0], v5[1][1],
                                              v5[1][0] + 0.20, v5[1][1] - 0.16,
                                              0.02, 0.13),
                                   'carbon', grosor=0.022, bisel=0.006))
        for j, (vx, vy, dx, dy) in enumerate(((v5[3][0], v5[3][1], 0.16, -0.18),
                                              (v4[2][0], v4[2][1], -0.02, -0.22))):
            for i in range(4):
                t = (i + 1) / 4.0
                px, py = vx + dx * t, vy + dy * t
                ancho = 0.035 + 0.045 * t
                piezas.append(self.silueta(
                    ctx, f'pen_hash{j}_{i}',
                    self.barra(px - ancho, py, px + ancho, py, 0.024),
                    'carbon', grosor=0.016, bisel=0.004))

        return self._centrar_grupo(ctx, piezas, 'penicilina',
                                   2 * spec.VENTANA_MEDIO_X,
                                   0.86 * 2 * spec.VENTANA_MEDIO_Y)

    def _proteina(self, ctx):
        """Sin fórmula. Representación en cintas: tres hélices alfa como tubos
        enrollados, una lámina beta de cuatro hebras como flechas planas, y
        lazos que las cosen. Es la única carta del tema con profundidad de
        verdad, y por eso se lee como el rey.

        Escalada: de un átomo, a una molécula pequeña, a una máquina hecha de
        miles."""
        piezas = []

        # Los lazos primero, para que queden por DEBAJO: son el hilo que pasa
        # por todo y lo que convierte tres hélices y cuatro hebras sueltas en
        # un dominio plegado.
        for i, (x1, y1, x2, y2) in enumerate((
                (-0.46, 0.02, -0.18, -0.30), (-0.18, -0.30, 0.10, -0.44),
                (0.30, 0.06, 0.46, -0.24), (-0.34, 0.86, 0.06, 0.90),
                (0.36, 0.62, 0.50, 0.30), (0.24, -0.86, 0.46, -0.62))):
            piezas.append(self.silueta(
                ctx, f'prot_lazo{i}', self.barra(x1, y1, x2, y2, 0.05),
                'carbon', spec.Z_INTERIOR + 0.01, grosor=0.030, bisel=0.008,
                rugosidad=0.55))

        # Tres hélices alfa. Cada una es UNA cinta continua barrida por una
        # senoide, no una pila de anillas: apilar elipses daba una columna de
        # fichas de casino. Con la senoide, la cinta se ve pasar por delante y
        # por detrás del eje, que es exactamente cómo se dibuja una hélice.
        def helice(nombre, cx, cy, alto, amplitud, vueltas, giro, grosor=0.085):
            pasos = 14 * vueltas
            eje = []
            for i in range(pasos + 1):
                t = i / pasos
                eje.append((amplitud * math.sin(2 * math.pi * vueltas * t),
                            -alto / 2 + alto * t))
            # Se engorda el eje por su normal para convertirlo en cinta.
            arriba, abajo = [], []
            for i, (x, y) in enumerate(eje):
                j = min(i + 1, len(eje) - 1)
                k = max(i - 1, 0)
                dx, dy = eje[j][0] - eje[k][0], eje[j][1] - eje[k][1]
                largo = math.hypot(dx, dy) or 1e-6
                nx, ny = -dy / largo, dx / largo
                arriba.append((x + nx * grosor / 2, y + ny * grosor / 2))
                abajo.append((x - nx * grosor / 2, y - ny * grosor / 2))
            cinta = arriba + list(reversed(abajo))
            piezas.append(self.silueta(
                ctx, nombre, self.mover(self.girar(cinta, giro), cx, cy),
                'oxygen', spec.Z_INTERIOR + 0.05, grosor=0.06, bisel=0.020,
                suave=True, rugosidad=0.42))

        helice('prot_h0', -0.44, 0.40, 0.88, 0.135, 4, 8)
        helice('prot_h1', 0.08, 0.56, 0.66, 0.125, 3, -12)
        helice('prot_h2', 0.48, 0.02, 0.72, 0.125, 3, 14)

        # Lámina beta: cuatro hebras paralelas como flechas planas, abajo a la
        # izquierda, formando un bloque. El canto extruido es lo que las separa
        # visualmente de las hélices, que son tubos.
        for s, (x, y0, largo, giro) in enumerate((
                (-0.52, -0.92, 0.62, -7), (-0.30, -0.96, 0.70, 3),
                (-0.08, -0.92, 0.64, -4), (0.14, -0.96, 0.58, 6))):
            ancho, cabeza = 0.048, 0.098
            flecha = [(-ancho, y0), (ancho, y0), (ancho, y0 + largo - 0.13),
                      (cabeza, y0 + largo - 0.13), (0.0, y0 + largo),
                      (-cabeza, y0 + largo - 0.13), (-ancho, y0 + largo - 0.13)]
            piezas.append(self.silueta(
                ctx, f'prot_s{s}', self.mover(self.girar(flecha, giro, 0, y0), x, 0),
                'nitrogen', spec.Z_INTERIOR + 0.035, grosor=0.042, bisel=0.012,
                rugosidad=0.42))

        return self._centrar_grupo(ctx, piezas, 'proteina',
                                   2 * spec.VENTANA_MEDIO_X * 0.94,
                                   0.88 * 2 * spec.VENTANA_MEDIO_Y)

    # ------------------------------------------------------------------
    # Dorso — grafeno
    # ------------------------------------------------------------------

    def dorso(self, ctx):
        rig.carta_base(ctx, rig.material_plano('quim_dorso', self.color('frame')))

        # Cuadrícula al 7 %, de canto a canto.
        paso, mitad = 0.11, 0.0035
        for i in range(-int(spec.MEDIO_X / paso) - 1, int(spec.MEDIO_X / paso) + 2):
            x = i * paso
            self.plana(ctx, f'dgv{i}', [
                (x - mitad, -spec.MEDIO_Y), (x + mitad, -spec.MEDIO_Y),
                (x + mitad, spec.MEDIO_Y), (x - mitad, spec.MEDIO_Y),
            ], 'grid', spec.Z_BG + 0.002, alfa=0.07)
        for i in range(-int(spec.MEDIO_Y / paso) - 1, int(spec.MEDIO_Y / paso) + 2):
            y = i * paso
            self.plana(ctx, f'dgh{i}', [
                (-spec.MEDIO_X, y - mitad), (spec.MEDIO_X, y - mitad),
                (spec.MEDIO_X, y + mitad), (-spec.MEDIO_X, y + mitad),
            ], 'grid', spec.Z_BG + 0.002, alfa=0.07)

        # Panal de hexágonos: grafeno, en la práctica.
        maestro = rig.forma('dorso_hexa',
                            [self.poligono_regular(0, 0, 0.15, 6, 30),
                             self.poligono_regular(0, 0, 0.132, 6, 30)],
                            spec.Z_INTERIOR, 0.0, 0.0, False, ctx.col['INTERIOR'])
        rig.poner_material(maestro, rig.material_plano(
            'quim_dorso_hexa', self.color('chalk'), 0.08))
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

        # Centro: un benceno verde con su círculo aromático.
        anillo = rig.forma('dorso_benceno',
                           [self.poligono_regular(0, 0, 0.42, 6, 30),
                            self.poligono_regular(0, 0, 0.392, 6, 30)],
                           spec.Z_INTERIOR + 0.10, 0.02, 0.006, False,
                           ctx.col['INTERIOR'])
        rig.poner_material(anillo, rig.material_pbr(
            'quim_dorso_benc', self.color('halogen'), 0.5))
        sexteto = self.silueta(ctx, 'dorso_sexteto',
                               self.aro(0, 0, 0.23, 0.026, 44), 'halogen',
                               spec.Z_INTERIOR + 0.10, grosor=0.02, bisel=0.006)
        return [anillo, sexteto]


TEMA = OrganicChemistry()

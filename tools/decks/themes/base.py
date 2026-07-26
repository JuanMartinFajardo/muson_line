# ==========================================================================
# themes/base.py — La clase que hereda cada tema. Se ejecuta dentro de Blender.
# --------------------------------------------------------------------------
# El reparto es el del DECK_SPEC: el spec manda en geometría, cámara, luces,
# marco, exportación y peso; el tema manda en paleta, sujeto y ornamento.
#
# Un tema nuevo son ~150 líneas: declarar la paleta, devolver el objeto de la
# pinta, y modelar las tres figuras. Todo lo demás — el marco, los numerales,
# los siete patrones de pintas, el jitter, el encaje en las cajas máximas — ya
# está resuelto aquí y sale igual en los 64 temas, que es lo que hace legible
# una mano con cuatro temas distintos encima de la mesa.
# ==========================================================================

import math
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import spec   # noqa: E402
import rig    # noqa: E402


class Tema:
    # --- Identidad (la lee también el instalador) ---
    slug = 'sin-nombre'
    nombre = ''
    nombre_en = ''
    descripcion = ''

    # --- Declaraciones del archivo de tema ---
    paleta = {}                  # rol → hex, ≤ 8 + tintes (§6.1)
    fuente_numerales = None      # ruta a un .ttf/.otf/.ttc del sistema
    hex_numeral = '#FFFFFF'
    hex_banda = '#333333'
    rugosidad_banda = 0.5
    hex_filete = None
    potencia_luces = 1.0         # único ajuste libre del rig (§5)
    eje_escalada = ''            # 10 → 11 → 12: en qué crece el rango
    glifos = None                # {'01': '一', …} si los numerales no son latinos

    # ------------------------------------------------------------------
    # Ganchos que implementa cada tema
    # ------------------------------------------------------------------

    def fondo(self, ctx):
        """Capa BG. Plano, degradado de dos paradas o una forma grande y suave;
        nunca ruido ni textura fina (§6.2)."""
        raise NotImplementedError

    def pip(self, ctx):
        """El objeto que se cuenta en las cartas 1–7. Se devuelve UNO; el
        patrón lo duplica en enlazado."""
        raise NotImplementedError

    def figura(self, ctx, pieza):
        """Sota (10), caballo (11) o rey (12). Un sujeto, de pie, sin espejo."""
        raise NotImplementedError

    def dorso(self, ctx):
        """El reverso. Tiene que ser simétrico: girar una carta no puede
        delatar nada."""
        raise NotImplementedError

    def ornamento_esquina(self, ctx, x, y):
        """Opcional: adorno dentro de la caja 8..46 px, detrás del numeral."""
        return None

    def antes_de_render(self, ctx):
        """Último gancho antes de disparar (niebla de calor, halos, capas de
        valor que deben ir por encima de todo lo demás)."""
        return None

    # ------------------------------------------------------------------
    # Construcción de una carta — lo compartido
    # ------------------------------------------------------------------

    def construir(self, ctx):
        if ctx.pieza == 'back':
            # El dorso monta su propio fondo: casi siempre es un campo a
            # sangre distinto del de las caras, y superponerlos deja asomar
            # por debajo las vetas o el degradado de la cara.
            self.dorso(ctx)
        else:
            self.fondo(ctx)
            if ctx.pieza in spec.FIGURAS:
                self.figura(ctx, ctx.pieza)
            else:
                self.cartas_de_numero(ctx, int(ctx.pieza))
            self.marco(ctx)

        self.antes_de_render(ctx)

    # `figura` recibe la pieza; el resto del árbol de construcción no cambia.

    def marco(self, ctx):
        rig.marco(ctx, self.hex_banda, self.rugosidad_banda, self.hex_filete)
        for esquina in ('sup-izq', 'inf-der'):
            x, y = spec.caja_numeral(esquina)
            self.ornamento_esquina(ctx, x, y)
        glifo = (self.glifos or {}).get(ctx.pieza)
        rig.numerales(ctx, ctx.pieza, self.hex_numeral,
                      self.fuente_numerales, glifo, self.hex_numeral)

    def cartas_de_numero(self, ctx, n):
        """Los siete patrones del §4.1, con el jitter que hace que la carta
        parezca hecha a mano y no estampada. Un tema que necesite una
        composición propia sobrescribe este método para su carta y lo dice en
        su archivo — la única condición es que N siga contándose de un vistazo.
        """
        patron = spec.PATRONES[n]
        ancho_max, alto_max = patron['caja']
        espejo = patron.get('espejo_inferior', False) and self.pip_tiene_arriba

        maestro = self.pip(ctx)
        rig.encajar_en(maestro, ancho_max, alto_max)
        rig.aplanar(maestro)

        instancias = []
        for i, (cx, cy) in enumerate(patron['centros']):
            escala = 1.0 + ctx.rnd.uniform(-spec.JITTER_ESCALA, spec.JITTER_ESCALA)
            if i == 2 and n == 5 and 'escala_centro' in patron:
                escala *= patron['escala_centro']
            giro = ctx.rnd.uniform(-spec.JITTER_ROTACION, spec.JITTER_ROTACION)
            if espejo and cy < 0:
                giro += 180.0        # la mitad de abajo, del revés
            copia = rig.instancia(maestro, f'pip_{n}_{i}', (cx, cy),
                                  giro, escala, ctx.col['INTERIOR'])
            instancias.append(copia)

        # El maestro sólo servía de molde.
        bpy.data.objects.remove(maestro, do_unlink=True)
        return instancias

    #: Si la pinta tiene un "arriba" claro, la mitad inferior del 2 se gira
    #: 180°, como en la baraja tradicional (§4.1). Un grano de café no lo tiene.
    pip_tiene_arriba = True

    # ------------------------------------------------------------------
    # Atajos para los temas
    # ------------------------------------------------------------------

    def color(self, rol):
        return self.paleta[rol]

    def plano(self, nombre, rol, alfa=1.0):
        return rig.material_plano(f'{self.slug}_{nombre}', self.color(rol), alfa)

    def pbr(self, nombre, rol, rugosidad=0.5, metalico=0.0, alfa=1.0):
        return rig.material_pbr(f'{self.slug}_{nombre}', self.color(rol),
                                rugosidad, metalico, alfa)

    def silueta(self, ctx, nombre, contornos, rol, z=None, grosor=0.02,
                bisel=0.004, suave=False, alfa=1.0, rugosidad=0.65, capa='INTERIOR'):
        """Una forma rellena con material, en una línea. El recurso más
        rentable del sistema: pesa poquísimo en webp y el bisel le da justo la
        luz que necesita para no parecer pegada encima del fondo.

        Con `alfa < 1` el material pasa a ser plano (emisión + transparencia):
        una silueta translúcida tiene que valer su hex exacto, no lo que la
        iluminación decida.
        """
        obj = rig.forma(f'{self.slug}_{nombre}', contornos,
                        spec.Z_INTERIOR if z is None else z,
                        grosor, bisel, suave, ctx.col[capa])
        material = (rig.material_plano(f'{self.slug}_{nombre}_m', self.color(rol), alfa)
                    if alfa < 1.0 else
                    rig.material_pbr(f'{self.slug}_{nombre}_m', self.color(rol), rugosidad))
        rig.poner_material(obj, material)
        return obj

    def plana(self, ctx, nombre, contornos, rol, z=None, alfa=1.0, suave=False,
              capa='BG'):
        """Igual, pero sin relieve y con color exacto. Para el fondo y para los
        rótulos: lo que no debe capturar luz no debe tener grosor."""
        obj = rig.forma(f'{self.slug}_{nombre}', contornos,
                        (spec.Z_BG + 0.002) if z is None else z,
                        0.0, 0.0, suave, ctx.col[capa])
        rig.poner_material(obj, rig.material_plano(
            f'{self.slug}_{nombre}_m', self.color(rol), alfa))
        return obj

    # --- Generadores de contornos que usan varios temas ---

    @staticmethod
    def circulo(cx, cy, radio, segmentos=32):
        return [(cx + radio * math.cos(2 * math.pi * i / segmentos),
                 cy + radio * math.sin(2 * math.pi * i / segmentos))
                for i in range(segmentos)]

    @staticmethod
    def elipse(cx, cy, rx, ry, segmentos=32, giro=0.0):
        puntos = []
        c, s = math.cos(math.radians(giro)), math.sin(math.radians(giro))
        for i in range(segmentos):
            a = 2 * math.pi * i / segmentos
            x, y = rx * math.cos(a), ry * math.sin(a)
            puntos.append((cx + x * c - y * s, cy + x * s + y * c))
        return puntos

    @staticmethod
    def anillo_puntos(cx, cy, radio, grosor, segmentos=48):
        """Contornos exterior e interior de un aro, listos para malla_anillo."""
        fuera = Tema.circulo(cx, cy, radio + grosor / 2, segmentos)
        dentro = Tema.circulo(cx, cy, radio - grosor / 2, segmentos)
        return fuera, dentro

    @staticmethod
    def barra(x1, y1, x2, y2, grosor, grosor2=None):
        """Rectángulo de extremo a extremo, opcionalmente ahusado: el enlace
        químico, el asta de la lanza, el aspa del molino."""
        g2 = grosor if grosor2 is None else grosor2
        dx, dy = x2 - x1, y2 - y1
        largo = math.hypot(dx, dy) or 1e-6
        ux, uy = -dy / largo, dx / largo
        return [(x1 + ux * grosor / 2, y1 + uy * grosor / 2),
                (x2 + ux * g2 / 2, y2 + uy * g2 / 2),
                (x2 - ux * g2 / 2, y2 - uy * g2 / 2),
                (x1 - ux * grosor / 2, y1 - uy * grosor / 2)]

    @staticmethod
    def arco(cx, cy, radio, grosor, de=0.0, a=360.0, segmentos=32):
        """Banda curva: la onda del agua, el aro del sello, la ceja del
        tejado. Con de/a completos sale un aro cerrado."""
        de_r, a_r = math.radians(de), math.radians(a)
        fuera, dentro = [], []
        for i in range(segmentos + 1):
            ang = de_r + (a_r - de_r) * i / segmentos
            c, s = math.cos(ang), math.sin(ang)
            fuera.append((cx + (radio + grosor / 2) * c, cy + (radio + grosor / 2) * s))
            dentro.append((cx + (radio - grosor / 2) * c, cy + (radio - grosor / 2) * s))
        return fuera + list(reversed(dentro))

    @staticmethod
    def aro(cx, cy, radio, grosor, segmentos=48):
        """Aro completo como dos contornos (forma + agujero). Se pasa tal cual
        a `silueta`, que aplica la regla par-impar."""
        return [Tema.circulo(cx, cy, radio + grosor / 2, segmentos),
                Tema.circulo(cx, cy, radio - grosor / 2, segmentos)]

    @staticmethod
    def poligono_regular(cx, cy, radio, lados, giro=0.0):
        return [(cx + radio * math.cos(math.radians(giro) + 2 * math.pi * i / lados),
                 cy + radio * math.sin(math.radians(giro) + 2 * math.pi * i / lados))
                for i in range(lados)]

    @staticmethod
    def escalar(puntos, factor, cx=0.0, cy=0.0):
        return [(cx + (x - cx) * factor, cy + (y - cy) * factor) for x, y in puntos]

    @staticmethod
    def mover(puntos, dx, dy):
        return [(x + dx, y + dy) for x, y in puntos]

    @staticmethod
    def girar(puntos, grados, cx=0.0, cy=0.0):
        c, s = math.cos(math.radians(grados)), math.sin(math.radians(grados))
        return [(cx + (x - cx) * c - (y - cy) * s,
                 cy + (x - cx) * s + (y - cy) * c) for x, y in puntos]

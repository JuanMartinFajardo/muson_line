# bot_ml_4.py — Bots de Mus a 4 jugadores (2v2).
#
# Fase 0 del plan de wiki/Bot-AI-4p-Roadmap.md: un bot heurístico jugable HOY,
# sin ML, detrás de la interfaz definitiva. Lo importante de este archivo no es
# la heurística (que es reemplazable) sino el CONTRATO:
#
#     MusBotBase.obtener_accion(vista) -> None | (accion, cantidad, meta)
#
# donde `vista` es el diccionario de observación local al asiento que produce
# PartidaMus4.vista(seat) — nunca el motor entero. La heurística de hoy, el bot
# de Deep CFR de la Fase 2 y el bot paramétrico de la Fase 4 implementan esa
# misma firma, así que el servidor no vuelve a cambiar.
#
# NO se toca bot_ml.py (bot de 2 jugadores): solo se reutilizan sus tablas
# precalculadas (mus_data.json) y mus_discard_chooser.py, que son válidas como
# aproximación por mano también a 4 jugadores.

import json
import os
import random

from mus_discard_chooser import get_best_discard_strategy


# ==========================================================================
# Tablas precalculadas (mismas que usa el bot de 2p)
# --------------------------------------------------------------------------
# `probabilities[clave] = [G,C,P,J (mano), G,C,P,J (postre)]` es la probabilidad
# de ganar cada lance contra UNA mano rival aleatoria; `expected_values[clave] =
# [ev_mano, ev_postre]`. Se cargan una vez por proceso y se comparten entre
# todas las salas (igual que el modelo del bot de 2p).
# ==========================================================================
RUTA_TABLAS = os.path.join('learn', 'global_variables', 'mus_data.json')

_tablas = None


def cargar_tablas():
    """{'expected_values':…, 'probabilities':…, 'meta_constants':…} cacheado."""
    global _tablas
    if _tablas is None:
        datos = {}
        if os.path.exists(RUTA_TABLAS):
            try:
                with open(RUTA_TABLAS, 'r', encoding='utf-8') as f:
                    datos = json.load(f)
                print("🧠 [BOT4] Tablas de EV/probabilidades cargadas.")
            except Exception as e:
                print(f"⚠️ [BOT4] No se pudo leer {RUTA_TABLAS}: {e}")
        else:
            print(f"⚠️ [BOT4] No se encontró {RUTA_TABLAS}: el bot jugará a ciegas.")
        _tablas = {
            'expected_values': datos.get('expected_values', {}),
            'probabilities': datos.get('probabilities', {}),
            'meta_constants': datos.get('meta_constants', {}),
        }
    return _tablas


# ==========================================================================
# Personalidades (Roadmap #12). Los campos a None se re-tiran cada mano, que es
# el comportamiento "equilibrado" de siempre. `bias_apuesta` desplaza los
# umbrales de apuesta: positivo = más agresivo (apuesta y paga con menos mano).
# ==========================================================================
PERSONALIDADES = {
    'equilibrado':  None,
    'agresivo':     {'musero': 0.3, 'bluffer': 0.35, 'aleatorio': 0.2, 'fish': 0.1, 'bias_apuesta': +0.15},
    'conservador':  {'musero': 0.8, 'bluffer': 0.05, 'aleatorio': 0.1, 'fish': 0.05, 'bias_apuesta': -0.15},
    'musero':       {'musero': 1.2, 'bluffer': 0.15, 'aleatorio': 0.2, 'fish': 0.1, 'bias_apuesta': 0.0},
    'caotico':      {'musero': None, 'bluffer': 0.5, 'aleatorio': 0.6, 'fish': 0.4, 'bias_apuesta': 0.0},
}

PERSONALIDAD_POR_DEFECTO = 'equilibrado'


class MusBotBase:
    """Interfaz que implementan TODOS los bots de 4 jugadores.

    El servidor solo conoce esto. `obtener_accion` recibe la vista del asiento
    y devuelve `None` (nada que hacer ahora) o una terna:

        (accion, cantidad, meta)

      * `accion`: 'repartir' | 'mus' | 'no_mus' | 'descartar' | 'pedrete' |
                  'pasar' | 'envidar' | 'subir' | 'ver' | 'nover' | 'ordago' |
                  'listo_siguiente_ronda'
      * `cantidad`: puntos del envite/subida (0 en el resto).
      * `meta`: extras de la jugada e información de diagnóstico. Para
        'descartar' lleva `indices`; siempre lleva `personalidad` y la fuerza
        percibida, útil para los logs y para el análisis de la Fase 5.
    """

    def __init__(self, sid, asiento, personalidad=PERSONALIDAD_POR_DEFECTO):
        self.sid = sid
        self.asiento = asiento
        self.personalidad = personalidad if personalidad in PERSONALIDADES else PERSONALIDAD_POR_DEFECTO

    def obtener_accion(self, vista):
        raise NotImplementedError


# ==========================================================================
# SmartBot4 v1 — heurístico
# ==========================================================================

# Índice del lance dentro del array de probabilidades de la tabla.
IDX_LANCE = {'Grande': 0, 'Chica': 1, 'Pares': 2, 'Juego': 3, 'Punto': 3}

ACCIONES_APUESTA = ('pasar', 'envidar', 'subir', 'ver', 'nover', 'ordago')

# Umbral de fuerza (probabilidad estimada de que gane MI EQUIPO el lance) a
# partir del cual se abre apuesta. Pares y Juego son algo más baratos de abrir
# porque el lance ya viene filtrado: solo llega quien tiene la jugada.
UMBRAL_ENVITE = {'Grande': 0.62, 'Chica': 0.62, 'Pares': 0.58, 'Juego': 0.58, 'Punto': 0.62}
UMBRAL_SUBIR = 0.78            # subir sobre la apuesta del rival
UMBRAL_ORDAGO_LANZAR = 0.99    # mano cerrada: se escala un envite a órdago
UMBRAL_ORDAGO_ACEPTAR = 0.75   # aceptar un órdago se juega la partida entera
MARGEN_VER = 0.04              # colchón sobre el pot-odds puro (no pagar 50/50)
ORDAGO_CIERRE = 38             # puntos_equipo + bote a partir de los cuales
                               # ganar el lance ya gana la partida


class SmartBot4(MusBotBase):
    """Bot heurístico de 4 jugadores. Sin red neuronal.

    - Mus y descarte: tablas de EV precalculadas (`mus_data.json` +
      `mus_discard_chooser`), exactamente como el bot de 2p.
    - Apuestas: reglas sobre la probabilidad estimada de que gane el equipo el
      lance, con pot-odds para pagar y órdago al cierre de la partida.
    """

    def __init__(self, sid, asiento, personalidad=PERSONALIDAD_POR_DEFECTO):
        super().__init__(sid, asiento, personalidad)
        tablas = cargar_tablas()
        self.expected_values = tablas['expected_values']
        self.probabilities = tablas['probabilities']
        self.meta_variables = self._tirar_meta()
        self._ronda_vista = None

    # ---------- personalidad ----------
    def _tirar_meta(self):
        """Valores de la personalidad para esta mano.

        Los campos fijos del preset mandan; los que valen None (o el preset
        entero, en 'equilibrado') se re-tiran cada mano, que es lo que hace
        impredecible al bot de 2p."""
        base = {
            'musero': random.random(),
            'bluffer': min(0.35, random.random()),
            'aleatorio': min(0.4, random.random()),
            'fish': random.random(),
            'bias_apuesta': 0.0,
        }
        preset = PERSONALIDADES.get(self.personalidad)
        if preset:
            for clave, valor in preset.items():
                if valor is not None:
                    base[clave] = valor
        return base

    def _quizas_nueva_mano(self, vista):
        ronda = vista['meta']['ronda_n']
        if ronda != self._ronda_vista:
            self._ronda_vista = ronda
            self.meta_variables = self._tirar_meta()

    # ---------- lectura de la mano ----------
    def _clave_mano(self, vista):
        valores = vista['A_propio']['valores_mus']
        if len(valores) != 4:
            return None
        return str(sorted(valores, reverse=True))

    def _idx_posicion(self, vista):
        """0 = mano (gana los empates), 1 = resto. La tabla es de 2 jugadores:
        aproximamos "ser mano" por estar el primero en el orden de la mesa."""
        return 0 if vista['A_propio']['dist_mano'] == 0 else 1

    def _ev_mano(self, vista):
        clave = self._clave_mano(vista)
        if not clave:
            return 0.0
        return self.expected_values.get(clave, [0.0, 0.0])[self._idx_posicion(vista)]

    def _prob_vs_uno(self, vista, lance):
        """Probabilidad de ganar el lance contra UNA mano rival cualquiera."""
        clave = self._clave_mano(vista)
        if not clave or lance not in IDX_LANCE:
            return 0.5
        probs = self.probabilities.get(clave)
        if not probs or len(probs) < 8:
            return 0.5
        return probs[IDX_LANCE[lance] + 4 * self._idx_posicion(vista)]

    def _en_juego(self, vista, lance):
        """(rivales que disputan el lance, ¿mi compañero lo disputa?).

        En Pares y Juego las declaraciones son públicas (el motor las canta al
        entrar en el lance), así que se usan tal cual: un rival que ha dicho
        "no pares" ya no compite."""
        otros = vista['B_publico']['otros']
        rivales = [o for o in otros if not o['es_companero']]
        companero = next((o for o in otros if o['es_companero']), None)

        if lance == 'Pares':
            n = sum(1 for o in rivales if o['pares_dec'] is not False)
            comp = bool(companero and companero['pares_dec'] is not False)
        elif lance == 'Juego':
            n = sum(1 for o in rivales if o['juego_dec'] is not False)
            comp = bool(companero and companero['juego_dec'] is not False)
        else:
            # Grande, Chica y Punto los disputa todo el mundo.
            n = len(rivales)
            comp = True
        return n, comp

    def _fuerza(self, vista, lance):
        """Probabilidad estimada de que MI EQUIPO gane el lance, con el sesgo de
        personalidad ya aplicado.

        Aproximación (documentada a propósito, es lo que sustituirá el encoder
        de la Fase 2): mi mano gana a los `k` rivales con p**k, y el compañero
        —cuya mano no veo— es el mejor de los k+1 desconocidos con probabilidad
        1/(k+1). El equipo gana si gana cualquiera de los dos. Con una mano
        mediana (p=0.5) y dos rivales sale ~0.5, que es la referencia correcta.
        """
        k, comp_juega = self._en_juego(vista, lance)
        if k == 0:
            fuerza = 1.0            # nadie disputa: el lance ya es nuestro
        else:
            p_yo = self._prob_vs_uno(vista, lance) ** k
            p_comp = (1.0 / (k + 1)) if comp_juega else 0.0
            fuerza = 1.0 - (1.0 - p_yo) * (1.0 - p_comp)

        # Farol y ruido: la misma forma que en el bot de 2p, reescalados al
        # rango [0,1] de una probabilidad.
        impulso = self.meta_variables['bluffer'] * random.random() * 0.25
        ruido = self.meta_variables['aleatorio'] * random.uniform(-1.0, 1.0) * 0.10
        return min(1.0, max(0.0, fuerza + impulso + ruido))

    # ---------- decisiones ----------
    def _decidir_mus(self, vista):
        """Cortar el mus cuando el EV de la mano supera el umbral `musero`."""
        ev = self._ev_mano(vista)
        impulso = self.meta_variables['bluffer'] * random.random()
        ruido = self.meta_variables['aleatorio'] * random.uniform(-1.0, 1.0) * 0.2
        return 'no_mus' if (ev + impulso + ruido) >= self.meta_variables['musero'] else 'mus'

    def _indices_descarte(self, vista):
        valores = vista['A_propio']['valores']
        if not valores:
            return []
        resultado = get_best_discard_strategy(
            my_hand=valores,
            ev_lookup_table=self.expected_values,
            am_i_mano=(self._idx_posicion(vista) == 0),
        )
        mejor = resultado.get('best_action') or {}
        indices = [int(i) for i in (mejor.get('discard') or [])]
        if indices:
            return indices

        # Quien ha pedido mus está obligado a tirar al menos una carta: cogemos
        # el mejor descarte de una sola carta de la misma tabla de evaluaciones
        # (viene ordenada por EV descendente).
        norm = [12 if v == 3 else 1 if v == 2 else v for v in valores]
        for opcion in resultado.get('all_evaluations', []):
            tirados = opcion.get('discarded') or []
            if len(tirados) == 1 and tirados[0] in norm:
                return [norm.index(tirados[0])]
        return [random.randrange(len(valores))]

    def _decidir_apuesta(self, vista):
        legales = vista['meta']['acciones_legales']
        lance = vista['B_publico']['lance'] or 'Grande'
        ap = vista['C_apuestas']
        marcador = vista['D_marcador']
        bias = self.meta_variables['bias_apuesta']
        fuerza = self._fuerza(vista, lance)
        # Para el órdago "de museo" miramos MI mano contra el campo entero
        # (probabilidad de ganar a los `k` rivales), no la fuerza del equipo:
        # contar con la mano del compañero, que no veo, inflaría el número justo
        # donde más caro sale equivocarse. El roadmap pide "percentil > 0.97";
        # medido contra un solo rival eso lo cumple ~1 mano de cada 30 y la
        # partida se acababa en 3 manos de órdago, así que se mide contra los
        # rivales que de verdad disputan el lance.
        k_rivales, _ = self._en_juego(vista, lance)
        percentil = self._prob_vs_uno(vista, lance) ** max(1, k_rivales)

        def salida(accion, cantidad=0):
            return (accion, cantidad, {
                'personalidad': self.personalidad,
                'lance': lance,
                'fuerza': round(fuerza, 4),
                'percentil': round(percentil, 4),
            })

        opciones = [a for a in legales if a in ACCIONES_APUESTA]
        if not opciones:
            return None
        # Sin la jugada del lance (pares/juego) o con el deje forzado, el motor
        # deja una sola salida: no hay nada que decidir.
        if len(opciones) == 1:
            return salida(opciones[0])

        # --- Nos han echado un órdago: se juega la partida entera ---
        if ap['es_ordago'] and 'ver' in opciones:
            if 'nover' not in opciones:
                return salida('ver')       # el deje ya daría la partida al rival
            return salida('ver' if fuerza >= UMBRAL_ORDAGO_ACEPTAR - bias else 'nover')

        # --- Nos han envidado ---
        if 'ver' in opciones:
            pot = ap['bote_lance'] + ap['coste_ver']
            if pot > 0:
                # Pot-odds: pagar sale a cuenta si p*(pot) - (1-p)*(pot) >= -deje.
                umbral_ver = (pot - ap['deje']) / (2.0 * pot) + MARGEN_VER - bias
            else:
                umbral_ver = 0.5 - bias
            # Con una mano cerrada, el órdago sí es una subida de verdad: hay
            # una apuesta viva que escalar.
            if 'ordago' in opciones and percentil >= UMBRAL_ORDAGO_LANZAR:
                return salida('ordago')
            if 'subir' in opciones and fuerza >= UMBRAL_SUBIR - bias:
                return salida('subir', 2)
            if fuerza >= umbral_ver or 'nover' not in opciones:
                return salida('ver')
            return salida('nover')

        # --- Abrimos el lance ---
        umbral = UMBRAL_ENVITE.get(lance, 0.62) - bias
        if fuerza >= umbral:
            # Órdago si la partida ya está sentenciada (ganar el lance nos deja
            # a tiro y arriesgamos poco) o con mano de museo. En el final de
            # partida se exige mano de verdad, no solo pasar el umbral de envite.
            cierra_partida = ((marcador['puntos_equipo'] + ap['bote_lance'] + 2) >= ORDAGO_CIERRE
                              and fuerza >= 0.6)
            if 'ordago' in opciones and cierra_partida:
                return salida('ordago')
            if 'envidar' in opciones:
                return salida('envidar', 2)
            if 'ordago' in opciones:
                return salida('ordago')    # ya no cabe un envite normal
        return salida('pasar') if 'pasar' in opciones else salida(opciones[0])

    # ---------- entrada única ----------
    def obtener_accion(self, vista):
        """Única puerta de entrada del servidor. Ver MusBotBase."""
        self._quizas_nueva_mano(vista)
        legales = vista['meta']['acciones_legales']
        if not legales:
            return None

        base_meta = {'personalidad': self.personalidad}

        if 'pedrete' in legales:
            return ('pedrete', 0, base_meta)
        if 'listo_siguiente_ronda' in legales:
            return ('listo_siguiente_ronda', 0, base_meta)
        if 'descartar' in legales:
            indices = self._indices_descarte(vista)
            return ('descartar', 0, dict(base_meta, indices=indices))
        if 'repartir' in legales:
            return ('repartir', 0, base_meta)
        if 'mus' in legales:
            decision = self._decidir_mus(vista)
            return (decision, 0, dict(base_meta, ev=round(self._ev_mano(vista), 3)))
        if vista['meta']['fase'] == 'apuestas':
            return self._decidir_apuesta(vista)
        return None

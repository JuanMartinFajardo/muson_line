# mus_env4.py — Gimnasio de apuestas para 4 jugadores (2v2). Fase 1.5.
#
# Análogo de mus_env.py sobre PartidaMus4, con tres diferencias que son justo
# las correcciones que pedía el audit (wiki/Bot-AI-4p-ML-Strategy.md §3):
#
#   1. La observación es el CONTRATO de la Fase 0 (`PartidaMus4.vista(seat)`)
#      codificado por encoder.py — el mismo código que corre al servir. Sin dos
#      codificaciones no hay skew entrenamiento/servicio que valga (§3.4).
#   2. La recompensa es el DELTA de puntos de la ronda por equipo, no el
#      marcador absoluto: el offset de la puntuación inicial aleatoria se
#      cancelaba dentro de los regrets pero gastaba capacidad y metía varianza
#      (§3.2). La Fase 2 sustituirá el delta por ΔV(marcador) (§6.2).
#   3. El adelanto hasta las apuestas no inventa marcadores uniformes: muestrea
#      estados REALES de los logs v2 (§3.4 / Fase 1.5). Sin logs todavía, cae a
#      un prior explícito, y se dice cuál.
#
# El mus y los descartes siguen siendo heurísticos (tablas de EV), igual que en
# 2p; entran en el árbol aprendido en la generación 4g3 (§6.5).

import json
import os
import random

import numpy as np

from mus_mecanicas_4 import PartidaMus4
from mus_discard_chooser import get_best_discard_strategy
from bot_ml_4 import cargar_tablas
import encoder

RUTA_DISTRIBUCION = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 'learn', 'global_variables', 'estados_4p.json')


# ==========================================================================
# Muestreo de estados reales
# ==========================================================================
class DistribucionEstados:
    """De dónde salen el marcador y las rondas de mus con las que arranca cada
    traversal.

    El gimnasio de 2p arrancaba con `random.randint(0, 39)` por jugador, lo que
    entrena al bot sobre marcadores que en una partida real casi no se dan (26-3
    es raro; 0-0 y los finales apretados son constantes). Aquí se muestrean
    tripletas (puntos_A, puntos_B, rondas_mus) observadas de verdad en los logs
    v2. Mientras no haya corpus se usa el prior de abajo — explícito, para que
    nadie confunda "sin datos" con "medido"."""

    def __init__(self, muestras=None, origen='prior'):
        self.muestras = muestras or []
        self.origen = origen

    # -------- prior mientras no hay logs --------
    @staticmethod
    def prior():
        """Marcadores plausibles sin datos: la mayoría de las manos se juegan
        pronto en la partida, y las rondas de mus se concentran en 0–2."""
        muestras = []
        for _ in range(4000):
            a = min(39, int(abs(random.gauss(0, 13))))
            b = min(39, int(abs(random.gauss(0, 13))))
            r = random.choices([0, 1, 2, 3, 4], weights=[38, 30, 18, 9, 5])[0]
            muestras.append((a, b, r))
        return DistribucionEstados(muestras, origen='prior')

    # -------- extracción desde los logs v2 --------
    @staticmethod
    def desde_logs(dir_logs=None, limite=None):
        """Recorre los logs v2 y anota el estado con el que EMPIEZA cada mano."""
        from mus_log import listar, leer
        muestras = []
        rutas = listar(dir_logs)
        if limite:
            rutas = rutas[:limite]
        for ruta in rutas:
            eventos = leer(ruta)
            if not eventos or eventos[0].get('mode') != '4p':
                continue
            puntos = [0, 0]
            descartes = 0
            en_ronda = False
            for ev in eventos:
                t = ev.get('t')
                if t == 'deal':
                    # El marcador vigente al repartir es el estado de entrada.
                    descartes = 0
                    en_ronda = True
                    inicio = (puntos[0], puntos[1])
                elif t == 'a' and ev.get('a') == 'descarte':
                    descartes += 1
                elif t == 'eor' and en_ronda:
                    muestras.append((inicio[0], inicio[1], min(4, descartes // 4)))
                    puntos = list(ev.get('scores') or puntos)
                    if puntos[0] >= 40 or puntos[1] >= 40:
                        puntos = [0, 0]      # empieza otra partida del match
                    en_ronda = False
        if not muestras:
            return DistribucionEstados.prior()
        return DistribucionEstados(muestras, origen=f'logs v2 ({len(muestras)} manos)')

    # -------- caché en disco --------
    @staticmethod
    def cargar(ruta=RUTA_DISTRIBUCION, refrescar=False, dir_logs=None):
        if not refrescar and os.path.exists(ruta):
            try:
                with open(ruta, 'r', encoding='utf-8') as f:
                    datos = json.load(f)
                return DistribucionEstados([tuple(m) for m in datos['muestras']],
                                           origen=datos.get('origen', ruta))
            except Exception:
                pass
        dist = DistribucionEstados.desde_logs(dir_logs)
        dist.guardar(ruta)
        return dist

    def guardar(self, ruta=RUTA_DISTRIBUCION):
        try:
            os.makedirs(os.path.dirname(ruta), exist_ok=True)
            with open(ruta, 'w', encoding='utf-8') as f:
                json.dump({'origen': self.origen,
                           'muestras': [list(m) for m in self.muestras]}, f)
        except Exception as e:
            print(f"⚠️ [ENV4] no se pudo guardar la distribución: {e}")

    def muestrear(self):
        if not self.muestras:
            return (0, 0, 0)
        return random.choice(self.muestras)


# ==========================================================================
# El entorno
# ==========================================================================
class MusBettingEnv4:
    """Un traversal = una mano de 2v2 desde el primer envite hasta el recuento."""

    def __init__(self, distribucion=None, al_mejor_de=3):
        self.dist = distribucion if distribucion is not None else DistribucionEstados.prior()
        self.al_mejor_de = al_mejor_de
        tablas = cargar_tablas()
        self.expected_values = tablas['expected_values']
        self.partida = None
        self._puntos_iniciales = {'A': 0, 'B': 0}

    # ---------------- ciclo de vida ----------------
    def reset(self):
        self.partida = PartidaMus4()
        self.partida.al_mejor_de = self.al_mejor_de
        self.partida.iniciar_ronda()           # arranca con NullLogger: no escribe
        self._adelantar_hasta_apuestas()
        return self.observacion()

    def _adelantar_hasta_apuestas(self):
        p = self.partida
        pa, pb, rondas = self.dist.muestrear()
        p.puntos['A'], p.puntos['B'] = pa, pb

        guardas = 0
        while p.fase in ('espera_reparto', 'mus', 'descarte'):
            guardas += 1
            if guardas > 200:
                raise RuntimeError("el adelanto hasta apuestas no converge")

            if p.fase == 'espera_reparto':
                p.repartir_inicial()

            elif p.fase == 'mus':
                seat = p.turno_de
                # Se fuerza el número de rondas de mus muestreado: mientras no se
                # llegue, todo el mundo da mus; a partir de ahí, corta el primero
                # cuya mano lo pida (o el que hable, si ninguna lo pide).
                if p.rondas_mus < rondas:
                    p.cantar_mus(seat, True)
                else:
                    p.cantar_mus(seat, not self._quiere_mus(seat))

            elif p.fase == 'descarte':
                for s in range(4):
                    if not p.estado[s]['descartes_listos']:
                        p.procesar_descarte(s, self._indices_descarte(s))

            # Los avisos de "nadie tiene pares" / "juego a punto" los consume el
            # servidor con su temporizador; aquí, al momento.
            while p.fase == 'apuestas' and p.mensaje_transicion is not None:
                p.mensaje_transicion = None
                p.preparar_subfase()

        self._puntos_iniciales = dict(p.puntos)

    # ---------------- heurísticas de mus/descarte (idénticas a las de 2p) ----------------
    def _clave(self, seat):
        from mus_core import get_valores_mus
        cartas = self.partida.estado[seat]['cartas']
        if len(cartas) != 4:
            return None
        return str(sorted(get_valores_mus(cartas), reverse=True))

    def _quiere_mus(self, seat):
        """True = cortar el mus (la mano rinde). Mismo umbral que mus_env.py."""
        clave = self._clave(seat)
        if not clave:
            return False
        idx = 0 if self.partida._dist_mano(seat) == 0 else 1
        ev = self.expected_values.get(clave, [0.0, 0.0])[idx]
        return ev > 0.5

    def _indices_descarte(self, seat):
        cartas = self.partida.estado[seat]['cartas']
        resultado = get_best_discard_strategy(
            my_hand=[c['valor'] for c in cartas],
            ev_lookup_table=self.expected_values,
            am_i_mano=(self.partida._dist_mano(seat) == 0))
        mejor = resultado.get('best_action') or {}
        indices = [int(i) for i in (mejor.get('discard') or [])]
        # Quien ha pedido mus está obligado a tirar al menos una carta.
        return indices or [random.randrange(len(cartas))]

    # ---------------- interfaz de juego ----------------
    def observacion(self):
        """Vista del asiento al que le toca hablar (None si la mano acabó)."""
        if self.partida.fase != 'apuestas':
            return None
        return self.partida.vista(self.partida.turno_de)

    def vector(self, vista=None):
        vista = vista if vista is not None else self.observacion()
        return None if vista is None else encoder.codificar(vista)

    def seat_actual(self):
        return self.partida.turno_de

    def acciones_legales(self):
        if self.partida.fase != 'apuestas':
            return []
        return [a for a in self.partida.acciones_legales(self.partida.turno_de)
                if a in encoder.ACCION_A_IDX]

    def step(self, accion, cantidad=None):
        """Aplica la acción del asiento en turno. Devuelve (recompensas, done).

        `recompensas` son los puntos GANADOS EN ESTA MANO por cada equipo (delta,
        no marcador): la corrección §3.2 del audit.

        A diferencia de mus_env.MusBettingEnv (2p), `step` NO devuelve la
        observación: construir el dict de `vista()` en cada paso costaba un tercio
        del tiempo de travesía y CFR casi nunca lo necesita en ese momento (en los
        nodos muestreados basta con las acciones legales). Quien la quiera llama a
        `observacion()` / `vector()`, que es justo donde hace falta."""
        if cantidad is None:
            cantidad = 2 if accion in ('envidar', 'subir') else 0
        seat = self.partida.turno_de
        self.partida.accion_apuesta(seat, accion, cantidad)

        while self.partida.fase == 'apuestas' and self.partida.mensaje_transicion is not None:
            self.partida.mensaje_transicion = None
            self.partida.preparar_subfase()

        done = (self.partida.fase == 'recuento')
        recompensas = {'A': 0, 'B': 0}
        if done:
            self.partida.calcular_recuento()
            recompensas = {eq: self.partida.puntos[eq] - self._puntos_iniciales[eq]
                           for eq in ('A', 'B')}
        return recompensas, done

    def utilidad_equipo(self, equipo):
        """Utilidad terminal del equipo, normalizada y de suma cero.

        Es el pago que consume CFR: (mis puntos − los suyos) / 40. En la Fase 2
        esto pasa a ser ΔV(marcador) del shaping de valor de match (§6.2)."""
        rival = 'B' if equipo == 'A' else 'A'
        d_yo = self.partida.puntos[equipo] - self._puntos_iniciales[equipo]
        d_rival = self.partida.puntos[rival] - self._puntos_iniciales[rival]
        return (d_yo - d_rival) / 40.0

    def fork(self, copiador=None):
        """Bifurca el universo (CFR explora cada acción del traversante).

        Copia plana: ver PartidaMus4.fork(). Aquí es donde se gana el orden de
        magnitud del gate de la Fase 1.4. La configuración (distribución de
        estados, tablas de EV) se COMPARTE: es de solo lectura.

        `copiador` existe solo para el benchmark: pasarle `copy.deepcopy` copia
        el motor a la antigua dejando todo lo demás igual."""
        otro = object.__new__(MusBettingEnv4)
        otro.dist = self.dist
        otro.al_mejor_de = self.al_mejor_de
        otro.expected_values = self.expected_values
        otro.partida = (copiador(self.partida) if copiador is not None
                        else self.partida.fork())
        otro._puntos_iniciales = self._puntos_iniciales
        return otro

    clone = fork


if __name__ == '__main__':
    import time

    env = MusBettingEnv4()
    print(f"distribución de estados: {env.dist.origen}")
    t0 = time.time()
    n, decisiones = 2000, 0
    for _ in range(n):
        env.reset()
        done = False
        while not done:
            legales = env.acciones_legales()
            _, done = env.step(random.choice(legales))
            decisiones += 1
    dt = time.time() - t0
    print(f"{n} manos en {dt:.2f}s → {n / dt:.0f} manos/s, "
          f"{decisiones / n:.1f} decisiones por mano")

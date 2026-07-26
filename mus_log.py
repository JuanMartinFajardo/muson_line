# mus_log.py — Log v2 (event sourcing) para Mus. Fase 1.1 del roadmap de IA.
#
# Ver wiki/Bot-AI-4p-ML-Strategy.md §8. Un solo módulo para los DOS motores
# (PartidaMus de 2 jugadores y PartidaMus4 de 2v2): mismo esquema, mismo parser,
# `mode` distingue.
#
# Principio: se registran los HECHOS MÍNIMOS que hacen la partida exactamente
# reproducible por el motor (que es determinista salvo por la baraja), más una
# cabecera y los resúmenes de cierre. Cualquier feature de entrenamiento —
# incluidas las que aún no hemos inventado— se deriva luego RE-JUGANDO el log,
# en vez de quedar congelada en el momento de escribir. El formato v1
# (logs/*.jsonl) queda congelado: no se escribe nunca más ahí.
#
# Eventos (una línea JSON cada uno, `t` = tipo):
#
#   hdr   cabecera: versión, match, modo, reglas, asientos (uid/kind/bot), equipos
#   deal  reparto inicial de una ronda: mano y las 4 (o 2) manos, en orden de asiento
#   draw  cartas robadas por un asiento (descarte o pedrete) — el log es la baraja
#   a     una decisión: mus/no_mus/descarte/pedrete/pasar/envidar/subir/ver/nover/ordago
#   decl  declaración pública de pares/juego al entrar en el lance
#   pi    introspección opcional del bot: distribución de política y valor
#   eor   fin de ronda: resolución por lance, marcador y manos finales
#   eom   fin de match: ganador, partidas y número de eventos (chequeo de integridad)
#
# Reglas del formato: SIEMPRE índices de asiento (nunca nombres); identidad por
# `uid`/`code` de la cuenta; timestamp UTC ISO solo en `hdr` y el resto en `ms`
# (delta desde el evento anterior: más pequeño y más útil — es el dato de ritmo
# humano que necesitan el clonado de comportamiento y las señas).
#
# ¿Por qué los valores de carta son los CRUDOS (1..7,10..12) y no los
# normalizados de mus (3→12, 2→1) que sugería el borrador del esquema? Porque
# normalizar es una línea en el encoder pero es irreversible en el log: sin el
# valor crudo no se puede re-jugar (el pedrete es exactamente 4-5-6-7 y la
# composición de la baraja depende de los 2 y los 3). El log guarda hechos; las
# features las pone el encoder.

import json
import os
import time
import datetime

VERSION = 2

# Directorio de los logs v2. Los v1 se quedan donde estaban (logs/*.jsonl),
# congelados, para que nada de lo ya escrito cambie de sitio ni de formato.
DIR_LOGS_V2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs', 'v2')

# Orden canónico de las acciones de apuesta (el mismo que usan las redes).
ACCIONES = ('pasar', 'envidar', 'ver', 'nover', 'subir', 'ordago')


def _ahora_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


class MatchLogger:
    """Escribe un fichero JSONL por match, evento a evento.

    Se escribe y se hace flush en el momento (no al final): una partida que se
    corta a la mitad deja igualmente sus manos completas, que es justo lo que
    más abunda en producción. El coste es despreciable comparado con la latencia
    de socket que ya hay entre jugadas.

    `enabled=False` la deja como objeto nulo (mismo API, no toca el disco):
    lo usan el gimnasio, la arena y los tests.
    """

    def __init__(self, match_id, mode, enabled=True, dir_logs=None, ruta=None):
        self.match_id = match_id
        self.mode = mode
        self.enabled = enabled
        self.n_events = 0
        self._t_prev = time.monotonic()
        self._f = None
        self._cerrado = False
        self.ruta = ruta
        if self.enabled and self.ruta is None:
            base = dir_logs or DIR_LOGS_V2
            self.ruta = os.path.join(base, f"{match_id}.jsonl")

    # ---------------- infraestructura ----------------
    def _escribir(self, evento):
        if not self.enabled or self._cerrado:
            return
        self.n_events += 1
        try:
            if self._f is None:
                os.makedirs(os.path.dirname(self.ruta), exist_ok=True)
                self._f = open(self.ruta, 'a', encoding='utf-8')
            self._f.write(json.dumps(evento, ensure_ascii=False, separators=(',', ':')) + '\n')
            self._f.flush()
        except Exception as e:
            # Un log roto jamás puede tumbar una partida en curso.
            print(f"⚠️ [LOG v2] {self.match_id}: {e}")
            self.enabled = False

    def _ms(self):
        ahora = time.monotonic()
        delta = int(round((ahora - self._t_prev) * 1000))
        self._t_prev = ahora
        return delta

    def cerrar(self):
        if self._f is not None:
            try:
                self._f.close()
            except Exception:
                pass
            self._f = None

    # ---------------- eventos ----------------
    def hdr(self, rules, seats, teams):
        """seats: [{'s':0,'kind':'human','uid':…,'code':…}, …]; teams: [[0,2],[1,3]]."""
        self._t_prev = time.monotonic()
        self._escribir({'v': VERSION, 't': 'hdr', 'match': self.match_id, 'mode': self.mode,
                        'ts': _ahora_iso(), 'rules': rules, 'seats': seats, 'teams': teams})

    def seat(self, seat, kind, **campos):
        """Cambio de ocupante de un asiento a mitad de match (reemplazo, sustitución
        humano→bot). Aditivo: el `hdr` describe el arranque y estos eventos las
        altas posteriores, así que la atribución por persona sigue siendo exacta."""
        self._escribir(dict({'t': 'seat', 's': seat, 'kind': kind}, **campos))

    def deal(self, ronda, mano, hands):
        """hands: lista indexada por asiento con los valores crudos de las 4 cartas."""
        self._escribir({'t': 'deal', 'r': ronda, 'mano': mano, 'hands': hands})

    def draw(self, seat, cards):
        self._escribir({'t': 'draw', 's': seat, 'cards': list(cards)})

    def accion(self, seat, accion, lance=None, cantidad=None, idx=None):
        ev = {'t': 'a', 's': seat, 'a': accion}
        if lance is not None:
            ev['lance'] = lance
        if cantidad:
            ev['n'] = cantidad
        if idx is not None:
            ev['idx'] = list(idx)
        ev['ms'] = self._ms()
        self._escribir(ev)

    def decl(self, seat, lance, have):
        self._escribir({'t': 'decl', 's': seat, 'lance': lance, 'have': bool(have)})

    def pi(self, seat, probs, ev=None, extra=None):
        """Introspección del bot en el momento de decidir (supervisión gratis)."""
        e = {'t': 'pi', 's': seat, 'p': [round(float(x), 4) for x in probs]}
        if ev is not None:
            e['ev'] = round(float(ev), 4)
        if extra:
            e.update(extra)
        self._escribir(e)

    def eor(self, ronda, lances, scores, hands):
        """lances: {'grande': {'win': 0|'A', 'pts': 2}, …}; scores: marcador por EQUIPO."""
        self._escribir({'t': 'eor', 'r': ronda, 'lances': lances,
                        'scores': scores, 'hands': hands})

    def eom(self, winner, games):
        # n_events se cuenta incluyendo esta línea, para que el verificador pueda
        # comprobar que no falta ninguna (fichero truncado, disco lleno…).
        self._escribir({'t': 'eom', 'winner': winner, 'games': games,
                        'n_events': self.n_events + 1})
        self._cerrado = True
        self.cerrar()


class NullLogger(MatchLogger):
    """Logger que no escribe nada. Motor por defecto en entrenamiento y tests."""

    def __init__(self, match_id='-', mode='2p'):
        super().__init__(match_id, mode, enabled=False)


class MemLogger(MatchLogger):
    """Acumula los eventos en memoria en vez de en disco.

    Lo usa la re-jugada (mus_replay.py): el verificador compara el flujo de
    eventos REGENERADO por el motor con el del fichero, evento a evento. Ese
    es el sentido fuerte de "el log es reproducible"."""

    def __init__(self, match_id='-', mode='2p'):
        super().__init__(match_id, mode, enabled=True, ruta='')
        self.eventos = []

    def _escribir(self, evento):
        if self._cerrado:
            return
        self.n_events += 1
        self.eventos.append(evento)


# ==========================================================================
# Lado de la relectura
# ==========================================================================
def leer(ruta):
    """Devuelve la lista de eventos de un fichero v2 (saltando líneas rotas)."""
    eventos = []
    with open(ruta, 'r', encoding='utf-8') as f:
        for linea in f:
            linea = linea.strip()
            if not linea:
                continue
            try:
                eventos.append(json.loads(linea))
            except json.JSONDecodeError:
                continue
    return eventos


def es_v2(ruta):
    """True si el fichero empieza por una cabecera v2 (distingue del formato v1)."""
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            primera = f.readline().strip()
        if not primera:
            return False
        d = json.loads(primera)
        return d.get('v') == VERSION and d.get('t') == 'hdr'
    except Exception:
        return False


def listar(dir_logs=None):
    """Rutas de todos los ficheros v2 de un directorio."""
    base = dir_logs or DIR_LOGS_V2
    if not os.path.isdir(base):
        return []
    return sorted(os.path.join(base, n) for n in os.listdir(base)
                  if n.endswith('.jsonl') and es_v2(os.path.join(base, n)))


class FuenteCartas:
    """Baraja guionizada para la re-jugada: sirve las cartas que dice el log.

    Se instala en el motor (`motor.fuente_cartas = FuenteCartas(...)`) y sustituye
    a `robar()`. Así la re-jugada no depende de la semilla del RNG ni del orden
    interno de la baraja: depende solo de los hechos registrados, que es lo que
    hace que el log sobreviva a cualquier refactor del motor.

    Los valores del log se convierten a cartas del motor con el palo que toque;
    el palo es irrelevante en el mus (ninguna regla lo mira) así que se reparte
    de forma determinista para que dos re-jugadas den exactamente lo mismo.
    """

    def __init__(self, valores=()):
        self.pendientes = list(valores)
        self.servidas = 0
        self._n_palo = 0

    def añadir(self, valores):
        self.pendientes.extend(valores)

    def __call__(self, cantidad):
        from mus_mecanicas import obtener_ruta_imagen
        palos = ['Oros', 'Copas', 'Espadas', 'Bastos']
        traduccion = {'Oros': 'coins', 'Copas': 'cups', 'Espadas': 'swords', 'Bastos': 'clubs'}
        salida = []
        for _ in range(cantidad):
            if not self.pendientes:
                raise ValueError("FuenteCartas agotada: el log no registra este robo")
            valor = self.pendientes.pop(0)
            palo = palos[self._n_palo % 4]
            self._n_palo += 1
            self.servidas += 1
            salida.append({
                'valor': valor,
                'palo': palo,
                'img': obtener_ruta_imagen(f"card_{traduccion[palo]}_{valor:02d}"),
                'texto': f"{valor} de {palo}",
            })
        return salida

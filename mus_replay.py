# mus_replay.py — Re-jugada de logs v2. Fase 1.2 del roadmap de IA.
#
# El log v2 (mus_log.py) guarda HECHOS, no features: reparto, robos, decisiones
# y declaraciones. Este módulo los vuelve a meter por el motor determinista para
# reconstruir la partida entera, jugada a jugada. Encima de esto van:
#
#   * tools/log_verify.py    — integridad: ¿el motor regenera EXACTAMENTE el
#                              mismo flujo de eventos? (también es un test de
#                              regresión del motor contra tráfico real)
#   * tools/logs2dataset.py  — dataset: en cada decisión hay una `vista` completa
#                              del asiento que decide, así que las features se
#                              recalculan con el encoder DE HOY sobre logs de
#                              cualquier fecha. Eso es lo que el v1 no permitía.
#
# Cómo funciona el determinismo: el motor solo tiene una fuente de azar, la
# baraja. La re-jugada la sustituye por una FIFO con las cartas que dice el log
# (`deal` en orden de reparto + cada `draw` en orden de fichero), que es
# exactamente el orden en que el motor pide cartas. Todo lo demás se deriva.

from mus_log import MemLogger, FuenteCartas, leer
from mus_mecanicas import PartidaMus
from mus_mecanicas_4 import PartidaMus4

ACCIONES_APUESTA = ('pasar', 'envidar', 'subir', 'ver', 'nover', 'ordago')

# Eventos que el motor NO puede regenerar por sí solo y que por tanto quedan
# fuera de la comparación de integridad: la introspección del bot (`pi`) y los
# cambios de ocupante de asiento (`seat`), que son cosas del servidor.
EVENTOS_NO_REGENERABLES = ('pi', 'seat')


class ErrorReplay(Exception):
    pass


class Replay:
    """Re-jugada de un match v2.

    `on_decision(motor, seat, evento, vista)` se llama JUSTO ANTES de aplicar
    cada decisión, con el estado del motor tal y como lo veía quien decidió —
    ahí es donde tools/logs2dataset.py saca sus filas.
    """

    def __init__(self, eventos, on_decision=None):
        if not eventos or eventos[0].get('t') != 'hdr':
            raise ErrorReplay("el fichero no empieza por una cabecera v2")
        self.eventos = eventos
        self.hdr = eventos[0]
        self.mode = self.hdr.get('mode', '2p')
        self.on_decision = on_decision
        self.motor = None
        self.log = None
        self.fuente = FuenteCartas()
        self.n_decisiones = 0

    # ---------------- utilidades de asiento ----------------
    def _jugador(self, seat):
        """Traduce índice de asiento → identificador que espera el motor."""
        return seat if self.mode == '4p' else self.motor.asientos[seat]

    def _vista(self, seat):
        """Observación local del asiento. Solo la ofrece el motor de 4p; en 2p
        se devuelve el information set del gimnasio, que es su equivalente."""
        if self.mode == '4p':
            return self.motor.vista(seat)
        return None

    # ---------------- montaje ----------------
    def _crear_motor(self):
        reglas = self.hdr.get('rules') or {}
        if self.mode == '4p':
            motor = PartidaMus4()
        else:
            motor = PartidaMus('S0', 'S1')
            motor.asientos = [motor.j1, motor.j2]
        motor.al_mejor_de = reglas.get('al_mejor_de', 3)
        motor.match_id = self.hdr.get('match', '-')
        motor.fuente_cartas = self.fuente
        self.log = MemLogger(motor.match_id, self.mode)
        motor.log = self.log
        # La cabecera se copia tal cual: describe al servidor, no al motor.
        self.log._escribir(dict(self.hdr))
        # `iniciar_ronda()` es lo que pone ronda_n a 1; el servidor la llama
        # nada más montar la mesa, así que la re-jugada hace lo mismo.
        motor.iniciar_ronda()
        self.motor = motor
        return motor

    def _fijar_mano(self, seat_mano):
        if self.mode == '4p':
            self.motor.mano = seat_mano
            self.motor.turno_de = seat_mano
        else:
            self.motor.id_mano = self.motor.asientos[seat_mano]
            self.motor.id_postre = self.motor.asientos[1 - seat_mano]
            self.motor.turno_de = self.motor.id_mano

    def _auto_transiciones(self):
        """Consume los avisos de "nadie tiene pares"/"juego a punto" igual que
        hace el servidor con su temporizador: siempre antes de la jugada
        siguiente, que es lo que fija el orden de los eventos `decl`."""
        guardas = 0
        while self.motor.mensaje_transicion is not None and self.motor.fase == 'apuestas':
            self.motor.mensaje_transicion = None
            self.motor.preparar_subfase()
            guardas += 1
            if guardas > 8:
                raise ErrorReplay("bucle de transiciones")

    def _avanzar_ronda(self):
        if self.mode == '4p':
            terminada = self.motor.puntos['A'] >= 40 or self.motor.puntos['B'] >= 40
        else:
            terminada = any(self.motor.estado[p]['puntos'] >= 40 for p in self.motor.asientos)
        if terminada:
            self.motor.reiniciar_partida()
        elif self.mode == '4p':
            self.motor.siguiente_ronda()
        else:
            self.motor.cambiar_roles()
            self.motor.iniciar_ronda()
        self.motor.jugadores_listos = []
        # `PartidaMus.reiniciar_partida` no baja el flag (lo hace el servidor
        # al avanzar la ronda); si no, el recuento siguiente no se calcularía.
        self.motor.recuento_calculado = False

    # ---------------- bucle principal ----------------
    def ejecutar(self):
        self._crear_motor()
        primera_ronda = True

        for i, ev in enumerate(self.eventos):
            if i == 0:
                continue
            t = ev.get('t')

            if t == 'deal':
                if not primera_ronda:
                    self._avanzar_ronda()
                primera_ronda = False
                # El log manda sobre quién es mano: así la re-jugada sobrevive a
                # los caminos raros (sustituciones, rondas descartadas).
                self._fijar_mano(ev['mano'])
                orden = (self.motor.orden_desde(self.motor.mano) if self.mode == '4p'
                         else [self.motor.asientos.index(self.motor.id_mano),
                               self.motor.asientos.index(self.motor.id_postre)])
                for s in orden:
                    self.fuente.añadir(ev['hands'][s])
                self.motor.repartir_inicial()

            elif t == 'draw':
                # Las cartas del robo se encolan; las consumirá el `robar()` que
                # dispare la acción ya aplicada (descarte/pedrete). Ver abajo:
                # los `draw` se pre-encolan al aplicar la acción, así que aquí
                # solo quedan los que aún no se hubieran consumido.
                pass

            elif t == 'a':
                self._aplicar_accion(ev, i)

            elif t == 'eor':
                # El último lance puede acabar en un aviso ("no juego", "juego a
                # punto"): hasta que no se consume, el motor no entra en recuento.
                self._auto_transiciones()
                if self.motor.fase == 'recuento':
                    self.motor.calcular_recuento()

            elif t in ('decl', 'eom'):
                pass   # los regenera el motor

            elif t in EVENTOS_NO_REGENERABLES:
                pass

        return self.motor

    def _draws_pendientes(self, indice_desde):
        """Cartas de los `draw` que siguen inmediatamente a una acción."""
        salida = []
        for ev in self.eventos[indice_desde:]:
            if ev.get('t') == 'draw':
                salida.extend(ev['cards'])
            elif ev.get('t') in ('pi',):
                continue
            else:
                break
        return salida

    def _aplicar_accion(self, ev, indice):
        self._auto_transiciones()
        seat = ev['s']
        accion = ev['a']
        jugador = self._jugador(seat)

        if self.on_decision is not None:
            self.on_decision(self.motor, seat, ev, self._vista(seat))
        self.n_decisiones += 1

        # Las acciones que roban cartas necesitan tenerlas ya en la FIFO: se
        # adelantan los `draw` que vienen justo detrás en el fichero.
        if accion in ('descarte', 'pedrete'):
            self.fuente.añadir(self._draws_pendientes(indice + 1))

        if accion in ('mus', 'no_mus'):
            self.motor.cantar_mus(jugador, accion == 'mus')
        elif accion == 'descarte':
            self.motor.procesar_descarte(jugador, ev.get('idx') or [])
        elif accion == 'pedrete':
            self.motor.procesar_pedrete(jugador)
        elif accion in ACCIONES_APUESTA:
            self.motor.accion_apuesta(jugador, accion, ev.get('n', 0))
        else:
            raise ErrorReplay(f"acción desconocida en el log: {accion!r}")


def replay_fichero(ruta, on_decision=None):
    r = Replay(leer(ruta), on_decision=on_decision)
    r.ejecutar()
    return r


# ==========================================================================
# Comparación de flujos de eventos
# ==========================================================================
def normalizar(eventos):
    """Deja los eventos comparables: fuera el ritmo humano y lo no regenerable.

    `ms` es un dato valioso del log (§10.1) pero no es reproducible por
    definición, así que no entra en la comprobación de integridad."""
    salida = []
    for ev in eventos:
        if ev.get('t') in EVENTOS_NO_REGENERABLES:
            continue
        limpio = {k: v for k, v in ev.items() if k not in ('ms', 'ts')}
        salida.append(limpio)
    return salida


def diferencias(original, regenerado, maximo=10):
    """Lista legible de las diferencias entre dos flujos ya normalizados."""
    fallos = []
    for i in range(max(len(original), len(regenerado))):
        a = original[i] if i < len(original) else None
        b = regenerado[i] if i < len(regenerado) else None
        if a != b:
            fallos.append((i, a, b))
            if len(fallos) >= maximo:
                break
    return fallos

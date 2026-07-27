# mus_mecanicas_4.py — Motor de Mus para 4 jugadores (2v2, online, sin bots).
#
# Diseño (ver wiki/Implementing-Mus-4-Players.md §3): modelado de cerca sobre
# PartidaMus (mus_mecanicas.py) pero generalizado a 4 asientos / 2 equipos.
#
# Claves estructurales frente al motor de 2 jugadores:
#   * `estado` está indexado por ASIENTO (0..3), no por sid. El servidor mantiene
#     el mapeo asiento↔sid, así que el motor nunca ve ids de socket → la
#     reconexión es trivial (solo se cambia el sid del asiento en el servidor).
#   * Puntos y apuestas son POR EQUIPO: A = asientos {0,2}, B = {1,3}.
#   * Los comparadores por pares del motor de 2p se reutilizan vía mus_core:
#     cada equipo se reduce a su mano representativa (la mejor) y se comparan.
#
# NO se toca mus_mecanicas.py: solo se importan sus funciones puras desde mus_core.

import random
import string

from mus_core import (
    crear_baraja, get_valores_mus, tiene_pares, get_pares_info,
    get_suma_juego, tiene_juego, comparar_cartas, comp_pares_info,
    comp_juego, comp_punto, mejor_hand_equipo,
    cartas_a_claves, claves_a_cartas,
)
from mus_log import MatchLogger, NullLogger

# Logger mudo compartido por todos los `fork()`. Un fork nunca escribe (es una
# rama hipotética del árbol de CFR), así que construirle un NullLogger propio en
# cada clon era pura asignación tirada en el camino más caliente del gimnasio.
_LOG_MUDO = NullLogger('-', '4p')


class PartidaMus4:
    FASES_APUESTA = ['Grande', 'Chica', 'Pares', 'Juego']

    def __init__(self):
        # Equipos fijos: compañeros enfrentados. A = {0,2}, B = {1,3}.
        self.equipos = {'A': [0, 2], 'B': [1, 3]}
        self.equipo_de = {0: 'A', 1: 'B', 2: 'A', 3: 'B'}

        # Fuente de azar del motor. `None` = el `random` global de siempre (así
        # `random.seed()` sigue controlando los repartos, como esperan los soaks);
        # la arena y las sondas le enchufan un random.Random(semilla) para que dos
        # enfrentamientos vean EXACTAMENTE los mismos repartos (números aleatorios
        # comunes = mucha menos varianza por partida). Se guarda como None y no
        # como el módulo porque un módulo no es copiable ni serializable.
        self.rng = None
        self.mano = random.randint(0, 3)   # asiento de la Mano esta ronda
        self.baraja = []
        self.descartes = []

        self.estado = {
            s: {'cartas': [], 'quiere_mus': None,
                'descartes_listos': False, 'descartes_hechos': 0,
                'tiene_pares_dec': None, 'tiene_juego_dec': None}
            for s in range(4)
        }

        # Puntuación por equipo.
        self.puntos = {'A': 0, 'B': 0}
        self.partidas_ganadas = {'A': 0, 'B': 0}
        self.al_mejor_de = 3
        self.match_finalizado = False
        self.partida_sumada = False

        self.fase = 'espera_reparto'
        self.indice_fase = 0
        self.turno_de = None               # ASIENTO cuyo turno es

        self.botes = {f: 0 for f in self.FASES_APUESTA}
        self.dejes_fase = {f: None for f in self.FASES_APUESTA}
        self.ganadores_fase = {f: None for f in self.FASES_APUESTA}  # guarda 'A'/'B'
        self.apuesta_vista = 0
        self.subida_pendiente = 0
        self.quien_sube = None             # equipo 'A'/'B' con la apuesta viva
        self.equipo_apostador = None       # equipo con apuesta viva (o None)
        self.ultimo_apostador = None       # ASIENTO que hizo la última apuesta viva
        self.respondedores = []            # asientos del equipo rival que aún pueden responder
        self.pases_consecutivos = 0
        self.ordago_aceptado_en = None
        self.juego_es_punto = False
        self.transicion_punto_mostrada = False
        self.quien_corta_mus = None
        self.rondas_mus = 0

        self.mensaje_transicion = None

        # Ronda de cantes de Pares/Juego. En una mesa de verdad, antes de apostar
        # a Pares cada jugador dice en voz alta si los tiene; sólo después se
        # envida. El motor SIEMPRE hace esa declaración (es información pública y
        # va al log), pero por omisión la resuelve de golpe, que es lo que
        # necesitan el gimnasio, la arena y el replay: sin sockets no hay a quién
        # enseñársela y una cola pendiente los dejaría colgados.
        #
        # El servidor la enciende (`declaracion_pausada = True`) para repartirla
        # en el tiempo: se encola el orden de mesa y se va cantando asiento a
        # asiento, con la mesa congelada mientras tanto (`acciones_legales`
        # devuelve [], como con un mensaje de transición).
        self.declaracion_pausada = False
        self.declaraciones_pendientes = []   # [(asiento, bool)] aún por cantar
        self.declaracion_fase = None         # lance cuya ronda de cantes se preparó

        self.recuento_calculado = False
        self.baraja_agotada_aviso = False
        self.pasos_recuento = []
        self.jugadores_listos = []         # asientos listos para la siguiente ronda
        self.ronda_n = 0

        # Log v2 (mus_log.py). Arranca mudo: el servidor llama a `activar_log()`
        # cuando ya sabe quién se sienta dónde, y el gimnasio/arena lo dejan así.
        self.match_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        self.nombres = {}                  # {asiento: nombre para mostrar}
        self.usernames = {}                # {asiento: username registrado o None}
        self.log = NullLogger(self.match_id, '4p')
        self._lances_ronda = {}            # resolución por lance, para el evento `eor`

        # Baraja guionizada para la re-jugada (tools/log_verify.py). Si está
        # puesta, `robar()` sirve de aquí en vez de la baraja aleatoria.
        self.fuente_cartas = None

    # ==========================================
    # Helpers de orden y equipos
    # ==========================================
    def orden_desde(self, seat):
        """Orden de mesa empezando en `seat`, en sentido ANTIHORARIO (reglas del
        mus: se juega hacia la derecha del que reparte): [seat, seat-1, seat-2, seat-3]."""
        return [(seat - i) % 4 for i in range(4)]

    def siguiente_seat(self, seat):
        # Antihorario: el turno pasa al asiento de la derecha.
        return (seat - 1) % 4

    def siguiente_rival(self, seat):
        """Siguiente asiento del equipo contrario, en orden de mesa.

        Con equipos {0,2} vs {1,3} los asientos adyacentes son siempre rivales,
        de modo que esto coincide con (seat+1)%4, pero lo dejamos explícito por
        claridad de intención (responde el equipo contrario)."""
        eq = self.equipo_de[seat]
        for s in self.orden_desde(self.siguiente_seat(seat)):
            if self.equipo_de[s] != eq:
                return s
        return self.siguiente_seat(seat)

    def _abrir_respuesta(self, seat):
        """Tras una apuesta de `seat`, el equipo rival debe responder.

        Encola a los DOS rivales en orden de turno y cede la palabra al primero.
        Si ese rival da un 'no quiero', la decisión pasa a su compañero (ver
        `accion_apuesta`) antes de conceder la apuesta: cualquiera de los dos
        puede querer/subir por el equipo."""
        eq = self.equipo_de[seat]
        self.respondedores = [s for s in self.orden_desde(self.siguiente_seat(seat))
                              if self.equipo_de[s] != eq]
        self.turno_de = self.respondedores[0]

    def _dist_mano(self, seat):
        """Distancia del asiento a la Mano en orden de turno (0 = la mano).

        Como el juego es antihorario, la distancia se mide contando asientos
        hacia la derecha desde la mano."""
        return (self.mano - seat) % 4

    def _asientos_equipo_desde_mano(self, equipo):
        """Asientos de un equipo ordenados por cercanía a la Mano (para desempates)."""
        return sorted(self.equipos[equipo], key=self._dist_mano)

    def _equipo_tiene(self, equipo, predicado):
        return any(predicado(self.estado[s]['cartas']) for s in self.equipos[equipo])

    def _azar(self):
        return self.rng if self.rng is not None else random

    # ==========================================
    # Log v2 (wiki/Bot-AI-4p-ML-Strategy.md §8)
    # ==========================================
    def _lance_actual(self):
        if self.fase == 'apuestas' and self.indice_fase < len(self.FASES_APUESTA):
            nombre = self.FASES_APUESTA[self.indice_fase]
            return 'Punto' if (nombre == 'Juego' and self.juego_es_punto) else nombre
        return None

    def activar_log(self, seats=None, rules=None, dir_logs=None, enabled=True):
        """Abre el fichero v2 del match y escribe la cabecera.

        `seats` es la lista de identidades por asiento que conoce el servidor
        ({'s','kind','uid','code','ckpt','pers'}); si no se pasa, se deduce de
        `usernames` para que las herramientas offline también logueen algo útil.
        """
        if seats is None:
            seats = [{'s': s, 'kind': 'human', 'code': self.usernames.get(s)}
                     for s in range(4)]
        # `team_response` deja constancia de CON QUÉ REGLAS se jugó la mano, que es
        # lo que hará comparables los logs de antes y después de la Fase 2: hoy
        # responde el turno y, si rehúsa, su compañero ('companero'); la Fase 2.1
        # abre la respuesta a cualquiera de los dos en cualquier orden ('libre').
        base = {'objetivo': 40, 'al_mejor_de': self.al_mejor_de,
                'team_response': 'companero', 'senas': False, 'engine': 'mus4'}
        if rules:
            base.update(rules)
        self.log = MatchLogger(self.match_id, '4p', enabled=enabled, dir_logs=dir_logs)
        self.log.hdr(base, seats, [self.equipos['A'], self.equipos['B']])
        return self.log

    # ==========================================
    # Reparto y baraja
    # ==========================================
    def robar(self, cantidad):
        # Re-jugada: las cartas las dicta el log, no el azar.
        if self.fuente_cartas is not None:
            return self.fuente_cartas(cantidad)
        robadas = []
        for _ in range(cantidad):
            if not self.baraja:
                # Sin cartas: rebarajamos los descartes y avisamos (Roadmap #14).
                self.baraja = self.descartes.copy()
                self._azar().shuffle(self.baraja)
                self.descartes = []
                self.baraja_agotada_aviso = True
            if self.baraja:
                robadas.append(self.baraja.pop(0))
        return robadas

    def iniciar_ronda(self):
        self.baraja = []
        self.descartes = []
        self.ronda_n += 1
        for s in range(4):
            self.estado[s]['cartas'] = []
            self.estado[s]['quiere_mus'] = None
            self.estado[s]['descartes_listos'] = False
            self.estado[s]['descartes_hechos'] = 0
            self.estado[s]['tiene_pares_dec'] = None
            self.estado[s]['tiene_juego_dec'] = None
        self.fase = 'espera_reparto'
        self.turno_de = self.mano
        self.quien_corta_mus = None
        self.rondas_mus = 0
        self.mensaje_transicion = None
        self.declaraciones_pendientes = []
        self.declaracion_fase = None
        self.baraja_agotada_aviso = False
        self._lances_ronda = {}

    def repartir_inicial(self):
        self.baraja = crear_baraja()
        self._azar().shuffle(self.baraja)
        self.descartes = []
        for s in self.orden_desde(self.mano):
            self.estado[s]['cartas'] = self.robar(4)
        self.fase = 'mus'
        self.turno_de = self.mano
        self.log.deal(self.ronda_n, self.mano,
                      [[c['valor'] for c in self.estado[s]['cartas']] for s in range(4)])

    # ==========================================
    # Fase de Mus y descartes
    # ==========================================
    def cantar_mus(self, seat, quiere_mus):
        self.log.accion(seat, 'mus' if quiere_mus else 'no_mus')
        self.estado[seat]['quiere_mus'] = quiere_mus

        if not quiere_mus:
            # Un solo "no mus" corta: quien corta abre Grande.
            self.quien_corta_mus = seat
            self.iniciar_fase_apuestas()
            return 'apuestas'

        # Siguiente asiento (desde la mano) que aún no ha hablado.
        siguiente = None
        for s in self.orden_desde(self.mano):
            if self.estado[s]['quiere_mus'] is None:
                siguiente = s
                break

        if siguiente is None:
            # Los cuatro quieren mus → descarte.
            self.fase = 'descarte'
            for s in range(4):
                self.estado[s]['descartes_listos'] = False
            self.rondas_mus += 1
            self.turno_de = self.mano
            return 'descarte'

        self.turno_de = siguiente
        return 'esperando_mus'

    def procesar_pedrete(self, seat):
        """4-5-6-7: punto inmediato al EQUIPO y mano nueva para ese asiento."""
        if self.fase not in ['mus', 'descarte']:
            return False
        valores = sorted([c['valor'] for c in self.estado[seat]['cartas']])
        if valores != [4, 5, 6, 7]:
            return False

        self.log.accion(seat, 'pedrete')
        eq = self.equipo_de[seat]
        self.puntos[eq] += 1

        self.descartes.extend(self.estado[seat]['cartas'])
        self.estado[seat]['cartas'] = self.robar(4)
        self.log.draw(seat, [c['valor'] for c in self.estado[seat]['cartas']])

        if self.puntos[eq] >= 40:
            self.fase = 'recuento'
            self.recuento_calculado = True
            self.pasos_recuento = [{'ganador_equipo': eq, 'datos': {'code': 'recuento_pedrete_win'}}]
            self._lances_ronda['Pedrete'] = {'win': eq, 'pts': 1}
            self._cerrar_ronda()
        return True

    def procesar_descarte(self, seat, indices_cartas_a_tirar):
        indices_cartas_a_tirar = [int(i) for i in indices_cartas_a_tirar]
        cartas_jugador = self.estado[seat]['cartas']
        # El log guarda los ÍNDICES tirados (no los valores): es lo que hace
        # falta para re-jugar, y las cartas ya se saben por el `deal`/`draw`.
        self.log.accion(seat, 'descarte', idx=sorted(indices_cartas_a_tirar))

        cartas_tiradas = [cartas_jugador.pop(i) for i in sorted(indices_cartas_a_tirar, reverse=True)]
        self.descartes.extend(cartas_tiradas)
        self.estado[seat]['descartes_hechos'] = len(indices_cartas_a_tirar)
        nuevas = self.robar(len(indices_cartas_a_tirar))
        self.estado[seat]['cartas'].extend(nuevas)
        self.estado[seat]['descartes_listos'] = True
        if nuevas:
            self.log.draw(seat, [c['valor'] for c in nuevas])

        if all(self.estado[s]['descartes_listos'] for s in range(4)):
            # Vuelta al mus.
            self.fase = 'mus'
            for s in range(4):
                self.estado[s]['quiere_mus'] = None
            self.turno_de = self.mano
            return 'nuevo_mus'
        return 'esperando_rival'

    # ==========================================
    # Motor de apuestas (por equipo)
    # ==========================================
    def iniciar_fase_apuestas(self):
        self.fase = 'apuestas'
        self.indice_fase = 0
        self.botes = {f: 0 for f in self.FASES_APUESTA}
        self.dejes_fase = {f: None for f in self.FASES_APUESTA}
        self.ganadores_fase = {f: None for f in self.FASES_APUESTA}
        self.ordago_aceptado_en = None
        self.juego_es_punto = False
        self.transicion_punto_mostrada = False
        self.declaraciones_pendientes = []
        self.declaracion_fase = None
        self.preparar_subfase()

    def preparar_subfase(self):
        self.mensaje_transicion = None
        if self.indice_fase >= len(self.FASES_APUESTA):
            self.fase = 'recuento'
            return

        nombre_fase = self.FASES_APUESTA[self.indice_fase]
        self.apuesta_vista = 0
        self.subida_pendiente = 0
        self.quien_sube = None
        self.equipo_apostador = None
        self.ultimo_apostador = None
        self.respondedores = []
        self.pases_consecutivos = 0

        # Grande la abre quien cortó el mus; el resto de lances empiezan en la mano.
        if nombre_fase == 'Grande' and self.quien_corta_mus is not None:
            self.turno_de = self.quien_corta_mus
        else:
            self.turno_de = self.mano

        if nombre_fase == 'Pares':
            # Declaración automática (sin señas): cada asiento declara según sus cartas.
            # Son información PÚBLICA y la señal más informativa del mus, así que
            # van al log como eventos de primera clase (§8.3), en orden de mesa.
            if self._cantar_declaraciones('Pares', tiene_pares):
                return   # la mesa espera a que se canten una a una
            a_tiene = self._equipo_tiene('A', tiene_pares)
            b_tiene = self._equipo_tiene('B', tiene_pares)
            if not (a_tiene and b_tiene):
                if not a_tiene and not b_tiene:
                    self.mensaje_transicion = {'code': 'nadie_pares', 'fase': 'Pares'}
                else:
                    ganador = 'A' if a_tiene else 'B'
                    sin_pares = 'B' if a_tiene else 'A'   # el equipo que NO tiene
                    self.ganadores_fase['Pares'] = ganador
                    self.mensaje_transicion = {'code': 'no_pares', 'equipo': sin_pares, 'fase': 'Pares'}
                self.indice_fase += 1
                return
            self.turno_de = self._primer_asiento_eligible(tiene_pares)

        elif nombre_fase == 'Juego':
            # Ojo: a esta rama se vuelve a entrar tras el aviso "juego a punto",
            # por eso la declaración se emite una sola vez por ronda.
            if self._cantar_declaraciones('Juego', tiene_juego):
                return   # la mesa espera a que se canten una a una
            a_tiene = self._equipo_tiene('A', tiene_juego)
            b_tiene = self._equipo_tiene('B', tiene_juego)
            if not a_tiene and not b_tiene:
                # Nadie tiene juego → se juega al Punto (se sigue apostando).
                self.juego_es_punto = True
                if not self.transicion_punto_mostrada:
                    self.mensaje_transicion = {'code': 'juego_a_punto', 'fase': 'Juego'}
                    self.transicion_punto_mostrada = True
                    return
            elif a_tiene != b_tiene:
                ganador = 'A' if a_tiene else 'B'
                sin_juego = 'B' if a_tiene else 'A'   # el equipo que NO tiene
                self.ganadores_fase['Juego'] = ganador
                self.mensaje_transicion = {'code': 'no_juego', 'equipo': sin_juego, 'fase': 'Juego'}
                self.indice_fase += 1
                return
            else:
                self.turno_de = self._primer_asiento_eligible(tiene_juego)

    _CLAVE_DEC = {'Pares': 'tiene_pares_dec', 'Juego': 'tiene_juego_dec'}

    def _cantar_declaraciones(self, lance, predicado):
        """Ronda de cantes de un lance. Devuelve True si la mesa debe esperar.

        Sin pausa (gimnasio, arena, replay) declara los cuatro asientos de golpe
        y devuelve False: el lance se resuelve en la misma llamada, como siempre.
        Con pausa encola el orden de mesa y devuelve True hasta que la cola se
        vacía a base de `declarar_siguiente()`. `preparar_subfase` se vuelve a
        llamar sola al cantar el último, y entonces sí cae por aquí sin esperar.
        """
        clave = self._CLAVE_DEC[lance]
        if self.declaracion_fase != lance:
            self.declaracion_fase = lance
            self.declaraciones_pendientes = [
                (s, predicado(self.estado[s]['cartas']))
                for s in self.orden_desde(self.mano)
                if self.estado[s][clave] is None
            ]
            if not self.declaracion_pausada:
                # De golpe: se cantan todas aquí mismo y no queda cola.
                for s, valor in self.declaraciones_pendientes:
                    self.estado[s][clave] = valor
                    self.log.decl(s, lance, valor)
                self.declaraciones_pendientes = []
        return bool(self.declaraciones_pendientes)

    def declarar_siguiente(self):
        """Canta la declaración del siguiente asiento de la cola.

        Devuelve `(asiento, lance, tiene)` o None si no había nada pendiente. Al
        cantar la última vuelve a `preparar_subfase`, que ya resuelve el lance
        (abre las apuestas o pone el mensaje de transición que corresponda).
        """
        if not self.declaraciones_pendientes:
            return None
        lance = self.declaracion_fase
        seat, valor = self.declaraciones_pendientes.pop(0)
        self.estado[seat][self._CLAVE_DEC[lance]] = valor
        self.log.decl(seat, lance, valor)
        if not self.declaraciones_pendientes:
            self.preparar_subfase()
        return (seat, lance, valor)

    def _primer_asiento_eligible(self, predicado):
        """Primer asiento desde la mano cuya mano cumple el predicado (pares/juego).

        Ambos equipos son elegibles cuando se llega aquí; empezamos en el primer
        jugador que realmente tiene la jugada para que abra quien puede apostar."""
        for s in self.orden_desde(self.mano):
            if predicado(self.estado[s]['cartas']):
                return s
        return self.mano

    def avanzar_subfase(self, bote_extra):
        nombre_fase = self.FASES_APUESTA[self.indice_fase]
        self.botes[nombre_fase] += bote_extra
        self.indice_fase += 1
        self.preparar_subfase()

    def accion_apuesta(self, seat, accion, cantidad=0):
        # Se registra la cantidad PEDIDA, no la recortada: es la decisión real
        # del jugador y es lo que hay que reinyectar para re-jugar la mano.
        self.log.accion(seat, accion, lance=self._lance_actual(), cantidad=cantidad)
        nombre_fase = self.FASES_APUESTA[self.indice_fase]
        eq = self.equipo_de[seat]
        eq_rival = 'B' if eq == 'A' else 'A'

        if accion == 'pasar':
            self.pases_consecutivos += 1
            if self.pases_consecutivos >= 4:
                # Pase corrido de los cuatro. Punto "de paso" solo en Grande/Chica
                # (se resuelve en el recuento como bonus).
                punto_pase = 1 if nombre_fase in ['Grande', 'Chica'] else 0
                self.avanzar_subfase(punto_pase)
            else:
                self.turno_de = self.siguiente_seat(seat)

        elif accion == 'envidar' or accion == 'subir':
            self.pases_consecutivos = 0
            if accion == 'subir':
                self.apuesta_vista += self.subida_pendiente

            # Tope legal: no se puede apostar más de lo que separa del final (40).
            pts_max = max(self.puntos[eq], self.puntos[eq_rival])
            tope_legal = 40 - pts_max - self.apuesta_vista
            if tope_legal <= 0:
                self.subida_pendiente = 'ÓRDAGO'
            else:
                self.subida_pendiente = max(1, min(cantidad, tope_legal))

            self.quien_sube = eq
            self.equipo_apostador = eq
            self.ultimo_apostador = seat
            self._abrir_respuesta(seat)

        elif accion == 'ver':
            if self.subida_pendiente == 'ÓRDAGO':
                self.botes[nombre_fase] = 40
                self.ordago_aceptado_en = nombre_fase
                self.fase = 'recuento'
            else:
                self.botes[nombre_fase] += (self.apuesta_vista + self.subida_pendiente)
                self.avanzar_subfase(0)

        elif accion == 'nover':
            deje = self.apuesta_vista if self.apuesta_vista > 0 else 1
            # Obligado a ver si el deje da la partida al equipo contrario.
            if self.puntos[eq_rival] + deje >= 40:
                if self.subida_pendiente == 'ÓRDAGO':
                    self.botes[nombre_fase] = 40
                    self.ordago_aceptado_en = nombre_fase
                    self.fase = 'recuento'
                else:
                    self.botes[nombre_fase] += (self.apuesta_vista + self.subida_pendiente)
                    self.avanzar_subfase(0)
            else:
                # Si el compañero aún no ha respondido, le pasa la palabra: puede
                # querer/subir por el equipo antes de que se conceda la apuesta.
                self.respondedores = [s for s in self.respondedores if s != seat]
                if self.respondedores:
                    self.turno_de = self.respondedores[0]
                    return
                # Ambos rivales rehúsan → el equipo apostador se lleva la concesión.
                ganador_eq = self.quien_sube if self.quien_sube else eq_rival
                self.puntos[ganador_eq] += deje
                self.ganadores_fase[nombre_fase] = ganador_eq
                self.dejes_fase[nombre_fase] = {'ganador': ganador_eq, 'valor': deje}
                self.avanzar_subfase(0)

        elif accion == 'ordago':
            self.pases_consecutivos = 0
            if self.subida_pendiente != 'ÓRDAGO':
                self.apuesta_vista += self.subida_pendiente
            self.subida_pendiente = 'ÓRDAGO'
            self.quien_sube = eq
            self.equipo_apostador = eq
            self.ultimo_apostador = seat
            self._abrir_respuesta(seat)

    # ==========================================
    # Contrato de observación por asiento (Roadmap 4p, Fase 0.3)
    # ------------------------------------------------------------------
    # `vista(seat)` es lo ÚNICO que ve un bot: un diccionario de observación
    # local al asiento, nunca el motor entero. Los bloques A–E siguen el
    # layout de wiki/Bot-AI-4p-ML-Strategy.md §4.2, así que el encoder de
    # Deep CFR (Fase 1) podrá consumir este mismo dict sin que cambie ni el
    # servidor ni la firma de los bots. Todo lo de aquí es de solo lectura.
    # ==========================================
    def puede_pedrete(self, seat):
        if self.fase not in ('mus', 'descarte'):
            return False
        return sorted([c['valor'] for c in self.estado[seat]['cartas']]) == [4, 5, 6, 7]

    def acciones_legales(self, seat):
        """Acciones que `seat` puede ejecutar AHORA mismo, ya filtradas.

        Incluye tanto la legalidad del motor (turno, fase, topes de 40) como
        las reglas del mus que el motor no vigila por sí solo (no se apuesta a
        Pares/Juego sin la jugada). Un bot que solo elija de esta lista no
        puede hacer una jugada ilegal, que es la garantía que pide la Fase 0.
        """
        if self.match_finalizado:
            return []
        # Mientras se muestra un mensaje de transición el servidor auto-avanza:
        # nadie tiene que (ni puede) hacer nada.
        if self.mensaje_transicion:
            return []
        # Ídem mientras se está cantando la ronda de Pares/Juego: hasta que no
        # haya declarado el último no se sabe siquiera si hay lance que apostar.
        if self.declaraciones_pendientes:
            return []

        acciones = []
        if self.puede_pedrete(seat):
            acciones.append('pedrete')

        if self.fase == 'recuento':
            if seat not in self.jugadores_listos:
                acciones.append('listo_siguiente_ronda')
            return acciones

        if self.fase == 'descarte':
            if not self.estado[seat]['descartes_listos']:
                acciones.append('descartar')
            return acciones

        if seat != self.turno_de:
            return acciones

        if self.fase == 'espera_reparto':
            acciones.append('repartir')
            return acciones

        if self.fase == 'mus':
            if self.estado[seat]['quiere_mus'] is None:
                acciones.extend(['mus', 'no_mus'])
            return acciones

        if self.fase != 'apuestas' or self.indice_fase >= len(self.FASES_APUESTA):
            return acciones

        nombre_fase = self.FASES_APUESTA[self.indice_fase]
        cartas = self.estado[seat]['cartas']
        respondiendo = (self.subida_pendiente != 0)

        # Sin la jugada no se apuesta: solo se puede pasar (o rehusar).
        if nombre_fase == 'Pares' and not tiene_pares(cartas):
            return acciones + (['nover'] if respondiendo else ['pasar'])
        if nombre_fase == 'Juego' and not tiene_juego(cartas) and not self.juego_es_punto:
            return acciones + (['nover'] if respondiendo else ['pasar'])

        eq = self.equipo_de[seat]
        eq_rival = 'B' if eq == 'A' else 'A'
        pts_max = max(self.puntos[eq], self.puntos[eq_rival])
        deje = self.apuesta_vista if self.apuesta_vista > 0 else 1
        obligado_a_ver = (self.puntos[eq_rival] + deje >= 40)

        if not respondiendo:
            acciones.append('pasar')
            # Si no cabe un envite normal, lo único que queda por encima es el órdago.
            if 40 - pts_max - self.apuesta_vista > 0:
                acciones.append('envidar')
            acciones.append('ordago')
            return acciones

        if self.subida_pendiente == 'ÓRDAGO':
            acciones.append('ver')
            if not obligado_a_ver:
                acciones.append('nover')
            return acciones

        acciones.append('ver')
        if not obligado_a_ver:
            acciones.append('nover')
        if 40 - pts_max - (self.apuesta_vista + self.subida_pendiente) > 0:
            acciones.append('subir')
        acciones.append('ordago')
        return acciones

    def vista(self, seat):
        """Observación local del asiento `seat` (bloques A–E de §4.2)."""
        eq = self.equipo_de[seat]
        eq_rival = 'B' if eq == 'A' else 'A'
        companero = (seat + 2) % 4
        cartas = self.estado[seat]['cartas']
        pares_info = get_pares_info(cartas) if cartas else {'tipo': 0, 'premio': 0}
        suma_juego = get_suma_juego(cartas) if cartas else 0
        nombre_fase = (self.FASES_APUESTA[self.indice_fase]
                       if self.fase == 'apuestas' and self.indice_fase < len(self.FASES_APUESTA)
                       else None)
        lance = 'Punto' if (nombre_fase == 'Juego' and self.juego_es_punto) else nombre_fase

        def relativo(equipo_ganador):
            """Propiedad de un lance en clave de equipo: 1 mío, 0 rival, 0.5 abierto."""
            if equipo_ganador is None:
                return 0.5
            return 1.0 if equipo_ganador == eq else 0.0

        # Bloque B — los otros tres asientos, en orden relativo al mío
        # (rel 1 = rival de la derecha, 2 = compañero, 3 = rival de la izquierda).
        otros = []
        for rel in (1, 2, 3):
            s = (seat + rel) % 4
            otros.append({
                'rel': rel,
                'asiento': s,
                'es_companero': (s == companero),
                'pares_dec': self.estado[s]['tiene_pares_dec'],
                'juego_dec': self.estado[s]['tiene_juego_dec'],
                'descartes': self.estado[s]['descartes_hechos'],
                'quiere_mus': self.estado[s]['quiere_mus'],
            })

        deje = self.apuesta_vista if self.apuesta_vista > 0 else 1
        subida = self.subida_pendiente
        es_ordago = (subida == 'ÓRDAGO')

        return {
            # --- Mecánica: lo que hace falta para actuar, no para aprender ---
            'meta': {
                'modo': '4p',
                'match_id': self.match_id,
                'ronda_n': self.ronda_n,
                'fase': self.fase,
                'turno_de': self.turno_de,
                'es_mi_turno': (seat == self.turno_de),
                'mensaje_transicion': self.mensaje_transicion,
                'acciones_legales': self.acciones_legales(seat),
                'puede_pedrete': self.puede_pedrete(seat),
                'match_finalizado': self.match_finalizado,
                'ya_listo': (seat in self.jugadores_listos),
            },
            # --- Bloque A — yo ---
            'A_propio': {
                'asiento': seat,
                'equipo': eq,
                'es_mano': (seat == self.mano),
                'dist_mano': self._dist_mano(seat),
                'cartas': list(cartas),
                'valores': [c['valor'] for c in cartas],
                'valores_mus': get_valores_mus(cartas) if cartas else [],
                'tiene_pares': bool(cartas) and tiene_pares(cartas),
                'pares_tipo': pares_info['tipo'],
                'pares_premio': pares_info['premio'],
                'tiene_juego': suma_juego >= 31,
                'suma_juego': suma_juego,
                'juego_valor': (3 if suma_juego == 31 else 2) if suma_juego >= 31 else 0,
                'descartes_hechos': self.estado[seat]['descartes_hechos'],
                'descartes_listos': self.estado[seat]['descartes_listos'],
                'quiere_mus': self.estado[seat]['quiere_mus'],
            },
            # --- Bloque B — público ---
            'B_publico': {
                'lance': lance,
                'indice_fase': self.indice_fase,
                'rondas_mus': self.rondas_mus,
                'juego_es_punto': self.juego_es_punto,
                'quien_corto_mus': self.quien_corta_mus,
                'otros': otros,
            },
            # --- Bloque C — apuestas ---
            'C_apuestas': {
                'subida_pendiente': subida,
                'es_ordago': es_ordago,
                'apuesta_vista': self.apuesta_vista,
                'botes': dict(self.botes),
                'bote_lance': self.botes.get(nombre_fase, 0) if nombre_fase else 0,
                'owners': {f: relativo(g) for f, g in self.ganadores_fase.items()},
                'apuesta_de_mi_equipo': (None if self.equipo_apostador is None
                                         else self.equipo_apostador == eq),
                'ultimo_apostador_rel': (None if self.ultimo_apostador is None
                                         else (self.ultimo_apostador - seat) % 4),
                'companero_puede_responder': (companero in self.respondedores),
                'deje': deje,
                'coste_ver': (self.apuesta_vista if es_ordago
                              else self.apuesta_vista + self.subida_pendiente),
                'obligado_a_ver': (self.puntos[eq_rival] + deje >= 40),
                'pases_consecutivos': self.pases_consecutivos,
            },
            # --- Bloque D — marcador ---
            'D_marcador': {
                'puntos_equipo': self.puntos[eq],
                'puntos_rival': self.puntos[eq_rival],
                'a_40_propio': 40 - self.puntos[eq],
                'a_40_rival': 40 - self.puntos[eq_rival],
                'partidas_propias': self.partidas_ganadas[eq],
                'partidas_rival': self.partidas_ganadas[eq_rival],
                'al_mejor_de': self.al_mejor_de,
            },
            # --- Bloque E — señas (reservado, todo a cero hasta la Fase 6) ---
            'E_senas': {
                'pareja_pares': 0, 'pareja_juego': 0, 'pareja_31': 0,
                'pareja_reyes': 0, 'pareja_ases': 0, 'confianza': 0.0,
                'cazado_rival_1': 0, 'cazado_rival_3': 0,
            },
        }

    # ==========================================
    # Recuento
    # ==========================================
    def _cmp_lance(self, nombre_lance):
        """Comparador unificado basado en cartas para un lance concreto.

        Devuelve una función cmp(cartas_a, cartas_b) -> 'mano'/'postre', donde
        'mano' = ganó el primer argumento. Envuelve los comparadores de 2p
        (comp_pares_info espera info de pares, no cartas)."""
        if nombre_lance == 'Grande':
            return lambda a, b: comparar_cartas(a, b, True)
        if nombre_lance == 'Chica':
            return lambda a, b: comparar_cartas(a, b, False)
        if nombre_lance == 'Pares':
            return lambda a, b: comp_pares_info(get_pares_info(a), get_pares_info(b))
        if nombre_lance == 'Juego':
            return comp_juego
        if nombre_lance == 'Punto':
            return comp_punto
        raise ValueError(nombre_lance)

    def _comparar_equipos(self, nombre_lance):
        """Devuelve el equipo ganador comparando las manos representativas.

        Reduce cada equipo a su mejor mano (mus_core.mejor_hand_equipo) y luego
        compara las dos representantes; los empates van al asiento más cercano a
        la mano (por eso ordenamos por cercanía y pasamos la más cercana primero)."""
        cmp = self._cmp_lance(nombre_lance)
        cartas_A = {s: self.estado[s]['cartas'] for s in self._asientos_equipo_desde_mano('A')}
        cartas_B = {s: self.estado[s]['cartas'] for s in self._asientos_equipo_desde_mano('B')}
        repr_A = mejor_hand_equipo(cartas_A, cmp)
        repr_B = mejor_hand_equipo(cartas_B, cmp)

        # Ordenamos las dos representantes por cercanía a la mano: la más cercana
        # va primero, así el empate ('mano') la favorece.
        if self._dist_mano(repr_A) <= self._dist_mano(repr_B):
            primera, segunda, eq_primera, eq_segunda = repr_A, repr_B, 'A', 'B'
        else:
            primera, segunda, eq_primera, eq_segunda = repr_B, repr_A, 'B', 'A'

        gan = cmp(self.estado[primera]['cartas'], self.estado[segunda]['cartas'])
        return eq_primera if gan == 'mano' else eq_segunda

    def _bonus_equipo(self, equipo, nombre_fase):
        """Suma el premio de CADA mano cualificada del equipo ganador."""
        total = 0
        if nombre_fase == 'Pares':
            for s in self.equipos[equipo]:
                if tiene_pares(self.estado[s]['cartas']):
                    total += get_pares_info(self.estado[s]['cartas'])['premio']
        elif nombre_fase == 'Juego':
            for s in self.equipos[equipo]:
                if tiene_juego(self.estado[s]['cartas']):
                    total += 3 if get_suma_juego(self.estado[s]['cartas']) == 31 else 2
        return total

    def calcular_recuento(self):
        if self.recuento_calculado:
            return self.pasos_recuento

        self.recuento_calculado = True
        self.pasos_recuento = []
        fases_eval = [self.ordago_aceptado_en] if self.ordago_aceptado_en else self.FASES_APUESTA

        for fase in fases_eval:
            if self.puntos['A'] >= 40 or self.puntos['B'] >= 40:
                break

            ganador_eq = self.ganadores_fase.get(fase)
            bote = self.botes.get(fase, 0)
            pts_bonus = 0
            n_log = fase

            if self.ordago_aceptado_en:
                # Solo se evalúa el lance del órdago; el ganador se lleva la partida.
                if not ganador_eq:
                    if fase in ('Grande', 'Chica', 'Pares'):
                        ganador_eq = self._comparar_equipos(fase)
                    elif fase == 'Juego':
                        a_j = self._equipo_tiene('A', tiene_juego)
                        b_j = self._equipo_tiene('B', tiene_juego)
                        if not a_j and not b_j:
                            n_log = 'Punto'
                            ganador_eq = self._comparar_equipos('Punto')
                        else:
                            ganador_eq = self._comparar_equipos('Juego')
                pts_total = 40
                self.puntos[ganador_eq] = 40
                self.pasos_recuento.append({
                    'ganador_equipo': ganador_eq,
                    'datos': {'code': 'recuento_ordago', 'fase': n_log},
                })
                self._lances_ronda[n_log] = {'win': ganador_eq, 'pts': 40, 'ordago': True}
                continue

            if fase == 'Grande' and not ganador_eq:
                ganador_eq = self._comparar_equipos('Grande')
            elif fase == 'Chica' and not ganador_eq:
                ganador_eq = self._comparar_equipos('Chica')
            elif fase == 'Pares':
                a_p = self._equipo_tiene('A', tiene_pares)
                b_p = self._equipo_tiene('B', tiene_pares)
                if not a_p and not b_p:
                    continue
                if not ganador_eq:
                    if a_p and not b_p:
                        ganador_eq = 'A'
                    elif b_p and not a_p:
                        ganador_eq = 'B'
                    else:
                        ganador_eq = self._comparar_equipos('Pares')
                pts_bonus = self._bonus_equipo(ganador_eq, 'Pares')
            elif fase == 'Juego':
                a_j = self._equipo_tiene('A', tiene_juego)
                b_j = self._equipo_tiene('B', tiene_juego)
                if not a_j and not b_j:
                    n_log = 'Punto'
                    if not ganador_eq:
                        ganador_eq = self._comparar_equipos('Punto')
                    pts_bonus = 1
                else:
                    if not ganador_eq:
                        if a_j and not b_j:
                            ganador_eq = 'A'
                        elif b_j and not a_j:
                            ganador_eq = 'B'
                        else:
                            ganador_eq = self._comparar_equipos('Juego')
                    pts_bonus = self._bonus_equipo(ganador_eq, 'Juego')

            pts_total = bote + pts_bonus
            if pts_total > 0 and ganador_eq:
                self.puntos[ganador_eq] = min(40, self.puntos[ganador_eq] + pts_total)

            deje = self.dejes_fase.get(fase)
            if deje is not None and pts_total == 0:
                datos_paso = {'code': 'recuento_nover', 'fase': n_log}
            else:
                datos_paso = {'code': 'recuento_gana', 'puntos': pts_total, 'fase': n_log}
            self.pasos_recuento.append({'ganador_equipo': ganador_eq, 'datos': datos_paso})
            # `pts` es lo que se apunta en el recuento; `deje` son los puntos que
            # ya se cobraron en el momento del "no quiero" (no se suman dos veces).
            self._lances_ronda[n_log] = {'win': ganador_eq, 'pts': pts_total}
            if deje is not None:
                self._lances_ronda[n_log]['deje'] = deje['valor']

        self._cerrar_ronda()
        return self.pasos_recuento

    def _cerrar_ronda(self):
        """Cierre de ronda: evento `eor`, recuento de partidas y, si toca, `eom`.

        Vive aparte porque hay DOS caminos hasta aquí: el recuento normal y el
        pedrete que llega a 40 (que se salta `calcular_recuento` entero)."""
        # Resolución por lance, marcador y manos finales — la verdad del
        # showdown, que es lo que entrena al belief net de la Fase 3.
        self.log.eor(self.ronda_n, self._lances_ronda,
                     [self.puntos['A'], self.puntos['B']],
                     [[c['valor'] for c in self.estado[s]['cartas']] for s in range(4)])

        # --- Cierre de partida / match ---
        if not self.partida_sumada:
            if self.puntos['A'] >= 40:
                self.partidas_ganadas['A'] += 1
                self.partida_sumada = True
            elif self.puntos['B'] >= 40:
                self.partidas_ganadas['B'] += 1
                self.partida_sumada = True

            if self.partida_sumada:
                objetivo = (self.al_mejor_de // 2) + 1
                if self.partidas_ganadas['A'] >= objetivo or self.partidas_ganadas['B'] >= objetivo:
                    self.match_finalizado = True

        if self.match_finalizado:
            ganador = 'A' if self.partidas_ganadas['A'] > self.partidas_ganadas['B'] else 'B'
            self.log.eom(ganador, [self.partidas_ganadas['A'], self.partidas_ganadas['B']])

    # ==========================================
    # Estado plano: fork() y (de)serialización — Fase 1.3
    # ------------------------------------------------------------------
    # `copy.deepcopy(motor)` era el cuello de botella del gimnasio: el muestreo
    # externo de CFR clona el entorno en CADA acción explorada, y deepcopy
    # recorre también los dicts de carta (valor/palo/img/texto) y el logger.
    #
    # Las cartas son INMUTABLES en la práctica: el motor las mueve de una lista
    # a otra pero nunca las modifica. Así que `fork()` copia los contenedores y
    # COMPARTE los dicts de carta — que es de donde sale la mayor parte de la
    # ganancia. `to_state()/from_state()` sí serializan de verdad (a tuplas
    # planas JSON-ables), y de paso dan gratis la persistencia de partida que
    # pide el Roadmap #18 capa 2.
    # ==========================================
    _CAMPOS_ESCALARES = (
        'mano', 'al_mejor_de', 'match_finalizado', 'partida_sumada', 'fase',
        'indice_fase', 'turno_de', 'apuesta_vista', 'subida_pendiente',
        'quien_sube', 'equipo_apostador', 'ultimo_apostador', 'pases_consecutivos',
        'ordago_aceptado_en', 'juego_es_punto', 'transicion_punto_mostrada',
        'quien_corta_mus', 'rondas_mus', 'recuento_calculado', 'ronda_n',
        'baraja_agotada_aviso', 'match_id',
        'declaracion_pausada', 'declaracion_fase',
    )

    def fork(self):
        """Copia rápida e independiente del motor (sin logger: un fork no escribe)."""
        otro = object.__new__(PartidaMus4)
        d, od = self.__dict__, otro.__dict__
        for campo in PartidaMus4._CAMPOS_ESCALARES:
            od[campo] = d[campo]
        # Constantes compartidas: nadie las muta.
        od['equipos'] = self.equipos
        od['equipo_de'] = self.equipo_de
        od['rng'] = self.rng
        od['nombres'] = self.nombres
        od['usernames'] = self.usernames
        od['baraja'] = self.baraja[:]
        od['descartes'] = self.descartes[:]
        od['estado'] = {s: {'cartas': e['cartas'][:],
                            'quiere_mus': e['quiere_mus'],
                            'descartes_listos': e['descartes_listos'],
                            'descartes_hechos': e['descartes_hechos'],
                            'tiene_pares_dec': e['tiene_pares_dec'],
                            'tiene_juego_dec': e['tiene_juego_dec']}
                        for s, e in self.estado.items()}
        od['puntos'] = dict(self.puntos)
        od['partidas_ganadas'] = dict(self.partidas_ganadas)
        od['botes'] = dict(self.botes)
        od['dejes_fase'] = dict(self.dejes_fase)
        od['ganadores_fase'] = dict(self.ganadores_fase)
        od['respondedores'] = self.respondedores[:]
        od['jugadores_listos'] = self.jugadores_listos[:]
        od['pasos_recuento'] = list(self.pasos_recuento)
        od['declaraciones_pendientes'] = list(self.declaraciones_pendientes)
        od['mensaje_transicion'] = self.mensaje_transicion
        od['_lances_ronda'] = dict(self._lances_ronda)
        od['log'] = _LOG_MUDO
        od['fuente_cartas'] = None
        return otro

    def to_state(self):
        """Estado completo como estructura plana JSON-able."""
        est = {str(s): {'cartas': cartas_a_claves(e['cartas']),
                        'quiere_mus': e['quiere_mus'],
                        'descartes_listos': e['descartes_listos'],
                        'descartes_hechos': e['descartes_hechos'],
                        'tiene_pares_dec': e['tiene_pares_dec'],
                        'tiene_juego_dec': e['tiene_juego_dec']}
               for s, e in self.estado.items()}
        return {
            'v': 1,
            'escalares': {c: getattr(self, c) for c in PartidaMus4._CAMPOS_ESCALARES},
            'baraja': cartas_a_claves(self.baraja),
            'descartes': cartas_a_claves(self.descartes),
            'estado': est,
            'puntos': dict(self.puntos),
            'partidas_ganadas': dict(self.partidas_ganadas),
            'botes': dict(self.botes),
            'dejes_fase': dict(self.dejes_fase),
            'ganadores_fase': dict(self.ganadores_fase),
            'respondedores': list(self.respondedores),
            'jugadores_listos': list(self.jugadores_listos),
            'pasos_recuento': list(self.pasos_recuento),
            'declaraciones_pendientes': [list(d) for d in self.declaraciones_pendientes],
            'mensaje_transicion': self.mensaje_transicion,
            'lances_ronda': dict(self._lances_ronda),
        }

    @classmethod
    def from_state(cls, estado_plano):
        motor = cls()
        for campo, valor in estado_plano['escalares'].items():
            setattr(motor, campo, valor)
        motor.baraja = claves_a_cartas(estado_plano['baraja'])
        motor.descartes = claves_a_cartas(estado_plano['descartes'])
        motor.estado = {int(s): {'cartas': claves_a_cartas(e['cartas']),
                                 'quiere_mus': e['quiere_mus'],
                                 'descartes_listos': e['descartes_listos'],
                                 'descartes_hechos': e['descartes_hechos'],
                                 'tiene_pares_dec': e['tiene_pares_dec'],
                                 'tiene_juego_dec': e['tiene_juego_dec']}
                        for s, e in estado_plano['estado'].items()}
        motor.puntos = dict(estado_plano['puntos'])
        motor.partidas_ganadas = dict(estado_plano['partidas_ganadas'])
        motor.botes = dict(estado_plano['botes'])
        motor.dejes_fase = dict(estado_plano['dejes_fase'])
        motor.ganadores_fase = dict(estado_plano['ganadores_fase'])
        motor.respondedores = list(estado_plano['respondedores'])
        motor.jugadores_listos = list(estado_plano['jugadores_listos'])
        motor.pasos_recuento = list(estado_plano['pasos_recuento'])
        motor.declaraciones_pendientes = [tuple(d) for d in
                                          (estado_plano.get('declaraciones_pendientes') or [])]
        motor.mensaje_transicion = estado_plano['mensaje_transicion']
        motor._lances_ronda = dict(estado_plano.get('lances_ronda') or {})
        motor.log = NullLogger(motor.match_id, '4p')
        return motor

    # ==========================================
    # Avance de ronda / partida
    # ==========================================
    def reiniciar_partida(self):
        """Nueva partida dentro del match: se rota la mano y se ponen a 0 los puntos."""
        self.puntos = {'A': 0, 'B': 0}
        self.partida_sumada = False
        self.mano = self.siguiente_seat(self.mano)
        self.recuento_calculado = False
        self.iniciar_ronda()

    def siguiente_ronda(self):
        """Siguiente ronda de la misma partida (nadie ha llegado a 40)."""
        self.mano = self.siguiente_seat(self.mano)
        self.recuento_calculado = False
        self.iniciar_ronda()

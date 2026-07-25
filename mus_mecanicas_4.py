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

import os
import json
import random
import string
import datetime

from mus_core import (
    crear_baraja, get_valores_mus, tiene_pares, get_pares_info,
    get_suma_juego, tiene_juego, comparar_cartas, comp_pares_info,
    comp_juego, comp_punto, mejor_hand_equipo,
)


class PartidaMus4:
    FASES_APUESTA = ['Grande', 'Chica', 'Pares', 'Juego']

    def __init__(self):
        # Equipos fijos: compañeros enfrentados. A = {0,2}, B = {1,3}.
        self.equipos = {'A': [0, 2], 'B': [1, 3]}
        self.equipo_de = {0: 'A', 1: 'B', 2: 'A', 3: 'B'}

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
        self.respondedores = []            # asientos del equipo rival que aún pueden responder
        self.pases_consecutivos = 0
        self.ordago_aceptado_en = None
        self.juego_es_punto = False
        self.transicion_punto_mostrada = False
        self.quien_corta_mus = None
        self.rondas_mus = 0

        self.mensaje_transicion = None
        self.recuento_calculado = False
        self.pasos_recuento = []
        self.jugadores_listos = []         # asientos listos para la siguiente ronda
        self.ronda_n = 0

        # Logging (misma forma que el JSONL de 2p, con modo='4p').
        self.match_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        self.nombres = {}                  # {asiento: nombre para mostrar}
        self.usernames = {}                # {asiento: username registrado o None}
        self.historial_ia = []
        self.generate_log = True

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

    # ==========================================
    # Logging
    # ==========================================
    def registrar_movimiento(self, seat, accion, cantidad=0, detalles=None):
        if not self.estado[seat]['cartas']:
            return
        fase_actual = self.fase
        if self.fase == 'apuestas' and self.indice_fase < len(self.FASES_APUESTA):
            fase_actual = self.FASES_APUESTA[self.indice_fase]

        hora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        self.historial_ia.append({
            "timestamp": hora,
            "modo": "4p",
            "match_id": self.match_id,
            "ronda_n": self.ronda_n,
            "fase": fase_actual,
            "asiento": seat,
            "equipo": self.equipo_de[seat],
            "es_mano": (seat == self.mano),
            "jugador": self.nombres.get(seat, f"J{seat}"),
            "puntos_equipo": self.puntos[self.equipo_de[seat]],
            "puntos_rival": self.puntos['B' if self.equipo_de[seat] == 'A' else 'A'],
            "cartas_propias": [c['valor'] for c in self.estado[seat]['cartas']],
            "accion": accion,
            "cantidad": cantidad,
            "detalles": detalles,
        })

    # ==========================================
    # Reparto y baraja
    # ==========================================
    def robar(self, cantidad):
        robadas = []
        for _ in range(cantidad):
            if not self.baraja:
                # Sin cartas: rebarajamos los descartes y avisamos (Roadmap #14).
                self.baraja = self.descartes.copy()
                random.shuffle(self.baraja)
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
        self.baraja_agotada_aviso = False

    def repartir_inicial(self):
        self.baraja = crear_baraja()
        random.shuffle(self.baraja)
        self.descartes = []
        for s in self.orden_desde(self.mano):
            self.estado[s]['cartas'] = self.robar(4)
        self.fase = 'mus'
        self.turno_de = self.mano

    # ==========================================
    # Fase de Mus y descartes
    # ==========================================
    def cantar_mus(self, seat, quiere_mus):
        self.registrar_movimiento(seat, 'mus' if quiere_mus else 'no_mus')
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

        self.registrar_movimiento(seat, 'pedrete')
        eq = self.equipo_de[seat]
        self.puntos[eq] += 1

        self.descartes.extend(self.estado[seat]['cartas'])
        self.estado[seat]['cartas'] = self.robar(4)

        if self.puntos[eq] >= 40:
            self.fase = 'recuento'
            self.recuento_calculado = True
            self.pasos_recuento = [{'ganador_equipo': eq, 'datos': {'code': 'recuento_pedrete_win'}}]
        return True

    def procesar_descarte(self, seat, indices_cartas_a_tirar):
        indices_cartas_a_tirar = [int(i) for i in indices_cartas_a_tirar]
        cartas_jugador = self.estado[seat]['cartas']
        valores_tirados = [cartas_jugador[i]['valor']
                           for i in sorted(indices_cartas_a_tirar, reverse=True)]
        self.registrar_movimiento(seat, 'descarte', detalles={"cartas_tiradas": valores_tirados})

        cartas_tiradas = [cartas_jugador.pop(i) for i in sorted(indices_cartas_a_tirar, reverse=True)]
        self.descartes.extend(cartas_tiradas)
        self.estado[seat]['descartes_hechos'] = len(indices_cartas_a_tirar)
        self.estado[seat]['cartas'].extend(self.robar(len(indices_cartas_a_tirar)))
        self.estado[seat]['descartes_listos'] = True

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
        self.respondedores = []
        self.pases_consecutivos = 0

        # Grande la abre quien cortó el mus; el resto de lances empiezan en la mano.
        if nombre_fase == 'Grande' and self.quien_corta_mus is not None:
            self.turno_de = self.quien_corta_mus
        else:
            self.turno_de = self.mano

        if nombre_fase == 'Pares':
            # Declaración automática (sin señas): cada asiento declara según sus cartas.
            for s in range(4):
                self.estado[s]['tiene_pares_dec'] = tiene_pares(self.estado[s]['cartas'])
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
            for s in range(4):
                self.estado[s]['tiene_juego_dec'] = tiene_juego(self.estado[s]['cartas'])
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
        self.registrar_movimiento(seat, accion, cantidad)
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
            self._abrir_respuesta(seat)

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

            if self.dejes_fase.get(fase) is not None and pts_total == 0:
                datos_paso = {'code': 'recuento_nover', 'fase': n_log}
            else:
                datos_paso = {'code': 'recuento_gana', 'puntos': pts_total, 'fase': n_log}
            self.pasos_recuento.append({'ganador_equipo': ganador_eq, 'datos': datos_paso})

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

        # Volcado del log al terminar la partida.
        if self.partida_sumada:
            self._dump_log()

        return self.pasos_recuento

    def _dump_log(self):
        if not self.historial_ia:
            return
        ganador_eq = 'A' if self.puntos['A'] >= self.puntos['B'] else 'B'
        for mov in self.historial_ia:
            mov['gano_ronda'] = (mov['equipo'] == ganador_eq)
            mov['puntos_finales_equipo'] = self.puntos[mov['equipo']]
        if self.generate_log:
            try:
                if not os.path.exists('logs'):
                    os.makedirs('logs')
                ruta = os.path.join('logs', f"{self.match_id}.jsonl")
                with open(ruta, 'a', encoding='utf-8') as f:
                    for mov in self.historial_ia:
                        f.write(json.dumps(mov) + '\n')
            except Exception as e:
                print(f"Error guardando JSONL 4p en {self.match_id}:", e)
        self.historial_ia = []

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

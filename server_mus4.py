# server_mus4.py — Handlers Socket.IO para Mus a 4 jugadores (2v2, online, sin bots).
#
# Se registra sobre la instancia `socketio` ya existente en server.py (que hace
# `import server_mus4` al final, una vez definidos socketio/jugadores/helpers).
# Los eventos usan nombres propios con sufijo `_4` para no colisionar nunca con
# el flujo de 2 jugadores. El registro de salas (salas4) es SEPARADO de `salas`.
#
# El motor (PartidaMus4) está indexado por asiento; aquí vive el mapeo asiento↔sid,
# lo que hace la reconexión trivial (basta reasignar el sid del asiento).

import time
import random
import string

from flask import request, session
from flask_socketio import emit, join_room, leave_room

import base_datos
from mus_mecanicas_4 import PartidaMus4

# Referencias inyectadas por init_mus4() desde server.py (mismo patrón que social.py).
# NO importamos `socketio` desde `server`: server.py se ejecuta como __main__, así
# que `from server import socketio` re-importaría el módulo y registraría los
# handlers en OTRA instancia de socketio distinta de la que corre.
socketio = None
jugadores = None
salas = None

# code -> room dict (ver estructura más abajo)
salas4 = {}

TURNO_SEGUNDOS = 30          # anti-AFK: auto-acción si un jugador no responde
GRACIA_RECONEXION = 90       # ventana para reconectar tras caer en plena partida
TRANSICION_SEGUNDOS = 3      # auto-avance de mensajes de transición (nadie pares, etc.)
RECUENTO_TIMEOUT = 60        # auto-"listo" en el recuento para no bloquear a los demás
ESPERA_REEMPLAZO = 300       # ventana en la que la partida se anuncia buscando sustituto


def _codigo_libre():
    letras = string.ascii_uppercase + string.digits
    while True:
        cod = ''.join(random.choice(letras) for _ in range(4))
        if cod not in salas4 and cod not in salas:
            return cod


def _token():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=12))


# ==========================================
# Lista pública de salas 4p
# ==========================================
def emitir_publicas_4():
    lista = []
    for cod, room in salas4.items():
        ocupados = sum(1 for s in room['asientos'] if s is not None)
        if room['estado'] == 'esperando' and room.get('publico'):
            lista.append({
                'codigo': cod,
                'creador': room.get('creador_nombre', 'Desconocido'),
                'creador_username': room.get('creador_username'),
                'ocupados': ocupados,
                'al_mejor_de': room.get('al_mejor_de', 3),
            })

        # Partida EN CURSO con asientos libres. Solo se anuncia si alguno de los
        # que siguen dentro ha aceptado esperar sustituto, y si queda alguien vivo.
        elif room['estado'] == 'esperando_reemplazo' and room.get('esperando_votos') and ocupados:
            motor = room.get('motor')
            vivo = next((s for s in range(4) if room['asientos'][s] is not None), None)
            lista.append({
                'codigo': cod,
                'creador': room['nombres'].get(vivo, 'Desconocido'),
                'creador_username': room['usernames'].get(vivo),
                'ocupados': ocupados,
                'al_mejor_de': room.get('al_mejor_de', 3),
                'en_curso': True,
                'puntos': dict(motor.puntos) if motor else None,
                'partidas': dict(motor.partidas_ganadas) if motor else None,
                'expira_en': max(0, int(ESPERA_REEMPLAZO - (time.time() - room.get('esperando_desde', 0)))),
            })
    socketio.emit('actualizar_publicas_4', lista)


def handle_pedir_publicas_4():
    emitir_publicas_4()


# ==========================================
# Crear / unirse
# ==========================================
def _asignar_asiento(room, sid, nombre, username, asiento_pedido, token):
    """Sienta a un jugador. Devuelve el asiento asignado o -1 si no hay sitio."""
    asiento = -1
    if isinstance(asiento_pedido, int) and 0 <= asiento_pedido <= 3 and room['asientos'][asiento_pedido] is None:
        asiento = asiento_pedido
    else:
        for s in range(4):
            if room['asientos'][s] is None:
                asiento = s
                break
    if asiento == -1:
        return -1
    room['asientos'][asiento] = sid
    room['nombres'][asiento] = nombre
    room['usernames'][asiento] = username
    room['owners'][asiento] = username           # para reconexión de usuarios
    room['tokens'][asiento] = token              # para reconexión de invitados
    return asiento


def handle_crear_sala_4(datos):
    sid = request.sid
    nombre = (datos.get('nombre') or 'Jugador').strip()
    publico = bool(datos.get('publico', False))
    al_mejor_de = datos.get('al_mejor_de', 3)
    asiento = datos.get('asiento', 0)
    username = session.get('username')
    token = _token()

    codigo = _codigo_libre()
    room = {
        'estado': 'esperando',
        'asientos': [None, None, None, None],
        'motor': None,
        'al_mejor_de': al_mejor_de,
        'publico': publico,
        'creador_username': username,
        'creador_nombre': nombre,
        'ultima_actividad': time.time(),
        'nombres': {}, 'usernames': {}, 'owners': {}, 'tokens': {},
        'turno_token': 0, 'turno_deadline': None,
    }
    salas4[codigo] = room

    asiento_real = _asignar_asiento(room, sid, nombre, username, asiento, token)
    jugadores[sid] = {'nombre': nombre, 'sala': codigo, 'username': username, 'modo4': True}
    join_room(codigo)

    emit('sala_creada_4', {'codigo': codigo, 'asiento': asiento_real, 'token': token})
    _emitir_estado_espera(codigo)
    emitir_publicas_4()


def handle_unirse_sala_4(datos):
    sid = request.sid
    nombre = (datos.get('nombre') or 'Jugador').strip()
    codigo = (datos.get('codigo') or '').upper()
    asiento = datos.get('asiento', None)
    username = session.get('username')
    token = _token()

    room = salas4.get(codigo)
    if not room or room['estado'] not in ('esperando', 'esperando_reemplazo'):
        emit('error_sala_4', {'mensaje': 'La sala no existe o ya está en juego.'})
        return

    # Anti-doble-clic: si ya está sentado, reconfirmamos.
    if sid in room['asientos']:
        emit('sala_creada_4', {'codigo': codigo, 'asiento': room['asientos'].index(sid), 'token': token})
        return

    # Bloqueo de misma cuenta ocupando dos asientos.
    if username:
        for s in range(4):
            if room['asientos'][s] is not None and room['owners'].get(s) == username:
                emit('error_sala_4', {'mensaje': 'Ya estás en esta sala con esta cuenta.'})
                return

    # Entrar de sustituto en una partida ya empezada tiene su propio camino.
    if room['estado'] == 'esperando_reemplazo':
        _sentar_reemplazo_4(codigo, sid, nombre, username, asiento, token)
        return

    asiento_real = _asignar_asiento(room, sid, nombre, username, asiento, token)
    if asiento_real == -1:
        emit('error_sala_4', {'mensaje': 'La sala ya está llena.'})
        return

    jugadores[sid] = {'nombre': nombre, 'sala': codigo, 'username': username, 'modo4': True}
    join_room(codigo)
    emit('sala_creada_4', {'codigo': codigo, 'asiento': asiento_real, 'token': token})

    if all(x is not None for x in room['asientos']):
        _iniciar_partida(codigo)
    else:
        _emitir_estado_espera(codigo)
    emitir_publicas_4()


def _sentar_reemplazo_4(codigo, sid, nombre, username, asiento_pedido, token):
    """Mete a un recién llegado en un asiento vacante de una partida 2v2 en curso.

    Conserva el marcador (puntos y partidas del equipo) pero descarta la ronda que
    estaba en juego y reparte de nuevo en cuanto la mesa vuelve a estar completa:
    quien se fue ya vio esas cartas y así no hay que heredar envites a medias."""
    room = salas4.get(codigo)
    if not room:
        return
    asiento_real = _asignar_asiento(room, sid, nombre, username, asiento_pedido, token)
    if asiento_real == -1:
        emit('error_sala_4', {'mensaje': 'Esa partida ya no admite jugadores.'})
        return

    motor = room['motor']
    motor.nombres[asiento_real] = nombre
    motor.usernames[asiento_real] = username
    jugadores[sid] = {'nombre': nombre, 'sala': codigo, 'username': username, 'modo4': True}
    join_room(codigo)
    room['ultima_actividad'] = time.time()
    emit('sala_creada_4', {'codigo': codigo, 'asiento': asiento_real, 'token': token})

    if not all(x is not None for x in room['asientos']):
        # Aún faltan asientos: seguimos buscando y este ya ve la mesa esperando.
        emit('iniciar_partida_4', {'codigo': codigo})
        _emitir_espera_reemplazo_4(codigo)
        emitir_publicas_4()
        return

    # Mesa completa → ronda nueva conservando el marcador.
    if motor.puntos['A'] >= 40 or motor.puntos['B'] >= 40:
        motor.reiniciar_partida()
        room.pop('registrado_4', None)
    else:
        motor.siguiente_ronda()
    motor.jugadores_listos = []
    motor.mensaje_transicion = None

    room['estado'] = 'jugando'
    room.pop('esperando_desde', None)
    room.pop('esperando_votos', None)
    room.pop('pausada_desde', None)

    socketio.emit('iniciar_partida_4', {'codigo': codigo}, room=codigo)
    socketio.emit('reemplazo_encontrado_4', {'nombre': username or nombre, 'asiento': asiento_real}, room=codigo)
    enviar_estado_4(codigo)
    emitir_publicas_4()


def _emitir_estado_espera(codigo):
    """Envía a la sala la foto de los asientos mientras se espera a que se llene."""
    room = salas4.get(codigo)
    if not room:
        return
    asientos = [{
        'asiento': s,
        'nombre': room['nombres'].get(s),
        'equipo': 'A' if s in (0, 2) else 'B',
        'ocupado': room['asientos'][s] is not None,
    } for s in range(4)]
    socketio.emit('estado_espera_4', {
        'codigo': codigo,
        'asientos': asientos,
        'al_mejor_de': room.get('al_mejor_de', 3),
        'publico': room.get('publico', False),
    }, room=codigo)


def _iniciar_partida(codigo):
    room = salas4.get(codigo)
    if not room:
        return
    motor = PartidaMus4()
    motor.al_mejor_de = room.get('al_mejor_de', 3)
    motor.nombres = {s: room['nombres'].get(s, f'J{s}') for s in range(4)}
    motor.usernames = {s: room['usernames'].get(s) for s in range(4)}
    motor.iniciar_ronda()
    room['motor'] = motor
    room['estado'] = 'jugando'
    room['ultima_actividad'] = time.time()
    socketio.emit('iniciar_partida_4', {'codigo': codigo}, room=codigo)
    enviar_estado_4(codigo)


# ==========================================
# Acciones de juego
# ==========================================
def handle_accion_juego_4(datos):
    sid = request.sid
    for codigo, room in salas4.items():
        if room['estado'] == 'jugando' and sid in room['asientos']:
            seat = room['asientos'].index(sid)
            procesar_accion_4(seat, codigo, datos)
            return


def procesar_accion_4(seat, codigo, datos):
    room = salas4.get(codigo)
    if not room or room['estado'] != 'jugando':
        return
    motor = room['motor']
    room['ultima_actividad'] = time.time()
    accion = datos.get('accion')

    if accion == 'pedrete':
        if motor.procesar_pedrete(seat):
            enviar_estado_4(codigo)
        return

    if seat == motor.turno_de:
        if accion == 'repartir' and motor.fase == 'espera_reparto':
            motor.repartir_inicial()
            enviar_estado_4(codigo)
            return
        elif accion == 'mus':
            motor.cantar_mus(seat, True)
            enviar_estado_4(codigo)
            return
        elif accion == 'no_mus':
            motor.cantar_mus(seat, False)
            enviar_estado_4(codigo)
            return
        elif accion in ('pasar', 'envidar', 'subir', 'ver', 'ordago', 'nover') and motor.fase == 'apuestas':
            motor.accion_apuesta(seat, accion, datos.get('cantidad', 0))
            enviar_estado_4(codigo)
            return

    if accion == 'descartar' and motor.fase == 'descarte':
        if not motor.estado[seat]['descartes_listos']:
            motor.procesar_descarte(seat, datos.get('indices', []))
            enviar_estado_4(codigo)
        return

    if accion == 'continuar_transicion':
        motor.mensaje_transicion = None
        motor.preparar_subfase()
        enviar_estado_4(codigo)
        return

    if accion == 'listo_siguiente_ronda':
        if motor.match_finalizado:
            return
        if seat not in motor.jugadores_listos:
            motor.jugadores_listos.append(seat)
        if len(set(motor.jugadores_listos)) >= 4:
            _avanzar_ronda(codigo)
        else:
            enviar_estado_4(codigo)
        return


def _avanzar_ronda(codigo):
    room = salas4.get(codigo)
    if not room:
        return
    motor = room['motor']
    if motor.match_finalizado:
        return
    if motor.puntos['A'] >= 40 or motor.puntos['B'] >= 40:
        motor.reiniciar_partida()
    else:
        motor.siguiente_ronda()
    motor.jugadores_listos = []
    enviar_estado_4(codigo)


# ==========================================
# Envío de estado (reparto ciego por asiento)
# ==========================================
def _accion_por_defecto(motor):
    """Acción automática al expirar el turno (autoridad del servidor, Roadmap #9)."""
    if motor.fase == 'espera_reparto':
        return 'repartir'
    if motor.fase == 'mus':
        # AFK en el canto: no cortamos el mus unilateralmente; el jugador acepta
        # mus y, si se llega al descarte, se le tiran cartas al azar (ver timer).
        return 'mus'
    if motor.fase == 'apuestas':
        return 'pasar' if motor.subida_pendiente == 0 else 'nover'
    return None


def enviar_estado_4(codigo):
    room = salas4.get(codigo)
    if not room:
        return
    motor = room['motor']
    if not motor:
        return

    # Recuento PRIMERO: calcular_recuento fija puntos/partidas y match_finalizado.
    # (Debe ir antes del registro y del cálculo del ganador.)
    pasos = motor.calcular_recuento() if motor.fase == 'recuento' else None

    # Registro del resultado (una sola vez) al terminar el match.
    if motor.match_finalizado and not room.get('registrado_4'):
        _registrar_resultado_4(motor, room)

    aviso_baraja = getattr(motor, 'baraja_agotada_aviso', False)
    nombre_turno = motor.nombres.get(motor.turno_de) if motor.turno_de is not None else None
    ganador_equipo = None
    if motor.match_finalizado:
        ganador_equipo = 'A' if motor.partidas_ganadas['A'] > motor.partidas_ganadas['B'] else 'B'

    room['turno_token'] = room.get('turno_token', 0) + 1
    token_actual = room['turno_token']

    # Deadline del turno (para la barra de cuenta atrás del cliente).
    deadline = None
    if motor.fase in ('espera_reparto', 'mus', 'apuestas', 'descarte') and not motor.mensaje_transicion:
        deadline = time.time() + TURNO_SEGUNDOS
        room['turno_deadline'] = deadline

    for seat in range(4):
        sid = room['asientos'][seat]
        if sid is None:
            continue
        mi_equipo = motor.equipo_de[seat]
        eq_rival = 'B' if mi_equipo == 'A' else 'A'

        # Info de asientos (pública, sin cartas salvo en recuento).
        seats_info = []
        for s in range(4):
            info = {
                'asiento': s,
                'nombre': motor.nombres.get(s, f'J{s}'),
                'equipo': motor.equipo_de[s],
                'es_mano': (s == motor.mano),
                'descartes_hechos': motor.estado[s]['descartes_hechos'],
                'pares_dec': motor.estado[s]['tiene_pares_dec'],
                'juego_dec': motor.estado[s]['tiene_juego_dec'],
                'presente': room['asientos'][s] is not None,
                'listo': (s in motor.jugadores_listos),
            }
            if motor.fase == 'recuento':
                info['cartas'] = motor.estado[s]['cartas']
            seats_info.append(info)

        # Dejes (concesiones por no-ver).
        dejes = {}
        for f, d in motor.dejes_fase.items():
            if d is not None:
                dejes[f] = {'gano_mi_equipo': (d['ganador'] == mi_equipo), 'valor': d['valor']}

        info_apuestas = {
            'fase_actual': motor.FASES_APUESTA[motor.indice_fase] if (motor.fase == 'apuestas' and motor.indice_fase < len(motor.FASES_APUESTA)) else '',
            'subida': motor.subida_pendiente,
            'botes': motor.botes,
            'dejes': dejes,
            'apuesta_vista': motor.apuesta_vista,
            'mi_equipo_sube': (motor.quien_sube == mi_equipo),
            'equipo_apostador': motor.equipo_apostador,
            'juego_es_punto': motor.juego_es_punto,
        }

        # Mensaje de estado (mismos códigos que 2p; el cliente los localiza).
        if motor.fase == 'descarte':
            mensaje = {'code': 'fase_descarte'}
        elif motor.fase == 'apuestas':
            if motor.indice_fase < len(motor.FASES_APUESTA):
                mensaje = {'code': 'fase_apuestas', 'fase': info_apuestas['fase_actual'], 'jugador': nombre_turno}
            else:
                mensaje = {'code': 'fase_recuento'}
        else:
            mensaje = {'code': 'fase_general', 'fase': motor.fase, 'jugador': nombre_turno}

        # Pedrete disponible para este asiento.
        puede_pedrete = False
        if motor.fase in ('mus', 'descarte'):
            vals = sorted([c['valor'] for c in motor.estado[seat]['cartas']])
            puede_pedrete = (vals == [4, 5, 6, 7])

        datos_recuento = None
        if pasos is not None:
            datos_recuento = [{
                'gano_mi_equipo': (paso['ganador_equipo'] == mi_equipo),
                'datos': paso['datos'],
            } for paso in pasos]

        payload = {
            'para_sid': sid,
            'mi_asiento': seat,
            'mi_equipo': mi_equipo,
            'mano': motor.mano,
            'turno_de': motor.turno_de,
            'es_mi_turno': (seat == motor.turno_de),
            'fase': motor.fase,
            'mis_cartas': motor.estado[seat]['cartas'],
            'mis_descartes_listos': motor.estado[seat]['descartes_listos'],
            'seats': seats_info,
            'puntos': motor.puntos,
            'mis_puntos_equipo': motor.puntos[mi_equipo],
            'puntos_rival_equipo': motor.puntos[eq_rival],
            'partidas': motor.partidas_ganadas,
            'al_mejor_de': motor.al_mejor_de,
            'apuestas': info_apuestas,
            'mensaje': mensaje,
            'mensaje_transicion': motor.mensaje_transicion,
            'recuento': datos_recuento,
            'puede_pedrete': puede_pedrete,
            'match_finalizado': motor.match_finalizado,
            'ganador_equipo': ganador_equipo,
            'aviso_baraja': aviso_baraja,
            'turno_deadline_epoch': deadline,
        }
        socketio.emit('actualizar_mesa_4', payload, room=codigo)

    # El aviso de baraja agotada se muestra una sola vez.
    if aviso_baraja:
        motor.baraja_agotada_aviso = False

    _programar_timers(codigo, token_actual)


def _registrar_resultado_4(motor, room):
    room['registrado_4'] = True
    ganador = 'A' if motor.partidas_ganadas['A'] > motor.partidas_ganadas['B'] else 'B'
    perdedor = 'B' if ganador == 'A' else 'A'
    g_users = [motor.usernames.get(s) for s in motor.equipos[ganador]]
    p_users = [motor.usernames.get(s) for s in motor.equipos[perdedor]]
    try:
        base_datos.registrar_partida_4(
            g_users, p_users,
            motor.partidas_ganadas[ganador], motor.partidas_ganadas[perdedor],
            motor.match_id, motor.al_mejor_de)
    except Exception as e:
        print(f"⚠️ Error registrando partida 4p {motor.match_id}: {e}")


# ==========================================
# Temporizadores autoritativos (turno / transición / recuento)
# ==========================================
def _programar_timers(codigo, token):
    room = salas4.get(codigo)
    if not room or room['estado'] != 'jugando':
        return
    motor = room['motor']
    if motor.match_finalizado:
        return

    if motor.mensaje_transicion:
        kind, delay = 'transicion', TRANSICION_SEGUNDOS
    elif motor.fase == 'recuento':
        kind, delay = 'recuento', RECUENTO_TIMEOUT
    elif motor.fase == 'descarte':
        kind, delay = 'descarte', TURNO_SEGUNDOS
    elif motor.fase in ('espera_reparto', 'mus', 'apuestas'):
        kind, delay = 'turno', TURNO_SEGUNDOS
    else:
        return

    def tarea():
        socketio.sleep(delay)
        r = salas4.get(codigo)
        if not r or r['estado'] != 'jugando' or r.get('turno_token') != token:
            return  # el estado avanzó: temporizador obsoleto e inofensivo
        m = r['motor']
        if kind == 'transicion':
            m.mensaje_transicion = None
            m.preparar_subfase()
            enviar_estado_4(codigo)
        elif kind == 'recuento':
            for s in range(4):
                if s not in m.jugadores_listos:
                    m.jugadores_listos.append(s)
            _avanzar_ronda(codigo)
        elif kind == 'descarte':
            for s in range(4):
                if not m.estado[s]['descartes_listos']:
                    # AFK en el descarte: se tira una selección aleatoria de al
                    # menos una carta (regla acordada para no dejar la mano intacta).
                    n = len(m.estado[s]['cartas'])
                    indices = random.sample(range(n), random.randint(1, n)) if n else []
                    m.procesar_descarte(s, indices)
            enviar_estado_4(codigo)
        elif kind == 'turno':
            acc = _accion_por_defecto(m)
            if acc:
                procesar_accion_4(m.turno_de, codigo, {'accion': acc})

    socketio.start_background_task(tarea)


# ==========================================
# Conexión: abandono, desconexión y reconexión
# ==========================================
def handle_abandonar_sala_4():
    """Salida voluntaria. Desde el vestíbulo solo libera el asiento; desde la mesa
    (botón «Salir», ya confirmado en el cliente) la partida NO muere: el asiento
    queda vacante y a los que siguen se les pregunta si esperan sustituto o se van
    también. La sala aguanta mientras quede al menos un jugador esperando."""
    sid = request.sid
    _quitar_sid(sid, abandono_voluntario=True)


def handle_esperar_reemplazo_4():
    """Uno de los que se quedan acepta esperar: la partida se anuncia como en curso."""
    sid = request.sid
    for codigo, room in salas4.items():
        if sid not in room['asientos']:
            continue
        if room['estado'] != 'esperando_reemplazo':
            return
        room.setdefault('esperando_votos', set()).add(room['asientos'].index(sid))
        _emitir_espera_reemplazo_4(codigo)
        emitir_publicas_4()
        return


def _emitir_espera_reemplazo_4(codigo):
    """Avisa a los que siguen sentados de cuántos huecos faltan y cuánto queda."""
    room = salas4.get(codigo)
    if not room:
        return
    libres = [s for s in range(4) if room['asientos'][s] is None]
    restante = max(0, int(ESPERA_REEMPLAZO - (time.time() - room.get('esperando_desde', time.time()))))
    socketio.emit('esperando_reemplazo_4',
                  {'libres': libres, 'segundos': restante}, room=codigo)


def _abrir_hueco_4(codigo, seat, nombre, motivo):
    """Libera un asiento de una partida 2v2 en curso y ofrece esperar sustituto."""
    room = salas4.get(codigo)
    if not room:
        return
    room['asientos'][seat] = None
    room.get('esperando_votos', set()).discard(seat)

    if all(s is None for s in room['asientos']):
        _destruir_sala(codigo)
        return

    room['estado'] = 'esperando_reemplazo'
    room.setdefault('esperando_desde', time.time())
    room.setdefault('esperando_votos', set())
    # Para poder rellenar el hueco hay que ser visible: una sala privada se publica
    # mientras dure la espera (decidido con el usuario).
    room['publico'] = True
    socketio.emit('jugador_abandono_4',
                  {'asiento': seat, 'nombre': nombre, 'motivo': motivo,
                   'espera': ESPERA_REEMPLAZO}, room=codigo)
    _programar_fin_espera_4(codigo, room['esperando_desde'])
    emitir_publicas_4()


def _programar_fin_espera_4(codigo, marca):
    """Si nadie ocupa los huecos dentro de la ventana, la partida se da por acabada."""
    def tarea():
        socketio.sleep(ESPERA_REEMPLAZO)
        r = salas4.get(codigo)
        if r and r['estado'] == 'esperando_reemplazo' and r.get('esperando_desde') == marca:
            socketio.emit('rival_desconectado_4', {'motivo': 'sin_reemplazo'}, room=codigo)
            _destruir_sala(codigo)
    socketio.start_background_task(tarea)


def handle_reanudar_partida_4(datos):
    sid = request.sid
    codigo = (datos.get('codigo') or '').upper()
    token = datos.get('token')
    username = session.get('username')

    room = salas4.get(codigo)
    if not room or room['estado'] not in ('pausada', 'jugando', 'esperando_reemplazo'):
        emit('error_sala_4', {'mensaje': 'No hay ninguna partida que reanudar.'})
        return

    # Identificamos el asiento por IDENTIDAD (username/token), esté o no vacío.
    # En un refresco rápido el socket NUEVO llega ANTES de que el servidor detecte
    # la caída del viejo, así que el asiento puede seguir ocupado por un sid muerto:
    # hay que reclamarlo igualmente (si exigiéramos asiento vacío, fallaría la
    # reconexión y el jugador se quedaría sin botones).
    seat = None
    for s in range(4):
        if username and room['owners'].get(s) == username:
            seat = s
            break
        if token and room['tokens'].get(s) == token:
            seat = s
            break
    if seat is None:
        emit('error_sala_4', {'mensaje': 'No se encontró tu asiento para reanudar.'})
        return

    # Desalojamos el sid viejo (muerto) que aún pudiera ocupar el asiento.
    old_sid = room['asientos'][seat]
    if old_sid and old_sid != sid:
        jugadores.pop(old_sid, None)
    room['asientos'][seat] = sid
    nombre = room['nombres'].get(seat, 'Jugador')
    jugadores[sid] = {'nombre': nombre, 'sala': codigo, 'username': username, 'modo4': True}
    join_room(codigo)

    estado_previo = room['estado']
    if all(x is not None for x in room['asientos']):
        room['estado'] = 'jugando'
        room.pop('pausada_desde', None)
        # Volvió justo cuando ya se buscaba sustituto: se cancela la búsqueda.
        room.pop('esperando_desde', None)
        room.pop('esperando_votos', None)
        if estado_previo == 'esperando_reemplazo':
            emitir_publicas_4()

    emit('reanudado_4', {'codigo': codigo, 'asiento': seat})
    socketio.emit('jugador_reconectado_4', {'asiento': seat}, room=codigo)
    if room['estado'] == 'esperando_reemplazo':
        _emitir_espera_reemplazo_4(codigo)
        emitir_publicas_4()
    enviar_estado_4(codigo)


def _quitar_sid(sid, abandono_voluntario=False):
    """Saca un sid de su sala 4p (abandono o desconexión)."""
    for codigo, room in list(salas4.items()):
        if sid not in room['asientos']:
            continue
        seat = room['asientos'].index(sid)
        estado = room['estado']

        try:
            leave_room(codigo)
        except Exception:
            pass

        if estado == 'esperando':
            room['asientos'][seat] = None
            room['nombres'].pop(seat, None)
            room['usernames'].pop(seat, None)
            room['owners'].pop(seat, None)
            room['tokens'].pop(seat, None)
            if all(s is None for s in room['asientos']):
                salas4.pop(codigo, None)
            else:
                _emitir_estado_espera(codigo)
            emitir_publicas_4()

        elif estado in ('jugando', 'pausada', 'esperando_reemplazo'):
            nombre = room['nombres'].get(seat, 'Jugador')
            motor = room.get('motor')
            if abandono_voluntario:
                # Salida explícita. Si el match ya terminó no hay nada que ofrecer;
                # si no, el asiento queda vacante y los demás deciden.
                room['tokens'].pop(seat, None)
                jugadores.pop(sid, None)
                if not motor or motor.match_finalizado:
                    room['asientos'][seat] = None
                    if all(s is None for s in room['asientos']):
                        _destruir_sala(codigo)
                    else:
                        emitir_publicas_4()
                else:
                    _abrir_hueco_4(codigo, seat, nombre, motivo='abandono')
            elif estado == 'esperando_reemplazo':
                # Se cae uno de los que esperaban. Conservamos su token y su voto por
                # si es un refresco (`reanudar_partida_4` lo devuelve a su asiento);
                # si no vuelve, lo barre el temporizador de la ventana de espera.
                room['asientos'][seat] = None
                emitir_publicas_4()
            else:
                # Desconexión → pausa con ventana de gracia para reconectar.
                room['asientos'][seat] = None
                room['estado'] = 'pausada'
                room['pausada_desde'] = time.time()
                socketio.emit('jugador_desconectado_4', {'asiento': seat}, room=codigo)
                _programar_fin_por_gracia(codigo)
        break


def _programar_fin_por_gracia(codigo):
    """Agotada la gracia, el asiento se declara vacante en vez de matar la partida:
    los que siguen dentro deciden si esperan un sustituto o se van."""
    def tarea():
        socketio.sleep(GRACIA_RECONEXION)
        r = salas4.get(codigo)
        if not r or r['estado'] != 'pausada':
            return
        libres = [s for s in range(4) if r['asientos'][s] is None]
        motor = r.get('motor')
        if not libres or not motor or motor.match_finalizado:
            socketio.emit('rival_desconectado_4', {'motivo': 'timeout'}, room=codigo)
            _destruir_sala(codigo)
            return
        seat = libres[0]
        _abrir_hueco_4(codigo, seat, r['nombres'].get(seat, 'Un jugador'), motivo='timeout')
    socketio.start_background_task(tarea)


def _destruir_sala(codigo):
    room = salas4.pop(codigo, None)
    if not room:
        return
    for sid in room['asientos']:
        if sid and sid in jugadores and jugadores[sid].get('sala') == codigo:
            jugadores.pop(sid, None)
    emitir_publicas_4()


def disconnect_4():
    # Flask-SocketIO 5.x solo admite UN handler por evento, así que NO registramos
    # nuestro propio 'disconnect': server.py llama a esta función desde el suyo
    # (igual que a social.presencia_disconnect). Escanea salas4 por request.sid
    # sin depender de jugadores[sid], que el handler de 2p ya pudo borrar.
    _quitar_sid(request.sid, abandono_voluntario=False)


# ==========================================
# Barredor de salas fantasma (Roadmap #21)
# ==========================================
def _barredor():
    while True:
        socketio.sleep(300)  # cada 5 min
        ahora = time.time()
        for codigo, room in list(salas4.items()):
            estado = room['estado']
            edad = ahora - room.get('ultima_actividad', ahora)
            if estado == 'esperando' and edad > 1800:            # >30 min esperando
                _destruir_sala(codigo)
            elif estado == 'jugando' and edad > 7200:            # >2 h inactiva
                socketio.emit('rival_desconectado_4', {'motivo': 'idle'}, room=codigo)
                _destruir_sala(codigo)
            elif estado == 'pausada' and (ahora - room.get('pausada_desde', ahora)) > GRACIA_RECONEXION:
                socketio.emit('rival_desconectado_4', {'motivo': 'timeout'}, room=codigo)
                _destruir_sala(codigo)
            elif estado == 'esperando_reemplazo' and (ahora - room.get('esperando_desde', ahora)) > ESPERA_REEMPLAZO:
                socketio.emit('rival_desconectado_4', {'motivo': 'sin_reemplazo'}, room=codigo)
                _destruir_sala(codigo)


# ==========================================
# Inicialización: registra los handlers sobre la instancia real de socketio
# (la de server.py/__main__), igual que social.init_social. Ver comentario arriba.
# ==========================================
def init_mus4(sio, jugadores_ref, salas_ref):
    global socketio, jugadores, salas
    socketio = sio
    jugadores = jugadores_ref
    salas = salas_ref

    sio.on('pedir_publicas_4')(handle_pedir_publicas_4)
    sio.on('crear_sala_4')(handle_crear_sala_4)
    sio.on('unirse_sala_4')(handle_unirse_sala_4)
    sio.on('accion_juego_4')(handle_accion_juego_4)
    sio.on('abandonar_sala_4')(handle_abandonar_sala_4)
    sio.on('abandonar_partida_4')(handle_abandonar_sala_4)
    sio.on('esperar_reemplazo_4')(handle_esperar_reemplazo_4)
    sio.on('reanudar_partida_4')(handle_reanudar_partida_4)
    # 'disconnect' NO se registra aquí (solo se admite un handler por evento):
    # server.py llama a server_mus4.disconnect_4() desde su propio handler.

    sio.start_background_task(_barredor)
    print("👥 Mus 4 jugadores: handlers registrados.")


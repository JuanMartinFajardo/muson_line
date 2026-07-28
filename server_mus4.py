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
import decks
import mus_senas
import analitica          # medición de audiencia (Roadmap #24); nunca lanza
import seguridad          # validación de entrada en el borde (Roadmap #16.6)
from mus_mecanicas_4 import PartidaMus4
from bot_ml_4 import SmartBot4, PERSONALIDADES, PERSONALIDAD_POR_DEFECTO

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
# Ronda de cantes de Pares/Juego: lo que se tarda de un «¡pares sí!» al siguiente.
# En una mesa de verdad, antes de envidar a pares todos dicen si los llevan; el
# motor ya lo declaraba, pero de golpe y sin que se viera. Repartido en el tiempo
# la mesa respira como la de casa. Cuatro asientos ≈ 2,8 s por lance.
DECLARACION_SEGUNDOS = 0.7
ESPERA_REEMPLAZO = 300       # ventana en la que la partida se anuncia buscando sustituto

# Log v2 (mus_log.py). Encendido: cada partida 2v2 deja un JSONL reproducible en
# logs/v2, que es el corpus de entrenamiento de las fases 2–4. Los soaks lo
# apagan ANTES de crear la mesa (`S.LOG_V2 = False`) para no ensuciar el corpus
# con miles de partidas de prueba.
LOG_V2 = True

# --- Señas (2v2) -----------------------------------------------------------
# Valores por defecto; todos se pueden ajustar en caliente desde /admin.
FOCO_COOLDOWN = 1.0          # s mínimos entre dos cambios de foco (anti-barrido)
FOCO_SOLAPE = 1.0            # s que sigues viendo al que acabas de dejar de mirar
SENA_COOLDOWN = 3.0          # s entre dos señas del mismo jugador
DENUNCIA_COOLDOWN = 2.0      # s entre dos denuncias del mismo jugador
# Fases en las que tiene sentido señalar: ya tienes cartas y aún se juega la mano.
# En el descarte no: el cliente clava el foco en tus propias cartas y nadie miraría.
FASES_CON_SENAS = ('mus', 'apuestas')
# En el recuento las cuatro manos están sobre la mesa: el juego de mirar se apaga
# entero (ni señas, ni miradas, ni denuncias) hasta que se reparta de nuevo.
FASES_SIN_FOCO = ('recuento',)

# Regiones que ve el jugador, en su propio marco de referencia. Coincide con la
# colocación de la mesa (ver slotDeAsiento4 en static/table4.js): la pareja
# enfrente, los rivales a los lados.
REGIONES = {'frente': 2, 'izquierda': 1, 'derecha': 3}


def _codigo_libre():
    letras = string.ascii_uppercase + string.digits
    while True:
        cod = ''.join(random.choice(letras) for _ in range(4))
        if cod not in salas4 and cod not in salas:
            return cod


def _token():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=12))


# ==========================================
# Asientos ocupados por bots (Roadmap 4p, Fase 0.2)
# ------------------------------------------------------------------
# Un bot es un asiento con un sid falso `BOT_<codigo>_<asiento>`: para todo el
# resto del servidor es un jugador más (ocupa asiento, sale en el estado, cuenta
# para arrancar la partida), solo que nunca hay un socket detrás. La instancia
# vive en room['bots'][asiento] y actúa desde el hook de difusión de estado.
# ==========================================
def _es_bot(sid):
    return bool(sid) and str(sid).startswith('BOT_')


def _humanos_sentados(room):
    """Asientos ocupados por personas de verdad. Una sala sin ninguno se cierra:
    no tiene sentido que cuatro bots sigan jugando solos."""
    return [s for s in room['asientos'] if s is not None and not _es_bot(s)]


# --- Barajas (Roadmap #5) ---------------------------------------------------
# Cada asiento se pinta con la baraja de quien lo ocupa, así que la suya viaja
# con el estado de la mesa. El registro lo lleva decks.py, indexado por sid; lo
# alimenta el evento `mi_baraja`, que atiende server.py para los dos modos.

def _baraja_de_asiento(room, seat):
    sid = room['asientos'][seat]
    if sid is None or _es_bot(sid):
        return dict(decks.CONFIG_DEFECTO)     # el asiento vacío y el bot, clásica
    return decks.baraja_en_mesa(sid, room['usernames'].get(seat))


def difundir_baraja_4(sid, config):
    """Alguien ha cambiado de baraja en «Mis barajas»: se avisa a su mesa para
    que repinte sus cartas al momento. Va suelto y no como estado completo,
    porque una difusión de estado reinicia el reloj del turno."""
    for codigo, room in salas4.items():
        if sid in room['asientos']:
            socketio.emit('baraja_mesa_4',
                          {'asiento': room['asientos'].index(sid), 'config': config},
                          room=codigo)
            return


def _mejor_de_4(valor):
    """«Al mejor de» saneado: impar, entre 1 y 21 (Roadmap #16.6). Gemelo del
    `_mejor_de` de server.py; están separados porque los dos módulos se cargan
    por su cuenta y no comparten más que `seguridad`."""
    n = seguridad.entero(valor, 1, 21, 3)
    return n if n % 2 else min(21, n + 1)


def _normalizar_bots(datos):
    """Lee del cliente qué asientos quiere rellenar con bots.

    Acepta `bots` como lista de asientos ([1,2,3]) o como mapa
    asiento→personalidad ({"1": "agresivo"}); `personalidad` fija la que se usa
    para los asientos sin una propia. Devuelve {asiento: personalidad}."""
    por_defecto = datos.get('personalidad') or PERSONALIDAD_POR_DEFECTO
    if por_defecto not in PERSONALIDADES:
        por_defecto = PERSONALIDAD_POR_DEFECTO

    pedidos = datos.get('bots') or []
    salida = {}
    items = pedidos.items() if isinstance(pedidos, dict) else [(s, None) for s in pedidos]
    for asiento, personalidad in items:
        try:
            seat = int(asiento)
        except (TypeError, ValueError):
            continue
        if not 0 <= seat <= 3:
            continue
        salida[seat] = personalidad if personalidad in PERSONALIDADES else por_defecto
    return salida


def _sentar_bot(room, codigo, seat, personalidad):
    """Ocupa un asiento libre con un bot. Sin token ni username: no reconecta ni
    puntúa, y `owners`/`tokens` se dejan vacíos para que nadie lo reclame."""
    sid = f'BOT_{codigo}_{seat}'
    room['asientos'][seat] = sid
    room['nombres'][seat] = f'Bot {seat}'
    room['usernames'][seat] = None
    room['owners'][seat] = None
    room['tokens'][seat] = None
    room['bots'][seat] = SmartBot4(sid, seat, personalidad)
    return sid


# ==========================================
# Señas (2v2)
# ------------------------------------------------------------------
# El servidor es el ÚNICO que sabe quién mira a quién, y por eso es el único
# que puede repartir señas y miradas. Un cliente parcheado no puede espiar una
# seña que no le corresponde porque nunca le llega el evento: `sena_vista_4`
# sale sólo hacia los sids que en ese instante estaban mirando al que la hizo.
#
# Cada asiento guarda en room['foco']:
#   objetivo      → asiento al que mira, o 'abajo' (sus propias cartas)
#   desde         → cuándo empezó a mirar ahí (para el cooldown)
#   previo        → a quién miraba antes
#   previo_hasta  → hasta cuándo sigue viendo también al anterior (solape)
# El solape es lo que impide señalar justo cuando el rival aparta la vista.
# ==========================================
def _cfg(clave, defecto, minimo, maximo):
    valor = base_datos.config_get_float(clave, defecto)
    return min(max(valor, minimo), maximo)


def _foco_apagado(room):
    """¿Está el juego de mirar en pausa? En el recuento sí: las manos se enseñan
    enteras, así que no hay nada que espiar ni nadie a quien mirar."""
    motor = room.get('motor')
    return bool(motor) and motor.fase in FASES_SIN_FOCO


def _foco_de(room, seat):
    return room.setdefault('foco', {}).get(seat)


def _objetivo_a_region(seat, objetivo):
    """Traduce un asiento absoluto a la región que ve `seat` (frente/izq/dcha)."""
    if objetivo == 'abajo' or objetivo is None:
        return 'abajo'
    for region, salto in REGIONES.items():
        if (seat + salto) % 4 == objetivo:
            return region
    return None


def _region_a_objetivo(seat, region):
    """Y al revés: qué asiento (o 'abajo') hay en esa región para `seat`."""
    if region == 'abajo':
        return 'abajo'
    salto = REGIONES.get(region)
    return (seat + salto) % 4 if salto is not None else None


def _mirada_de(room, seat, ahora=None):
    """A quién mira un asiento ahora mismo.

    Los bots no tienen cliente que informe, así que su mirada se sortea aquí y
    se renueva sola cada 1,2-2,6 s (ver `_ticker_miradas`): al mirarles, la cara
    se mueve como la de cualquiera y no se les distingue por estar quietos."""
    ahora = ahora or time.time()
    foco = _foco_de(room, seat)
    if _es_bot(room['asientos'][seat]):
        if not foco or ahora >= foco.get('hasta', 0):
            objetivo = random.choice([s for s in range(4) if s != seat])
            foco = {'objetivo': objetivo, 'desde': ahora, 'previo': None,
                    'previo_hasta': 0, 'hasta': ahora + random.uniform(1.2, 2.6)}
            room.setdefault('foco', {})[seat] = foco
        return foco['objetivo']
    return foco['objetivo'] if foco else None


def _observadores(room, objetivo, ahora=None):
    """Asientos (con socket) que en este instante ven a `objetivo`.

    Cuenta tanto el foco actual como el anterior mientras dure el solape, que es
    justo lo que hace que una seña hecha "al filo" siga viéndose."""
    ahora = ahora or time.time()
    if _foco_apagado(room):
        return []                     # recuento: nadie mira a nadie
    salida = []
    for s in range(4):
        sid = room['asientos'][s]
        if sid is None or _es_bot(sid) or s == objetivo:
            continue
        foco = _foco_de(room, s)
        if not foco:
            continue
        if foco['objetivo'] == objetivo or (foco.get('previo') == objetivo and ahora < foco.get('previo_hasta', 0)):
            salida.append((s, sid))
    return salida


def _difundir_mirada(room, seat, ahora=None):
    """Avisa a quien esté mirando a `seat` de que ha cambiado de mirada."""
    ahora = ahora or time.time()
    mira = _mirada_de(room, seat, ahora)
    for _, sid_obs in _observadores(room, seat, ahora):
        socketio.emit('mirada_4', {'asiento': seat, 'mira': mira}, to=sid_obs)


def _sala_de_sid(sid, estados=('jugando',)):
    """Sala y asiento de un sid, o (None, None, None)."""
    for codigo, room in salas4.items():
        if room['estado'] in estados and sid in room['asientos']:
            return codigo, room, room['asientos'].index(sid)
    return None, None, None


def _sembrar_foco(room, seat):
    """Foco inicial de quien se sienta: mirando a su pareja, como en la mesa."""
    if not room.get('senas'):
        return
    ahora = time.time()
    room.setdefault('foco', {})[seat] = {
        'objetivo': (seat + 2) % 4, 'desde': ahora,
        'previo': None, 'previo_hasta': 0,
    }


def handle_foco_4(datos):
    """El cliente informa de a dónde mira. Es la única fuente de la verdad para
    repartir señas, así que aquí se valida el cooldown y se guarda el solape."""
    sid = request.sid
    codigo, room, seat = _sala_de_sid(sid)
    if not room or not room.get('senas') or _foco_apagado(room):
        return
    region = (datos or {}).get('region')
    objetivo = _region_a_objetivo(seat, region)
    if objetivo is None:
        return

    ahora = time.time()
    foco = _foco_de(room, seat)
    if foco and foco['objetivo'] == objetivo:
        return                                  # ya estaba mirando ahí
    if foco and (ahora - foco['desde']) < _cfg('senas_foco_cooldown', FOCO_COOLDOWN, 0, 10):
        # Demasiado rápido: se rechaza y el cliente vuelve a donde estaba.
        emit('foco_4', {'region': _objetivo_a_region(seat, foco['objetivo']), 'rechazado': True})
        return

    solape = _cfg('senas_foco_solape', FOCO_SOLAPE, 0, 10)
    room['foco'][seat] = {
        'objetivo': objetivo, 'desde': ahora,
        'previo': foco['objetivo'] if foco else None,
        'previo_hasta': ahora + solape if foco else 0,
    }

    # Al que mira se le manda de golpe la mirada de a quién acaba de enfocar (y
    # la del que deja atrás durante el solape): así la cara aparece ya orientada.
    miradas = {}
    for candidato in (objetivo, foco['objetivo'] if foco else None):
        if isinstance(candidato, int):
            miradas[str(candidato)] = _mirada_de(room, candidato, ahora)
    emit('foco_4', {
        'region': region,
        'previo': _objetivo_a_region(seat, foco['objetivo']) if foco else None,
        'solape_ms': int(solape * 1000) if foco else 0,
        'miradas': miradas,
    })

    # Y a quien estuviera mirándole a él, que ha movido los ojos.
    _difundir_mirada(room, seat, ahora)


def handle_sena_4():
    """Hacer una seña. No se elige: sale la más alta que permita la mano."""
    sid = request.sid
    codigo, room, seat = _sala_de_sid(sid)
    if not room or not room.get('senas'):
        return
    motor = room.get('motor')
    if not motor or motor.fase not in FASES_CON_SENAS or motor.mensaje_transicion:
        return

    ahora = time.time()
    ultimas = room.setdefault('ultima_sena', {})
    if ahora - ultimas.get(seat, 0) < _cfg('senas_cooldown', SENA_COOLDOWN, 0, 60):
        return

    sena = mus_senas.sena_de(motor.estado[seat]['cartas'], mus_senas.orden_configurado())
    if not sena:
        return
    ultimas[seat] = ahora

    # Al que la hace se le confirma cuál le ha salido (no se ve su propia cara).
    emit('sena_hecha_4', {'sena': sena})
    for _, sid_obs in _observadores(room, seat, ahora):
        socketio.emit('sena_vista_4', {'asiento': seat, 'sena': sena}, to=sid_obs)


def handle_denuncia_sena_4(datos):
    """«Te he visto». Es puro tanteo social: no da ni quita puntos, sólo se
    anuncia en la mesa. Se denuncia a un rival (a la pareja no tendría sentido)."""
    sid = request.sid
    codigo, room, seat = _sala_de_sid(sid)
    if not room or not room.get('senas') or _foco_apagado(room):
        return
    motor = room.get('motor')
    if not motor:
        return

    datos = datos or {}
    try:
        acusado = int(datos.get('asiento'))
    except (TypeError, ValueError):
        return
    sena = datos.get('sena')
    if not (0 <= acusado <= 3) or not mus_senas.es_sena(sena):
        return
    if motor.equipo_de[acusado] == motor.equipo_de[seat]:
        return

    ahora = time.time()
    ultimas = room.setdefault('ultima_denuncia', {})
    if ahora - ultimas.get(seat, 0) < DENUNCIA_COOLDOWN:
        return
    ultimas[seat] = ahora

    socketio.emit('denuncia_4', {'de': seat, 'a': acusado, 'sena': sena}, room=codigo)


def _ticker_miradas():
    """Mueve los ojos de los bots.

    Un único greenlet para todo el servidor (como `_barredor`): recorre las
    mesas con señas y bots, renueva la mirada que haya vencido y se la manda a
    quien esté mirando a ese bot. Sin esto los bots tendrían la mirada fija
    hasta que alguien los enfocara, y cantarían mucho."""
    while True:
        socketio.sleep(0.5)
        ahora = time.time()
        for room in list(salas4.values()):
            if room['estado'] != 'jugando' or not room.get('senas') or not room.get('bots'):
                continue
            if _foco_apagado(room):
                continue
            for seat in list(room.get('bots', {})):
                foco = _foco_de(room, seat)
                if foco and ahora < foco.get('hasta', 0):
                    continue
                _mirada_de(room, seat, ahora)     # sortea una mirada nueva
                _difundir_mirada(room, seat, ahora)


def _sena_de_bot(codigo, seat):
    """Un bot también señala: una vez por mano, si lleva algo que merezca la pena.

    No decide nada del juego (los bots de la Fase 0 no leen señas todavía); está
    para que una mesa con bots no sea un juego de señas en el vacío."""
    room = salas4.get(codigo)
    if not room or not room.get('senas') or room['estado'] != 'jugando':
        return
    if base_datos.config_get('senas_bots', '1') != '1':
        return
    motor = room.get('motor')
    if not motor or motor.fase not in FASES_CON_SENAS:
        return

    hechas = room.setdefault('senas_bot_ronda', {})
    if hechas.get(seat) == motor.ronda_n:
        return
    sena = mus_senas.sena_de(motor.estado[seat]['cartas'], mus_senas.orden_configurado())
    if not sena or sena == 'ciego':
        return
    hechas[seat] = motor.ronda_n

    ahora = time.time()
    for _, sid_obs in _observadores(room, seat, ahora):
        socketio.emit('sena_vista_4', {'asiento': seat, 'sena': sena}, to=sid_obs)


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
                'senas': room.get('senas', False),
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
                'senas': room.get('senas', False),
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
    _sembrar_foco(room, asiento)
    return asiento


def handle_crear_sala_4(datos):
    sid = request.sid
    datos = seguridad.dic(datos)
    nombre = seguridad.texto(datos.get('nombre'), 20, 'Jugador')
    publico = bool(datos.get('publico', False))
    al_mejor_de = _mejor_de_4(datos.get('al_mejor_de'))
    asiento = seguridad.entero(datos.get('asiento'), 0, 3, 0)
    senas = bool(datos.get('senas', False))
    username = session.get('username')
    token = _token()

    codigo = _codigo_libre()
    room = {
        'estado': 'esperando',
        'asientos': [None, None, None, None],
        'motor': None,
        'al_mejor_de': al_mejor_de,
        'publico': publico,
        'senas': senas,
        'creador_username': username,
        'creador_nombre': nombre,
        'ultima_actividad': time.time(),
        'nombres': {}, 'usernames': {}, 'owners': {}, 'tokens': {},
        'bots': {}, 'bot_pensando': False,
        'foco': {}, 'ultima_sena': {}, 'ultima_denuncia': {}, 'senas_bot_ronda': {},
        'turno_token': 0, 'turno_deadline': None,
    }
    salas4[codigo] = room

    asiento_real = _asignar_asiento(room, sid, nombre, username, asiento, token)
    jugadores[sid] = {'nombre': nombre, 'sala': codigo, 'username': username, 'modo4': True}
    join_room(codigo)

    # Asientos que el creador ha marcado como "Bot" (los que pida ocupados se
    # ignoran: el suyo propio nunca se le quita).
    for seat, personalidad in _normalizar_bots(datos).items():
        if room['asientos'][seat] is None:
            _sentar_bot(room, codigo, seat, personalidad)

    emit('sala_creada_4', {'codigo': codigo, 'asiento': asiento_real, 'token': token})

    if all(x is not None for x in room['asientos']):
        # Mesa completa a la primera (todos los demás son bots): a jugar ya.
        _iniciar_partida(codigo)
    else:
        _emitir_estado_espera(codigo)
    emitir_publicas_4()


def handle_rellenar_bots_4(datos=None):
    """Desde la sala de espera: rellenar los asientos que faltan con bots.

    Lo puede pedir cualquiera de los que ya están sentados (si estás esperando
    a que llegue gente que no llega, no hace falta ir a buscar al creador)."""
    sid = request.sid
    datos = seguridad.dic(datos)
    for codigo, room in salas4.items():
        if sid not in room['asientos'] or room['estado'] != 'esperando':
            continue
        personalidad = datos.get('personalidad') or PERSONALIDAD_POR_DEFECTO
        if personalidad not in PERSONALIDADES:
            personalidad = PERSONALIDAD_POR_DEFECTO
        for seat in range(4):
            if room['asientos'][seat] is None:
                _sentar_bot(room, codigo, seat, personalidad)
        room['ultima_actividad'] = time.time()
        _iniciar_partida(codigo)
        emitir_publicas_4()
        return


def handle_unirse_sala_4(datos):
    sid = request.sid
    datos = seguridad.dic(datos)
    nombre = seguridad.texto(datos.get('nombre'), 20, 'Jugador')
    codigo = seguridad.codigo_sala(datos.get('codigo'))
    # `None` = «siéntame donde haya sitio»; solo se sanea si pide uno concreto.
    asiento = (None if datos.get('asiento') is None
               else seguridad.entero(datos.get('asiento'), 0, 3, 0))
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
    # El asiento cambia de dueño a mitad de match: queda en el log para que la
    # atribución por persona siga siendo exacta al derivar el dataset.
    motor.log.seat(asiento_real, 'human', code=username)
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
        'bot': s in room.get('bots', {}),
        'personalidad': room['bots'][s].personalidad if s in room.get('bots', {}) else None,
    } for s in range(4)]
    socketio.emit('estado_espera_4', {
        'codigo': codigo,
        'asientos': asientos,
        'al_mejor_de': room.get('al_mejor_de', 3),
        'publico': room.get('publico', False),
        'senas': room.get('senas', False),
    }, room=codigo)


def _seats_log_4(room):
    """Identidad por asiento para la cabecera del log v2 (mus_log.py §8.3).

    Nunca nombres para mostrar: `code` es el username registrado (o None para
    invitados) y los bots se identifican por su personalidad/checkpoint."""
    seats = []
    for s in range(4):
        bot = room.get('bots', {}).get(s)
        if bot is not None:
            seats.append({'s': s, 'kind': 'bot', 'pers': bot.personalidad,
                          'ckpt': getattr(bot, 'checkpoint', None)})
        else:
            seats.append({'s': s, 'kind': 'human', 'code': room['usernames'].get(s)})
    return seats


def _iniciar_partida(codigo):
    room = salas4.get(codigo)
    if not room:
        return
    motor = PartidaMus4()
    motor.al_mejor_de = room.get('al_mejor_de', 3)
    # En una mesa con gente, los cantes de Pares y Juego se dicen uno a uno y se
    # oyen: el motor los encola y `_programar_timers` los va soltando. Fuera del
    # servidor (gimnasio, arena, replay) el motor sigue resolviéndolos de golpe.
    motor.declaracion_pausada = True
    motor.nombres = {s: room['nombres'].get(s, f'J{s}') for s in range(4)}
    motor.usernames = {s: room['usernames'].get(s) for s in range(4)}
    # Log v2: desde este punto TODA partida 2v2 deja rastro reproducible. Es la
    # materia prima de las fases 2–4 del roadmap de IA, y por eso se enciende
    # aquí (y no bajo una opción de sala): los datos solo se acumulan una vez.
    if LOG_V2:
        motor.activar_log(seats=_seats_log_4(room),
                          rules={'al_mejor_de': motor.al_mejor_de,
                                 'senas': bool(room.get('senas')),
                                 'publico': bool(room.get('publico'))})
    motor.iniciar_ronda()
    room['motor'] = motor
    room['estado'] = 'jugando'
    room['ultima_actividad'] = time.time()
    room['empezada_en'] = time.time()
    # Analítica (#24): una partida empezada por asiento con cuenta. Se atribuye
    # por nombre y no por la petición en curso, porque a la mesa la arranca uno
    # solo y los cuatro empiezan a jugar.
    for _s in range(4):
        _u = room['usernames'].get(_s)
        if _u:
            analitica.evento('partida_inicio', modo='online4',
                             username=_u, por_usuario=True)
    socketio.emit('iniciar_partida_4', {'codigo': codigo, 'sorteo': _sorteo_mano_4(motor)},
                  room=codigo)
    enviar_estado_4(codigo)


# --- El sorteo de la Mano (static/sorteo.js) ---------------------------------
# La ruleta de pintas que ve la mesa antes de saber quién es Mano. El asiento de
# la Mano ya lo echó a suertes el motor (PartidaMus4.__init__): aquí sólo se
# reparten las cuatro pintas —una por jugador, en sentido antihorario según se
# ve la mesa, empezando por un asiento cualquiera— y se dice en cuál para la
# ruleta, que es forzosamente la de la Mano. Lo decide el servidor para que los
# cuatro clientes vean exactamente el mismo sorteo.
PINTAS_SORTEO = ['oros', 'copas', 'espadas', 'bastos']


def _sorteo_mano_4(motor):
    # En pantalla, el asiento siguiente se pinta a la izquierda (table4.js,
    # `slotDeAsiento4`), o sea que asiento+1 va en sentido horario: para repartir
    # las pintas al revés se resta.
    inicio = random.randint(0, 3)
    palos = {s: PINTAS_SORTEO[(inicio - s) % 4] for s in range(4)}
    return {
        'palos': palos,
        'nombres': {s: motor.nombres.get(s, f'J{s}') for s in range(4)},
        'mano': motor.mano,
        'parada': palos[motor.mano],
    }


# ==========================================
# Acciones de juego
# ------------------------------------------------------------------
# Además de aplicar la jugada, cada acción se ANUNCIA a la mesa: en el 2v2 hay
# cuatro sitios que mirar y con solo el resaltado del turno cuesta seguir quién
# ha hecho qué. El cliente lo pinta un momento en el sitio de quien la hizo.
# Todo lo que se anuncia es información pública del mus (lo que se canta en voz
# alta y el número de cartas que se descartan), así que va a la sala entera.
# ==========================================
def _anunciar_accion_4(codigo, seat, accion, cantidad=None):
    socketio.emit('accion_4', {'asiento': seat, 'accion': accion, 'cantidad': cantidad},
                  room=codigo)


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
    datos = seguridad.dic(datos)
    accion = datos.get('accion')

    if accion == 'pedrete':
        if motor.procesar_pedrete(seat):
            _anunciar_accion_4(codigo, seat, 'pedrete')
            enviar_estado_4(codigo)
        return

    if seat == motor.turno_de:
        if accion == 'repartir' and motor.fase == 'espera_reparto':
            motor.repartir_inicial()
            enviar_estado_4(codigo)
            return
        elif accion == 'mus':
            motor.cantar_mus(seat, True)
            _anunciar_accion_4(codigo, seat, 'mus')
            enviar_estado_4(codigo)
            return
        elif accion == 'no_mus':
            motor.cantar_mus(seat, False)
            _anunciar_accion_4(codigo, seat, 'no_mus')
            enviar_estado_4(codigo)
            return
        elif accion in ('pasar', 'envidar', 'subir', 'ver', 'ordago', 'nover') and motor.fase == 'apuestas':
            # El motor sabe qué puede hacer cada asiento AHORA (turno, topes de
            # 40 y, sobre todo, las reglas que no vigila `accion_apuesta`: a
            # Pares/Juego no apuesta quien no lleva la jugada, aunque la lleve
            # su compañero). Sin este filtro un cliente manipulado —o uno con
            # los botones desfasados— podía envidar a unos pares que no tiene.
            if accion not in motor.acciones_legales(seat):
                return
            motor.accion_apuesta(seat, accion,
                                 seguridad.entero(datos.get('cantidad', 0), 0, 40, 0))
            # La cantidad se lee DESPUÉS de jugar: el motor recorta el envite al
            # tope legal (lo que falta para 40) y lo convierte en órdago si ya no
            # cabe, así que lo cantado no siempre es lo que se pidió.
            if accion in ('envidar', 'subir'):
                if motor.subida_pendiente == 'ÓRDAGO':
                    _anunciar_accion_4(codigo, seat, 'ordago')
                else:
                    _anunciar_accion_4(codigo, seat, accion, motor.subida_pendiente)
            else:
                _anunciar_accion_4(codigo, seat, accion)
            enviar_estado_4(codigo)
            return

    if accion == 'descartar' and motor.fase == 'descarte':
        if not motor.estado[seat]['descartes_listos']:
            tirar = seguridad.indices(datos.get('indices'), 4)
            n = len(tirar)
            motor.procesar_descarte(seat, tirar)
            _anunciar_accion_4(codigo, seat, 'descartar', n)
            enviar_estado_4(codigo)
        return

    if accion == 'continuar_transicion':
        if not motor.mensaje_transicion:
            return   # nada que cerrar (p. ej. llega en plena ronda de cantes)
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

    # Los bots dan por vista la ronda AL MOMENTO, no cuando les llega su turno de
    # "pensar": esperar a que tres bots pulsen su botón de uno en uno (bot_delay
    # cada uno) hacía que la siguiente mano tardara en salir aunque las personas
    # ya estuvieran listas. Así la ronda arranca en cuanto la pulsan ellas.
    if motor.fase == 'recuento' and not motor.match_finalizado:
        for seat in room.get('bots', {}):
            if seat not in motor.jugadores_listos:
                motor.jugadores_listos.append(seat)

    # Registro del resultado (una sola vez) al terminar el match. Las mesas con
    # bots no puntúan: el 2v2 de la clasificación es entre personas.
    if motor.match_finalizado and not room.get('registrado_4') and not room.get('bots'):
        _registrar_resultado_4(motor, room)

    aviso_baraja = getattr(motor, 'baraja_agotada_aviso', False)
    nombre_turno = motor.nombres.get(motor.turno_de) if motor.turno_de is not None else None
    ganador_equipo = None
    if motor.match_finalizado:
        ganador_equipo = 'A' if motor.partidas_ganadas['A'] > motor.partidas_ganadas['B'] else 'B'

    room['turno_token'] = room.get('turno_token', 0) + 1
    token_actual = room['turno_token']

    # Deadline del turno (para la barra de cuenta atrás del cliente).
    # Durante la ronda de cantes no corre reloj de nadie: no hay turno que agotar.
    deadline = None
    if (motor.fase in ('espera_reparto', 'mus', 'apuestas', 'descarte')
            and not motor.mensaje_transicion and not motor.declaraciones_pendientes):
        deadline = time.time() + TURNO_SEGUNDOS
        room['turno_deadline'] = deadline

    # Ajustes de señas: se leen UNA vez por difusión, no una por asiento (cada
    # _cfg es una consulta a la base de datos).
    ajustes_senas = None
    if room.get('senas'):
        ajustes_senas = {
            'foco_cooldown_ms': int(_cfg('senas_foco_cooldown', FOCO_COOLDOWN, 0, 10) * 1000),
            'foco_solape_ms': int(_cfg('senas_foco_solape', FOCO_SOLAPE, 0, 10) * 1000),
            'foco_manual_ms': int(_cfg('senas_foco_manual', 2.5, 0.5, 30) * 1000),
            'sena_cooldown_ms': int(_cfg('senas_cooldown', SENA_COOLDOWN, 0, 60) * 1000),
        }

    for seat in range(4):
        sid = room['asientos'][seat]
        if sid is None or _es_bot(sid):
            continue   # los bots no tienen socket al que mandarles la mesa
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
                'bot': s in room.get('bots', {}),
                'personalidad': room['bots'][s].personalidad if s in room.get('bots', {}) else None,
                # Su baraja: sus cartas se pintan con ella, tanto el dorso como
                # las caras que se ven en el recuento (Roadmap #5).
                'baraja': _baraja_de_asiento(room, s),
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
        if motor.declaraciones_pendientes:
            # Nadie tiene el turno: la mesa está diciendo si lleva la jugada.
            mensaje = {'code': 'ronda_cantes',
                       'fase': motor.declaracion_fase}
        elif motor.fase == 'descarte':
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
            # Lo que este asiento puede hacer ahora mismo, ya filtrado por el
            # motor (la misma lista que consumen los bots). El cliente pinta los
            # botones a partir de ella, así que la mesa nunca ofrece una jugada
            # que el servidor vaya a rechazar.
            'acciones_legales': motor.acciones_legales(seat),
            'mensaje': mensaje,
            'mensaje_transicion': motor.mensaje_transicion,
            # Lance cuya ronda de cantes se está diciendo ahora mismo ('Pares' /
            # 'Juego'), o None. El cliente lo usa para no resaltar un turno que
            # todavía no es de nadie.
            'declarando': motor.declaracion_fase if motor.declaraciones_pendientes else None,
            'recuento': datos_recuento,
            'puede_pedrete': puede_pedrete,
            'match_finalizado': motor.match_finalizado,
            'ganador_equipo': ganador_equipo,
            'aviso_baraja': aviso_baraja,
            'turno_deadline_epoch': deadline,
            # Señas: el cliente sólo enciende el módulo si la mesa las lleva.
            'senas': room.get('senas', False),
            'senas_ajustes': ajustes_senas,
        }
        socketio.emit('actualizar_mesa_4', payload, room=codigo)

    # El aviso de baraja agotada se muestra una sola vez.
    if aviso_baraja:
        motor.baraja_agotada_aviso = False

    _programar_timers(codigo, token_actual)
    _programar_bots(codigo)


# ==========================================
# Turno de los bots
# ------------------------------------------------------------------
# Mismo patrón que el bot de 2p en server.py: tras CADA difusión de estado se
# programa una tarea que, pasado el retardo de "pensar", ejecuta UNA acción de
# UN bot. Esa acción vuelve a difundir estado y a programar la siguiente, así
# que los bots juegan en serie y nunca se pisan.
#
# El seguro NO es `turno_token` (como en los temporizadores) sino la bandera
# `bot_pensando`: hay como mucho una tarea de bot viva, y al despertar mira el
# estado ACTUAL en vez de caducar. Con el token, cualquier difusión ajena
# (p. ej. alguien pulsando «siguiente ronda» dos veces seguidas) invalidaba la
# tarea antes de que venciera el retardo y los bots se quedaban sin jugar.
# ==========================================
def _programar_bots(codigo):
    room = salas4.get(codigo)
    if not room or room['estado'] != 'jugando' or not room.get('bots'):
        return
    if room.get('bot_pensando'):
        return   # ya hay una acción de bot en camino
    motor = room.get('motor')
    if not motor or motor.match_finalizado:
        return
    # Con un mensaje de transición en pantalla —o con la ronda de cantes a
    # medias— manda su temporizador: nadie (tampoco un bot) juega hasta que
    # se cierre.
    if motor.mensaje_transicion or motor.declaraciones_pendientes:
        return
    # Si ningún bot tiene nada que hacer, no gastamos un greenlet.
    if not any(motor.acciones_legales(seat) for seat in room['bots']):
        return

    # Retardo "pensando", editable en caliente desde el panel (Roadmap #13/#15).
    retardo = base_datos.config_get_float('bot_delay', 1.5)
    retardo = min(max(retardo, 0.0), 10.0)
    room['bot_pensando'] = True

    def tarea():
        socketio.sleep(retardo)
        r = salas4.get(codigo)
        if r:
            # Se libera ANTES de jugar: la difusión que provoque la jugada tiene
            # que poder programar ya la siguiente acción de bot.
            r['bot_pensando'] = False
        try:
            if not r or r['estado'] != 'jugando':
                return
            m = r.get('motor')
            if not m or m.match_finalizado or m.mensaje_transicion or m.declaraciones_pendientes:
                return
            for seat in sorted(r['bots']):
                decision = r['bots'][seat].obtener_accion(m.vista(seat))
                if not decision:
                    continue
                accion, cantidad, extra = decision
                datos = {'accion': accion, 'cantidad': cantidad}
                if accion == 'descartar':
                    datos['indices'] = extra.get('indices', [])
                # Antes de mover, el bot hace su seña de la mano (si toca): así
                # cae dentro del ritmo de la mesa y no de la nada.
                _sena_de_bot(codigo, seat)
                print(f"🤖 [4p {codigo}] asiento {seat}: {accion} {cantidad or ''}".rstrip())
                procesar_accion_4(seat, codigo, datos)
                return   # una acción por tarea; la difusión programa la siguiente
        except Exception as e:
            # Una excepción aquí mataba el greenlet y dejaba la mesa congelada
            # (mismo fallo que arreglamos en el bot de 2p, Roadmap #21 bug 5).
            print(f"❌ Error en el turno de un bot 4p ({codigo}): {e}")

    socketio.start_background_task(tarea)


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

    duracion = int(time.time() - (room.get('empezada_en') or time.time()))
    for username in (g_users + p_users):
        if username:
            analitica.evento('partida_fin', modo='online4', valor=duracion,
                             username=username, por_usuario=True)


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

    if motor.declaraciones_pendientes:
        kind, delay = 'declaracion', DECLARACION_SEGUNDOS
    elif motor.mensaje_transicion:
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
        if kind == 'declaracion':
            # Un cante por vuelta: se anuncia en el sitio de quien lo dice y se
            # difunde la mesa, lo que programa el siguiente. Al cantar el último,
            # el motor resuelve el lance solo (abre apuestas o pone el aviso de
            # "nadie tiene pares"), así que la difusión ya lleva el resultado.
            cantado = m.declarar_siguiente()
            if cantado:
                seat, lance, tiene = cantado
                _anunciar_accion_4(codigo, seat,
                                   ('pares' if lance == 'Pares' else 'juego') +
                                   ('_si' if tiene else '_no'))
            enviar_estado_4(codigo)
        elif kind == 'transicion':
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
                    _anunciar_accion_4(codigo, s, 'descartar', len(indices))
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

    # Sin personas dentro la sala se cierra, aunque queden bots sentados.
    if not _humanos_sentados(room):
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
    datos = seguridad.dic(datos)
    codigo = seguridad.codigo_sala(datos.get('codigo'))
    token = seguridad.texto(datos.get('token'), 64)
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
    # El cliente que vuelve arranca mirando a su pareja; el foco viejo no vale.
    _sembrar_foco(room, seat)

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
            # Si solo quedan bots (o nadie), la sala se cierra: los bots existen
            # para acompañar a alguien, no para esperar solos.
            if not _humanos_sentados(room):
                _destruir_sala(codigo)
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
                    if not _humanos_sentados(room):
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
    sio.on('rellenar_bots_4')(handle_rellenar_bots_4)
    sio.on('accion_juego_4')(handle_accion_juego_4)
    sio.on('abandonar_sala_4')(handle_abandonar_sala_4)
    sio.on('abandonar_partida_4')(handle_abandonar_sala_4)
    sio.on('esperar_reemplazo_4')(handle_esperar_reemplazo_4)
    sio.on('reanudar_partida_4')(handle_reanudar_partida_4)
    # Señas (sólo hacen algo en las mesas creadas con señas).
    sio.on('foco_4')(handle_foco_4)
    sio.on('sena_4')(handle_sena_4)
    sio.on('denuncia_sena_4')(handle_denuncia_sena_4)
    # 'disconnect' NO se registra aquí (solo se admite un handler por evento):
    # server.py llama a server_mus4.disconnect_4() desde su propio handler.

    sio.start_background_task(_barredor)
    sio.start_background_task(_ticker_miradas)
    print("👥 Mus 4 jugadores: handlers registrados.")


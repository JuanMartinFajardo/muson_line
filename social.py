# ==========================================================================
# CAPA SOCIAL (Roadmap #3): amigos, mensajería, grupos y clasificación de grupo
# --------------------------------------------------------------------------
# Módulo ADITIVO. No toca los manejadores del juego. Se engancha desde
# server.py mediante init_social(app, socketio, ctx); ctx comparte el estado
# de las salas para poder crear invitaciones de partida reutilizando el flujo
# existente de crear_sala / unirse_sala.
#
# Regla de oro: persistir SIEMPRE primero (REST/SQLite), y luego notificar en
# tiempo real solo si el destinatario está conectado. La entrega en vivo es una
# optimización, nunca la fuente de la verdad.
# ==========================================================================

import time
import secrets
from functools import wraps

from flask import request, session, jsonify
from flask_socketio import join_room

import base_datos

# username -> set de sids (un usuario puede tener varias pestañas abiertas)
usuarios_conectados = {}

# Referencias inyectadas desde server.py
_socketio = None
_ctx = {}

# --- Rate limiting sencillo en memoria (se apoya en Roadmap #16 más adelante) ---
_rl_mensajes = {}
_rl_solicitudes = {}


def _rate_ok(bucket, user_id, max_n, ventana):
    ahora = time.time()
    recientes = [t for t in bucket.get(user_id, []) if ahora - t < ventana]
    bucket[user_id] = recientes
    if len(recientes) >= max_n:
        return False
    recientes.append(ahora)
    return True


# ==========================================================================
# Presencia y notificaciones en tiempo real
# ==========================================================================

def _sids_de(username):
    return list(usuarios_conectados.get(username, []))


def esta_online(username):
    return bool(usuarios_conectados.get(username))


def notificar(username, tipo, payload):
    """Empuja una notificación a todas las pestañas conectadas de un usuario."""
    if not username or _socketio is None:
        return
    for sid in _sids_de(username):
        _socketio.emit('notificacion', {'tipo': tipo, **payload}, room=sid)


def _broadcast_presencia(username, online):
    """Avisa a los amigos aceptados de este usuario de su cambio de estado."""
    uid = base_datos.obtener_id_usuario(username)
    if uid is None:
        return
    for amigo in base_datos.listar_amigos(uid):
        notificar(amigo['username'], 'presencia', {'username': username, 'online': online})


def presencia_connect():
    """Registrar en el connect del socket (server.py no define connect propio)."""
    u = session.get('username')
    if u:
        primera_pestana = not usuarios_conectados.get(u)
        usuarios_conectados.setdefault(u, set()).add(request.sid)
        if primera_pestana:
            _broadcast_presencia(u, True)


def presencia_disconnect():
    """Llamado desde el handle_disconnect del juego en server.py."""
    u = session.get('username')
    sid = request.sid
    if u and u in usuarios_conectados:
        usuarios_conectados[u].discard(sid)
        if not usuarios_conectados[u]:
            del usuarios_conectados[u]
            _broadcast_presencia(u, False)


# ==========================================================================
# Utilidades de sesión
# ==========================================================================

def login_requerido(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if 'username' not in session:
            return jsonify({'exito': False, 'mensaje': 'no_auth'}), 401
        return f(*a, **kw)
    return wrapper


def _mi_id():
    return base_datos.obtener_id_usuario(session.get('username'))


def _resolver_objetivo(texto):
    """Traduce lo que el usuario ha escrito en la caja de 'añadir' a (id, username).

    Acepta el nombre o el código público (#A7K2QX, Roadmap #23). El código es la vía
    fiable: no cambia al renombrarse y no se recicla, así que nunca acaba señalando a
    otra persona. Devuelve (None, None) si no hay ninguna cuenta viva que encaje.
    """
    texto = (texto or '').strip()
    if not texto:
        return (None, None)
    if texto.startswith('#'):
        encontrado = base_datos.obtener_usuario_por_codigo(texto)
        return encontrado if encontrado else (None, None)
    uid = base_datos.obtener_id_usuario(texto)
    return (uid, base_datos.obtener_username_por_id(uid)) if uid else (None, None)


# ==========================================================================
# Registro de rutas HTTP y eventos de socket
# ==========================================================================

def init_social(app, socketio, ctx):
    global _socketio, _ctx
    _socketio = socketio
    _ctx = ctx or {}

    # -------------------- Presencia (connect) --------------------
    # Flask-SocketIO 5.x solo admite UN handler por evento y este es el único
    # 'connect' del servidor, así que la comprobación de baneo (Roadmap #13) vive
    # aquí: devolver False rechaza la conexión antes de que el socket exista.
    @socketio.on('connect')
    def _social_connect():
        usuario = session.get('username')
        if usuario:
            baneado, _motivo = base_datos.esta_baneado(usuario)
            if baneado:
                print(f"⛔ Conexión rechazada: {usuario} está baneado.")
                return False
        presencia_connect()

    # ======================================================================
    # AMIGOS
    # ======================================================================

    @app.route('/api/friends', methods=['GET'])
    @login_requerido
    def api_friends():
        me = _mi_id()
        amigos = base_datos.listar_amigos(me)
        no_leidos = base_datos.contar_no_leidos(me)
        total_no_leidos = 0
        for a in amigos:
            a['online'] = esta_online(a['username'])
            a['no_leidos'] = no_leidos.get(a['id'], 0)
            total_no_leidos += a['no_leidos']
        pendientes = base_datos.listar_solicitudes_pendientes(me)
        return jsonify({'exito': True, 'amigos': amigos,
                        'solicitudes': pendientes,
                        'total_no_leidos': total_no_leidos})

    @app.route('/api/friends/requests', methods=['GET'])
    @login_requerido
    def api_friend_requests():
        return jsonify({'exito': True,
                        'solicitudes': base_datos.listar_solicitudes_pendientes(_mi_id())})

    @app.route('/api/friends/request', methods=['POST'])
    @login_requerido
    def api_friend_request():
        me = _mi_id()
        if not _rate_ok(_rl_solicitudes, me, 20, 3600):
            return jsonify({'exito': False, 'mensaje': 'rate_limit'})
        datos = request.json or {}
        to_id, _nombre = _resolver_objetivo(datos.get('username'))
        if not to_id:
            return jsonify({'exito': False, 'mensaje': 'no_existe'})
        ok, codigo = base_datos.enviar_solicitud_amistad(me, to_id)
        if ok:
            notificar(base_datos.obtener_username_por_id(to_id),
                      'solicitud_amistad', {'de': session['username']})
        return jsonify({'exito': ok, 'mensaje': codigo})

    @app.route('/api/friends/respond', methods=['POST'])
    @login_requerido
    def api_friend_respond():
        me = _mi_id()
        datos = request.json or {}
        other_id = datos.get('user_id')
        aceptar = bool(datos.get('accept'))
        if not isinstance(other_id, int):
            return jsonify({'exito': False, 'mensaje': 'bad_id'})
        ok = base_datos.responder_solicitud(me, other_id, aceptar)
        if ok and aceptar:
            notificar(base_datos.obtener_username_por_id(other_id),
                      'amistad_aceptada', {'de': session['username']})
        return jsonify({'exito': ok})

    @app.route('/api/friends/<int:user_id>', methods=['DELETE'])
    @login_requerido
    def api_friend_delete(user_id):
        base_datos.eliminar_amistad(_mi_id(), user_id)
        return jsonify({'exito': True})

    @app.route('/api/friends/<int:user_id>/block', methods=['POST'])
    @login_requerido
    def api_friend_block(user_id):
        base_datos.bloquear_usuario(_mi_id(), user_id)
        return jsonify({'exito': True})

    # ======================================================================
    # MENSAJES DIRECTOS
    # ======================================================================

    @app.route('/api/messages/<int:friend_id>', methods=['GET'])
    @login_requerido
    def api_messages_get(friend_id):
        me = _mi_id()
        before = request.args.get('before', type=int)
        mensajes = base_datos.obtener_conversacion(me, friend_id, before_id=before)
        return jsonify({'exito': True, 'mensajes': mensajes})

    @app.route('/api/messages/<int:friend_id>', methods=['POST'])
    @login_requerido
    def api_messages_post(friend_id):
        me = _mi_id()
        if not _rate_ok(_rl_mensajes, me, 30, 60):
            return jsonify({'exito': False, 'mensaje': 'rate_limit'})
        datos = request.json or {}
        ok, mensaje = base_datos.enviar_mensaje_dm(me, friend_id, datos.get('body'))
        if not ok:
            return jsonify({'exito': False, 'mensaje': 'invalido'})
        # notificar al amigo si está conectado (incluye el propio nombre para la UI)
        notificar(base_datos.obtener_username_por_id(friend_id), 'mensaje',
                  {**mensaje, 'de': session['username']})
        return jsonify({'exito': True, 'mensaje': mensaje})

    # ======================================================================
    # GRUPOS
    # ======================================================================

    @app.route('/api/groups', methods=['GET'])
    @login_requerido
    def api_groups_get():
        return jsonify({'exito': True, 'grupos': base_datos.listar_grupos_de(_mi_id())})

    @app.route('/api/groups', methods=['POST'])
    @login_requerido
    def api_groups_create():
        datos = request.json or {}
        ok, res = base_datos.crear_grupo(_mi_id(), datos.get('name'))
        if not ok:
            return jsonify({'exito': False, 'mensaje': res})
        return jsonify({'exito': True, 'group_id': res})

    @app.route('/api/groups/<int:group_id>', methods=['GET'])
    @login_requerido
    def api_group_detail(group_id):
        me = _mi_id()
        if not base_datos.es_miembro(group_id, me):
            return jsonify({'exito': False, 'mensaje': 'no_miembro'}), 403
        grupo = base_datos.obtener_grupo(group_id)
        return jsonify({'exito': True, 'grupo': grupo,
                        'miembros': base_datos.listar_miembros(group_id),
                        'mi_rol': base_datos.rol_en_grupo(group_id, me)})

    @app.route('/api/groups/<int:group_id>/invite', methods=['POST'])
    @login_requerido
    def api_group_invite(group_id):
        me = _mi_id()
        datos = request.json or {}
        to_id, objetivo = _resolver_objetivo(datos.get('username'))
        if not to_id:
            return jsonify({'exito': False, 'mensaje': 'no_existe'})
        ok, codigo = base_datos.añadir_miembro(group_id, to_id, me)
        if ok:
            grupo = base_datos.obtener_grupo(group_id)
            notificar(objetivo, 'invitacion_grupo',
                      {'group_id': group_id, 'nombre': grupo['name'] if grupo else '',
                       'de': session['username']})
        return jsonify({'exito': ok, 'mensaje': codigo})

    @app.route('/api/groups/<int:group_id>/leave', methods=['POST'])
    @login_requerido
    def api_group_leave(group_id):
        ok = base_datos.salir_del_grupo(group_id, _mi_id())
        return jsonify({'exito': ok})

    @app.route('/api/groups/<int:group_id>/members/<int:user_id>/role', methods=['POST'])
    @login_requerido
    def api_group_member_role(group_id, user_id):
        datos = request.json or {}
        ok, codigo = base_datos.cambiar_rol_miembro(group_id, _mi_id(), user_id, datos.get('role'))
        if ok:
            nombre = base_datos.obtener_username_por_id(user_id)
            grupo = base_datos.obtener_grupo(group_id)
            notificar(nombre, 'rol_grupo',
                      {'group_id': group_id, 'nombre': grupo['name'] if grupo else '',
                       'role': datos.get('role')})
        return jsonify({'exito': ok, 'mensaje': codigo})

    @app.route('/api/groups/<int:group_id>/members/<int:user_id>/remove', methods=['POST'])
    @login_requerido
    def api_group_member_remove(group_id, user_id):
        ok, codigo = base_datos.expulsar_miembro(group_id, _mi_id(), user_id)
        if ok:
            nombre = base_datos.obtener_username_por_id(user_id)
            grupo = base_datos.obtener_grupo(group_id)
            notificar(nombre, 'expulsado_grupo',
                      {'group_id': group_id, 'nombre': grupo['name'] if grupo else ''})
        return jsonify({'exito': ok, 'mensaje': codigo})

    @app.route('/api/groups/<int:group_id>/settings', methods=['POST'])
    @login_requerido
    def api_group_settings(group_id):
        datos = request.json or {}
        ok, codigo = base_datos.actualizar_invite_policy(group_id, _mi_id(), datos.get('invite_policy'))
        return jsonify({'exito': ok, 'mensaje': codigo})

    @app.route('/api/groups/<int:group_id>/messages', methods=['GET'])
    @login_requerido
    def api_group_messages_get(group_id):
        me = _mi_id()
        before = request.args.get('before', type=int)
        mensajes = base_datos.obtener_mensajes_grupo(group_id, me, before_id=before)
        if mensajes is None:
            return jsonify({'exito': False, 'mensaje': 'no_miembro'}), 403
        return jsonify({'exito': True, 'mensajes': mensajes})

    @app.route('/api/groups/<int:group_id>/messages', methods=['POST'])
    @login_requerido
    def api_group_messages_post(group_id):
        me = _mi_id()
        if not _rate_ok(_rl_mensajes, me, 30, 60):
            return jsonify({'exito': False, 'mensaje': 'rate_limit'})
        datos = request.json or {}
        ok, mensaje = base_datos.enviar_mensaje_grupo(me, group_id, datos.get('body'))
        if not ok:
            return jsonify({'exito': False, 'mensaje': 'invalido'})
        mensaje['sender_name'] = session['username']
        # notificar al resto de miembros conectados
        for m in base_datos.listar_miembros(group_id):
            if m['id'] != me:
                notificar(m['username'], 'mensaje_grupo', {**mensaje})
        return jsonify({'exito': True, 'mensaje': mensaje})

    @app.route('/api/groups/<int:group_id>/leaderboard', methods=['GET'])
    @login_requerido
    def api_group_leaderboard(group_id):
        if not base_datos.es_miembro(group_id, _mi_id()):
            return jsonify({'exito': False, 'mensaje': 'no_miembro'}), 403
        return jsonify({'exito': True, 'leaderboard': base_datos.leaderboard_grupo(group_id)})

    # ======================================================================
    # INVITACIÓN A PARTIDA (reutiliza el flujo de salas del juego)
    # ======================================================================

    @socketio.on('invitar_amigo')
    def _invitar_amigo(datos):
        sid = request.sid
        yo = session.get('username')
        if not yo:
            socketio.emit('error_invitacion', {'mensaje': 'no_auth'}, room=sid)
            return

        me = base_datos.obtener_id_usuario(yo)
        friend_id = datos.get('friend_id')
        al_mejor_de = datos.get('al_mejor_de', 3)
        if not isinstance(friend_id, int) or not base_datos.son_amigos(me, friend_id):
            socketio.emit('error_invitacion', {'mensaje': 'no_amigo'}, room=sid)
            return

        amigo_username = base_datos.obtener_username_por_id(friend_id)
        if not esta_online(amigo_username):
            socketio.emit('error_invitacion', {'mensaje': 'offline'}, room=sid)
            return

        salas = _ctx['salas']
        jugadores = _ctx['jugadores']
        generar_codigo = _ctx['generar_codigo']
        emitir_lista_publicas = _ctx.get('emitir_lista_publicas')
        salir_de_sala = _ctx.get('salir_de_sala')

        # Si el anfitrión ya estaba sentado en otra sala (p.ej. esperando en el
        # vestíbulo), hay que desalojarlo antes: si no, `jugadores[sid]` se
        # sobrescribe más abajo y la sala anterior queda de fantasma (Roadmap #21).
        if salir_de_sala:
            salir_de_sala(sid)

        codigo = generar_codigo()
        while codigo in salas:
            codigo = generar_codigo()

        # Sentamos al anfitrión en el asiento 0, sala PRIVADA (no aparece en públicas).
        token = secrets.token_hex(16)
        jugadores[sid] = {'nombre': yo, 'sala': codigo, 'username': yo}
        join_room(codigo)
        salas[codigo] = {
            'estado': 'esperando', 'sids': [sid], 'al_mejor_de': al_mejor_de,
            'publico': False, 'username': yo, 'creador_nombre': yo,
            'tokens': {0: token},
            'creada_en': time.time(), 'ultima_actividad': time.time()
        }

        # El anfitrión entra al panel de espera exactamente igual que hoy.
        # El token le permite reanudar si refresca antes de que llegue el invitado.
        socketio.emit('sala_creada', {'codigo': codigo, 'token': token}, room=sid)
        # Al invitado le llega el código para que se una con el flujo normal.
        notificar(amigo_username, 'invitacion_partida',
                  {'codigo': codigo, 'de': yo, 'al_mejor_de': al_mejor_de})
        if emitir_lista_publicas:
            emitir_lista_publicas()

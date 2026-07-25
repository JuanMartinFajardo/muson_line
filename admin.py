# ==========================================================================
# PANEL DE ADMINISTRACIÓN (Roadmap #13)
# --------------------------------------------------------------------------
# Módulo ADITIVO, igual que social.py: no toca los manejadores del juego. Se
# engancha desde server.py con init_admin(app, socketio, ctx); `ctx` inyecta lo
# que hace falta del servidor (registro de salas, correo, notificaciones…) para
# no importar `server` desde aquí (server.py corre como __main__ y volvería a
# ejecutarse entero).
#
# NO necesita despliegue aparte: vive en el mismo proceso Flask, el mismo
# puerto y la misma sesión que el juego. Basta con abrir /admin.
#
# Contiene tres bloques:
#   1. /admin/**            → panel, solo para cuentas con is_admin
#   2. /api/soporte/**      → buzón de soporte del jugador (su lado del hilo)
#   3. /api/anuncios/**     → avisos y mensajes fijados que ve el jugador
#
# El panel se sirve en castellano (es una herramienta interna del dueño); todo
# lo que ve el jugador —soporte y anuncios— sí pasa por el diccionario ES/EN.
# ==========================================================================

import io
import os
import time
import json
import zipfile
import sqlite3
import tempfile
from functools import wraps
from datetime import datetime, timedelta

from flask import (render_template, request, session, jsonify,
                   send_file, Response)

import base_datos

RAIZ = os.path.dirname(os.path.abspath(__file__))
DIR_LOGS = os.path.join(RAIZ, 'logs')
DIR_CHECKPOINTS = os.path.join(RAIZ, 'learn', 'cfr')

# Referencias inyectadas desde server.py
_socketio = None
_ctx = {}

# Variables globales que el panel conoce por su nombre: valor por defecto y a qué
# afectan. Cualquier otra clave se puede crear igualmente (editor genérico), pero
# solo estas tienen hoy a alguien que las lea.
CONFIG_CONOCIDA = {
    'bot_checkpoint': {
        'defecto': '',
        'ayuda': 'Checkpoint de la IA (archivo de learn/cfr). Vacío = el que trae bot_ml por defecto.',
    },
    'bot_delay': {
        'defecto': '1.5',
        'ayuda': 'Segundos que "piensa" el bot antes de mover (Roadmap #15).',
    },
    'mantenimiento_activo': {
        'defecto': '0',
        'ayuda': '1 = enseña el cartel de mantenimiento a todos los jugadores.',
    },
    'mantenimiento_texto': {
        'defecto': '',
        'ayuda': 'Texto del cartel de mantenimiento.',
    },
}

# --- Rate limiting en memoria (mismo patrón que social.py) ------------------
_rl = {}


def _rate_ok(bucket_key, max_n, ventana):
    ahora = time.time()
    recientes = [t for t in _rl.get(bucket_key, []) if ahora - t < ventana]
    _rl[bucket_key] = recientes
    if len(recientes) >= max_n:
        return False
    recientes.append(ahora)
    return True


# ==========================================================================
# Permisos
# ==========================================================================

def _ip():
    """IP real del cliente. Detrás de nginx/Cloudflare (Roadmap #16) el proxy
    manda la original en X-Forwarded-For; el primer valor es el cliente."""
    reenviada = request.headers.get('X-Forwarded-For', '')
    return (reenviada.split(',')[0].strip() or request.remote_addr) if reenviada else request.remote_addr


def es_admin_actual():
    return base_datos.es_admin(session.get('username'))


def admin_requerido(f):
    """Puerta de todas las rutas del panel. Sin sesión o sin el bit is_admin se
    responde 403 (nunca se filtra si la cuenta existe o no)."""
    @wraps(f)
    def wrapper(*a, **kw):
        if not es_admin_actual():
            if request.path.startswith('/admin/api/'):
                return jsonify({'exito': False, 'mensaje': 'no_admin'}), 403
            return Response('403 — No tienes acceso a esta página.', status=403,
                            mimetype='text/plain; charset=utf-8')
        return f(*a, **kw)
    return wrapper


def _auditar(accion, objetivo=None, detalle=None):
    base_datos.registrar_auditoria(session.get('username'), accion, objetivo, detalle, _ip())


def _notificar(username, tipo, payload):
    """Empuja por socket usando la capa social (si el usuario está conectado)."""
    fn = _ctx.get('notificar')
    if fn:
        try:
            fn(username, tipo, payload)
        except Exception as e:
            print(f"⚠️ [admin] No se pudo notificar a {username}: {e}")


def _avisar_admins(tipo, payload):
    """Aviso en vivo a los administradores conectados (soporte nuevo, etc.)."""
    for fila in base_datos.buscar_usuarios('', limite=200):
        if fila['is_admin']:
            _notificar(fila['username'], tipo, payload)


# ==========================================================================
# Arranque: primer administrador desde ADMIN_USERNAME
# ==========================================================================

def bootstrap_admin():
    """Promueve al usuario indicado en ADMIN_USERNAME. Es la única vía para tener
    el primer administrador: a partir de ahí se otorga desde el propio panel."""
    nombre = (os.environ.get('ADMIN_USERNAME') or '').strip()
    if not nombre:
        if base_datos.contar_admins() == 0:
            print("ℹ️  No hay ningún administrador. Define ADMIN_USERNAME para crear el primero.")
        return
    if base_datos.es_admin(nombre):
        print(f"🔑 Administrador: {nombre}")
        return
    ok, _ = base_datos.marcar_admin(nombre, True)
    if ok:
        base_datos.registrar_auditoria('SISTEMA', 'promover_admin', nombre, 'ADMIN_USERNAME')
        print(f"🔑 {nombre} promovido a administrador (ADMIN_USERNAME).")
    else:
        print(f"⚠️  ADMIN_USERNAME={nombre} no corresponde a ninguna cuenta.")


# ==========================================================================
# Registro de rutas
# ==========================================================================

def init_admin(app, socketio, ctx):
    global _socketio, _ctx
    _socketio = socketio
    _ctx = ctx or {}

    bootstrap_admin()

    # ======================================================================
    # 0. La página
    # ======================================================================

    @app.route('/admin')
    @admin_requerido
    def admin_index():
        return render_template('admin.html', admin=session.get('username'))

    # ======================================================================
    # 1. Resumen
    # ======================================================================

    @app.route('/admin/api/resumen', methods=['GET'])
    @admin_requerido
    def admin_resumen():
        salas = _ctx.get('salas') or {}
        salas4 = _ctx.get('salas4') or {}
        jugadores = _ctx.get('jugadores') or {}
        datos = base_datos.estadisticas_globales()
        datos.update({
            'salas_2p': len(salas),
            'salas_4p': len(salas4),
            'jugando_2p': sum(1 for s in salas.values() if s.get('estado') == 'jugando'),
            'jugando_4p': sum(1 for s in salas4.values() if s.get('estado') == 'jugando'),
            'conexiones': len(jugadores),
            'online': len(_ctx.get('usuarios_conectados') or {}),
        })
        return jsonify({'exito': True, 'resumen': datos})

    # ======================================================================
    # 2. Cuentas
    # ======================================================================

    @app.route('/admin/api/usuarios', methods=['GET'])
    @admin_requerido
    def admin_usuarios():
        usuarios = base_datos.buscar_usuarios(
            request.args.get('q', ''),
            limite=request.args.get('limite', 50, type=int),
            incluir_eliminadas=request.args.get('eliminadas') == '1')
        return jsonify({'exito': True, 'usuarios': usuarios})

    @app.route('/admin/api/usuarios/<int:user_id>/ban', methods=['POST'])
    @admin_requerido
    def admin_ban(user_id):
        datos = request.json or {}
        banear = bool(datos.get('banear', True))
        objetivo = base_datos.obtener_usuario_admin(user_id)
        if not objetivo:
            return jsonify({'exito': False, 'mensaje': 'no_existe'}), 404
        # Un administrador no se banea a sí mismo ni a otro administrador: para eso
        # hay que quitarle antes el bit, que queda en la auditoría.
        if banear and objetivo['is_admin']:
            return jsonify({'exito': False, 'mensaje': 'es_admin'})

        ok, username = base_datos.admin_banear(user_id, banear, datos.get('motivo'))
        if not ok:
            return jsonify({'exito': False, 'mensaje': 'no_existe'}), 404
        _auditar('ban' if banear else 'desban', username, datos.get('motivo'))
        if banear:
            _expulsar_de_todo(username)
        return jsonify({'exito': True, 'usuario': base_datos.obtener_usuario_admin(user_id)})

    @app.route('/admin/api/usuarios/<int:user_id>/estadisticas', methods=['POST'])
    @admin_requerido
    def admin_stats(user_id):
        datos = request.json or {}
        try:
            ok = base_datos.admin_editar_estadisticas(
                user_id,
                elo=datos.get('elo'),
                victorias=datos.get('victorias'),
                derrotas=datos.get('derrotas'))
        except (TypeError, ValueError):
            return jsonify({'exito': False, 'mensaje': 'valor_invalido'})
        if not ok:
            return jsonify({'exito': False, 'mensaje': 'sin_cambios'})
        _auditar('editar_estadisticas', base_datos.obtener_username_por_id(user_id),
                 json.dumps({k: datos.get(k) for k in ('elo', 'victorias', 'derrotas')
                             if datos.get(k) is not None}))
        return jsonify({'exito': True, 'usuario': base_datos.obtener_usuario_admin(user_id)})

    @app.route('/admin/api/usuarios/<int:user_id>/admin', methods=['POST'])
    @admin_requerido
    def admin_promover(user_id):
        datos = request.json or {}
        valor = bool(datos.get('admin', True))
        username = base_datos.obtener_username_por_id(user_id)
        if not username:
            return jsonify({'exito': False, 'mensaje': 'no_existe'}), 404
        # Nadie puede quedarse sin administradores por un despiste.
        if not valor and base_datos.contar_admins() <= 1:
            return jsonify({'exito': False, 'mensaje': 'ultimo_admin'})
        ok, codigo = base_datos.marcar_admin(username, valor)
        if not ok:
            return jsonify({'exito': False, 'mensaje': codigo})
        _auditar('promover_admin' if valor else 'degradar_admin', username)
        return jsonify({'exito': True, 'usuario': base_datos.obtener_usuario_admin(user_id)})

    @app.route('/admin/api/usuarios/<int:user_id>/reset_password', methods=['POST'])
    @admin_requerido
    def admin_reset_password(user_id):
        """No fija ninguna contraseña: manda al correo del usuario el mismo código
        de recuperación que el flujo de "he olvidado mi contraseña". El
        administrador nunca llega a conocer la contraseña de nadie."""
        objetivo = base_datos.obtener_usuario_admin(user_id)
        if not objetivo:
            return jsonify({'exito': False, 'mensaje': 'no_existe'}), 404
        email = objetivo.get('email')
        if not email:
            return jsonify({'exito': False, 'mensaje': 'sin_email'})

        generar = _ctx.get('generar_codigo_verificacion')
        enviar = _ctx.get('enviar_correo')
        pendientes = _ctx.get('codigos_pendientes')
        if not (generar and enviar and pendientes is not None):
            return jsonify({'exito': False, 'mensaje': 'sin_correo_configurado'})

        codigo = generar()
        pendientes[email] = {'code': codigo, 'ts': time.time(), 'tipo': 'reset'}
        enviar(email, "Restablece tu contraseña de CallMus",
               f"Hola {objetivo['username']},\n\n"
               f"Un administrador de CallMus ha iniciado el restablecimiento de tu "
               f"contraseña. Tu código es: {codigo}\n\n"
               f"Caduca en 15 minutos. Introdúcelo en «He olvidado mi contraseña».\n"
               f"Si no esperabas esto, ignora el correo: tu contraseña actual sigue valiendo.")
        _auditar('reset_password', objetivo['username'])
        return jsonify({'exito': True})

    @app.route('/admin/api/usuarios/<int:user_id>/eliminar', methods=['POST'])
    @admin_requerido
    def admin_eliminar(user_id):
        """Mismo borrado que hace el usuario desde sus ajustes: anonimiza la fila y
        borra su rastro social, conservando el historial de sus rivales."""
        objetivo = base_datos.obtener_usuario_admin(user_id)
        if not objetivo:
            return jsonify({'exito': False, 'mensaje': 'no_existe'}), 404
        if objetivo['is_admin']:
            return jsonify({'exito': False, 'mensaje': 'es_admin'})
        exito, codigo, anonimo = base_datos.anonimizar_usuario(objetivo['username'])
        if not exito:
            return jsonify({'exito': False, 'mensaje': codigo})
        _auditar('eliminar_cuenta', objetivo['username'], anonimo)
        _expulsar_de_todo(objetivo['username'])
        return jsonify({'exito': True, 'anonimo': anonimo})

    # ======================================================================
    # 3. Operaciones en vivo: salas
    # ======================================================================

    @app.route('/admin/api/salas', methods=['GET'])
    @admin_requerido
    def admin_salas():
        return jsonify({'exito': True, 'salas': _listar_salas()})

    @app.route('/admin/api/salas/<codigo>/cerrar', methods=['POST'])
    @admin_requerido
    def admin_cerrar_sala(codigo):
        codigo = (codigo or '').upper()
        salas = _ctx.get('salas') or {}
        salas4 = _ctx.get('salas4') or {}
        if codigo in salas:
            destruir = _ctx.get('destruir_sala')
            if not destruir:
                return jsonify({'exito': False, 'mensaje': 'no_disponible'})
            destruir(codigo, 'admin')
        elif codigo in salas4:
            destruir4 = _ctx.get('destruir_sala4')
            if not destruir4:
                return jsonify({'exito': False, 'mensaje': 'no_disponible'})
            if _socketio:
                _socketio.emit('rival_desconectado', {'motivo': 'admin'}, room=codigo)
            destruir4(codigo)
        else:
            return jsonify({'exito': False, 'mensaje': 'no_existe'}), 404
        _auditar('cerrar_sala', codigo)
        return jsonify({'exito': True})

    # ======================================================================
    # 4. Descarga de datos
    # ======================================================================

    @app.route('/admin/api/descargas/db', methods=['GET'])
    @admin_requerido
    def admin_descargar_db():
        """Copia consistente de mus.db con la API de backup de SQLite: copiar el
        archivo a pelo mientras el servidor escribe puede dar una copia rota."""
        destino = os.path.join(tempfile.gettempdir(),
                               f"mus_backup_{datetime.now():%Y%m%d_%H%M%S}.db")
        origen = sqlite3.connect(base_datos.DB_NAME)
        copia = sqlite3.connect(destino)
        try:
            origen.backup(copia)
        finally:
            copia.close()
            origen.close()
        _auditar('descargar_db')
        return send_file(destino, as_attachment=True,
                         download_name=os.path.basename(destino))

    @app.route('/admin/api/descargas/logs', methods=['GET'])
    @admin_requerido
    def admin_descargar_logs():
        """Zip de logs/*.jsonl, opcionalmente acotado por fecha de modificación
        (?desde=YYYY-MM-DD&hasta=YYYY-MM-DD, ambos inclusive)."""
        desde = _fecha(request.args.get('desde'))
        hasta = _fecha(request.args.get('hasta'))
        if hasta:
            hasta = hasta + timedelta(days=1)      # 'hasta' inclusive

        memoria = io.BytesIO()
        incluidos = 0
        with zipfile.ZipFile(memoria, 'w', zipfile.ZIP_DEFLATED) as z:
            for nombre in sorted(os.listdir(DIR_LOGS)) if os.path.isdir(DIR_LOGS) else []:
                if not nombre.endswith('.jsonl'):
                    continue
                ruta = os.path.join(DIR_LOGS, nombre)
                marca = datetime.fromtimestamp(os.path.getmtime(ruta))
                if (desde and marca < desde) or (hasta and marca >= hasta):
                    continue
                z.write(ruta, arcname=f"logs/{nombre}")
                incluidos += 1
        memoria.seek(0)
        _auditar('descargar_logs', None, f"{incluidos} archivos")
        return send_file(memoria, mimetype='application/zip', as_attachment=True,
                         download_name=f"callmus_logs_{datetime.now():%Y%m%d_%H%M%S}.zip")

    # ======================================================================
    # 5. Variables globales y ajustes del bot
    # ======================================================================

    @app.route('/admin/api/config', methods=['GET'])
    @admin_requerido
    def admin_config_get():
        guardada = {c['key']: c for c in base_datos.config_all()}
        conocidas = []
        for clave, meta in CONFIG_CONOCIDA.items():
            fila = guardada.pop(clave, None)
            conocidas.append({
                'key': clave,
                'value': fila['value'] if fila else meta['defecto'],
                'defecto': meta['defecto'],
                'ayuda': meta['ayuda'],
                'guardada': fila is not None,
                'updated_at': fila['updated_at'] if fila else None,
                'updated_by': fila['updated_by'] if fila else None,
            })
        return jsonify({'exito': True, 'conocidas': conocidas,
                        'otras': list(guardada.values()),
                        'checkpoints': _listar_checkpoints()})

    @app.route('/admin/api/config', methods=['POST'])
    @admin_requerido
    def admin_config_set():
        datos = request.json or {}
        clave = (datos.get('key') or '').strip()
        if not clave or len(clave) > 60:
            return jsonify({'exito': False, 'mensaje': 'clave_invalida'})
        valor = datos.get('value')

        # El checkpoint se valida contra lo que hay realmente en learn/cfr: un
        # nombre inventado dejaría al bot sin cerebro en la siguiente partida.
        if clave == 'bot_checkpoint' and valor:
            if valor not in _listar_checkpoints():
                return jsonify({'exito': False, 'mensaje': 'checkpoint_no_existe'})
        if clave == 'bot_delay':
            try:
                v = float(valor)
            except (TypeError, ValueError):
                return jsonify({'exito': False, 'mensaje': 'valor_invalido'})
            if not (0 <= v <= 10):
                return jsonify({'exito': False, 'mensaje': 'fuera_de_rango'})

        base_datos.config_set(clave, valor, session.get('username'))
        _auditar('config', clave, str(valor)[:200])
        # El bot relee su checkpoint de la BD; le avisamos para que suelte el que
        # tenga cacheado y cargue el nuevo sin reiniciar el servidor.
        if clave == 'bot_checkpoint':
            try:
                import bot_ml
                bot_ml.invalidar_modelo_cacheado()
            except Exception as e:
                print(f"⚠️ [admin] No se pudo refrescar el modelo del bot: {e}")
        return jsonify({'exito': True})

    @app.route('/admin/api/config/<clave>', methods=['DELETE'])
    @admin_requerido
    def admin_config_delete(clave):
        base_datos.config_delete(clave)
        _auditar('config_borrar', clave)
        if clave == 'bot_checkpoint':
            try:
                import bot_ml
                bot_ml.invalidar_modelo_cacheado()
            except Exception:
                pass
        return jsonify({'exito': True})

    # ======================================================================
    # 6. Soporte — lado del administrador
    # ======================================================================

    @app.route('/admin/api/tickets', methods=['GET'])
    @admin_requerido
    def admin_tickets():
        estado = request.args.get('estado')
        return jsonify({'exito': True,
                        'tickets': base_datos.listar_tickets(estado),
                        'pendientes': base_datos.contar_tickets_pendientes()})

    @app.route('/admin/api/tickets/<int:ticket_id>', methods=['GET'])
    @admin_requerido
    def admin_ticket(ticket_id):
        ticket = base_datos.obtener_ticket(ticket_id)
        if not ticket:
            return jsonify({'exito': False, 'mensaje': 'no_existe'}), 404
        base_datos.marcar_ticket_leido(ticket_id, 'admin')
        return jsonify({'exito': True, 'ticket': ticket,
                        'mensajes': base_datos.mensajes_ticket(ticket_id)})

    @app.route('/admin/api/tickets/<int:ticket_id>/responder', methods=['POST'])
    @admin_requerido
    def admin_ticket_responder(ticket_id):
        datos = request.json or {}
        ticket = base_datos.obtener_ticket(ticket_id)
        if not ticket:
            return jsonify({'exito': False, 'mensaje': 'no_existe'}), 404
        ok, res = base_datos.responder_ticket(ticket_id, 'admin',
                                              session.get('username'), datos.get('body'))
        if not ok:
            return jsonify({'exito': False, 'mensaje': res})
        _auditar('responder_ticket', ticket['username'], f"#{ticket_id}")
        _notificar(ticket['username'], 'soporte_respuesta',
                   {'ticket_id': ticket_id, 'asunto': ticket['asunto']})
        return jsonify({'exito': True, 'mensaje': res})

    @app.route('/admin/api/tickets/<int:ticket_id>/estado', methods=['POST'])
    @admin_requerido
    def admin_ticket_estado(ticket_id):
        datos = request.json or {}
        estado = datos.get('estado')
        if not base_datos.cambiar_estado_ticket(ticket_id, estado):
            return jsonify({'exito': False, 'mensaje': 'estado_invalido'})
        _auditar('estado_ticket', f"#{ticket_id}", estado)
        return jsonify({'exito': True})

    # ======================================================================
    # 7. Anuncios — lado del administrador
    # ======================================================================

    @app.route('/admin/api/anuncios', methods=['GET'])
    @admin_requerido
    def admin_anuncios():
        return jsonify({'exito': True, 'anuncios': base_datos.listar_anuncios(),
                        'grupos': _listar_grupos()})

    @app.route('/admin/api/anuncios', methods=['POST'])
    @admin_requerido
    def admin_anuncio_crear():
        datos = request.json or {}
        audiencia = datos.get('audiencia', 'todos')

        destinatarios = None
        if audiencia == 'usuarios':
            # Se aceptan nombres o códigos públicos, uno por línea o separados por comas.
            destinatarios, desconocidos = _resolver_destinatarios(datos.get('usuarios'))
            if desconocidos:
                return jsonify({'exito': False, 'mensaje': 'usuarios_desconocidos',
                                'detalle': desconocidos})

        expira = _expiracion(datos.get('horas'))
        ok, res = base_datos.crear_anuncio(
            tipo=datos.get('tipo', 'notificacion'),
            titulo=datos.get('titulo'),
            cuerpo=datos.get('cuerpo'),
            creado_por=session.get('username'),
            audiencia=audiencia,
            group_id=datos.get('group_id'),
            destinatarios=destinatarios,
            expira_en=expira)
        if not ok:
            return jsonify({'exito': False, 'mensaje': res})

        anuncio_id = res
        objetivos = base_datos.destinatarios_de(anuncio_id)
        # `notificar` monta {'tipo': …, **payload}: la forma del anuncio viaja como
        # `tipo_anuncio` para no pisar el tipo de notificación.
        for username in objetivos:
            _notificar(username, 'anuncio', {
                'id': anuncio_id, 'tipo_anuncio': datos.get('tipo', 'notificacion'),
                'titulo': datos.get('titulo'), 'cuerpo': datos.get('cuerpo')})
        _auditar('anuncio', datos.get('tipo'), f"{audiencia} · {len(objetivos)} destinatarios")
        return jsonify({'exito': True, 'id': anuncio_id, 'destinatarios': len(objetivos)})

    @app.route('/admin/api/anuncios/<int:anuncio_id>/desactivar', methods=['POST'])
    @admin_requerido
    def admin_anuncio_desactivar(anuncio_id):
        if not base_datos.desactivar_anuncio(anuncio_id):
            return jsonify({'exito': False, 'mensaje': 'no_existe'}), 404
        _auditar('anuncio_desactivar', f"#{anuncio_id}")
        if _socketio:
            _socketio.emit('anuncio_retirado', {'id': anuncio_id})
        return jsonify({'exito': True})

    # ======================================================================
    # 8. Auditoría
    # ======================================================================

    @app.route('/admin/api/auditoria', methods=['GET'])
    @admin_requerido
    def admin_auditoria():
        return jsonify({'exito': True,
                        'registros': base_datos.listar_auditoria(
                            request.args.get('limite', 100, type=int))})

    # ======================================================================
    # 9. SOPORTE — lado del jugador
    # ======================================================================

    @app.route('/api/soporte', methods=['GET'])
    def soporte_listar():
        uid = _mi_id()
        if not uid:
            return jsonify({'exito': False, 'mensaje': 'no_auth'}), 401
        return jsonify({'exito': True, 'tickets': base_datos.listar_tickets_de(uid),
                        'no_leidos': base_datos.contar_soporte_no_leido(uid)})

    @app.route('/api/soporte', methods=['POST'])
    def soporte_crear():
        uid = _mi_id()
        if not uid:
            return jsonify({'exito': False, 'mensaje': 'no_auth'}), 401
        if not _rate_ok(f"ticket:{uid}", 5, 3600):
            return jsonify({'exito': False, 'mensaje': 'rate_limit'})
        datos = request.json or {}
        ok, res = base_datos.crear_ticket(uid, datos.get('asunto'), datos.get('cuerpo'),
                                          datos.get('tipo', 'otro'))
        if not ok:
            return jsonify({'exito': False, 'mensaje': res})
        _avisar_admins('soporte_nuevo', {'ticket_id': res, 'de': session.get('username')})
        return jsonify({'exito': True, 'ticket_id': res})

    @app.route('/api/soporte/<int:ticket_id>', methods=['GET'])
    def soporte_ver(ticket_id):
        uid = _mi_id()
        if not uid:
            return jsonify({'exito': False, 'mensaje': 'no_auth'}), 401
        ticket = base_datos.obtener_ticket(ticket_id)
        if not ticket or ticket['user_id'] != uid:
            return jsonify({'exito': False, 'mensaje': 'no_existe'}), 404
        base_datos.marcar_ticket_leido(ticket_id, 'user')
        return jsonify({'exito': True, 'ticket': ticket,
                        'mensajes': base_datos.mensajes_ticket(ticket_id)})

    @app.route('/api/soporte/<int:ticket_id>', methods=['POST'])
    def soporte_responder(ticket_id):
        uid = _mi_id()
        if not uid:
            return jsonify({'exito': False, 'mensaje': 'no_auth'}), 401
        if not _rate_ok(f"soporte_msg:{uid}", 20, 3600):
            return jsonify({'exito': False, 'mensaje': 'rate_limit'})
        ticket = base_datos.obtener_ticket(ticket_id)
        if not ticket or ticket['user_id'] != uid:
            return jsonify({'exito': False, 'mensaje': 'no_existe'}), 404
        datos = request.json or {}
        ok, res = base_datos.responder_ticket(ticket_id, 'user', session.get('username'),
                                              datos.get('body'))
        if not ok:
            return jsonify({'exito': False, 'mensaje': res})
        _avisar_admins('soporte_nuevo', {'ticket_id': ticket_id, 'de': session.get('username')})
        return jsonify({'exito': True, 'mensaje': res})

    @app.route('/api/soporte/<int:ticket_id>/cerrar', methods=['POST'])
    def soporte_cerrar(ticket_id):
        """El propio usuario da su incidencia por resuelta."""
        uid = _mi_id()
        if not uid:
            return jsonify({'exito': False, 'mensaje': 'no_auth'}), 401
        ticket = base_datos.obtener_ticket(ticket_id)
        if not ticket or ticket['user_id'] != uid:
            return jsonify({'exito': False, 'mensaje': 'no_existe'}), 404
        base_datos.cambiar_estado_ticket(ticket_id, 'resuelto')
        return jsonify({'exito': True})

    # ======================================================================
    # 10. ANUNCIOS — lado del jugador
    # ======================================================================

    @app.route('/api/anuncios', methods=['GET'])
    def anuncios_mios():
        """Funciona con y sin cuenta: el invitado ve los mensajes fijados públicos
        (entre ellos el cartel de mantenimiento)."""
        datos = base_datos.anuncios_para(_mi_id())
        mantenimiento = None
        if base_datos.config_get('mantenimiento_activo', '0') == '1':
            mantenimiento = base_datos.config_get('mantenimiento_texto', '') or ''
        return jsonify({'exito': True, **datos, 'mantenimiento': mantenimiento})

    @app.route('/api/anuncios/<int:anuncio_id>/leido', methods=['POST'])
    def anuncio_leido(anuncio_id):
        uid = _mi_id()
        if not uid:
            return jsonify({'exito': False, 'mensaje': 'no_auth'}), 401
        base_datos.marcar_anuncio_leido(anuncio_id, uid)
        return jsonify({'exito': True})


# ==========================================================================
# Utilidades internas
# ==========================================================================

def _mi_id():
    return base_datos.obtener_id_usuario(session.get('username'))


def _fecha(texto):
    try:
        return datetime.strptime((texto or '').strip(), '%Y-%m-%d')
    except (ValueError, AttributeError):
        return None


def _expiracion(horas):
    """'horas' → marca ISO de caducidad. 0/None = no caduca (hasta desfijarlo)."""
    try:
        h = float(horas)
    except (TypeError, ValueError):
        return None
    return (datetime.now() + timedelta(hours=h)).isoformat() if h > 0 else None


def _listar_checkpoints():
    """Modelos disponibles para el bot, del más reciente al más antiguo."""
    if not os.path.isdir(DIR_CHECKPOINTS):
        return []
    archivos = [f for f in os.listdir(DIR_CHECKPOINTS) if f.endswith('.pth')]
    archivos.sort(key=lambda f: os.path.getmtime(os.path.join(DIR_CHECKPOINTS, f)), reverse=True)
    return archivos


def _listar_grupos():
    """Grupos existentes, para poder dirigirles un anuncio."""
    with base_datos._conn() as c:
        filas = c.execute("""SELECT g.id, g.name,
                                    (SELECT COUNT(*) FROM GroupMembers m WHERE m.group_id = g.id) n
                             FROM Groups g ORDER BY g.name COLLATE NOCASE""").fetchall()
    return [dict(r) for r in filas]


def _resolver_destinatarios(texto):
    """'juan, #A7K2QX\\nmaria' → ([ids], [no encontrados])."""
    if isinstance(texto, list):
        piezas = texto
    else:
        piezas = (texto or '').replace('\n', ',').split(',')
    ids, fallos = [], []
    for pieza in piezas:
        pieza = pieza.strip()
        if not pieza:
            continue
        if pieza.startswith('#'):
            encontrado = base_datos.obtener_usuario_por_codigo(pieza)
            uid = encontrado[0] if encontrado else None
        else:
            uid = base_datos.obtener_id_usuario(pieza)
        if uid:
            ids.append(uid)
        else:
            fallos.append(pieza)
    return (ids, fallos)


def _listar_salas():
    """Instantánea de todas las salas vivas, 2p y 4p, con edad y ocupación. Es la
    misma información que /api/debug/salas, unificada y sin token aparte."""
    ahora = time.time()
    salas = _ctx.get('salas') or {}
    salas4 = _ctx.get('salas4') or {}
    jugadores = _ctx.get('jugadores') or {}
    fuera = []

    for codigo, sala in list(salas.items()):
        motor = sala.get('motor')
        fuera.append({
            'codigo': codigo, 'modo': '2p',
            'estado': sala.get('estado'),
            'publico': bool(sala.get('publico')),
            'vs_bot': 'bot' in sala,
            'edad_s': int(ahora - sala.get('creada_en', ahora)),
            'inactiva_s': int(ahora - sala.get('ultima_actividad', sala.get('creada_en', ahora))),
            'jugadores': [jugadores.get(s, {}).get('nombre') or ('🤖' if s and s.startswith('BOT_') else None)
                          for s in sala.get('sids', [])],
            'ronda': getattr(motor, 'ronda_n', None) if motor else None,
            'fase': getattr(motor, 'fase', None) if motor else None,
        })

    for codigo, room in list(salas4.items()):
        motor = room.get('motor')
        fuera.append({
            'codigo': codigo, 'modo': '4p',
            'estado': room.get('estado'),
            'publico': bool(room.get('publico')),
            'vs_bot': False,
            'edad_s': None,
            'inactiva_s': int(ahora - room.get('ultima_actividad', ahora)),
            'jugadores': [room.get('nombres', {}).get(i) for i in range(4)],
            'ronda': getattr(motor, 'ronda_n', None) if motor else None,
            'fase': getattr(motor, 'fase', None) if motor else None,
        })

    fuera.sort(key=lambda s: s['inactiva_s'])
    return fuera


def _expulsar_de_todo(username):
    """Tras un baneo o un borrado: cerrar sus sockets y sacarlo de sus salas para
    que el castigo sea inmediato y no haya que esperar a que se desconecte solo."""
    conectados = _ctx.get('usuarios_conectados') or {}
    salir = _ctx.get('salir_de_sala')
    for sid in list(conectados.get(username, [])):
        try:
            if salir:
                salir(sid)
            if _socketio:
                _socketio.emit('sesion_cerrada', {'motivo': 'baneado'}, room=sid)
                _socketio.server.disconnect(sid)
        except Exception as e:
            print(f"⚠️ [admin] No se pudo desconectar a {username} ({sid}): {e}")

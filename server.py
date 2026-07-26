import eventlet
eventlet.monkey_patch()

import os
import re
import ssl
import time
import random
import string
import smtplib
import secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import timedelta

from flask import (Flask, render_template, request, session, jsonify,
                   send_from_directory, redirect, url_for)
import base_datos
import decks
import social
from flask_socketio import SocketIO, emit, join_room, leave_room
from mus_mecanicas import PartidaMus
from bot_ml import SmartBot


# ==========================================
# CONFIGURACIÓN (secretos vía variables de entorno / .env)
# ==========================================

def _cargar_dotenv():
    """Carga un archivo .env sin depender de python-dotenv (opcional)."""
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if not os.path.exists(ruta):
        return
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            for linea in f:
                linea = linea.strip()
                if not linea or linea.startswith('#') or '=' not in linea:
                    continue
                clave, _, valor = linea.partition('=')
                clave = clave.strip()
                valor = valor.strip().strip('"').strip("'")
                # No pisamos variables ya definidas en el entorno real
                os.environ.setdefault(clave, valor)
    except OSError as e:
        print(f"⚠️  No se pudo leer .env: {e}")

_cargar_dotenv()

SECRET_KEY = os.environ.get('SECRET_KEY')
SMTP_USER = os.environ.get('SMTP_USER')          # p.ej. callmus.contact@gmail.com
SMTP_PASS = os.environ.get('SMTP_PASS')          # contraseña de aplicación de Gmail (16 letras)
SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '465'))
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')

# Avisos de arranque para no descubrir la falta de config en producción por sorpresa
if not SECRET_KEY:
    print("⚠️  SECRET_KEY no definida: usando clave de desarrollo INSEGURA. Define SECRET_KEY en producción.")
    SECRET_KEY = 'clave_secreta_mus_dev'
if not (SMTP_USER and SMTP_PASS):
    print("⚠️  SMTP_USER/SMTP_PASS no definidos: el envío de correos (verificación y reseteo) está DESACTIVADO.")
if not (GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET):
    print("⚠️  GOOGLE_CLIENT_ID/SECRET no definidos: el login con Google está DESACTIVADO.")

app = Flask(__name__, static_folder='static', template_folder='.')
app.config['SECRET_KEY'] = SECRET_KEY
app.permanent_session_lifetime = timedelta(days=30)
# Techo global del cuerpo de una petición. Lo único que sube algo pesado es la
# subida de barajas del panel (Roadmap #5), y ahí `decks.py` aplica sus propios
# límites; esto es la red por debajo, para que nadie ocupe memoria mandando un
# cuerpo enorme a cualquier otra ruta.
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024
# ping_timeout/interval holgados: minimizar/cambiar de pestaña en el móvil suspende
# los temporizadores del navegador; con umbrales altos un parón breve NO cuenta como
# desconexión y ni siquiera hace falta reconectar. Compatible con eventlet.
socketio = SocketIO(app, cors_allowed_origins="*", ping_timeout=60, ping_interval=25)

# --- Google OAuth (Authlib). Solo se registra si hay credenciales. ---
oauth = None
if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    try:
        from authlib.integrations.flask_client import OAuth
        oauth = OAuth(app)
        oauth.register(
            name='google',
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile'},
        )
    except ImportError:
        print("⚠️  Authlib no está instalado; el login con Google no funcionará. Instala 'Authlib'.")
        oauth = None

@app.after_request
def add_header(response):
    # Verificamos la ruta de la petición de forma segura
    if request.path.startswith('/static/img/'):
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    elif request.path.startswith('/auth/') or request.path.startswith('/api/'):
        # NUNCA cachear el estado de sesión. Sin estas cabeceras algunos navegadores
        # (Safari sobre todo) reutilizan la respuesta anterior de /auth/sesion: entras
        # y la web sigue diciendo que no lo has hecho, o sales y al recargar vuelves a
        # aparecer dentro. Es el bug de "no me loguea hasta que refresco".
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

# --- NUEVA ARQUITECTURA MULTIJUGADOR ---
# jugadores = { 'sid': {'nombre': 'Juan', 'sala': 'A1B2'} }
jugadores = {}  
# salas = { 'A1B2': {'estado': 'esperando', 'sids': [sid1, sid2], 'motor': PartidaMus} }
salas = {}

show_global_log = False

# Reconexión 2p / vs-IA: ventana de gracia (s) que aguanta una partida en pausa
# tras una caída antes de darla por terminada. Igual valor que el 4p (server_mus4).
GRACIA_RECONEXION_2P = 90

# Sustituciones: cuando alguien abandona (o agota la gracia) y quien se queda
# acepta esperar, la partida pasa a 'esperando_reemplazo' y se anuncia en la lista
# pública como partida EN CURSO con hueco libre durante esta ventana.
ESPERA_REEMPLAZO = 300   # 5 min

# Barredor de salas fantasma (Roadmap #21). Los temporizadores puntuales
# (limpiar_sala_huerfana, fin de gracia, fin de espera) cubren el caso normal;
# esto es la red de seguridad para cuando uno de ellos se pierde (excepción en el
# greenlet, carrera con un rejoin, servidor recargado en caliente…).
VIDA_MAX_ESPERANDO = 1800    # 30 min en el vestíbulo sin llegar a arrancar
VIDA_MAX_JUGANDO = 7200      # 2 h sin una sola acción de nadie
INTERVALO_BARRIDO = 300      # el barredor pasa cada 5 min


def _sid_vivo(sid):
    """True si ese asiento lo ocupa una conexión real y todavía registrada."""
    return bool(sid) and not sid.startswith('BOT_') and sid in jugadores


def _tocar_sala(codigo):
    """Marca actividad en la sala (lo lee el barredor para matar salas zombis)."""
    sala = salas.get(codigo)
    if sala is not None:
        sala['ultima_actividad'] = time.time()


def _remap_sid_2p(motor, old, new):
    """Reasigna un sid viejo→nuevo dentro de una instancia PartidaMus SIN tocar la
    clase del motor (que es intocable). El motor está indexado por sid en todas
    partes (j1/j2, id_mano, id_postre, turno_de, claves de estado/nombres_ia,
    listas, sids incrustados en recuento/dejes…), así que recorremos su __dict__ en
    profundidad y sustituimos el escalar y las claves/valores de dicts y listas.
    Los sids son cadenas largas y únicas, así que no hay riesgo de colisión."""
    if old == new:
        return

    def _walk(obj):
        if obj == old:
            return new
        if isinstance(obj, dict):
            return {(_walk(k)): _walk(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_walk(v) for v in obj]
        if isinstance(obj, tuple):
            return tuple(_walk(v) for v in obj)
        return obj

    for attr, val in list(vars(motor).items()):
        setattr(motor, attr, _walk(val))


# ==========================================
# Abandono voluntario y sustituciones (2p / vs-IA)
# ==========================================
def _sids_humanos_2p(sala):
    """Asientos ocupados por personas reales (el bot tiene sid falso 'BOT_...')."""
    return [s for s in sala.get('sids', []) if s and not s.startswith('BOT_')]


def _destruir_sala_2p(codigo, motivo=None):
    """Cierra una sala y limpia TODOS sus rastros, incluido el sid falso del bot
    (que hasta ahora se quedaba huérfano en `jugadores`, ver Roadmap bugs #2)."""
    sala = salas.pop(codigo, None)
    if not sala:
        return
    if motivo:
        socketio.emit('rival_desconectado', {'motivo': motivo}, room=codigo)
    # Barremos `jugadores` entero, no solo los asientos actuales: un sid que quedó
    # apuntando a esta sala tras un remap/abandono también es basura (Roadmap #3).
    for s, info in list(jugadores.items()):
        if info.get('sala') == codigo:
            jugadores.pop(s, None)
    try:
        socketio.close_room(codigo)   # nadie queda suscrito a una sala muerta
    except Exception:
        pass
    emitir_lista_publicas()


def _seat_motor_2p(motor, seat):
    """sid con el que el motor indexa ese asiento. j1/j2 se fijan al crear la
    partida y NO cambian con `cambiar_roles` (eso solo permuta mano/postre), así
    que el asiento 0 es siempre j1 y el 1 siempre j2."""
    return motor.j1 if seat == 0 else motor.j2


def _abrir_hueco_2p(codigo, seat, nombre, motivo):
    """Deja libre un asiento de una partida en curso y ofrece a quien se queda la
    opción de esperar sustituto. Si no queda nadie, la sala muere."""
    sala = salas.get(codigo)
    if not sala:
        return
    sala.setdefault('ultimo_sid', {})[seat] = _seat_motor_2p(sala['motor'], seat) if sala.get('motor') else None
    sala['sids'][seat] = None
    sala.get('tokens', {}).pop(seat, None)
    sala.get('esperando_votos', set()).discard(seat)

    if not _sids_humanos_2p(sala):
        _destruir_sala_2p(codigo)
        return

    sala['estado'] = 'esperando_reemplazo'
    sala['esperando_desde'] = time.time()
    sala.setdefault('esperando_votos', set())
    # Para poder rellenar el hueco hay que ser visible: una sala privada se
    # publica mientras dure la espera (decidido con el usuario).
    sala['publico'] = True
    socketio.emit('jugador_abandono',
                  {'nombre': nombre, 'motivo': motivo, 'espera': ESPERA_REEMPLAZO},
                  room=codigo)
    _programar_fin_espera_2p(codigo, sala['esperando_desde'])
    emitir_lista_publicas()


def _programar_fin_espera_2p(codigo, marca):
    """Si nadie ocupa el hueco dentro de la ventana, la partida se da por acabada."""
    def tarea():
        socketio.sleep(ESPERA_REEMPLAZO)
        sala = salas.get(codigo)
        if sala and sala.get('estado') == 'esperando_reemplazo' and sala.get('esperando_desde') == marca:
            print(f"🧹 Nadie ocupó el hueco de {codigo}: se termina la partida.")
            _destruir_sala_2p(codigo, motivo='sin_reemplazo')
    socketio.start_background_task(tarea)


def _sentar_reemplazo_2p(codigo, sid, nombre, username):
    """Sienta a un recién llegado en el asiento vacante de una partida en curso.

    El marcador (puntos y partidas ganadas) se conserva, pero la ronda en juego se
    descarta y se reparte de nuevo: el que se fue ya vio esas cartas, y así no hay
    que heredar estados a medias (envites vivos, descartes ya hechos)."""
    sala = salas.get(codigo)
    if not sala or sala.get('estado') != 'esperando_reemplazo':
        return False
    sids = sala['sids']
    libres = [i for i, s in enumerate(sids) if s is None]
    # Solo se admite sustituto si el hueco es el ÚLTIMO: si el que esperaba también
    # está caído no hay partida a la que incorporarse (volverá o la barrerá el timer).
    if len(libres) != 1:
        return False
    seat = libres[0]

    motor = sala['motor']
    _remap_sid_2p(motor, _seat_motor_2p(motor, seat), sid)
    motor.nombres_ia[sid] = username or nombre
    # El asiento cambia de dueño a mitad de match: al log v2, para que la
    # atribución por persona del dataset derivado siga siendo exacta.
    motor.log.seat(motor.seat(sid), 'human', code=username)

    sids[seat] = sid
    sala.get('ultimo_sid', {}).pop(seat, None)
    jugadores[sid] = {'nombre': nombre, 'sala': codigo, 'username': username}
    join_room(codigo)

    token = secrets.token_hex(16)
    sala.setdefault('tokens', {})[seat] = token

    # Ronda nueva conservando el marcador (si la partida acababa de llegar a 40,
    # arrancamos la siguiente partida del match).
    if motor.estado[motor.j1]['puntos'] >= 40 or motor.estado[motor.j2]['puntos'] >= 40:
        motor.reiniciar_partida()
        motor.db_registrada = False
    else:
        motor.cambiar_roles()
        motor.iniciar_ronda()
        motor.fase = 'espera_reparto'
        motor.turno_de = motor.id_postre
    motor.jugadores_listos = []
    motor.recuento_calculado = False
    motor.pasos_recuento = []

    sala['estado'] = 'jugando'
    sala['ultima_actividad'] = time.time()
    sala.pop('esperando_desde', None)
    sala.pop('esperando_votos', None)
    sala.pop('pausada_desde', None)

    emit('sala_creada', {'codigo': codigo, 'token': token}, room=sid)
    emit('iniciar_partida', {'mensaje': '¡La partida comienza!'}, room=sid)
    socketio.emit('reemplazo_encontrado', {'nombre': username or nombre}, room=codigo)
    enviar_estado_a_jugadores(codigo)
    emitir_lista_publicas()
    return True


def generar_codigo():
    letras = string.ascii_uppercase + string.digits
    return ''.join(random.choice(letras) for _ in range(4))

@app.route('/')
def index():
    return render_template('index.html')


# ==========================================
# GESTIÓN DE USUARIOS Y SESIONES (Vía HTTP)
# ==========================================


@app.route('/api/leaderboard', methods=['GET'])
def api_leaderboard():
    datos = base_datos.obtener_leaderboard()
    return jsonify({'exito': True, 'leaderboard': datos})


# ==========================================
# BARAJAS TEMÁTICAS (Roadmap #5)
# ------------------------------------------
# El servidor NO deja de mandar el campo `img` de cada carta: la piel es cosa
# del cliente, que resuelve la ruta con el tema que el jugador tenga puesto en
# ese hueco de palo. Aquí sólo se dice qué temas existen, cuáles puede usar
# quien pregunta, y se guarda su elección si tiene cuenta.
#
# El catálogo se sirve también sin sesión (un invitado juega con la baraja
# clásica y ve el resto marcado como bloqueado), así que no hay nada privado
# en la respuesta.
#
# La elección SÍ viaja a la mesa: cada carta se pinta con la baraja de su dueño,
# así que la del rival hay que conocerla. La guarda `decks.recordar_baraja` por
# sid (ver el evento `mi_baraja` más abajo) y sale en el estado de la partida.
# ==========================================

@app.route('/api/decks', methods=['GET'])
def api_decks():
    username = session.get('username')
    es_admin = base_datos.es_admin(username)
    idioma = 'en' if request.args.get('lang') == 'en' else 'es'
    temas = decks.temas_para(username, es_admin, idioma)
    usables = {t['slug'] for t in temas if not t['bloqueado']}
    return jsonify({
        'exito': True,
        'temas': temas,
        'huecos': list(decks.HUECOS),
        'config': decks.config_de(username, usables) if username else None,
        'defecto': decks.CONFIG_DEFECTO,
        'logueado': bool(username),
    })


@app.route('/api/deck', methods=['POST'])
def api_deck_guardar():
    """Guarda la baraja del jugador. Los invitados la conservan en su navegador
    (localStorage): sin cuenta no hay dónde guardarla ni nada que sincronizar."""
    username = session.get('username')
    if not username:
        return jsonify({'exito': False, 'codigo': 'necesita_cuenta'}), 401
    datos = request.json or {}
    config = datos.get('config')
    if not isinstance(config, dict):
        return jsonify({'exito': False, 'codigo': 'config_invalida'}), 400
    usables = decks.slugs_usables(username, base_datos.es_admin(username))
    guardada = decks.guardar_config(username, config, usables)
    return jsonify({'exito': True, 'config': guardada})


# --- Helpers de correo, validación y códigos temporales ---

# codigos_pendientes[email] = {'code': '123456', 'datos': {...}, 'ts': epoch, 'tipo': 'registro'|'reset'}
codigos_pendientes = {}
# solicitudes_por_email[email] = [epoch, epoch, ...]  (para limitar peticiones)
solicitudes_por_email = {}

CODIGO_VALIDEZ_SEG = 15 * 60      # el código caduca a los 15 minutos
MAX_SOLICITUDES_HORA = 3          # máximo de códigos por email y hora

EMAIL_REGEX = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
USERNAME_REGEX = re.compile(r'^[A-Za-z0-9_]{3,20}$')


def validar_registro(username, email, password):
    """Validación de servidor (espejo de la del cliente). Devuelve mensaje de error o None."""
    if not username or not USERNAME_REGEX.match(username):
        return "El usuario debe tener 3-20 caracteres (letras, números o _)."
    if not email or not EMAIL_REGEX.match(email):
        return "Introduce un correo electrónico válido."
    if not password or len(password) < 6:
        return "La contraseña debe tener al menos 6 caracteres."
    return None


def rate_limit_ok(email):
    """True si el email no ha superado el número de solicitudes por hora."""
    ahora = time.time()
    recientes = [t for t in solicitudes_por_email.get(email, []) if ahora - t < 3600]
    solicitudes_por_email[email] = recientes
    if len(recientes) >= MAX_SOLICITUDES_HORA:
        return False
    recientes.append(ahora)
    return True


def enviar_correo(destino, asunto, cuerpo_texto):
    """Envía un correo por SMTP (Gmail SSL). Devuelve True/False."""
    if not (SMTP_USER and SMTP_PASS):
        print(f"✉️  [SIMULADO — sin SMTP] Para {destino} | {asunto}\n{cuerpo_texto}")
        return False
    try:
        msg = MIMEMultipart()
        msg['From'] = f"CallMus <{SMTP_USER}>"
        msg['To'] = destino
        msg['Subject'] = asunto
        msg.attach(MIMEText(cuerpo_texto, 'plain', 'utf-8'))

        contexto = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=contexto) as servidor:
            servidor.login(SMTP_USER, SMTP_PASS)
            servidor.sendmail(SMTP_USER, destino, msg.as_string())
        return True
    except Exception as e:
        print(f"❌ Error enviando correo a {destino}: {e}")
        return False


def generar_codigo_verificacion():
    return ''.join(secrets.choice(string.digits) for _ in range(6))


@app.route('/auth/solicitar_codigo', methods=['POST'])
def auth_solicitar_codigo():
    """Paso 1 del registro: valida, comprueba duplicados y manda un código al correo."""
    datos = request.json or {}
    username = (datos.get('username') or '').strip()
    email = (datos.get('email') or '').strip()
    password = datos.get('password') or ''

    error = validar_registro(username, email, password)
    if error:
        return jsonify({'exito': False, 'mensaje': error})

    # Duplicados ANTES de enviar el código
    existe, msg = base_datos.existe_usuario(username, email)
    if existe:
        return jsonify({'exito': False, 'mensaje': msg})

    if not rate_limit_ok(email):
        return jsonify({'exito': False, 'mensaje': 'Demasiadas solicitudes. Inténtalo de nuevo en una hora.'})

    codigo = generar_codigo_verificacion()
    codigos_pendientes[email] = {'code': codigo, 'ts': time.time(), 'tipo': 'registro'}

    cuerpo = (f"¡Bienvenido a CallMus!\n\n"
              f"Tu código de verificación es: {codigo}\n\n"
              f"Caduca en 15 minutos. Si no has solicitado esto, ignora este correo.")
    enviado = enviar_correo(email, "Tu código de verificación de CallMus", cuerpo)

    if not enviado and not (SMTP_USER and SMTP_PASS):
        # En desarrollo sin SMTP configurado, no bloqueamos: el código sale por consola.
        return jsonify({'exito': True, 'mensaje': 'Código generado (modo desarrollo: revisa la consola del servidor).'})
    if not enviado:
        return jsonify({'exito': False, 'mensaje': 'No se pudo enviar el correo. Revisa la dirección e inténtalo de nuevo.'})

    return jsonify({'exito': True, 'mensaje': '¡Código enviado!'})


@app.route('/auth/registro', methods=['POST'])
def auth_registro():
    """Paso 2 del registro: verifica el código y crea la cuenta (con auto-login)."""
    datos = request.json or {}
    email = (datos.get('email') or '').strip()
    username = (datos.get('username') or '').strip()
    password = datos.get('password') or ''
    codigo_recibido = (datos.get('code') or '').strip()

    error = validar_registro(username, email, password)
    if error:
        return jsonify({'exito': False, 'mensaje': error})

    pendiente = codigos_pendientes.get(email)
    if not pendiente or pendiente.get('tipo') != 'registro':
        return jsonify({'exito': False, 'mensaje': 'No hay ninguna verificación pendiente para este correo.'})
    if time.time() - pendiente['ts'] > CODIGO_VALIDEZ_SEG:
        codigos_pendientes.pop(email, None)
        return jsonify({'exito': False, 'mensaje': 'El código ha caducado. Solicita uno nuevo.'})
    if codigo_recibido != pendiente['code']:
        return jsonify({'exito': False, 'mensaje': 'Código incorrecto.'})

    exito, msg = base_datos.registrar_usuario(
        username, password, datos.get('country'), datos.get('birthdate'), email)

    if exito:
        codigos_pendientes.pop(email, None)
        solicitudes_por_email.pop(email, None)
        session.permanent = True
        session['username'] = username

    return jsonify({'exito': exito, 'mensaje': msg})


@app.route('/auth/login', methods=['POST'])
def auth_login():
    """Acepta username O email como identificador."""
    datos = request.json or {}
    identificador = (datos.get('username') or '').strip()

    username = base_datos.verificar_login(identificador, datos.get('password') or '')
    if username:
        # Cuentas baneadas desde el panel (#13): la contraseña es correcta, pero no
        # se abre sesión. El motivo se enseña para que sepa a qué atenerse.
        baneado, motivo = base_datos.esta_baneado(username)
        if baneado:
            return jsonify({'exito': False, 'codigo': 'err_cuenta_baneada',
                            'motivo': motivo,
                            'mensaje': 'Esta cuenta está suspendida.' +
                                       (f' Motivo: {motivo}' if motivo else '')})
        session.permanent = bool(datos.get('remember', False))
        session['username'] = username
        return jsonify({'exito': True})

    return jsonify({'exito': False, 'mensaje': 'Usuario/correo o contraseña incorrectos'})


@app.route('/auth/solicitar_reset', methods=['POST'])
def auth_solicitar_reset():
    """Paso 1 de recuperación: manda un código al correo si existe una cuenta."""
    datos = request.json or {}
    email = (datos.get('email') or '').strip()

    if not email or not EMAIL_REGEX.match(email):
        return jsonify({'exito': False, 'mensaje': 'Introduce un correo electrónico válido.'})

    if not rate_limit_ok(email):
        return jsonify({'exito': False, 'mensaje': 'Demasiadas solicitudes. Inténtalo de nuevo en una hora.'})

    username = base_datos.email_registrado(email)
    if username:
        codigo = generar_codigo_verificacion()
        codigos_pendientes[email] = {'code': codigo, 'ts': time.time(), 'tipo': 'reset'}
        cuerpo = (f"Hola {username},\n\n"
                  f"Tu código para restablecer la contraseña de CallMus es: {codigo}\n\n"
                  f"Caduca en 15 minutos. Si no has pedido esto, ignora este correo y tu cuenta seguirá segura.")
        enviar_correo(email, "Restablece tu contraseña de CallMus", cuerpo)

    # Respuesta idéntica exista o no la cuenta: no revelamos qué correos están registrados.
    return jsonify({'exito': True, 'mensaje': 'Si ese correo tiene una cuenta, te hemos enviado un código.'})


@app.route('/auth/reset', methods=['POST'])
def auth_reset():
    """Paso 2 de recuperación: verifica el código y cambia la contraseña."""
    datos = request.json or {}
    email = (datos.get('email') or '').strip()
    codigo_recibido = (datos.get('code') or '').strip()
    nueva = datos.get('password') or ''

    if len(nueva) < 6:
        return jsonify({'exito': False, 'mensaje': 'La nueva contraseña debe tener al menos 6 caracteres.'})

    pendiente = codigos_pendientes.get(email)
    if not pendiente or pendiente.get('tipo') != 'reset':
        return jsonify({'exito': False, 'mensaje': 'No hay ninguna solicitud de reseteo para este correo.'})
    if time.time() - pendiente['ts'] > CODIGO_VALIDEZ_SEG:
        codigos_pendientes.pop(email, None)
        return jsonify({'exito': False, 'mensaje': 'El código ha caducado. Solicita uno nuevo.'})
    if codigo_recibido != pendiente['code']:
        return jsonify({'exito': False, 'mensaje': 'Código incorrecto.'})

    if base_datos.actualizar_password(email, nueva):
        codigos_pendientes.pop(email, None)
        solicitudes_por_email.pop(email, None)
        return jsonify({'exito': True, 'mensaje': 'Contraseña actualizada. Ya puedes iniciar sesión.'})
    return jsonify({'exito': False, 'mensaje': 'No se pudo actualizar la contraseña.'})


# --- Google OAuth ---

@app.route('/auth/google/login')
def google_login():
    if not oauth:
        return "El login con Google no está configurado en este servidor.", 503
    # ?intent=signup viene del botón de registrarse y autoriza a crear la cuenta.
    # Cualquier otra cosa (incluido el botón de entrar) es solo iniciar sesión: si no
    # hay cuenta se avisa, en vez de crear una en silencio. Va por la sesión y no por
    # la URL de vuelta para que no se pueda forzar desde fuera.
    session['google_intent'] = 'signup' if request.args.get('intent') == 'signup' else 'login'
    redireccion = url_for('google_callback', _external=True)
    return oauth.google.authorize_redirect(redireccion)


@app.route('/auth/google/callback')
def google_callback():
    if not oauth:
        return redirect('/')
    try:
        token = oauth.google.authorize_access_token()
        info = token.get('userinfo') or oauth.google.userinfo()
    except Exception as e:
        print(f"❌ Error en el callback de Google: {e}")
        return redirect('/?auth_error=google')

    google_id = info.get('sub')
    email = info.get('email')
    nombre = info.get('name') or info.get('given_name') or ''
    intent = session.pop('google_intent', 'login')
    if not google_id:
        return redirect('/?auth_error=google')

    username = base_datos.registrar_o_loguear_google(google_id, email, nombre,
                                                     crear=(intent == 'signup'))
    if not username:
        # Venía de "Entrar" y esa cuenta de Google no está vinculada a ninguna.
        return redirect('/?auth_error=google_sin_cuenta')

    session.permanent = True
    session['username'] = username
    return redirect('/')


@app.route('/auth/sesion', methods=['GET'])
def auth_sesion():
    if 'username' in session:
        user = session['username']
        # Un baneo posterior al login tiene que echarle también de la sesión que ya
        # tenía abierta, no solo impedirle volver a entrar.
        baneado, _motivo = base_datos.esta_baneado(user)
        if baneado:
            session.pop('username', None)
            return jsonify({'exito': False, 'codigo': 'err_cuenta_baneada'})
        usuario_data = base_datos.obtener_usuario(user)
        if usuario_data:
            return jsonify({'exito': True, 'usuario': usuario_data})
        # La cuenta ya no existe (borrada, o renombrada en otra pestaña): la cookie
        # se queda coja, así que la vaciamos en vez de dejarla apuntando a la nada.
        session.pop('username', None)
    return jsonify({'exito': False})

@app.route('/auth/logout', methods=['POST'])
def auth_logout():
    session.pop('username', None)
    return jsonify({'exito': True})


# ==========================================
# AJUSTES DE CUENTA (Roadmap #22)
# ------------------------------------------
# Cambiar nombre, correo y contraseña, y borrar la cuenta. Todo pasa por la
# sesión de Flask (nunca se acepta el usuario objetivo desde el cliente) y por
# _autorizar_cambio(), que exige contraseña actual o código al correo.
# Las respuestas llevan un 'codigo' de traducción además del 'mensaje' en
# castellano, para que el cliente pueda enseñarlo en el idioma elegido.
# ==========================================

def _respuesta(exito, codigo, mensaje, **extra):
    return jsonify({'exito': exito, 'codigo': codigo, 'mensaje': mensaje, **extra})


def _ocultar_email(email):
    """juan.perez@gmail.com → j*********z@gmail.com (para enseñar a dónde va el código)."""
    if not email or '@' not in email:
        return ''
    local, _, dominio = email.partition('@')
    if len(local) <= 2:
        return f"{local[0]}*@{dominio}"
    return f"{local[0]}{'*' * (len(local) - 2)}{local[-1]}@{dominio}"


def _autorizar_cambio(username, datos):
    """Credencial para una operación sensible: contraseña actual O código de un solo
    uso enviado al correo de la cuenta (la única vía para quien entró con Google y
    no tiene contraseña). Devuelve (ok, codigo_error, mensaje_error)."""
    password = datos.get('password') or ''
    codigo = (datos.get('code') or '').strip()

    if password:
        if base_datos.verificar_password_usuario(username, password):
            return True, None, None
        return False, 'err_password_incorrecta', 'La contraseña actual no es correcta.'

    if codigo:
        email = base_datos.obtener_email(username)
        pendiente = codigos_pendientes.get(email) if email else None
        if not pendiente or pendiente.get('tipo') != 'cuenta':
            return False, 'err_sin_codigo', 'No hay ningún código pendiente para esta cuenta.'
        if time.time() - pendiente['ts'] > CODIGO_VALIDEZ_SEG:
            codigos_pendientes.pop(email, None)
            return False, 'err_codigo_caducado', 'El código ha caducado. Solicita uno nuevo.'
        if not secrets.compare_digest(codigo, pendiente['code']):
            return False, 'err_codigo_incorrecto', 'Código incorrecto.'
        codigos_pendientes.pop(email, None)      # de un solo uso
        return True, None, None

    return False, 'err_falta_credencial', 'Confirma la operación con tu contraseña.'


@app.route('/auth/cuenta/codigo', methods=['POST'])
def auth_cuenta_codigo():
    """Envía al correo de la cuenta un código para autorizar un cambio."""
    username = session.get('username')
    if not username:
        return _respuesta(False, 'err_sin_sesion', 'Tienes que iniciar sesión.'), 401

    email = base_datos.obtener_email(username)
    if not email:
        return _respuesta(False, 'err_sin_email', 'Esta cuenta no tiene ningún correo asociado.')
    if not rate_limit_ok(email):
        return _respuesta(False, 'err_demasiadas_solicitudes',
                          'Demasiadas solicitudes. Inténtalo de nuevo en una hora.')

    codigo = generar_codigo_verificacion()
    codigos_pendientes[email] = {'code': codigo, 'ts': time.time(), 'tipo': 'cuenta'}
    enviar_correo(email, "Código para cambiar los ajustes de tu cuenta de CallMus",
                  f"Hola {username},\n\n"
                  f"Tu código para confirmar el cambio es: {codigo}\n\n"
                  f"Caduca en 15 minutos. Si no has sido tú, ignora este correo y "
                  f"cambia tu contraseña por precaución.")
    return _respuesta(True, 'ok_codigo_enviado', 'Te hemos enviado un código.',
                      email_oculto=_ocultar_email(email))


@app.route('/auth/cuenta/username', methods=['POST'])
def auth_cuenta_username():
    username = session.get('username')
    if not username:
        return _respuesta(False, 'err_sin_sesion', 'Tienes que iniciar sesión.'), 401

    datos = request.json or {}
    nuevo = (datos.get('username') or '').strip()
    if not USERNAME_REGEX.match(nuevo):
        return _respuesta(False, 'err_username_invalido',
                          'El usuario debe tener 3-20 caracteres (letras, números o _).')
    if nuevo == username:
        return _respuesta(False, 'err_username_igual', 'Ese ya es tu nombre de usuario.')

    ok, cod_error, msg_error = _autorizar_cambio(username, datos)
    if not ok:
        return _respuesta(False, cod_error, msg_error)

    exito, codigo = base_datos.cambiar_username(username, nuevo)
    if exito:
        session['username'] = nuevo          # la sesión sigue al nombre nuevo
        return _respuesta(True, codigo, 'Nombre de usuario actualizado.', username=nuevo)

    dias = base_datos.DIAS_ESPERA_CAMBIO_USERNAME
    mensajes = {
        'err_username_en_uso': 'Ese nombre de usuario ya está en uso.',
        'err_username_espera': f'Solo puedes cambiar de nombre cada {dias} días.',
    }
    # `dias` viaja aparte para que el cliente pueda rellenar {dias} en su idioma.
    return _respuesta(False, codigo, mensajes.get(codigo, 'No se pudo cambiar el nombre.'), dias=dias)


@app.route('/auth/cuenta/email/solicitar', methods=['POST'])
def auth_cuenta_email_solicitar():
    """Paso 1 del cambio de correo: manda un código a la dirección NUEVA (así se
    demuestra que es suya) y avisa a la vieja de que alguien lo ha pedido."""
    username = session.get('username')
    if not username:
        return _respuesta(False, 'err_sin_sesion', 'Tienes que iniciar sesión.'), 401

    datos = request.json or {}
    nuevo = (datos.get('email') or '').strip()
    if not EMAIL_REGEX.match(nuevo):
        return _respuesta(False, 'err_email_invalido', 'Introduce un correo electrónico válido.')

    anterior = base_datos.obtener_email(username)
    if anterior and nuevo.lower() == anterior.lower():
        return _respuesta(False, 'err_email_igual', 'Ese ya es tu correo actual.')

    ok, cod_error, msg_error = _autorizar_cambio(username, datos)
    if not ok:
        return _respuesta(False, cod_error, msg_error)

    if base_datos.email_registrado(nuevo):
        return _respuesta(False, 'err_email_en_uso', 'Ya existe una cuenta con ese correo.')
    if not rate_limit_ok(nuevo):
        return _respuesta(False, 'err_demasiadas_solicitudes',
                          'Demasiadas solicitudes. Inténtalo de nuevo en una hora.')

    codigo = generar_codigo_verificacion()
    codigos_pendientes[nuevo] = {'code': codigo, 'ts': time.time(),
                                 'tipo': 'cambio_email', 'username': username}
    enviar_correo(nuevo, "Confirma tu nuevo correo de CallMus",
                  f"Hola {username},\n\n"
                  f"Tu código para confirmar este correo es: {codigo}\n\n"
                  f"Caduca en 15 minutos. Si no has pedido tú el cambio, ignora este correo.")
    if anterior:
        enviar_correo(anterior, "Se ha pedido cambiar el correo de tu cuenta de CallMus",
                      f"Hola {username},\n\n"
                      f"Alguien ha pedido cambiar el correo de tu cuenta a {_ocultar_email(nuevo)}.\n"
                      f"El cambio no será efectivo hasta que se confirme desde esa dirección.\n\n"
                      f"Si no has sido tú, cambia tu contraseña cuanto antes.")
    return _respuesta(True, 'ok_codigo_enviado', 'Te hemos enviado un código al correo nuevo.')


@app.route('/auth/cuenta/email/confirmar', methods=['POST'])
def auth_cuenta_email_confirmar():
    """Paso 2 del cambio de correo: verifica el código recibido en la dirección nueva."""
    username = session.get('username')
    if not username:
        return _respuesta(False, 'err_sin_sesion', 'Tienes que iniciar sesión.'), 401

    datos = request.json or {}
    nuevo = (datos.get('email') or '').strip()
    recibido = (datos.get('code') or '').strip()

    pendiente = codigos_pendientes.get(nuevo)
    if not pendiente or pendiente.get('tipo') != 'cambio_email' or pendiente.get('username') != username:
        return _respuesta(False, 'err_sin_codigo', 'No hay ningún cambio de correo pendiente.')
    if time.time() - pendiente['ts'] > CODIGO_VALIDEZ_SEG:
        codigos_pendientes.pop(nuevo, None)
        return _respuesta(False, 'err_codigo_caducado', 'El código ha caducado. Solicita uno nuevo.')
    if not secrets.compare_digest(recibido, pendiente['code']):
        return _respuesta(False, 'err_codigo_incorrecto', 'Código incorrecto.')

    exito, codigo = base_datos.cambiar_email(username, nuevo)
    if exito:
        codigos_pendientes.pop(nuevo, None)
        solicitudes_por_email.pop(nuevo, None)
        return _respuesta(True, codigo, 'Correo actualizado.', email=nuevo)
    return _respuesta(False, codigo, 'Ya existe una cuenta con ese correo.')


@app.route('/auth/cuenta/password', methods=['POST'])
def auth_cuenta_password():
    username = session.get('username')
    if not username:
        return _respuesta(False, 'err_sin_sesion', 'Tienes que iniciar sesión.'), 401

    datos = request.json or {}
    nueva = datos.get('password_nueva') or ''
    if len(nueva) < 6:
        return _respuesta(False, 'err_password_corta',
                          'La contraseña debe tener al menos 6 caracteres.')

    ok, cod_error, msg_error = _autorizar_cambio(username, datos)
    if not ok:
        return _respuesta(False, cod_error, msg_error)

    if base_datos.cambiar_password_usuario(username, nueva):
        return _respuesta(True, 'ok_password_cambiada', 'Contraseña actualizada.')
    return _respuesta(False, 'err_cuenta_no_encontrada', 'No se pudo actualizar la contraseña.')


@app.route('/auth/cuenta/eliminar', methods=['POST'])
def auth_cuenta_eliminar():
    """Borra la cuenta: se van los datos personales y el rastro social, y la fila
    queda anónima para no romper el historial de partidas de los rivales."""
    username = session.get('username')
    if not username:
        return _respuesta(False, 'err_sin_sesion', 'Tienes que iniciar sesión.'), 401

    datos = request.json or {}
    # Doble seguro: hay que teclear el propio nombre de usuario.
    if (datos.get('confirmacion') or '').strip().lower() != username.lower():
        return _respuesta(False, 'err_confirmacion_no_coincide',
                          'Escribe tu nombre de usuario exactamente para confirmar.')

    ok, cod_error, msg_error = _autorizar_cambio(username, datos)
    if not ok:
        return _respuesta(False, cod_error, msg_error)

    exito, codigo, _anonimo = base_datos.anonimizar_usuario(username)
    if exito:
        # La sesión se cierra aquí; el cliente recarga y su socket vuelve a
        # conectarse como invitado, soltando cualquier sala en la que estuviera.
        session.pop('username', None)
        return _respuesta(True, codigo, 'Cuenta eliminada.')
    return _respuesta(False, codigo, 'No se pudo eliminar la cuenta.')



# --- 1. GESTIÓN DE SALAS ---

def emitir_lista_publicas():
    """Recopila las salas públicas que están esperando y las manda a todos los conectados"""
    lista = []
    for cod, info in list(salas.items()):
        if info['estado'] == 'esperando' and info.get('publico', False):
            # Una sala en espera solo se anuncia si dentro hay alguien VIVO: si el
            # creador se cayó (o su sid murió sin pasar por `disconnect`), la sala
            # deja de listarse aquí mismo y el barredor acaba de enterrarla.
            # Antes se publicaba con `creador_sid: None` y quedaba como fantasma
            # en el vestíbulo para siempre (Roadmap #21, bug 1).
            vivos = [s for s in info.get('sids', []) if _sid_vivo(s)]
            if not vivos:
                continue
            # Leemos el nombre directamente de la sala
            nombre = info.get('creador_nombre', 'Desconocido')
            creador_sid = vivos[0]
            creador_username = info.get('username')

            lista.append({
                'codigo': cod,
                'creador': nombre,
                'creador_sid': creador_sid,
                'creador_username': creador_username,
                'al_mejor_de': info.get('al_mejor_de', 3)
            })

        # Partidas EN CURSO con hueco libre: solo se anuncian si quien se quedó
        # ha aceptado explícitamente esperar a un sustituto.
        elif info['estado'] == 'esperando_reemplazo' and info.get('esperando_votos'):
            motor = info.get('motor')
            humanos = [s for s in _sids_humanos_2p(info) if _sid_vivo(s)]
            if not humanos or not motor:
                continue
            vivo = humanos[0]                                   # el que espera
            hueco = _seat_motor_2p(motor, info['sids'].index(None))  # el asiento vacante
            quien_espera = jugadores.get(vivo, {})
            lista.append({
                'codigo': cod,
                'creador': quien_espera.get('nombre', 'Desconocido'),
                'creador_sid': vivo,
                'creador_username': quien_espera.get('username'),
                'al_mejor_de': info.get('al_mejor_de', 3),
                'en_curso': True,
                # Marcador visto desde el asiento que quedaría libre: [tú, él].
                'marcador': [motor.estado[hueco]['puntos'], motor.estado[vivo]['puntos']],
                'partidas': [motor.partidas_ganadas.get(hueco, 0), motor.partidas_ganadas.get(vivo, 0)],
                'expira_en': max(0, int(ESPERA_REEMPLAZO - (time.time() - info.get('esperando_desde', 0)))),
            })
    socketio.emit('actualizar_publicas', lista)

@socketio.on('pedir_publicas')
def handle_pedir_publicas():
    emitir_lista_publicas()


# ==========================================
# LA BARAJA DE CADA UNO EN LA MESA (Roadmap #5)
# ------------------------------------------
# El navegador anuncia con qué baraja juega: al conectar, al cargar el catálogo
# y cada vez que se cambia en «Mis barajas». Vale igual para el invitado, que no
# tiene dónde guardarla, y siempre se valida contra los temas que ese jugador
# puede usar de verdad.
# ==========================================

def _baraja_de_sid(sid):
    """La baraja con la que hay que pintar las cartas de ese asiento. Los bots
    juegan con la clásica: no eligen."""
    if not sid or sid.startswith('BOT_'):
        return dict(decks.CONFIG_DEFECTO)
    return decks.baraja_en_mesa(sid, jugadores.get(sid, {}).get('username'))


@socketio.on('mi_baraja')
def handle_mi_baraja(datos):
    sid = request.sid
    username = session.get('username')
    config = decks.recordar_baraja(sid, (datos or {}).get('config'),
                                   username, base_datos.es_admin(username))

    # A los demás se les manda un aviso suelto, no el estado entero de la mesa:
    # una difusión de estado reinicia el reloj del turno, y cambiar de baraja no
    # puede regalarle tiempo a nadie.
    info = jugadores.get(sid) or {}
    if info.get('modo4'):
        try:
            import server_mus4
            server_mus4.difundir_baraja_4(sid, config)
        except Exception as e:
            print(f"⚠️ Error difundiendo baraja 4p: {e}")
        return

    sala = salas.get(info.get('sala'))
    if not sala:
        return
    for otro in sala.get('sids', []):
        if otro and otro != sid and not otro.startswith('BOT_'):
            socketio.emit('baraja_rival', {'config': config}, room=otro)


# aqui iba el anteriorgestion de usuarios y sesiones


@socketio.on('crear_sala')
def handle_crear_sala(datos):
    sid = request.sid
    nombre = datos.get('nombre', 'Jugador 1')
    es_publico = datos.get('publico', False)
    al_mejor_de_valor = datos.get('al_mejor_de', 3)
    
    # Como ya está importado en la línea 1, lo usamos directamente
    real_username = session.get('username')

    codigo = generar_codigo()
    while codigo in salas:
        codigo = generar_codigo()
        
    # AQUÍ ESTABA EL FALLO: Ahora sí guardamos tu username en tus datos de conexión
    jugadores[sid] = {'nombre': nombre, 'sala': codigo, 'username': real_username}
    join_room(codigo)

    token = secrets.token_hex(16)   # identidad estable para reconectar (asiento 0)
    salas[codigo] = {'estado': 'esperando', 'sids': [sid], 'al_mejor_de': al_mejor_de_valor,
                     'publico': es_publico, 'username': real_username, 'creador_nombre': nombre,
                     'tokens': {0: token},
                     'creada_en': time.time(), 'ultima_actividad': time.time()}

    print(f"👉 {nombre} ha creado la sala {codigo} (Pública: {es_publico})")
    emit('sala_creada', {'codigo': codigo, 'token': token}, room=sid)
    emitir_lista_publicas()


@socketio.on('crear_partida_bot')
def handle_crear_partida_bot(datos):
    sid = request.sid
    nombre = datos.get('nombre', 'Humano')
    al_mejor_de_valor = datos.get('al_mejor_de', 3)
    real_username = session.get('username')

    codigo = generar_codigo()
    while codigo in salas:
        codigo = generar_codigo()
        
    # Creamos un SID falso para el bot
    bot_sid = 'BOT_' + codigo

    jugadores[sid] = {'nombre': nombre, 'sala': codigo, 'username': real_username}
    jugadores[bot_sid] = {'nombre': 'Bot IA', 'sala': codigo, 'username': 'Bot IA'}
    
    join_room(codigo) 
    
    # Creamos la sala directamente en estado 'jugando' e inyectamos la instancia del bot
    token = secrets.token_hex(16)   # identidad estable del humano (asiento 0)
    salas[codigo] = {
        'estado': 'jugando',
        'sids': [sid, bot_sid],
        'al_mejor_de': al_mejor_de_valor,
        'publico': False,
        'username': real_username,
        'tokens': {0: token},
        'creada_en': time.time(),
        'ultima_actividad': time.time(),
        'bot': SmartBot(bot_sid)
    }
    
    partida = PartidaMus(sid, bot_sid)
    partida.nombres_ia = {
        sid: real_username if real_username else nombre,
        bot_sid: 'Bot IA'
    }
    partida.al_mejor_de = al_mejor_de_valor
    # Log v2 (mus_log.py): el asiento 0 es quien crea la sala, el 1 el bot.
    partida.activar_log(
        seats=[{'s': 0, 'kind': 'human', 'code': real_username},
               {'s': 1, 'kind': 'bot', 'pers': getattr(salas[codigo]['bot'], 'personalidad', None)}],
        rules={'al_mejor_de': al_mejor_de_valor})
    partida.iniciar_ronda()
    salas[codigo]['motor'] = partida
    
    print(f"🤖 {nombre} ha creado la sala {codigo} contra la IA")
    emit('sala_creada', {'codigo': codigo, 'token': token}, room=sid)
    emit('iniciar_partida', {'mensaje': '¡La partida comienza!'}, room=codigo)
    enviar_estado_a_jugadores(codigo)




@socketio.on('unirse_sala')
def handle_unirse_sala(datos):
    sid = request.sid
    # Quitamos espacios accidentales al inicio o final
    nombre = datos.get('nombre', 'Jugador').strip()
    codigo = datos.get('codigo', '').upper()

    # --- Partida EN CURSO con hueco: el recién llegado entra de sustituto ---
    if codigo in salas and salas[codigo]['estado'] == 'esperando_reemplazo':
        sala = salas[codigo]
        mi_username = session.get('username')
        if mi_username:
            for s in sala['sids']:
                if s and jugadores.get(s, {}).get('username') == mi_username:
                    emit('error_sala', {'mensaje': 'Ya estás en esta partida con esta cuenta.'}, room=sid)
                    return
        if sid in sala['sids']:
            return   # anti-doble-clic
        if not _sentar_reemplazo_2p(codigo, sid, nombre, mi_username):
            emit('error_sala', {'mensaje': 'Esa partida ya no admite jugadores.'}, room=sid)
        return

    if codigo in salas and salas[codigo]['estado'] == 'esperando':
        mi_username = session.get('username')
        creador_username = salas[codigo].get('username')
        creador_nombre = salas[codigo].get('creador_nombre', '').strip()
        sids = salas[codigo]['sids']
    
        if mi_username and creador_username and mi_username == creador_username:
            emit('error_sala', {'mensaje': 'No puedes jugar contra ti mismo con la misma cuenta.'}, room=sid)
            return
        
        # --- 1. BLOQUEO ANTI-DOBLE CLIC (Lag) ---
        if sid in sids:
            emit('sala_creada', {'codigo': codigo}, room=sid)
            return # Lo ignoramos silenciosamente para no dar errores falsos
            
        # --- 2. IDENTIFICAMOS AL CREADOR (A prueba de fallos de sesión) ---
        es_creador = False
        if mi_username and creador_username and mi_username == creador_username:
            es_creador = True
        elif nombre.lower() == creador_nombre.lower():
            es_creador = True

        asiento_asignado = -1

        # --- 3. ASIENTOS INTELIGENTES ---
        # Normalizamos la lista a 2 huecos ANTES de elegir: así la asignación es
        # siempre `sids[i] = sid` sobre una lista de tamaño fijo, nunca un append.
        # Dos `unirse_sala` que se solapasen ya no pueden dejar tres asientos
        # (Roadmap #21, bug 4); el segundo se encuentra el hueco ocupado y rebota.
        while len(sids) < 2:
            sids.append(None)
        del sids[2:]

        if es_creador:
            # El creador legítimo recupera su trono (Asiento 0)
            if sids[0] is None:
                asiento_asignado = 0
            elif sids[1] is None:
                asiento_asignado = 1
        else:
            # Invitado buscando silla
            if sids[1] is None:
                asiento_asignado = 1
            elif sids[0] is None:
                # LA MAGIA: Si la sesión falló, pero el asiento del creador está libre,
                # sentamos a esta persona ahí para poder arrancar el juego de una vez.
                asiento_asignado = 0
                print(f"⚠️ {nombre} ocupó el Asiento 0 (vacío) por precaución en {codigo}.")

        # Revalidación justa antes de sentar (por si un greenlet se coló en medio).
        if asiento_asignado == -1 or sids[asiento_asignado] is not None:
            emit('error_sala', {'mensaje': 'La sala ya está llena.'}, room=sid)
            return
        sids[asiento_asignado] = sid
            
        # Añadimos los datos al jugador
        jugadores[sid] = {'nombre': nombre, 'sala': codigo, 'username': mi_username}
        join_room(codigo)
        _tocar_sala(codigo)

        # Identidad estable para reconectar (por si se cae en plena partida).
        token = secrets.token_hex(16)
        salas[codigo].setdefault('tokens', {})[asiento_asignado] = token
        emit('sala_creada', {'codigo': codigo, 'token': token}, room=sid)

        # --- 4. COMPROBAMOS SI ARRANCAMOS LA PARTIDA ---
        if len(sids) == 2 and sids[0] is not None and sids[1] is not None:
            salas[codigo]['estado'] = 'jugando'
            j1_sid, j2_sid = sids[0], sids[1]
            
            partida = PartidaMus(j1_sid, j2_sid)
            
            # Garantizamos que los nombres sean los correctos
            partida.nombres_ia = {
                j1_sid: jugadores.get(j1_sid, {}).get('username') or jugadores.get(j1_sid, {}).get('nombre', 'J1'),
                j2_sid: jugadores.get(j2_sid, {}).get('username') or jugadores.get(j2_sid, {}).get('nombre', 'J2')
            }
            partida.al_mejor_de = salas[codigo].get('al_mejor_de', 3)
            # Log v2 (mus_log.py): asientos estables 0 = j1, 1 = j2.
            partida.activar_log(
                seats=[{'s': i, 'kind': 'human',
                        'code': jugadores.get(s_sid, {}).get('username')}
                       for i, s_sid in enumerate((j1_sid, j2_sid))],
                rules={'al_mejor_de': salas[codigo].get('al_mejor_de', 3)})
            partida.iniciar_ronda()
            salas[codigo]['motor'] = partida
            
            emit('iniciar_partida', {'mensaje': '¡La partida comienza!'}, room=codigo)
            enviar_estado_a_jugadores(codigo)
            emitir_lista_publicas()
        else:
            # sala_creada (con token) ya se emitió arriba al asignar el asiento.
            emitir_lista_publicas()
            
    else:
        emit('error_sala', {'mensaje': 'El código no existe o la sala está en juego.'}, room=sid)

# --- 2. ACCIONES DE JUEGO AISLADAS ---

@socketio.on('accion_juego')
def handle_accion_juego(datos):
    sid_jugador = request.sid
    if sid_jugador not in jugadores: return
    codigo = jugadores[sid_jugador]['sala']

    procesar_accion_interna(sid_jugador, codigo, datos)

def procesar_accion_interna(sid_jugador, codigo, datos):
    if codigo not in salas or salas[codigo]['estado'] != 'jugando': return

    _tocar_sala(codigo)   # sello de actividad que usa el barredor (Roadmap #21, bug 6)

    # Extraemos el motor específico de la sala donde está este jugador
    partida_actual = salas[codigo]['motor']
    accion = datos.get('accion')
    
    if accion == 'pedrete':
        if partida_actual.procesar_pedrete(sid_jugador):
            enviar_estado_a_jugadores(codigo)
        return


    if sid_jugador == partida_actual.turno_de:
        if accion == 'repartir':
            partida_actual.repartir_inicial()
            enviar_estado_a_jugadores(codigo)
        elif accion == 'mus':
            partida_actual.cantar_mus(sid_jugador, True)
            enviar_estado_a_jugadores(codigo)
        elif accion == 'no_mus':
            partida_actual.cantar_mus(sid_jugador, False)
            enviar_estado_a_jugadores(codigo)
        elif accion in ['pasar', 'envidar', 'subir', 'ver', 'ordago', 'nover']:
            cantidad = datos.get('cantidad', 0)
            partida_actual.accion_apuesta(sid_jugador, accion, cantidad)
            enviar_estado_a_jugadores(codigo)

    if accion == 'descartar' and partida_actual.fase == 'descarte':
        if not partida_actual.estado[sid_jugador]['descartes_listos']:
            indices_a_tirar = datos.get('indices', [])
            partida_actual.procesar_descarte(sid_jugador, indices_a_tirar)
            enviar_estado_a_jugadores(codigo)

    if accion == 'continuar_transicion':
        partida_actual.mensaje_transicion = None
        partida_actual.preparar_subfase() 
        enviar_estado_a_jugadores(codigo)
        
    elif accion == 'listo_siguiente_ronda':
        if getattr(partida_actual, 'match_finalizado', False):
            return 
            
        if sid_jugador not in partida_actual.jugadores_listos:
            partida_actual.jugadores_listos.append(sid_jugador)
            
        if len(partida_actual.jugadores_listos) == 2:
            if partida_actual.estado[partida_actual.j1]['puntos'] >= 40 or partida_actual.estado[partida_actual.j2]['puntos'] >= 40:
                partida_actual.reiniciar_partida()
                partida_actual.db_registrada = False
            else:
                partida_actual.cambiar_roles() 
                partida_actual.iniciar_ronda() 
                partida_actual.fase = 'espera_reparto'
                partida_actual.turno_de = partida_actual.id_postre
            
            partida_actual.jugadores_listos = []
            partida_actual.recuento_calculado = False
            enviar_estado_a_jugadores(codigo)

# --- 3. REPARTO CIEGO POR SALA ---
def enviar_estado_a_jugadores(codigo_sala):
    puede_pedrete_ahora = False
    global show_global_log
    sala = salas.get(codigo_sala)
    if not sala: return
    partida_actual = sala.get('motor')
    if not partida_actual: return

    for sid in list(sala['sids']):
        if sid is None or sid.startswith('BOT_'): continue   # asiento en pausa / bot
        # El asiento puede tener un sid que el motor ya no conoce (remap a medias
        # tras una reconexión). Antes eso reventaba con KeyError y dejaba la sala
        # a medio actualizar = partida "congelada" (Roadmap #21, bug 5).
        estado_del_jugador = partida_actual.estado.get(sid)
        if estado_del_jugador is None:
            print(f"⚠️ [SALA {codigo_sala}] sid {sid} sin estado en el motor: se omite.")
            continue
        es_mi_turno = (sid == partida_actual.turno_de)
        soy_mano = (sid == partida_actual.id_mano)
        rival_sid = partida_actual.id_postre if sid == partida_actual.id_mano else partida_actual.id_mano
        
        # Nombre del jugador en turno, resistente a que su entrada en `jugadores`
        # ya no exista (p.ej. reconexión con el rival aún caído): usamos nombres_ia.
        def _nombre_turno():
            tsid = partida_actual.turno_de
            if not tsid:
                return "..."
            return (partida_actual.nombres_ia.get(tsid)
                    or jugadores.get(tsid, {}).get('nombre') or "...")

        if partida_actual.fase == 'descarte':
            mensaje = {'code': 'fase_descarte'}
        elif partida_actual.fase == 'apuestas':
            if partida_actual.indice_fase < len(partida_actual.fases_apuesta):
                n_fase = partida_actual.fases_apuesta[partida_actual.indice_fase]
                mensaje = {'code': 'fase_apuestas', 'fase': n_fase, 'jugador': _nombre_turno()}
            else:
                mensaje = {'code': 'fase_recuento'}
        else:
            mensaje = {'code': 'fase_general', 'fase': partida_actual.fase, 'jugador': _nombre_turno()}
        
        info_apuestas = {
            'fase_actual': '',
            'subida': partida_actual.subida_pendiente,
            'botes': partida_actual.botes,
            'dejes': {},
            'apuesta_vista': partida_actual.apuesta_vista,
            'soy_quien_sube': (partida_actual.quien_sube == sid),
            'juego_es_punto': getattr(partida_actual, 'juego_es_punto', False)
        }

        
        if hasattr(partida_actual, 'dejes_fase'):
            for f, d in partida_actual.dejes_fase.items():
                if d is not None:
                    info_apuestas['dejes'][f] = {
                        'gano_yo': (d['ganador'] == sid),
                        'valor': d['valor']
                    }

                

        if partida_actual.fase == 'apuestas' and partida_actual.indice_fase < len(partida_actual.fases_apuesta):
            info_apuestas['fase_actual'] = partida_actual.fases_apuesta[partida_actual.indice_fase]
        
        datos_recuento = None
        # Mismo blindaje para el rival: si su asiento está en pausa/remapeado, lo
        # tratamos como "sin datos" en vez de romper el reparto de estado.
        estado_rival = partida_actual.estado.get(rival_sid) or {}
        cartas_rival = estado_rival.get('cartas', [])

        puede_pedrete_ahora = False
        if partida_actual.fase == 'mus':
            vals = sorted([c['valor'] for c in estado_del_jugador['cartas']])
            if vals == [4, 5, 6, 7]:
                puede_pedrete_ahora = True

        if partida_actual.fase == 'recuento':
            pasos_crudos = partida_actual.calcular_recuento()

            if getattr(partida_actual, 'partida_sumada', False) and not getattr(partida_actual, 'db_registrada', False):
                partida_actual.db_registrada = True
                # (`base_datos` ya está importado arriba del todo; volver a
                #  importarlo AQUÍ lo convertía en local de toda la función y
                #  rompía cualquier otro uso del módulo dentro de ella.)

                if partida_actual.estado[partida_actual.j1]['puntos'] >= 40:
                    ganador_sid, perdedor_sid = partida_actual.j1, partida_actual.j2
                else:
                    ganador_sid, perdedor_sid = partida_actual.j2, partida_actual.j1
                    
                u_ganador = jugadores.get(ganador_sid, {}).get('username')
                u_perdedor = jugadores.get(perdedor_sid, {}).get('username')
                if u_ganador or u_perdedor:
                    base_datos.registrar_partida_completa(u_ganador, u_perdedor)

            datos_recuento = []
            for paso in pasos_crudos:
                paso_limpio = {
                    'gano_yo': (paso['ganador_sid'] == sid),
                    'datos': paso['datos']
                }
                datos_recuento.append(paso_limpio)
                
        if show_global_log:
            _quien = jugadores.get(sid, {}).get('nombre', sid)
            print(f"📤 [SALA {codigo_sala}] Estado a {_quien}: Fase {partida_actual.fase}")

        # === EL ARREGLO ESTÁ AQUÍ ===
        payload = {
            'para_sid': sid,  # Añadimos a quién va dirigido
            'reconexion_token': sala.get('tokens', {}).get(sala['sids'].index(sid)),
            'nombre_rival': partida_actual.nombres_ia.get(rival_sid, jugadores.get(rival_sid, {}).get('nombre', 'Rival')),
            # Sus cartas se pintan con SU baraja, tanto el dorso como las caras
            # que se enseñan en el recuento (Roadmap #5).
            'baraja_rival': _baraja_de_sid(rival_sid),
            'fase': partida_actual.fase,
            'puede_pedrete': puede_pedrete_ahora,
            'es_mi_turno': es_mi_turno,
            'soy_mano': soy_mano,
            'descartes_listos': estado_del_jugador.get('descartes_listos', False),
            'descartes_rival': estado_rival.get('descartes_hechos', 0),
            'apuestas': info_apuestas,
            'mensaje': mensaje,
            'mis_cartas': estado_del_jugador['cartas'],
            'mis_puntos': estado_del_jugador['puntos'],
            'puntos_rival': estado_rival.get('puntos', 0),
            'mensaje_transicion': partida_actual.mensaje_transicion,
            'recuento': datos_recuento,
            'cartas_rival': cartas_rival,
            'rival_puntos_finales': estado_rival.get('puntos', 0),
            'mis_partidas': partida_actual.partidas_ganadas.get(sid, 0),
            'partidas_rival': partida_actual.partidas_ganadas.get(rival_sid, 0),
            'al_mejor_de': partida_actual.al_mejor_de,
            'match_finalizado': partida_actual.match_finalizado
        }
        
        # Disparamos el mensaje a la sala entera, porque sabemos que eso sí llega siempre
        socketio.emit('actualizar_mesa', payload, room=codigo_sala) 

    # --- LÓGICA DEL BOT ---
    if sala['estado'] == 'jugando' and 'bot' in sala:
        bot_instance = sala['bot']
        accion_datos = bot_instance.obtener_accion(partida_actual)
        
        if accion_datos:
            bot_sid = bot_instance.sid
            
            # Retardo "pensando" del bot: editable en caliente desde el panel de
            # administración (variable `bot_delay`, Roadmap #13/#15).
            retardo = base_datos.config_get_float('bot_delay', 1.5)
            retardo = min(max(retardo, 0.0), 10.0)

            def bot_action_task():
                socketio.sleep(retardo)
                # Una excepción aquí mataba el greenlet dejando la mesa a medias
                # (partida "congelada" = fantasma percibido, Roadmap #21 bug 5).
                try:
                    if codigo_sala in salas and salas[codigo_sala]['estado'] == 'jugando':
                        acc = bot_instance.obtener_accion(salas[codigo_sala]['motor'])
                        if acc:
                            print(f"🤖 Bot ejecuta en sala {codigo_sala}: {acc}")
                            procesar_accion_interna(bot_sid, codigo_sala, acc)
                except Exception as e:
                    print(f"❌ Error en el turno del bot ({codigo_sala}): {e}")

            socketio.start_background_task(bot_action_task)

@socketio.on('abandonar_sala_limpiamente')
def handle_abandonar_limpiamente():
    """Salida desde el vestíbulo (botón «Volver al menú»).

    Antes solo borraba la sala: el jugador seguía suscrito a la room de Socket.IO y
    su entrada en `jugadores` podía quedar apuntando a una sala ya inexistente
    (Roadmap #21, bug 3). Ahora se sale de la room, se limpia el registro y, si
    quedaba alguien esperando dentro, se le avisa en vez de dejarlo colgado."""
    _salir_de_sala_2p(request.sid)


def _salir_de_sala_2p(sid):
    """Saca a `sid` de la sala 2p en la que esté, dejándolo todo consistente.

    Lo usan la salida por botón y `social.invitar_amigo` (que antes creaba una sala
    nueva encima, dejando la anterior colgada como fantasma)."""
    if sid not in jugadores:
        return
    codigo = jugadores[sid]['sala']
    sala = salas.get(codigo)

    if not sala:
        # La sala ya no existe: basta con limpiar el rastro del jugador.
        jugadores.pop(sid, None)
        try:
            leave_room(codigo)
        except Exception:
            pass
        return

    try:
        leave_room(codigo)
    except Exception:
        pass

    nombre = jugadores[sid].get('nombre', 'Jugador')
    motor = sala.get('motor')
    seat = sala['sids'].index(sid) if sid in sala.get('sids', []) else None

    # Si por lo que sea se llega aquí con una partida viva (el vestíbulo no debería,
    # pero un cliente antiguo o un doble evento sí), no matamos la sala en silencio:
    # se libera el asiento como en `abandonar_partida` y el rival decide.
    if (seat is not None and sala['estado'] != 'esperando' and motor
            and 'bot' not in sala and not getattr(motor, 'match_finalizado', False)):
        jugadores.pop(sid, None)
        _abrir_hueco_2p(codigo, seat, nombre, motivo='abandono')
        return

    if seat is not None:
        sala['sids'][seat] = None
        sala.get('tokens', {}).pop(seat, None)
    jugadores.pop(sid, None)

    # ¿Queda alguien humano dentro? Si sí, la sala sobrevive (y se reanuncia);
    # si no, muere del todo, incluido el sid falso del bot.
    if _sids_humanos_2p(sala):
        emitir_lista_publicas()
    else:
        # Destruimos la sala para que 'disconnect' no avise al rival.
        # _destruir_sala_2p limpia además el sid falso del bot.
        _destruir_sala_2p(codigo)


@socketio.on('abandonar_partida')
def handle_abandonar_partida():
    """Salida voluntaria desde la mesa (botón «Salir»), ya confirmada en el cliente.

    - vs IA: la sala muere con el jugador (no hay a quién avisar).
    - 1v1 online: se libera el asiento y al rival se le pregunta si espera o se va.
    """
    sid = request.sid
    if sid not in jugadores:
        return
    codigo = jugadores[sid]['sala']
    nombre = jugadores[sid].get('nombre', 'Jugador')
    sala = salas.get(codigo)
    if not sala:
        jugadores.pop(sid, None)
        return

    leave_room(codigo)

    # Sala aún en el vestíbulo, partida contra la IA o match ya terminado:
    # no hay partida viva que ofrecer a nadie.
    motor = sala.get('motor')
    if (sala['estado'] == 'esperando' or 'bot' in sala
            or not motor or getattr(motor, 'match_finalizado', False)):
        _destruir_sala_2p(codigo, motivo='abandono' if sala['estado'] != 'esperando' else None)
        return

    jugadores.pop(sid, None)
    seat = sala['sids'].index(sid) if sid in sala['sids'] else None
    if seat is None:
        return
    _abrir_hueco_2p(codigo, seat, nombre, motivo='abandono')


@socketio.on('esperar_reemplazo')
def handle_esperar_reemplazo():
    """El jugador que se queda acepta esperar: la partida se anuncia como en curso."""
    sid = request.sid
    if sid not in jugadores:
        return
    sala = salas.get(jugadores[sid]['sala'])
    if not sala or sala.get('estado') != 'esperando_reemplazo':
        return
    if sid in sala['sids']:
        sala.setdefault('esperando_votos', set()).add(sala['sids'].index(sid))
    restante = max(0, int(ESPERA_REEMPLAZO - (time.time() - sala.get('esperando_desde', time.time()))))
    emit('esperando_reemplazo', {'segundos': restante}, room=sid)
    emitir_lista_publicas()


def _programar_fin_gracia_2p(codigo):
    """Agotada la gracia de reconexión, el asiento se declara vacante: quien sigue
    dentro decide si espera un sustituto o se va (no matamos la sala sin más)."""
    def tarea():
        socketio.sleep(GRACIA_RECONEXION_2P)
        sala = salas.get(codigo)
        if not sala or sala.get('estado') != 'pausada':
            return
        print(f"🧹 Gracia agotada en {codigo}: se abre el asiento a un sustituto.")
        seat = next((i for i, s in enumerate(sala['sids']) if s is None), None)
        motor = sala.get('motor')
        if seat is None or 'bot' in sala or not motor or getattr(motor, 'match_finalizado', False):
            _destruir_sala_2p(codigo, motivo='timeout')
            return
        nombre = motor.nombres_ia.get(sala.get('ultimo_sid', {}).get(seat), 'Tu rival')
        _abrir_hueco_2p(codigo, seat, nombre, motivo='timeout')
    socketio.start_background_task(tarea)


@socketio.on('reanudar_partida')
def handle_reanudar_partida(datos):
    """Reconexión 2p / vs-IA: reengancha por IDENTIDAD (token o username) el asiento,
    reasigna el sid dentro del motor y reanuda. Funciona aunque el asiento siga
    ocupado por un sid muerto (refresco que se adelanta a la detección de la caída)."""
    sid = request.sid
    codigo = (datos.get('codigo') or '').upper()
    token = datos.get('token')
    username = session.get('username')

    sala = salas.get(codigo)
    if not sala or sala.get('estado') not in ('jugando', 'pausada', 'esperando_reemplazo') or 'motor' not in sala:
        emit('error_sala', {'mensaje': 'No hay ninguna partida que reanudar.'}, room=sid)
        return

    sids = sala['sids']
    tokens = sala.get('tokens', {})

    # Identidad → asiento, esté vacío u ocupado por un sid viejo.
    seat = None
    for s in range(len(sids)):
        if token and tokens.get(s) == token:
            seat = s
            break
    if seat is None and username and sala.get('username') == username:
        seat = 0   # respaldo para el creador logueado que perdió el token del navegador
    if seat is None:
        emit('error_sala', {'mensaje': 'No se encontró tu asiento para reanudar.'}, room=sid)
        return

    # sid con el que el motor sigue indexado: el que ocupa el asiento, o —si el
    # asiento ya se vació al detectar la caída— el que guardamos en 'ultimo_sid'.
    old = sids[seat] if sids[seat] is not None else sala.get('ultimo_sid', {}).get(seat)
    sids[seat] = sid
    if old and old != sid:
        _remap_sid_2p(sala['motor'], old, sid)
        jugadores.pop(old, None)
    sala.get('ultimo_sid', {}).pop(seat, None)

    nombre = sala['motor'].nombres_ia.get(sid) or jugadores.get(sid, {}).get('nombre', 'Jugador')
    jugadores[sid] = {'nombre': nombre, 'sala': codigo, 'username': username}
    join_room(codigo)
    sala['ultima_actividad'] = time.time()

    # Solo reanudamos de verdad si TODOS los asientos están ocupados; si el rival
    # sigue caído, seguimos en pausa (el reconectado ve el tablero y el aviso).
    estado_previo = sala.get('estado')
    if all(s is not None for s in sids):
        sala['estado'] = 'jugando'
        sala.pop('pausada_desde', None)
        # Volvió justo cuando ya se buscaba sustituto: se cancela la búsqueda.
        sala.pop('esperando_desde', None)
        sala.pop('esperando_votos', None)
        if estado_previo == 'esperando_reemplazo':
            socketio.emit('reemplazo_encontrado', {'nombre': nombre}, room=codigo)
            emitir_lista_publicas()

    emit('reanudado', {'codigo': codigo}, room=sid)
    if sala.get('estado') == 'pausada':
        emit('oponente_desconectado', {'gracia': GRACIA_RECONEXION_2P}, room=sid)
    elif sala.get('estado') == 'esperando_reemplazo':
        restante = max(0, int(ESPERA_REEMPLAZO - (time.time() - sala.get('esperando_desde', time.time()))))
        emit('esperando_reemplazo', {'segundos': restante}, room=sid)
    else:
        socketio.emit('oponente_reconectado', {}, room=codigo)
    enviar_estado_a_jugadores(codigo)


@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    # Presencia social: actualizar amigos conectados antes de la limpieza del juego.
    try:
        social.presencia_disconnect()
    except Exception as e:
        print(f"⚠️ Error en presencia_disconnect: {e}")

    # Mus 4 jugadores: limpieza/pausa de sus salas (solo un handler por evento).
    try:
        import server_mus4
        server_mus4.disconnect_4()
    except Exception as e:
        print(f"⚠️ Error en disconnect_4: {e}")

    # La baraja anunciada va con el socket: al reconectar se vuelve a mandar.
    decks.olvidar_baraja(sid)

    if sid in jugadores:
        codigo = jugadores[sid]['sala']
        nombre = jugadores[sid]['nombre']
        del jugadores[sid]  # Borramos los datos temporales del jugador
        
        if codigo in salas:
            if salas[codigo]['estado'] == 'esperando':
                # En lugar de borrar su espacio, dejamos un "hueco vacío" (None)
                if sid in salas[codigo]['sids']:
                    idx = salas[codigo]['sids'].index(sid)
                    salas[codigo]['sids'][idx] = None
                
                print(f"⚠️ {nombre} minimizó/desconectó. La sala {codigo} aguantará 2 minutos.")
                
                def limpiar_sala_huerfana():
                    socketio.sleep(120)
                    if codigo in salas and salas[codigo]['estado'] == 'esperando':
                        # Sala muerta si no queda NINGÚN asiento con una conexión viva.
                        # (Antes solo miraba `is None`: un asiento con un sid ya muerto
                        # la dejaba inmortal — Roadmap #21, bug 1.)
                        if not any(_sid_vivo(s) for s in salas[codigo]['sids']):
                            print(f"🧹 Limpiando sala abandonada: {codigo}")
                            _destruir_sala_2p(codigo)

                socketio.start_background_task(limpiar_sala_huerfana)
                emitir_lista_publicas()

            elif salas[codigo]['estado'] == 'esperando_reemplazo':
                # Ya buscábamos sustituto y ahora se cae quien esperaba. Vaciamos su
                # asiento pero conservamos token y voto: puede ser un simple refresco
                # y `reanudar_partida` lo devuelve a su sitio. Mientras no haya nadie
                # vivo la sala deja de anunciarse (emitir_lista_publicas la salta) y,
                # si no vuelve, la barre el temporizador de la ventana de espera.
                sala = salas[codigo]
                if sid in sala.get('sids', []):
                    seat = sala['sids'].index(sid)
                    sala.setdefault('ultimo_sid', {})[seat] = sid
                    sala['sids'][seat] = None
                print(f"⏸️ {nombre} se cayó mientras {codigo} esperaba sustituto.")
                emitir_lista_publicas()

            else:
                # Estaban jugando (o ya en pausa): en vez de destruir la sala, la
                # PAUSAMOS con una ventana de gracia para permitir reconexión. El
                # motor se congela solo (procesar_accion_interna y el bot exigen
                # estado=='jugando'). Si nadie vuelve a tiempo, se termina.
                sala = salas[codigo]
                if sid in sala.get('sids', []):
                    seat_caido = sala['sids'].index(sid)
                    # Recordamos el sid con el que el motor sigue indexado en ese
                    # asiento (al vaciarlo perderíamos la referencia para el remap).
                    sala.setdefault('ultimo_sid', {})[seat_caido] = sid
                    sala['sids'][seat_caido] = None
                sala['estado'] = 'pausada'
                sala['pausada_desde'] = time.time()
                print(f"⏸️ {nombre} se cayó en la sala {codigo}. Pausada {GRACIA_RECONEXION_2P}s para reconectar.")
                socketio.emit('oponente_desconectado', {'gracia': GRACIA_RECONEXION_2P}, room=codigo)
                _programar_fin_gracia_2p(codigo)
                emitir_lista_publicas()


# ==========================================
# BARREDOR DE SALAS FANTASMA + OBSERVABILIDAD (Roadmap #21, bug 6)
# ==========================================
def _codigos_vivos_4p():
    """Códigos que pertenecen al registro de 4 jugadores (otro diccionario, mismo
    `jugadores`): no deben contarse como huérfanos al barrer."""
    try:
        import server_mus4
        return set(server_mus4.salas4.keys())
    except Exception:
        return set()


def _barrer_huerfanos():
    """Entradas de `jugadores` que apuntan a salas que ya no existen en ningún
    registro. Devuelve cuántas se han eliminado."""
    codigos_4p = _codigos_vivos_4p()
    muertos = [s for s, info in jugadores.items()
               if info.get('sala') not in salas and info.get('sala') not in codigos_4p]
    for s in muertos:
        jugadores.pop(s, None)
    return len(muertos)


def _pasada_barredor():
    """Una pasada del barredor (extraída del bucle para poder probarla)."""
    ahora = time.time()
    for codigo, sala in list(salas.items()):
        estado = sala.get('estado')
        edad = ahora - sala.get('ultima_actividad', sala.get('creada_en', ahora))

        if estado == 'esperando':
            # Sin nadie vivo dentro, o demasiado tiempo sin arrancar. La marca
            # `vacia_desde` respeta los 2 min de gracia por si el creador solo
            # está refrescando (`unirse_sala` lo vuelve a sentar).
            if not any(_sid_vivo(s) for s in sala.get('sids', [])):
                vacia_desde = sala.setdefault('vacia_desde', ahora)
                if ahora - vacia_desde > 120:
                    print(f"🧹 Barredor: sala en espera sin nadie vivo {codigo}.")
                    _destruir_sala_2p(codigo)
                continue
            sala.pop('vacia_desde', None)
            if edad > VIDA_MAX_ESPERANDO:
                print(f"🧹 Barredor: sala en espera caducada {codigo}.")
                _destruir_sala_2p(codigo)

        elif estado == 'jugando' and edad > VIDA_MAX_JUGANDO:
            print(f"🧹 Barredor: partida inactiva {codigo}.")
            _destruir_sala_2p(codigo, motivo='idle')

        elif estado == 'pausada' and (ahora - sala.get('pausada_desde', ahora)) > GRACIA_RECONEXION_2P * 2:
            print(f"🧹 Barredor: pausa vencida en {codigo}.")
            _destruir_sala_2p(codigo, motivo='timeout')

        elif estado == 'esperando_reemplazo' and (ahora - sala.get('esperando_desde', ahora)) > ESPERA_REEMPLAZO * 2:
            print(f"🧹 Barredor: espera de sustituto vencida en {codigo}.")
            _destruir_sala_2p(codigo, motivo='sin_reemplazo')

    huerfanos = _barrer_huerfanos()
    if huerfanos:
        print(f"🧹 Barredor: {huerfanos} entradas huérfanas de `jugadores` eliminadas.")


def _barredor_2p():
    """Red de seguridad periódica: mata lo que los temporizadores puntuales hayan
    dejado atrás. Espeja al `_barredor` de server_mus4."""
    while True:
        socketio.sleep(INTERVALO_BARRIDO)
        try:
            _pasada_barredor()
        except Exception as e:
            print(f"❌ Error en el barredor de salas: {e}")


# Endpoint de diagnóstico. Sin `DEBUG_TOKEN` en el entorno no existe (404), para no
# exponer el estado interno del servidor por accidente. Cuando llegue el panel de
# administración (#13), esta vista es la fuente de datos de "salas activas".
DEBUG_TOKEN = os.environ.get('DEBUG_TOKEN')


@app.route('/api/debug/salas', methods=['GET'])
def api_debug_salas():
    if not DEBUG_TOKEN or request.args.get('token') != DEBUG_TOKEN:
        return jsonify({'error': 'not found'}), 404

    ahora = time.time()
    codigos_4p = _codigos_vivos_4p()
    detalle = []
    for codigo, sala in list(salas.items()):
        motor = sala.get('motor')
        detalle.append({
            'codigo': codigo,
            'estado': sala.get('estado'),
            'publico': sala.get('publico', False),
            'vs_bot': 'bot' in sala,
            'edad_s': int(ahora - sala.get('creada_en', ahora)),
            'inactiva_s': int(ahora - sala.get('ultima_actividad', sala.get('creada_en', ahora))),
            'asientos': [{'sid': s, 'vivo': _sid_vivo(s),
                          'nombre': jugadores.get(s, {}).get('nombre')} for s in sala.get('sids', [])],
            'ronda': getattr(motor, 'ronda_n', None) if motor else None,
            'fase': getattr(motor, 'fase', None) if motor else None,
        })

    huerfanos = [s for s, info in jugadores.items()
                 if info.get('sala') not in salas and info.get('sala') not in codigos_4p]
    return jsonify({
        'salas_2p': len(salas),
        'salas_4p': len(codigos_4p),
        'jugadores': len(jugadores),
        'huerfanos': len(huerfanos),
        'detalle': detalle,
    })


# ==========================================
# CAPA SOCIAL (Roadmap #3): amigos, mensajería, grupos.
# Se engancha aquí, ya definidos socketio, salas, jugadores y helpers.
# ==========================================
social.init_social(app, socketio, {
    'salas': salas,
    'jugadores': jugadores,
    'generar_codigo': generar_codigo,
    'emitir_lista_publicas': emitir_lista_publicas,
    'salir_de_sala': _salir_de_sala_2p,
})

# ==========================================
# MUS 4 JUGADORES (Roadmap #6): registra sus handlers sobre ESTA instancia de
# socketio (patrón init como social.py). No usar `from server import socketio`
# dentro del módulo: server.py corre como __main__ y se re-importaría en otra
# instancia distinta, dejando los handlers sin efecto.
# ==========================================
import server_mus4  # noqa: E402
server_mus4.init_mus4(socketio, jugadores, salas)

# ==========================================
# PANEL DE ADMINISTRACIÓN (Roadmap #13): mismo proceso, mismo puerto y misma
# sesión que el juego — no hay nada que desplegar aparte, basta con abrir /admin
# desde una cuenta con el bit de administrador (ADMIN_USERNAME crea el primero).
# Va después de server_mus4 porque el panel lista también las salas de 4.
# ==========================================
import admin  # noqa: E402
admin.init_admin(app, socketio, {
    'salas': salas,
    'salas4': server_mus4.salas4,
    'jugadores': jugadores,
    'usuarios_conectados': social.usuarios_conectados,
    'destruir_sala': _destruir_sala_2p,
    'destruir_sala4': server_mus4._destruir_sala,
    'salir_de_sala': _salir_de_sala_2p,
    'emitir_lista_publicas': emitir_lista_publicas,
    'notificar': social.notificar,
    # Para el "enviar código de contraseña" del panel: reutiliza el mismo circuito
    # de códigos temporales que la recuperación normal, sin duplicarlo.
    'enviar_correo': enviar_correo,
    'generar_codigo_verificacion': generar_codigo_verificacion,
    'codigos_pendientes': codigos_pendientes,
})

# El barredor de salas 2p arranca aquí (después de que exista el registro 4p, que
# consulta para no dar por huérfanas sus entradas en `jugadores`).
socketio.start_background_task(_barredor_2p)
print("🧹 Barredor de salas 2p activo (cada %ds)." % INTERVALO_BARRIDO)


if __name__ == '__main__':
    # PORT permite levantar una segunda instancia (pruebas) sin tocar la de siempre.
    puerto = int(os.environ.get('PORT', '5001'))
    print(f"🚀 Servidor de Mus iniciado en http://localhost:{puerto}")
    socketio.run(app, host='0.0.0.0', port=puerto, debug=True)
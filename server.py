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
socketio = SocketIO(app, cors_allowed_origins="*")

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
    return response

# --- NUEVA ARQUITECTURA MULTIJUGADOR ---
# jugadores = { 'sid': {'nombre': 'Juan', 'sala': 'A1B2'} }
jugadores = {}  
# salas = { 'A1B2': {'estado': 'esperando', 'sids': [sid1, sid2], 'motor': PartidaMus} }
salas = {}      

show_global_log = False 

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
    if not google_id:
        return redirect('/?auth_error=google')

    username = base_datos.registrar_o_loguear_google(google_id, email, nombre)
    session.permanent = True
    session['username'] = username
    return redirect('/')


@app.route('/auth/sesion', methods=['GET'])
def auth_sesion():
    if 'username' in session:
        user = session['username']
        usuario_data = base_datos.obtener_usuario(user)
        if usuario_data:
            return jsonify({'exito': True, 'usuario': usuario_data})
    return jsonify({'exito': False})

@app.route('/auth/logout', methods=['POST'])
def auth_logout():
    session.pop('username', None)
    return jsonify({'exito': True})



# --- 1. GESTIÓN DE SALAS ---

def emitir_lista_publicas():
    """Recopila las salas públicas que están esperando y las manda a todos los conectados"""
    lista = []
    for cod, info in salas.items():
        if info['estado'] == 'esperando' and info.get('publico', False):
            # Leemos el nombre directamente de la sala
            nombre = info.get('creador_nombre', 'Desconocido')
            creador_sid = info['sids'][0] if info['sids'] else None
            creador_username = info.get('username')

            lista.append({
                'codigo': cod,
                'creador': nombre,
                'creador_sid': creador_sid,
                'creador_username': creador_username,
                'al_mejor_de': info.get('al_mejor_de', 3)
            })
    socketio.emit('actualizar_publicas', lista)

@socketio.on('pedir_publicas')
def handle_pedir_publicas():
    emitir_lista_publicas()


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
    
    salas[codigo] = {'estado': 'esperando', 'sids': [sid], 'al_mejor_de': al_mejor_de_valor, 'publico': es_publico, 'username': real_username, 'creador_nombre': nombre}
    
    print(f"👉 {nombre} ha creado la sala {codigo} (Pública: {es_publico})")
    emit('sala_creada', {'codigo': codigo}, room=sid)
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
    salas[codigo] = {
        'estado': 'jugando', 
        'sids': [sid, bot_sid], 
        'al_mejor_de': al_mejor_de_valor, 
        'publico': False, 
        'username': real_username,
        'bot': SmartBot(bot_sid) 
    }
    
    partida = PartidaMus(sid, bot_sid)
    partida.nombres_ia = {
        sid: real_username if real_username else nombre,
        bot_sid: 'Bot IA'
    }
    partida.al_mejor_de = al_mejor_de_valor
    partida.iniciar_ronda()
    salas[codigo]['motor'] = partida
    
    print(f"🤖 {nombre} ha creado la sala {codigo} contra la IA")
    emit('sala_creada', {'codigo': codigo}, room=sid)
    emit('iniciar_partida', {'mensaje': '¡La partida comienza!'}, room=codigo)
    enviar_estado_a_jugadores(codigo)




@socketio.on('unirse_sala')
def handle_unirse_sala(datos):
    sid = request.sid
    # Quitamos espacios accidentales al inicio o final
    nombre = datos.get('nombre', 'Jugador').strip()
    codigo = datos.get('codigo', '').upper()
    
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
        if es_creador:
            # El creador legítimo recupera su trono (Asiento 0)
            if sids[0] is None:
                sids[0] = sid
                asiento_asignado = 0
            elif len(sids) == 1:
                sids.append(sid)
                asiento_asignado = 1
            elif len(sids) == 2 and sids[1] is None:
                sids[1] = sid
                asiento_asignado = 1
        else:
            # Invitado buscando silla
            if len(sids) == 1:
                sids.append(sid)
                asiento_asignado = 1
            elif len(sids) == 2 and sids[1] is None:
                sids[1] = sid
                asiento_asignado = 1
            elif len(sids) == 2 and sids[0] is None:
                # LA MAGIA: Si la sesión falló, pero el asiento del creador está libre, 
                # sentamos a esta persona ahí para poder arrancar el juego de una vez.
                sids[0] = sid
                asiento_asignado = 0
                print(f"⚠️ {nombre} ocupó el Asiento 0 (vacío) por precaución en {codigo}.")
                
        if asiento_asignado == -1:
            emit('error_sala', {'mensaje': 'La sala ya está llena.'}, room=sid)
            return
            
        # Añadimos los datos al jugador
        jugadores[sid] = {'nombre': nombre, 'sala': codigo, 'username': mi_username}
        join_room(codigo)

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
            partida.iniciar_ronda()
            salas[codigo]['motor'] = partida
            
            emit('iniciar_partida', {'mensaje': '¡La partida comienza!'}, room=codigo)
            enviar_estado_a_jugadores(codigo)
            emitir_lista_publicas()
        else:
            emit('sala_creada', {'codigo': codigo}, room=sid)
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
    partida_actual = sala['motor']
        
    for sid in sala['sids']:
        if sid.startswith('BOT_'): continue
        estado_del_jugador = partida_actual.estado[sid]
        es_mi_turno = (sid == partida_actual.turno_de)
        soy_mano = (sid == partida_actual.id_mano)
        rival_sid = partida_actual.id_postre if sid == partida_actual.id_mano else partida_actual.id_mano
        
        if partida_actual.fase == 'descarte':
            mensaje = {'code': 'fase_descarte'}
        elif partida_actual.fase == 'apuestas':
            if partida_actual.indice_fase < len(partida_actual.fases_apuesta):
                n_fase = partida_actual.fases_apuesta[partida_actual.indice_fase]
                nombre_turno = jugadores[partida_actual.turno_de]['nombre']
                mensaje = {'code': 'fase_apuestas', 'fase': n_fase, 'jugador': nombre_turno}
            else:
                mensaje = {'code': 'fase_recuento'}
        else:
            nombre_turno = jugadores[partida_actual.turno_de]['nombre'] if partida_actual.turno_de else "..."
            mensaje = {'code': 'fase_general', 'fase': partida_actual.fase, 'jugador': nombre_turno}
        
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
        cartas_rival = partida_actual.estado[rival_sid]['cartas']

        puede_pedrete_ahora = False
        if partida_actual.fase == 'mus':
            vals = sorted([c['valor'] for c in estado_del_jugador['cartas']])
            if vals == [4, 5, 6, 7]:
                puede_pedrete_ahora = True

        if partida_actual.fase == 'recuento':
            pasos_crudos = partida_actual.calcular_recuento()

            if getattr(partida_actual, 'partida_sumada', False) and not getattr(partida_actual, 'db_registrada', False):
                partida_actual.db_registrada = True 
                import base_datos
                
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
            print(f"📤 [SALA {codigo_sala}] Estado a {jugadores[sid]['nombre']}: Fase {partida_actual.fase}")

        # === EL ARREGLO ESTÁ AQUÍ ===
        payload = {
            'para_sid': sid,  # Añadimos a quién va dirigido
            'nombre_rival': partida_actual.nombres_ia.get(rival_sid, jugadores.get(rival_sid, {}).get('nombre', 'Rival')),
            'fase': partida_actual.fase,
            'puede_pedrete': puede_pedrete_ahora,
            'es_mi_turno': es_mi_turno,
            'soy_mano': soy_mano,
            'descartes_listos': estado_del_jugador.get('descartes_listos', False),
            'descartes_rival': partida_actual.estado[rival_sid].get('descartes_hechos', 0),
            'apuestas': info_apuestas,
            'mensaje': mensaje,
            'mis_cartas': estado_del_jugador['cartas'],
            'mis_puntos': estado_del_jugador['puntos'],
            'puntos_rival': partida_actual.estado[rival_sid]['puntos'],
            'mensaje_transicion': partida_actual.mensaje_transicion,
            'recuento': datos_recuento,
            'cartas_rival': cartas_rival,
            'rival_puntos_finales': partida_actual.estado[rival_sid]['puntos'],
            'mis_partidas': partida_actual.partidas_ganadas[sid],
            'partidas_rival': partida_actual.partidas_ganadas[rival_sid],
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
            
            def bot_action_task():
                socketio.sleep(1.5) 
                if codigo_sala in salas and salas[codigo_sala]['estado'] == 'jugando':
                    acc = bot_instance.obtener_accion(salas[codigo_sala]['motor'])
                    if acc:
                        print(f"🤖 Bot ejecuta en sala {codigo_sala}: {acc}")
                        procesar_accion_interna(bot_sid, codigo_sala, acc)
            
            socketio.start_background_task(bot_action_task)

@socketio.on('abandonar_sala_limpiamente')
def handle_abandonar_limpiamente():
    sid = request.sid
    if sid in jugadores:
        codigo = jugadores[sid]['sala']
        if codigo in salas:
            del salas[codigo] # Destruimos la sala para que 'disconnect' no avise al rival
            emitir_lista_publicas()


@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
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
                        # Si todos los asientos son None, la sala está completamente muerta
                        if all(s is None for s in salas[codigo]['sids']):
                            print(f"🧹 Limpiando sala abandonada: {codigo}")
                            del salas[codigo]
                            emitir_lista_publicas()
                
                socketio.start_background_task(limpiar_sala_huerfana)
                emitir_lista_publicas()
                
            else:
                # Si estaban jugando, destruimos la sala
                print(f"❌ {nombre} se desconectó en plena partida. Destruyendo sala {codigo}.")
                emit('rival_desconectado', room=codigo)
                del salas[codigo]
                emitir_lista_publicas()


if __name__ == '__main__':
    print("🚀 Servidor de Mus iniciado en http://localhost:5001")
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)
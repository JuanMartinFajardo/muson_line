"""
SEGURIDAD (Roadmap #16) — endurecimiento del servidor
=====================================================

Todo lo que se puede endurecer *desde el código*, sin depender de que la máquina
esté configurada de una forma concreta. Lo que sí necesita la máquina (nginx,
Cloudflare) está en `tools/nginx-callmus.conf` y en la wiki; este módulo se
limita a **aprovecharlo automáticamente cuando aparece** y a no estorbar
mientras no está. Esa es la regla de diseño de todo el archivo:

    ninguna protección de aquí puede dejar el sitio peor de como estaba.

Concretamente:

1. **IP real del cliente** (`ip_cliente`). Detrás de un proxy, `remote_addr` es
   el propio proxy. Werkzeug trae `ProxyFix`, que coge el **último** valor de
   `X-Forwarded-For` — el que añadió *nuestro* nginx — y no el primero, que lo
   puede escribir el atacante en su propia petición. Es la diferencia entre un
   límite por IP que sirve y uno que se salta con una cabecera.

2. **Cookie de sesión.** `HttpOnly` y `SameSite=Lax` siempre; `Secure` **según
   la petición**, no fijo en la configuración: mientras el proxy no diga que
   viene por TLS la cookie sale sin la marca (o sea, como hasta ahora) y el día
   que la diga se marca sola. Un `Secure` puesto a mano sobre HTTP habría
   dejado a todo el mundo sin poder iniciar sesión.

3. **Cabeceras de seguridad y CSP** con nonce para los dos bloques en línea de
   las plantillas. HSTS solo se manda cuando la petición ha llegado por HTTPS
   de verdad: prometerle a un navegador "solo HTTPS" desde un servidor que aún
   no lo tiene es la única forma de tirar un sitio con una cabecera.

4. **Límite de peticiones** en `/auth/*`, en memoria y sin dependencias nuevas
   (la caja es una e2-micro de 1 GB). Si el proxy no nos pasa la IP real —cosa
   que se detecta— el límite se aplica por identidad (usuario/correo enviado)
   en vez de por IP, para que un despiste de configuración no convierta a todos
   los visitantes en un mismo cubo y deje el login inservible.

5. **Copia de seguridad diaria** de `mus.db` y `analitica.db` con la API
   `backup()` de sqlite3 (consistente aunque haya escrituras a la vez), con
   rotación. Sin cron, sin nada que instalar.

6. **Validación de entrada** en el borde (`texto`, `codigo_sala`, `entero`,
   `indices`): el motor ya se defiende, pero se defiende mejor si no le llega
   basura.
"""

import os
import re
import time
import shutil
import sqlite3
import secrets
import ipaddress
from functools import wraps

from flask import request, session, jsonify, g, Response, has_request_context


# ==========================================================================
# Configuración (todo por variables de entorno, todo con un valor por defecto
# que funciona sin tocar nada)
# ==========================================================================

def _flag(nombre, defecto):
    return (os.environ.get(nombre, '1' if defecto else '0').strip().lower()
            not in ('0', 'false', 'no', ''))


# Nº de proxies de confianza delante (nginx = 1; con Cloudflare delante de nginx
# sigue siendo 1 para X-Forwarded-For, porque nginx reescribe la cadena).
PROXIES_DE_CONFIANZA = int(os.environ.get('PROXIES_DE_CONFIANZA', '1'))
# Forzar el modo HTTPS aunque el proxy no mande X-Forwarded-Proto.
FORZAR_HTTPS = _flag('FORZAR_HTTPS', False)
# Duración de HSTS. 180 días bastan para puntuar bien en securityheaders.com y
# son menos irreversibles que un año si algún día caduca el certificado.
HSTS_MAX_AGE = int(os.environ.get('HSTS_MAX_AGE', str(180 * 24 * 3600)))
# CSP: 'enforce' (bloquea), 'report' (solo avisa en la consola del navegador),
# 'off' (no se manda). 'report' es el modo para probar un cambio en las páginas.
CSP_MODO = os.environ.get('CSP_MODO', 'enforce').strip().lower()
# Límite de peticiones en /auth/*.
LIMITES_ACTIVOS = _flag('LIMITES_ACTIVOS', True)
# Copias de seguridad diarias.
BACKUP_ACTIVO = _flag('BACKUP_ACTIVO', True)
BACKUP_DIR = os.environ.get('BACKUP_DIR', 'backups')
BACKUP_COPIAS = int(os.environ.get('BACKUP_COPIAS', '7'))


# ==========================================================================
# 1. Quién nos está llamando de verdad
# ==========================================================================

def _es_privada(ip):
    """True para 127.0.0.1, ::1, 10.x, 192.168.x… o para una IP ilegible."""
    if not ip:
        return True
    try:
        return ipaddress.ip_address(ip).is_private or ipaddress.ip_address(ip).is_loopback
    except ValueError:
        return True


def ip_cliente():
    """La IP del visitante, ya sea directa o a través del proxy.

    `ProxyFix` (instalado en `init_seguridad`) deja en `remote_addr` el valor
    correcto de X-Forwarded-For. Cloudflare añade además `CF-Connecting-IP`,
    que es la IP original aunque haya varios saltos: se prefiere esa, pero
    **solo** si quien nos habla es el proxy local, para que nadie se invente la
    cabecera conectándose por su cuenta al puerto de la aplicación.
    """
    if not has_request_context():
        return None
    directa = request.remote_addr
    cf = request.headers.get('CF-Connecting-IP', '').strip()
    if cf and (PROXIES_DE_CONFIANZA > 0):
        return cf
    return directa


def ip_utilizable():
    """¿Sirve la IP que vemos para contar peticiones por cliente?

    Si el proxy no reenvía X-Forwarded-For, *todo el mundo* llega como
    127.0.0.1 y un límite por IP sería un límite global: mejor saberlo.
    """
    return not _es_privada(ip_cliente())


def es_https():
    """¿La petición llegó por TLS? Con ProxyFix esto ya mira X-Forwarded-Proto."""
    if FORZAR_HTTPS:
        return True
    if not has_request_context():
        return False
    return request.is_secure


# El primer aviso vale por todos: un print por arranque, no uno por petición.
_diagnostico_hecho = False


def _diagnostico_una_vez():
    global _diagnostico_hecho
    if _diagnostico_hecho:
        return
    _diagnostico_hecho = True
    ip = ip_cliente()
    tls = 'sí' if es_https() else 'NO'
    print(f"🔐 Seguridad: primera petición desde {ip} | HTTPS detectado: {tls} | "
          f"CSP: {CSP_MODO} | límites: {'sí' if LIMITES_ACTIVOS else 'no'}")
    if not ip_utilizable():
        print("⚠️  El proxy NO está reenviando la IP del cliente (X-Forwarded-For). "
              "Los límites de /auth/* se aplicarán por usuario/correo en vez de por IP. "
              "Añade 'proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;' "
              "en nginx (ver tools/nginx-callmus.conf).")
    if not es_https():
        print("⚠️  Sin HTTPS detectado: la cookie de sesión no lleva 'Secure' y no se "
              "manda HSTS. Si el sitio ya va por TLS, falta "
              "'proxy_set_header X-Forwarded-Proto $scheme;' en nginx.")


# ==========================================================================
# 2. Cookie de sesión: Secure decidido petición a petición
# ==========================================================================

def _instalar_cookie_segura(app):
    """`SESSION_COOKIE_SECURE` es una constante de configuración, y aquí hace
    falta que sea una decisión por petición (ver la cabecera del módulo). La
    interfaz de sesión de Flask expone justo el gancho necesario."""
    from flask.sessions import SecureCookieSessionInterface

    class SesionSegunEsquema(SecureCookieSessionInterface):
        def get_cookie_secure(self, app):
            return es_https()

    app.session_interface = SesionSegunEsquema()
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    # 'Lax' deja pasar la vuelta de Google OAuth (es una navegación GET de primer
    # nivel) y a la vez impide que un POST desde otro sitio viaje con la sesión,
    # que es la protección CSRF básica de todos los formularios del juego.
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'


# ==========================================================================
# 3. Cabeceras de seguridad y CSP
# ==========================================================================

def nonce_actual():
    """El nonce de esta petición, para las plantillas (`{{ csp_nonce }}`)."""
    n = getattr(g, '_csp_nonce', None)
    if n is None:
        n = secrets.token_urlsafe(16)
        g._csp_nonce = n
    return n


def _politica_csp():
    """La política, construida por petición porque lleva el nonce y el origen
    del WebSocket. Notas de las decisiones menos evidentes:

    - `style-src` lleva 'unsafe-inline' porque las páginas usan atributos
      style= por todas partes (95 en index.html) y un nonce no cubre atributos.
      Restringir el *origen* de las hojas sigue valiendo de algo.
    - `script-src` NO lleva 'unsafe-inline': el cliente de Socket.IO ya se sirve
      desde /static (Roadmap #16.7) y los dos bloques en línea llevan nonce.
    - `connect-src` necesita el origen ws:// además de 'self' para los
      navegadores que no consideran que 'self' incluya el WebSocket del mismo
      host (Safari antiguo, sobre todo).
    """
    host = request.host
    ws = f"wss://{host}" if es_https() else f"ws://{host} wss://{host}"
    return "; ".join([
        "default-src 'self'",
        "base-uri 'self'",
        "object-src 'none'",
        "frame-ancestors 'self'",
        "form-action 'self'",
        "img-src 'self' data: blob:",
        "font-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        f"script-src 'self' 'nonce-{nonce_actual()}'",
        f"connect-src 'self' {ws}",
    ])


def _cabeceras(response):
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
    # Redundante con frame-ancestors, pero es lo que miran los escáneres viejos.
    response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
    # El juego no pide cámara, micrófono ni ubicación: se cierra la puerta.
    response.headers.setdefault(
        'Permissions-Policy',
        'geolocation=(), microphone=(), camera=(), payment=(), usb=(), interest-cohort=()')

    if es_https() and HSTS_MAX_AGE > 0:
        response.headers.setdefault(
            'Strict-Transport-Security', f'max-age={HSTS_MAX_AGE}; includeSubDomains')

    # La CSP solo tiene sentido en documentos y respuestas de la aplicación; en
    # las imágenes de las cartas es peso muerto en cada una de las 40 cartas.
    if CSP_MODO in ('enforce', 'report') and not request.path.startswith('/static/'):
        tipo = (response.mimetype or '')
        if tipo in ('text/html', 'application/json') or tipo.startswith('text/'):
            clave = ('Content-Security-Policy' if CSP_MODO == 'enforce'
                     else 'Content-Security-Policy-Report-Only')
            response.headers.setdefault(clave, _politica_csp())
    return response


# ==========================================================================
# 4. Límite de peticiones (en memoria, sin dependencias)
# ==========================================================================
# Tabla ruta → tramos (nº máximo, ventana en segundos). Se aplica el más
# restrictivo que incumpla. Fuera de la tabla no se limita nada: /auth/sesion lo
# consulta el cliente en cada carga y /admin/* lo machaca el propio panel con su
# refresco, así que limitarlos rompería el uso normal sin ganar nada (los dos
# están detrás de sesión; la fuerza bruta ataca /auth/login, que sí está aquí).

LIMITES = (
    (re.compile(r'^/auth/login$'),            ((10, 60), (60, 3600))),
    (re.compile(r'^/auth/registro$'),         ((5, 60), (15, 3600))),
    (re.compile(r'^/auth/solicitar_codigo$'), ((3, 60), (10, 3600))),
    (re.compile(r'^/auth/solicitar_reset$'),  ((3, 60), (10, 3600))),
    (re.compile(r'^/auth/reset$'),            ((5, 60), (20, 3600))),
    (re.compile(r'^/auth/cuenta/'),           ((10, 60), (40, 3600))),
    (re.compile(r'^/auth/google/'),           ((10, 60), (60, 3600))),
)

_cubos = {}          # clave → [epoch, epoch, …]
_ultima_purga = 0.0


def _purgar(ahora):
    """Las claves son IPs y correos: sin esto la memoria crece con cada visitante
    nuevo y no baja nunca. Cada 10 min se tiran las que ya no cuentan nada."""
    global _ultima_purga
    if ahora - _ultima_purga < 600:
        return
    _ultima_purga = ahora
    for clave in [k for k, v in _cubos.items() if not v or ahora - v[-1] > 3600]:
        _cubos.pop(clave, None)


def _identidad_de_la_peticion():
    """Con quién estamos hablando, para contar sus intentos. Preferimos la IP;
    si el proxy no nos la pasa (o es la del propio proxy) usamos lo que la
    petición dice ser: el usuario o el correo del formulario. No es infalible
    —se cambia una letra y es otro cubo— pero frena el goteo automático y, sobre
    todo, no puede dejar fuera a todo el mundo a la vez."""
    if ip_utilizable():
        return 'ip:' + str(ip_cliente())
    datos = {}
    if request.is_json:
        try:
            datos = request.get_json(silent=True) or {}
        except Exception:
            datos = {}
    quien = (str(datos.get('username') or datos.get('email') or '')).strip().lower()
    return 'id:' + (quien or 'anonimo')


def _excedido(clave, tramos):
    ahora = time.time()
    _purgar(ahora)
    ventana_max = max(v for _, v in tramos)
    marcas = [t for t in _cubos.get(clave, []) if ahora - t < ventana_max]
    for maximo, ventana in tramos:
        if sum(1 for t in marcas if ahora - t < ventana) >= maximo:
            _cubos[clave] = marcas          # no se apunta el intento rechazado
            return int(ventana - (ahora - marcas[0])) or 1
    marcas.append(ahora)
    _cubos[clave] = marcas
    return 0


def _revisar_limite():
    """`before_request`: mira la tabla y corta si procede."""
    _diagnostico_una_vez()
    if not LIMITES_ACTIVOS:
        return None
    ruta = request.path
    for patron, tramos in LIMITES:
        if not patron.match(ruta):
            continue
        espera = _excedido(f'{ruta}|{_identidad_de_la_peticion()}', tramos)
        if not espera:
            return None
        print(f"🚦 Límite alcanzado en {ruta} para {_identidad_de_la_peticion()}")
        if ruta.startswith('/auth/google/'):
            # Estas dos son navegaciones del navegador, no fetch(): texto plano.
            resp = Response('Demasiados intentos. Espera un momento e inténtalo de nuevo.',
                            status=429, mimetype='text/plain; charset=utf-8')
        else:
            resp = jsonify({
                'exito': False,
                'codigo': 'err_demasiados_intentos',
                'mensaje': 'Demasiados intentos. Espera un momento e inténtalo de nuevo.',
            })
            resp.status_code = 429
        resp.headers['Retry-After'] = str(espera)
        return resp
    return None


def limitar(*tramos):
    """Decorador por si alguna ruta futura quiere su propio límite sin tocar la
    tabla: `@limitar((5, 60), (20, 3600))`."""
    def envoltorio(f):
        @wraps(f)
        def interior(*a, **kw):
            if LIMITES_ACTIVOS:
                espera = _excedido(f'{f.__name__}|{_identidad_de_la_peticion()}', tramos)
                if espera:
                    resp = jsonify({'exito': False, 'codigo': 'err_demasiados_intentos',
                                    'mensaje': 'Demasiados intentos. Espera un momento '
                                               'e inténtalo de nuevo.'})
                    resp.status_code = 429
                    resp.headers['Retry-After'] = str(espera)
                    return resp
            return f(*a, **kw)
        return interior
    return envoltorio


# ==========================================================================
# 5. Validación de entrada en el borde
# ==========================================================================
# El motor ya acota las apuestas y las salas ya comprueban los asientos; esto es
# la aduana previa, para que nada raro llegue siquiera a esa lógica. Todas las
# funciones devuelven SIEMPRE un valor válido: sanean, no lanzan excepciones —
# un evento de socket que revienta deja la partida a medias.

_RE_CODIGO = re.compile(r'^[A-Z0-9]{4}$')
# Se quitan los caracteres de control (incluido el separador de derecha a
# izquierda y demás trucos de bidireccionalidad) que pueden descuadrar la mesa.
_RE_CONTROL = re.compile('[\x00-\x1f\x7f'
                         '​-‏'    # anchos cero y marcas de dirección
                         '‪-‮'    # incrustaciones bidi
                         '⁦-⁩]')  # aislantes bidi


def dic(valor):
    """El payload de un evento de socket, garantizado como diccionario. Varios
    manejadores hacían `datos.get(...)` directamente: mandar `null` o una lista
    los rompía con un AttributeError dentro del greenlet."""
    return valor if isinstance(valor, dict) else {}


def texto(valor, maximo=20, defecto=''):
    """Cadena corta, sin control ni espacios de sobra, recortada a `maximo`."""
    if not isinstance(valor, str):
        return defecto
    limpio = _RE_CONTROL.sub('', valor).strip()
    limpio = re.sub(r'\s{2,}', ' ', limpio)[:maximo].strip()
    return limpio or defecto


def codigo_sala(valor):
    """Código de sala normalizado, o '' si no tiene la pinta de uno."""
    if not isinstance(valor, str):
        return ''
    v = valor.strip().upper()
    return v if _RE_CODIGO.match(v) else ''


def entero(valor, minimo, maximo, defecto=None):
    """Entero acotado. Un bool no cuela (en Python `True` es un entero)."""
    if isinstance(valor, bool) or not isinstance(valor, (int, float, str)):
        return defecto if defecto is not None else minimo
    try:
        n = int(valor)
    except (TypeError, ValueError):
        return defecto if defecto is not None else minimo
    return max(minimo, min(maximo, n))


def opcion(valor, permitidos, defecto):
    """Uno de los valores de una lista blanca, o el de por defecto."""
    return valor if valor in permitidos else defecto


def indices(valor, maximo=4):
    """Lista de índices de cartas: enteros únicos, dentro de la mano y ordenados."""
    if not isinstance(valor, (list, tuple)):
        return []
    vistos = []
    for v in valor[:20]:          # tope de lectura: no recorremos una lista enorme
        if len(vistos) >= maximo:
            break
        if isinstance(v, bool) or not isinstance(v, (int, float, str)):
            continue
        try:
            n = int(v)
        except (TypeError, ValueError):
            continue
        if 0 <= n < maximo and n not in vistos:
            vistos.append(n)
    return sorted(vistos)


# ==========================================================================
# 6. Copia de seguridad diaria de las bases de datos
# ==========================================================================

def _copiar_db(origen, destino):
    """Copia consistente con la API backup() de sqlite3: no hace falta parar el
    servidor ni preocuparse por una escritura a medias, y funciona igual con el
    WAL de la base de analítica (un `cp` no)."""
    src = sqlite3.connect(origen)
    try:
        dst = sqlite3.connect(destino)
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()


def _rotar(directorio, prefijo, copias):
    archivos = sorted(f for f in os.listdir(directorio)
                      if f.startswith(prefijo) and f.endswith('.db'))
    for viejo in archivos[:-copias] if copias > 0 else []:
        try:
            os.remove(os.path.join(directorio, viejo))
        except OSError:
            pass


def hacer_backup(bases, directorio=None, copias=None):
    """Una tanda de copias. Devuelve la lista de archivos escritos."""
    directorio = directorio or BACKUP_DIR
    copias = BACKUP_COPIAS if copias is None else copias
    os.makedirs(directorio, exist_ok=True)
    sello = time.strftime('%Y%m%d')
    escritos = []
    for ruta in bases:
        if not os.path.exists(ruta):
            continue
        base = os.path.splitext(os.path.basename(ruta))[0]
        destino = os.path.join(directorio, f'{base}_{sello}.db')
        try:
            _copiar_db(ruta, destino)
            _rotar(directorio, base + '_', copias)
            escritos.append(destino)
        except Exception as e:
            print(f"⚠️  No se pudo copiar {ruta}: {e}")
    return escritos


def _hay_sitio(directorio):
    """La e2-micro va justa de disco: si quedan menos de 500 MB no copiamos."""
    try:
        return shutil.disk_usage(directorio or '.').free > 500 * 1024 * 1024
    except OSError:
        return True


def _tarea_backup(socketio, bases):
    """Una copia al arrancar (para tener algo desde el minuto uno) y otra cada
    24 h. Los archivos son de cientos de kB, así que el parón del único hilo de
    eventlet es de milisegundos."""
    while True:
        try:
            os.makedirs(BACKUP_DIR, exist_ok=True)
            if _hay_sitio(BACKUP_DIR):
                escritos = hacer_backup(bases)
                if escritos:
                    print(f"💾 Copia de seguridad: {', '.join(escritos)}")
            else:
                print("⚠️  Copia de seguridad omitida: queda poco espacio en disco.")
        except Exception as e:
            print(f"⚠️  Fallo en la copia de seguridad: {e}")
        socketio.sleep(24 * 3600)


# ==========================================================================
# 7. Orígenes permitidos para el WebSocket (CORS)
# ==========================================================================

def origenes_permitidos(puerto=5001):
    """Lista blanca para `SocketIO(cors_allowed_origins=…)`.

    Se puede sustituir entera con CORS_ORIGINS (separada por comas) o poner
    CORS_ORIGINS=* para volver al comportamiento antiguo si algo se torciera en
    producción: es un cambio de variable de entorno y un reinicio, sin tocar
    código.
    """
    crudo = os.environ.get('CORS_ORIGINS', '').strip()
    if crudo == '*':
        return '*'
    if crudo:
        return [o.strip() for o in crudo.split(',') if o.strip()]
    dominios = ['https://callmus.com', 'https://www.callmus.com']
    for host in ('localhost', '127.0.0.1'):
        dominios.append(f'http://{host}:{puerto}')
    return dominios


# ==========================================================================
# Instalación
# ==========================================================================

def init_seguridad(app, socketio=None, bases=()):
    """Engancha todo lo anterior a la aplicación. Se llama una vez, pronto: el
    `before_request` del límite tiene que correr antes que el de nadie más."""
    if PROXIES_DE_CONFIANZA > 0:
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app,
                                x_for=PROXIES_DE_CONFIANZA,
                                x_proto=PROXIES_DE_CONFIANZA,
                                x_host=PROXIES_DE_CONFIANZA,
                                x_port=0, x_prefix=0)

    _instalar_cookie_segura(app)

    app.before_request(_revisar_limite)
    app.after_request(_cabeceras)
    # `{{ csp_nonce }}` en las plantillas. Es una función perezosa: el nonce solo
    # se genera en las páginas que lo usan.
    app.context_processor(lambda: {'csp_nonce': nonce_actual})

    if BACKUP_ACTIVO and socketio is not None and bases:
        socketio.start_background_task(_tarea_backup, socketio, list(bases))
        print(f"💾 Copias de seguridad diarias activas en {BACKUP_DIR}/ "
              f"({BACKUP_COPIAS} copias).")

    print(f"🔐 Seguridad activa (CSP: {CSP_MODO}, límites: "
          f"{'sí' if LIMITES_ACTIVOS else 'no'}, proxies de confianza: "
          f"{PROXIES_DE_CONFIANZA}).")

# ==========================================================================
# ANALÍTICA DE USO (Roadmap #24)
# --------------------------------------------------------------------------
# Módulo ADITIVO, igual que social.py y admin.py: no toca los manejadores del
# juego. Se engancha desde server.py con init_analitica(app, socketio, ctx).
# Vive en el mismo proceso Flask, el mismo puerto y la misma sesión: no hay
# nada que desplegar aparte.
#
# QUÉ MIDE
#   Visitas, visitantes, duración de la visita, embudo visita→juego, partidas,
#   altas, inicios de sesión, retención por cohortes de cuenta, interés por el
#   botón de Ko-fi, y el reparto por fuente de tráfico, país, idioma,
#   dispositivo, navegador, modo de juego y baraja.
#
# POR QUÉ NO HACE FALTA UN AVISO DE COOKIES
#   No se guarda NADA en el dispositivo del visitante para medir: ni cookie de
#   analítica, ni localStorage, ni huella persistente. El visitante se identifica
#   con un hash efímero de (sal + IP + user-agent) donde la SAL SE GENERA AL
#   AZAR EN MEMORIA Y ROTA CADA DÍA — no se guarda en disco, así que ni siquiera
#   el dueño del servidor puede recomponer a posteriori qué IP fue qué visita.
#   La IP en crudo no se almacena jamás. Todo es de primera parte (nada sale del
#   servidor), agregado y con los datos crudos borrados a los 90 días.
#   Ese es exactamente el perfil de "medición de audiencia" que la Guía de
#   cookies de la AEPD y la CNIL dejan fuera del consentimiento previo. Lo único
#   obligatorio es contarlo en la política de privacidad, y eso está hecho en el
#   texto `privacy_p3` de static/app.js (ES y EN).
#   Consecuencia asumida: un visitante sin cuenta solo es reconocible DENTRO del
#   mismo día. La retención entre días es exacta solo para cuentas.
#
# ARQUITECTURA
#   analitica.db (SQLite propio, WAL) — fuera de mus.db a propósito: es el flujo
#   de escritura más alto de la casa y no debe competir con las partidas ni
#   engordar la copia de seguridad que se descarga desde /admin.
#
#   Escritura: las visitas vivas están EN MEMORIA y un greenlet vuelca cada 5 s.
#   Ninguna petición del jugador espera nunca a una escritura de analítica.
#
#   Lectura: el panel NUNCA lee las tablas crudas. Lee los agregados diarios
#   (Dia / DiaDim / DiaUsuario), que se conservan para siempre; el día en curso
#   se recalcula al vuelo. Así una consulta de 2 años cuesta lo mismo que una de
#   una semana.
# ==========================================================================

import os
import re
import json
import time
import sqlite3
import secrets
import hashlib
import threading
from datetime import datetime, timedelta, date

from flask import request, session, jsonify, Response

import base_datos
import seguridad

DB_ANALITICA = os.environ.get('ANALYTICS_DB', 'analitica.db')

# Una visita se da por terminada tras esta inactividad (el estándar de facto).
INACTIVIDAD_SESION = 30 * 60
# Cada cuánto vuelca el greenlet lo acumulado en memoria.
INTERVALO_VOLCADO = 5
# Cada cuánto se consolidan días y se purga lo viejo.
INTERVALO_MANTENIMIENTO = 3600
# Días que se conservan las filas crudas. Los agregados diarios no caducan.
DIAS_CRUDOS = int(os.environ.get('ANALYTICS_RETENCION_DIAS', '90'))
# El cliente late cada 30 s; damos margen antes de considerar muerta una visita.
VENTANA_EN_VIVO = 120

# Tipos de evento que el cliente puede mandar. Todo lo demás se descarta: el
# endpoint es público y no puede convertirse en un vertedero de texto libre.
EVENTOS_CLIENTE = {
    'menu_jugar', 'menu_ranking', 'menu_ajustes', 'menu_tutorial', 'menu_barajas',
    'tutorial_fin', 'idioma', 'baraja', 'registro_abierto', 'login_abierto',
    'soporte_abierto', 'amigos_abierto', 'invitacion_enviada', 'error_cliente',
    'kofi',
}
# Eventos que solo genera el servidor (no se aceptan por HTTP).
EVENTOS_SERVIDOR = {
    'pagina', 'sala_creada', 'partida_inicio', 'partida_fin', 'partida_abandono',
    'registro', 'login', 'logout',
}

MODOS = ('bot', 'online2', 'online4')

_RE_BOT = re.compile(
    r'bot|crawl|spider|slurp|bingpreview|facebookexternalhit|headless|phantom|'
    r'python-requests|httpx|aiohttp|curl|wget|scrapy|monitor|uptime|pingdom|'
    r'semrush|ahrefs|mj12|dotbot|petalbot|bytespider|gptbot|claudebot|ccbot',
    re.I)
_RE_MOVIL = re.compile(r'android|iphone|ipod|windows phone|mobile', re.I)
_RE_TABLET = re.compile(r'ipad|tablet|kindle|silk', re.I)

_BUSCADORES = ('google.', 'bing.', 'duckduckgo', 'yahoo.', 'ecosia', 'yandex',
               'baidu', 'qwant', 'brave.com', 'startpage')

# --------------------------------------------------------------------------
# Estado en memoria
# --------------------------------------------------------------------------
_lock = threading.Lock()
_sesiones = {}          # clave_visitante -> dict de la visita viva
_eventos_pend = []      # eventos aún sin volcar
_pendientes_cierre = [] # visitas ya cerradas, a la espera del último volcado
_sal = {'dia': None, 'valor': None}   # sal del hash, solo en memoria
_socketio = None
_ctx = {}
_arrancado = False


# ==========================================================================
# Base de datos
# ==========================================================================

def _conn():
    c = sqlite3.connect(DB_ANALITICA, timeout=10)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    """Crea el esquema. Idempotente: se puede llamar en cada arranque."""
    with _conn() as c:
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA synchronous=NORMAL")

        # --- Crudo: una fila por visita -----------------------------------
        # `visitante` es el hash efímero del día; no sirve para nada al día
        # siguiente y por eso mismo no identifica a nadie.
        c.execute('''
            CREATE TABLE IF NOT EXISTS Sesiones (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                visitante   TEXT NOT NULL,
                dia         TEXT NOT NULL,
                inicio      REAL NOT NULL,
                fin         REAL NOT NULL,
                activo      INTEGER DEFAULT 0,   -- segundos con la pestaña visible
                vistas      INTEGER DEFAULT 0,
                eventos     INTEGER DEFAULT 0,
                user_id     INTEGER,
                username    TEXT,
                logueado    INTEGER DEFAULT 0,
                registro    INTEGER DEFAULT 0,
                login       INTEGER DEFAULT 0,
                interactuo  INTEGER DEFAULT 0,
                jugo        INTEGER DEFAULT 0,
                partidas    INTEGER DEFAULT 0,
                partidas_fin INTEGER DEFAULT 0,
                segundos_juego INTEGER DEFAULT 0,
                modos       TEXT,
                pais        TEXT,
                idioma      TEXT,
                dispositivo TEXT,
                navegador   TEXT,
                so          TEXT,
                fuente      TEXT,
                medio       TEXT,
                campana     TEXT,
                landing     TEXT,
                baraja      TEXT,
                trafico_bot INTEGER DEFAULT 0,
                kofi        INTEGER DEFAULT 0,   -- la visita pulsó Ko-fi
                kofi_clics  INTEGER DEFAULT 0
            )''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_ses_dia ON Sesiones(dia)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_ses_user ON Sesiones(user_id, dia)')

        c.execute('''
            CREATE TABLE IF NOT EXISTS Eventos (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                sesion_id INTEGER,
                dia       TEXT NOT NULL,
                ts        REAL NOT NULL,
                tipo      TEXT NOT NULL,
                etiqueta  TEXT,
                valor     REAL,
                user_id   INTEGER
            )''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_ev_dia ON Eventos(dia, tipo)')

        # --- Agregados diarios: se conservan para siempre -------------------
        c.execute('''
            CREATE TABLE IF NOT EXISTS Dia (
                dia            TEXT PRIMARY KEY,
                visitas        INTEGER DEFAULT 0,
                visitantes     INTEGER DEFAULT 0,
                duracion_total INTEGER DEFAULT 0,
                activo_total   INTEGER DEFAULT 0,
                rebotes        INTEGER DEFAULT 0,
                interactuaron  INTEGER DEFAULT 0,
                jugaron        INTEGER DEFAULT 0,
                partidas       INTEGER DEFAULT 0,
                partidas_fin   INTEGER DEFAULT 0,
                segundos_juego INTEGER DEFAULT 0,
                registros      INTEGER DEFAULT 0,
                logins         INTEGER DEFAULT 0,
                visitas_cuenta INTEGER DEFAULT 0,
                cuentas        INTEGER DEFAULT 0,
                kofi           INTEGER DEFAULT 0,   -- visitas que pulsaron Ko-fi
                kofi_clics     INTEGER DEFAULT 0,   -- clics (una visita puede repetir)
                consolidado    REAL
            )''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS DiaDim (
                dia            TEXT NOT NULL,
                dimension      TEXT NOT NULL,
                valor          TEXT NOT NULL,
                visitas        INTEGER DEFAULT 0,
                duracion_total INTEGER DEFAULT 0,
                activo_total   INTEGER DEFAULT 0,
                rebotes        INTEGER DEFAULT 0,
                jugaron        INTEGER DEFAULT 0,
                partidas       INTEGER DEFAULT 0,
                registros      INTEGER DEFAULT 0,
                kofi           INTEGER DEFAULT 0,
                PRIMARY KEY (dia, dimension, valor)
            )''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS DiaUsuario (
                dia            TEXT NOT NULL,
                user_id        INTEGER NOT NULL,
                username       TEXT,
                visitas        INTEGER DEFAULT 0,
                duracion_total INTEGER DEFAULT 0,
                activo_total   INTEGER DEFAULT 0,
                partidas       INTEGER DEFAULT 0,
                partidas_fin   INTEGER DEFAULT 0,
                segundos_juego INTEGER DEFAULT 0,
                kofi           INTEGER DEFAULT 0,
                PRIMARY KEY (dia, user_id)
            )''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_diausuario_user ON DiaUsuario(user_id, dia)')

        # Migración de bases creadas antes de una columna nueva. Mismo patrón
        # que base_datos.py: añadir columnas es la única forma de evolucionar
        # el esquema sin perder el histórico ya medido.
        _migrar(c, 'Sesiones', ('kofi', 'kofi_clics'))
        _migrar(c, 'Dia', ('kofi', 'kofi_clics'))
        _migrar(c, 'DiaDim', ('kofi',))
        _migrar(c, 'DiaUsuario', ('kofi',))


def _migrar(c, tabla, columnas):
    """Añade las columnas que falten, todas INTEGER DEFAULT 0. SQLite rellena
    las filas existentes con el valor por defecto."""
    existentes = {r['name'] for r in c.execute(f"PRAGMA table_info({tabla})")}
    for col in columnas:
        if col not in existentes:
            c.execute(f"ALTER TABLE {tabla} ADD COLUMN {col} INTEGER DEFAULT 0")
            print(f"🛠️ Analítica: columna {tabla}.{col} añadida.")


# ==========================================================================
# Identidad efímera del visitante
# ==========================================================================

def _hoy():
    return datetime.now().strftime('%Y-%m-%d')


def _sal_de_hoy():
    """Sal aleatoria del día. Solo en memoria: al reiniciar el servidor o al
    cambiar el día, los hashes anteriores dejan de ser reproducibles para
    siempre. Eso es una decisión de privacidad, no un descuido."""
    hoy = _hoy()
    if _sal['dia'] != hoy:
        _sal['dia'] = hoy
        _sal['valor'] = secrets.token_bytes(32)
    return _sal['valor']


def _ip_cruda():
    """Solo se usa para calcular el hash; nunca se guarda.

    La resuelve seguridad.ip_cliente() (Roadmap #16): el primer valor de
    X-Forwarded-For lo escribe el cliente si quiere, y con él bastaba una
    cabecera distinta en cada petición para contarse como mil visitantes."""
    return seguridad.ip_cliente() or '0.0.0.0'


def _clave_visitante():
    ua = request.headers.get('User-Agent', '')
    crudo = _sal_de_hoy() + (_ip_cruda() + '|' + ua).encode('utf-8', 'ignore')
    return hashlib.sha256(crudo).hexdigest()[:20]


# ==========================================================================
# Clasificación de la visita (dimensiones)
# ==========================================================================

def _dispositivo(ua):
    if _RE_TABLET.search(ua):
        return 'tablet'
    if _RE_MOVIL.search(ua):
        return 'móvil'
    return 'escritorio'


def _navegador(ua):
    for patron, nombre in (('Edg/', 'Edge'), ('OPR/', 'Opera'), ('Chrome/', 'Chrome'),
                           ('Firefox/', 'Firefox'), ('Safari/', 'Safari')):
        if patron in ua:
            # Chrome aparece dentro del UA de Edge y Opera, por eso el orden.
            return nombre
    return 'otro'


def _sistema(ua):
    for patron, nombre in (('Android', 'Android'), ('iPhone', 'iOS'), ('iPad', 'iPadOS'),
                           ('Mac OS X', 'macOS'), ('Windows', 'Windows'),
                           ('CrOS', 'ChromeOS'), ('Linux', 'Linux')):
        if patron in ua:
            return nombre
    return 'otro'


def _idioma():
    cab = request.headers.get('Accept-Language', '')
    if not cab:
        return 'desconocido'
    return cab.split(',')[0].split('-')[0].lower()[:5] or 'desconocido'


def _pais():
    """Cloudflare (Roadmap #16) inyecta CF-IPCountry. Sin proxy delante no hay
    geolocalización: NO metemos una base GeoIP ni llamamos a un servicio externo
    (sería ceder la IP a un tercero, justo lo que este diseño evita)."""
    for cab in ('CF-IPCountry', 'X-Country-Code'):
        v = request.headers.get(cab)
        if v and v not in ('XX', 'T1'):
            return v.upper()[:2]
    return 'desconocido'


def _fuente():
    """(fuente, medio, campaña) a partir del referer y los utm_*."""
    args = request.args
    utm_source = (args.get('utm_source') or '').strip()[:60]
    utm_medium = (args.get('utm_medium') or '').strip()[:40]
    campana = (args.get('utm_campaign') or '').strip()[:60] or None

    if utm_source:
        return utm_source.lower(), (utm_medium.lower() or 'campaña'), campana

    ref = request.referrer or ''
    if not ref:
        return 'directo', 'directo', campana
    try:
        dominio = ref.split('//', 1)[-1].split('/', 1)[0].lower()
    except Exception:
        return 'directo', 'directo', campana
    dominio = dominio.split(':')[0]
    if dominio.startswith('www.'):
        dominio = dominio[4:]
    propio = (request.host or '').split(':')[0].lower()
    if propio.startswith('www.'):
        propio = propio[4:]
    if not dominio or dominio == propio:
        return 'directo', 'directo', campana
    medio = 'orgánico' if any(b in dominio for b in _BUSCADORES) else 'referencia'
    return dominio[:60], medio, campana


# ==========================================================================
# Ciclo de vida de una visita
# ==========================================================================

def _nueva_sesion(clave, ahora):
    ua = request.headers.get('User-Agent', '')
    fuente, medio, campana = _fuente()
    username = session.get('username')
    fila = {
        'id': None,
        'visitante': clave,
        'dia': _hoy(),
        'inicio': ahora,
        'fin': ahora,
        'activo': 0,
        'vistas': 0,
        'eventos': 0,
        'user_id': None,
        'username': username,
        'logueado': 1 if username else 0,
        'registro': 0,
        'login': 0,
        'interactuo': 0,
        'jugo': 0,
        'partidas': 0,
        'partidas_fin': 0,
        'segundos_juego': 0,
        'modos': set(),
        'pais': _pais(),
        'idioma': _idioma(),
        'dispositivo': _dispositivo(ua),
        'navegador': _navegador(ua),
        'so': _sistema(ua),
        'fuente': fuente,
        'medio': medio,
        'campana': campana,
        'landing': (request.path or '/')[:80],
        'baraja': None,
        'trafico_bot': 1 if _RE_BOT.search(ua) else 0,
        'kofi': 0,
        'kofi_clics': 0,
        'sucia': True,
    }
    if username:
        fila['user_id'] = _id_de(username)
    return fila


def _id_de(username):
    if not username:
        return None
    try:
        return base_datos.obtener_id_usuario(username)
    except Exception:
        return None


def _sesion_actual(crear=True):
    """La visita viva del que hace esta petición. Devuelve None fuera de un
    contexto de petición (tareas de fondo)."""
    try:
        clave = _clave_visitante()
    except Exception:
        return None
    ahora = time.time()
    with _lock:
        s = _sesiones.get(clave)
        if s and (ahora - s['fin'] > INACTIVIDAD_SESION or s['dia'] != _hoy()):
            _cerrar(clave, s)
            s = None
        if s is None:
            if not crear:
                return None
            s = _nueva_sesion(clave, ahora)
            _sesiones[clave] = s
        s['fin'] = ahora
        s['sucia'] = True
        # La sesión pudo iniciarse como invitada y luego entrar con cuenta.
        try:
            u = session.get('username')
        except Exception:
            u = None
        if u and s['username'] != u:
            s['username'] = u
            s['user_id'] = _id_de(u)
            s['logueado'] = 1
        return s


def _sesion_de_usuario(username):
    """Visita viva de una cuenta, para eventos que llegan sin contexto de
    petición (tareas de fondo del motor)."""
    if not username:
        return None
    with _lock:
        candidatas = [s for s in _sesiones.values() if s.get('username') == username]
    return max(candidatas, key=lambda s: s['fin']) if candidatas else None


def _cerrar(clave, s):
    """Saca la visita de memoria dejándola marcada para el volcado final."""
    _sesiones.pop(clave, None)
    _pendientes_cierre.append(s)


# ==========================================================================
# API pública del módulo (lo que llaman server.py y server_mus4.py)
# ==========================================================================

def evento(tipo, etiqueta=None, valor=None, username=None, modo=None,
           por_usuario=False):
    """Registra un evento. NUNCA lanza: la analítica no puede tumbar una mano.

    Se puede llamar dentro de una petición HTTP, dentro de un manejador de
    Socket.IO (Flask-SocketIO da contexto de petición) o desde una tarea de
    fondo — en ese último caso hay que pasar `username` para poder atribuirlo.

    `por_usuario=True` IGNORA el contexto de la petición y busca la visita de
    esa cuenta. Es lo que hay que usar cuando un jugador provoca un evento que
    le pasa a OTRO (el que se une a una sala arranca también la partida del que
    la creó): sin esto, las dos partidas se le apuntarían al que pulsó.
    """
    try:
        _evento_interno(tipo, etiqueta, valor, username, modo, por_usuario)
    except Exception as e:      # pragma: no cover - defensivo a propósito
        print(f"⚠️ analítica: evento {tipo} descartado ({e})")


def _evento_interno(tipo, etiqueta, valor, username, modo, por_usuario=False):
    if por_usuario:
        s = _sesion_de_usuario(username)
    else:
        s = _sesion_actual(crear=(tipo == 'pagina'))
        if s is None and username:
            s = _sesion_de_usuario(username)

    ahora = time.time()
    if s is not None:
        s['fin'] = ahora
        s['sucia'] = True
        s['eventos'] += 1
        if tipo != 'pagina':
            s['interactuo'] = 1
        if tipo == 'pagina':
            s['vistas'] += 1
        elif tipo == 'partida_inicio':
            s['jugo'] = 1
            s['partidas'] += 1
            if modo:
                s['modos'].add(modo)
        elif tipo == 'partida_fin':
            s['partidas_fin'] += 1
            s['segundos_juego'] += int(valor or 0)
            if modo:
                s['modos'].add(modo)
        elif tipo == 'partida_abandono':
            s['segundos_juego'] += int(valor or 0)
        elif tipo == 'registro':
            s['registro'] = 1
            s['logueado'] = 1
        elif tipo == 'login':
            s['login'] = 1
            s['logueado'] = 1
        elif tipo == 'baraja' and etiqueta:
            s['baraja'] = etiqueta[:40]
        elif tipo == 'kofi':
            s['kofi'] = 1
            s['kofi_clics'] += 1
        if username and not s.get('username'):
            s['username'] = username
            s['user_id'] = _id_de(username)

    if tipo == 'kofi':
        # La etiqueta la pone el servidor, no el cliente (el endpoint es
        # público): dice si el clic llegó antes o después de jugar, que es lo
        # que de verdad interesa saber de un botón de apoyo.
        etiqueta = 'tras jugar' if (s and s['jugo']) else 'sin jugar'

    etiqueta_final = etiqueta or modo
    _eventos_pend.append({
        'sesion': s,
        'dia': _hoy(),
        'ts': ahora,
        'tipo': tipo[:40],
        'etiqueta': (etiqueta_final or None) and str(etiqueta_final)[:60],
        'valor': float(valor) if valor is not None else None,
        'user_id': (s or {}).get('user_id') or _id_de(username),
    })


def pagina(ruta=None):
    """Una carga de página. La llama el before_request."""
    evento('pagina', etiqueta=ruta)


# ==========================================================================
# Volcado a disco
# ==========================================================================

_COLUMNAS = ('visitante', 'dia', 'inicio', 'fin', 'activo', 'vistas', 'eventos',
             'user_id', 'username', 'logueado', 'registro', 'login', 'interactuo',
             'jugo', 'partidas', 'partidas_fin', 'segundos_juego', 'modos', 'pais',
             'idioma', 'dispositivo', 'navegador', 'so', 'fuente', 'medio',
             'campana', 'landing', 'baraja', 'trafico_bot', 'kofi', 'kofi_clics')


def _valores(s):
    return tuple(
        ','.join(sorted(s['modos'])) if col == 'modos' else s[col]
        for col in _COLUMNAS)


def volcar():
    """Escribe en analitica.db lo acumulado. Lo llama el greenlet cada 5 s."""
    with _lock:
        sucias = [s for s in _sesiones.values() if s.get('sucia')]
        cerradas = _pendientes_cierre[:]
        del _pendientes_cierre[:]
        eventos = _eventos_pend[:]
        del _eventos_pend[:]
        for s in sucias:
            s['sucia'] = False

    if not (sucias or cerradas or eventos):
        return

    with _conn() as c:
        for s in sucias + cerradas:
            if s['id'] is None:
                cur = c.execute(
                    "INSERT INTO Sesiones (%s) VALUES (%s)"
                    % (','.join(_COLUMNAS), ','.join('?' * len(_COLUMNAS))),
                    _valores(s))
                s['id'] = cur.lastrowid
            else:
                c.execute(
                    "UPDATE Sesiones SET %s WHERE id = ?"
                    % ','.join(col + '=?' for col in _COLUMNAS),
                    _valores(s) + (s['id'],))
        for e in eventos:
            ses = e.pop('sesion', None)
            c.execute("INSERT INTO Eventos (sesion_id, dia, ts, tipo, etiqueta, valor, user_id)"
                      " VALUES (?,?,?,?,?,?,?)",
                      ((ses or {}).get('id'), e['dia'], e['ts'], e['tipo'],
                       e['etiqueta'], e['valor'], e['user_id']))


def _barrer_inactivas():
    ahora = time.time()
    hoy = _hoy()
    with _lock:
        muertas = [(k, s) for k, s in _sesiones.items()
                   if ahora - s['fin'] > INACTIVIDAD_SESION or s['dia'] != hoy]
        for k, s in muertas:
            _cerrar(k, s)


# ==========================================================================
# Consolidación diaria y purga
# ==========================================================================

_DIMENSIONES_SESION = {
    'fuente': 'fuente', 'medio': 'medio', 'campana': 'campana', 'pais': 'pais',
    'idioma': 'idioma', 'dispositivo': 'dispositivo', 'navegador': 'navegador',
    'so': 'so', 'landing': 'landing', 'baraja': 'baraja',
}


def consolidar(dia):
    """Recalcula los agregados de un día a partir del crudo. Idempotente: borra
    y reescribe, así que se puede repetir tantas veces como haga falta (el día
    en curso se recalcula en cada consulta del panel)."""
    with _conn() as c:
        filas = [dict(r) for r in c.execute(
            "SELECT * FROM Sesiones WHERE dia = ? AND trafico_bot = 0", (dia,))]
        if not filas and dia != _hoy():
            return

        total = {
            'visitas': len(filas),
            'visitantes': len({f['visitante'] for f in filas}),
            'duracion_total': sum(int(f['fin'] - f['inicio']) for f in filas),
            'activo_total': sum(f['activo'] or 0 for f in filas),
            'rebotes': sum(1 for f in filas if not f['interactuo']),
            'interactuaron': sum(1 for f in filas if f['interactuo']),
            'jugaron': sum(1 for f in filas if f['jugo']),
            'partidas': sum(f['partidas'] or 0 for f in filas),
            'partidas_fin': sum(f['partidas_fin'] or 0 for f in filas),
            'segundos_juego': sum(f['segundos_juego'] or 0 for f in filas),
            'registros': sum(f['registro'] or 0 for f in filas),
            'logins': sum(f['login'] or 0 for f in filas),
            'visitas_cuenta': sum(1 for f in filas if f['logueado']),
            'cuentas': len({f['user_id'] for f in filas if f['user_id']}),
            'kofi': sum(1 for f in filas if f['kofi']),
            'kofi_clics': sum(f['kofi_clics'] or 0 for f in filas),
        }
        columnas = list(total.keys())
        c.execute("DELETE FROM Dia WHERE dia = ?", (dia,))
        c.execute("INSERT INTO Dia (dia,%s,consolidado) VALUES (?,%s,?)"
                  % (','.join(columnas), ','.join('?' * len(columnas))),
                  (dia,) + tuple(total[k] for k in columnas) + (time.time(),))

        # --- por dimensión -------------------------------------------------
        acc = {}

        def suma(dim, valor, f):
            if not valor:
                valor = 'desconocido'
            k = (dim, str(valor)[:60])
            d = acc.setdefault(k, dict(visitas=0, duracion_total=0, activo_total=0,
                                       rebotes=0, jugaron=0, partidas=0, registros=0,
                                       kofi=0))
            d['visitas'] += 1
            d['duracion_total'] += int(f['fin'] - f['inicio'])
            d['activo_total'] += f['activo'] or 0
            d['rebotes'] += 0 if f['interactuo'] else 1
            d['jugaron'] += 1 if f['jugo'] else 0
            d['partidas'] += f['partidas'] or 0
            d['registros'] += f['registro'] or 0
            d['kofi'] += 1 if f['kofi'] else 0

        for f in filas:
            for dim, col in _DIMENSIONES_SESION.items():
                suma(dim, f[col], f)
            # `modos` es multivalor: una visita puede jugar contra el bot y online.
            for m in (f['modos'] or '').split(','):
                if m:
                    suma('modo', m, f)

        # Los eventos del día entran como una dimensión más, para el desglose
        # "qué hace la gente" sin tener que consultar la tabla cruda.
        for r in c.execute("SELECT tipo, COUNT(*) n FROM Eventos WHERE dia = ? GROUP BY tipo", (dia,)):
            k = ('evento', r['tipo'])
            acc.setdefault(k, dict(visitas=0, duracion_total=0, activo_total=0,
                                   rebotes=0, jugaron=0, partidas=0, registros=0,
                                   kofi=0))
            acc[k]['visitas'] = r['n']

        # Ko-fi como dimensión propia: el clic se etiqueta en el servidor con
        # «tras jugar» / «sin jugar», que es lo que dice si la gente apoya el
        # proyecto después de haberlo probado o solo de pasada.
        for r in c.execute("SELECT COALESCE(etiqueta,'desconocido') e, COUNT(*) n "
                           "FROM Eventos WHERE dia = ? AND tipo = 'kofi' GROUP BY e", (dia,)):
            k = ('kofi', r['e'])
            acc.setdefault(k, dict(visitas=0, duracion_total=0, activo_total=0,
                                   rebotes=0, jugaron=0, partidas=0, registros=0,
                                   kofi=0))
            acc[k]['visitas'] = r['n']
            acc[k]['kofi'] = r['n']

        c.execute("DELETE FROM DiaDim WHERE dia = ?", (dia,))
        c.executemany(
            "INSERT INTO DiaDim (dia,dimension,valor,visitas,duracion_total,activo_total,"
            "rebotes,jugaron,partidas,registros,kofi) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            [(dia, dim, val, d['visitas'], d['duracion_total'], d['activo_total'],
              d['rebotes'], d['jugaron'], d['partidas'], d['registros'], d['kofi'])
             for (dim, val), d in acc.items()])

        # --- por cuenta ----------------------------------------------------
        por_usuario = {}
        for f in filas:
            if not f['user_id']:
                continue
            d = por_usuario.setdefault(f['user_id'], dict(
                username=f['username'], visitas=0, duracion_total=0, activo_total=0,
                partidas=0, partidas_fin=0, segundos_juego=0, kofi=0))
            d['username'] = f['username'] or d['username']
            d['visitas'] += 1
            d['duracion_total'] += int(f['fin'] - f['inicio'])
            d['activo_total'] += f['activo'] or 0
            d['partidas'] += f['partidas'] or 0
            d['partidas_fin'] += f['partidas_fin'] or 0
            d['segundos_juego'] += f['segundos_juego'] or 0
            d['kofi'] += f['kofi_clics'] or 0
        c.execute("DELETE FROM DiaUsuario WHERE dia = ?", (dia,))
        c.executemany(
            "INSERT INTO DiaUsuario (dia,user_id,username,visitas,duracion_total,"
            "activo_total,partidas,partidas_fin,segundos_juego,kofi) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            [(dia, uid, d['username'], d['visitas'], d['duracion_total'], d['activo_total'],
              d['partidas'], d['partidas_fin'], d['segundos_juego'], d['kofi'])
             for uid, d in por_usuario.items()])


def consolidar_pendientes():
    """Consolida los días con crudo que aún no tienen agregado (o que lo tienen
    de antes de la última fila escrita). Barato: solo mira días sin consolidar."""
    with _conn() as c:
        dias = [r['dia'] for r in c.execute(
            "SELECT DISTINCT s.dia FROM Sesiones s LEFT JOIN Dia d ON d.dia = s.dia "
            "WHERE d.dia IS NULL OR d.consolidado < s.fin")]
    for dia in dias:
        consolidar(dia)


def purgar():
    """Borra el crudo más viejo que DIAS_CRUDOS. Los agregados no se tocan: son
    los que sostienen las series largas del panel."""
    limite = (date.today() - timedelta(days=DIAS_CRUDOS)).isoformat()
    with _conn() as c:
        n1 = c.execute("DELETE FROM Sesiones WHERE dia < ?", (limite,)).rowcount
        n2 = c.execute("DELETE FROM Eventos WHERE dia < ?", (limite,)).rowcount
    if n1 or n2:
        print(f"🧹 Analítica: purgadas {n1} visitas y {n2} eventos anteriores a {limite}.")


# ==========================================================================
# Consultas para el panel
# ==========================================================================

def _rango(desde, hasta):
    hoy = _hoy()
    hasta = hasta or hoy
    desde = desde or (date.fromisoformat(hasta) - timedelta(days=27)).isoformat()
    if desde > hasta:
        desde, hasta = hasta, desde
    return desde, hasta


def _asegurar_dia_vivo(desde, hasta):
    """El día en curso solo existe en crudo/memoria: se vuelca y se consolida
    antes de responder para que el panel enseñe lo de hace 5 segundos."""
    hoy = _hoy()
    if desde <= hoy <= hasta:
        volcar()
        consolidar(hoy)


def resumen(desde, hasta):
    desde, hasta = _rango(desde, hasta)
    _asegurar_dia_vivo(desde, hasta)
    with _conn() as c:
        filas = [dict(r) for r in c.execute(
            "SELECT * FROM Dia WHERE dia BETWEEN ? AND ? ORDER BY dia", (desde, hasta))]

    campos = ('visitas', 'duracion_total', 'activo_total', 'rebotes', 'interactuaron',
              'jugaron', 'partidas', 'partidas_fin', 'segundos_juego', 'registros',
              'logins', 'visitas_cuenta', 'kofi', 'kofi_clics')
    tot = {k: sum(f[k] or 0 for f in filas) for k in campos}
    # Los visitantes únicos no se pueden sumar entre días (el hash rota cada
    # día): lo que se enseña es la suma de únicos diarios, y se dice.
    tot['visitantes'] = sum(f['visitantes'] or 0 for f in filas)
    tot['cuentas'] = _cuentas_unicas(desde, hasta)
    tot['dias'] = len(filas)
    tot['duracion_media'] = round(tot['duracion_total'] / tot['visitas'], 1) if tot['visitas'] else 0
    tot['activo_medio'] = round(tot['activo_total'] / tot['visitas'], 1) if tot['visitas'] else 0
    tot['tasa_rebote'] = round(100.0 * tot['rebotes'] / tot['visitas'], 1) if tot['visitas'] else 0
    tot['tasa_juego'] = round(100.0 * tot['jugaron'] / tot['visitas'], 1) if tot['visitas'] else 0
    tot['tasa_alta'] = round(100.0 * tot['registros'] / tot['visitas'], 2) if tot['visitas'] else 0
    tot['partidas_por_jugador'] = round(tot['partidas'] / tot['jugaron'], 2) if tot['jugaron'] else 0
    # CTR del botón de Ko-fi: visitas que lo pulsaron sobre el total de visitas.
    tot['tasa_kofi'] = round(100.0 * tot['kofi'] / tot['visitas'], 2) if tot['visitas'] else 0
    tot['kofi_por_jugador'] = (round(100.0 * tot['kofi'] / tot['jugaron'], 2)
                               if tot['jugaron'] else 0)

    serie = [{'dia': f['dia'],
              'visitas': f['visitas'], 'visitantes': f['visitantes'],
              'jugaron': f['jugaron'], 'partidas': f['partidas'],
              'registros': f['registros'], 'logins': f['logins'],
              'kofi': f['kofi'] or 0, 'kofi_clics': f['kofi_clics'] or 0,
              'activo_medio': round((f['activo_total'] or 0) / f['visitas'], 1) if f['visitas'] else 0,
              'tasa_juego': round(100.0 * f['jugaron'] / f['visitas'], 1) if f['visitas'] else 0}
             for f in filas]
    # Días sin una sola visita no tienen fila; el gráfico necesita el hueco a 0.
    serie = _rellenar_huecos(serie, desde, hasta)
    return {'desde': desde, 'hasta': hasta, 'totales': tot, 'serie': serie}


def _rellenar_huecos(serie, desde, hasta):
    porfecha = {f['dia']: f for f in serie}
    salida, d, fin = [], date.fromisoformat(desde), date.fromisoformat(hasta)
    while d <= fin:
        k = d.isoformat()
        salida.append(porfecha.get(k, {'dia': k, 'visitas': 0, 'visitantes': 0,
                                       'jugaron': 0, 'partidas': 0, 'registros': 0,
                                       'logins': 0, 'kofi': 0, 'kofi_clics': 0,
                                       'activo_medio': 0, 'tasa_juego': 0}))
        d += timedelta(days=1)
    return salida


def _cuentas_unicas(desde, hasta):
    with _conn() as c:
        r = c.execute("SELECT COUNT(DISTINCT user_id) n FROM DiaUsuario "
                      "WHERE dia BETWEEN ? AND ?", (desde, hasta)).fetchone()
    return r['n'] if r else 0


def periodo_anterior(desde, hasta):
    d0, d1 = date.fromisoformat(desde), date.fromisoformat(hasta)
    dias = (d1 - d0).days + 1
    return (d0 - timedelta(days=dias)).isoformat(), (d0 - timedelta(days=1)).isoformat()


def dimension(dim, desde, hasta, limite=40):
    desde, hasta = _rango(desde, hasta)
    _asegurar_dia_vivo(desde, hasta)
    with _conn() as c:
        filas = [dict(r) for r in c.execute(
            "SELECT valor, SUM(visitas) visitas, SUM(duracion_total) duracion_total, "
            "SUM(activo_total) activo_total, SUM(rebotes) rebotes, SUM(jugaron) jugaron, "
            "SUM(partidas) partidas, SUM(registros) registros, SUM(kofi) kofi "
            "FROM DiaDim WHERE dimension = ? AND dia BETWEEN ? AND ? "
            "GROUP BY valor ORDER BY visitas DESC LIMIT ?",
            (dim, desde, hasta, limite))]
    for f in filas:
        v = f['visitas'] or 0
        f['activo_medio'] = round((f['activo_total'] or 0) / v, 1) if v else 0
        f['tasa_rebote'] = round(100.0 * (f['rebotes'] or 0) / v, 1) if v else 0
        f['tasa_juego'] = round(100.0 * (f['jugaron'] or 0) / v, 1) if v else 0
        f['tasa_kofi'] = round(100.0 * (f['kofi'] or 0) / v, 2) if v else 0
    return filas


def embudo(desde, hasta):
    """El camino completo: llega → hace algo → juega → termina una partida →
    acaba con cuenta. Es la lectura de 'cuánta gente entra y de verdad juega'."""
    r = resumen(desde, hasta)['totales']
    pasos = [
        ('Visitas', r['visitas']),
        ('Interactúan', r['interactuaron']),
        ('Empiezan partida', r['jugaron']),
        ('Terminan partida', r['partidas_fin']),
        ('Con cuenta', r['visitas_cuenta']),
        ('Se registran', r['registros']),
    ]
    base = pasos[0][1] or 1
    salida, previo = [], pasos[0][1] or 1
    for nombre, n in pasos:
        salida.append({'paso': nombre, 'n': n,
                       'pct_total': round(100.0 * n / base, 1),
                       'pct_previo': round(100.0 * n / previo, 1) if previo else 0})
        previo = n or previo
    return salida


def usuarios(desde, hasta, orden='activo_total', limite=100, busca=''):
    desde, hasta = _rango(desde, hasta)
    _asegurar_dia_vivo(desde, hasta)
    ordenes = {'visitas', 'duracion_total', 'activo_total', 'partidas',
               'partidas_fin', 'segundos_juego', 'dias', 'ultima', 'kofi'}
    if orden not in ordenes:
        orden = 'activo_total'
    with _conn() as c:
        filas = [dict(r) for r in c.execute(
            "SELECT user_id, MAX(username) username, COUNT(DISTINCT dia) dias, "
            "MAX(dia) ultima, SUM(visitas) visitas, SUM(duracion_total) duracion_total, "
            "SUM(activo_total) activo_total, SUM(partidas) partidas, "
            "SUM(partidas_fin) partidas_fin, SUM(segundos_juego) segundos_juego, "
            "SUM(kofi) kofi "
            "FROM DiaUsuario WHERE dia BETWEEN ? AND ? GROUP BY user_id "
            "ORDER BY %s DESC LIMIT ?" % orden, (desde, hasta, limite))]
    if busca:
        b = busca.lower()
        filas = [f for f in filas if b in (f['username'] or '').lower()]
    for f in filas:
        f['activo_medio'] = round((f['activo_total'] or 0) / f['visitas'], 1) if f['visitas'] else 0
    return filas


def detalle_usuario(user_id, dias=90):
    """Serie diaria de una cuenta concreta, para el desplegable del panel."""
    desde = (date.today() - timedelta(days=dias)).isoformat()
    with _conn() as c:
        serie = [dict(r) for r in c.execute(
            "SELECT dia, visitas, duracion_total, activo_total, partidas, partidas_fin, "
            "segundos_juego, kofi FROM DiaUsuario WHERE user_id = ? AND dia >= ? ORDER BY dia",
            (user_id, desde))]
        eventos = [dict(r) for r in c.execute(
            "SELECT tipo, COUNT(*) n FROM Eventos WHERE user_id = ? AND dia >= ? "
            "GROUP BY tipo ORDER BY n DESC LIMIT 20", (user_id, desde))]
    return {'serie': serie, 'eventos': eventos}


def retencion(semanas=8):
    """Cohortes por semana de alta: de las cuentas creadas la semana W, cuántas
    tuvieron actividad en W+0, W+1, … Solo cuentas: un invitado no es seguible
    entre días por diseño (ver la cabecera del módulo)."""
    inicio = date.today() - timedelta(weeks=semanas)
    # Altas por semana desde mus.db.
    cohortes = {}
    try:
        with base_datos._conn() as c:
            for r in c.execute("SELECT id, fecha_registro FROM Usuarios "
                               "WHERE fecha_registro IS NOT NULL AND fecha_registro >= ?",
                               (inicio.isoformat(),)):
                try:
                    d = date.fromisoformat((r['fecha_registro'] or '')[:10])
                except ValueError:
                    continue
                cohortes.setdefault(_lunes(d), set()).add(r['id'])
    except Exception as e:
        print(f"⚠️ analítica: no se pudieron leer las altas ({e})")
        return []

    if not cohortes:
        return []
    # Tope de variables de SQLite: con cohortes de semanas recientes no se llega
    # ni de lejos, pero un pico de altas no puede reventar la consulta.
    ids = sorted({i for s in cohortes.values() for i in s})[:900]
    actividad = {}
    with _conn() as c:
        marcas = ','.join('?' * len(ids))
        for r in c.execute("SELECT DISTINCT user_id, dia FROM DiaUsuario "
                           "WHERE user_id IN (%s) AND dia >= ?" % marcas,
                           tuple(ids) + (inicio.isoformat(),)):
            try:
                actividad.setdefault(r['user_id'], set()).add(_lunes(date.fromisoformat(r['dia'])))
            except ValueError:
                continue

    salida = []
    for semana in sorted(cohortes, reverse=True):
        miembros = cohortes[semana]
        fila = {'cohorte': semana.isoformat(), 'altas': len(miembros), 'semanas': []}
        for k in range(semanas + 1):
            objetivo = semana + timedelta(weeks=k)
            if objetivo > _lunes(date.today()):
                break
            n = sum(1 for uid in miembros if objetivo in actividad.get(uid, ()))
            fila['semanas'].append({'k': k, 'n': n,
                                    'pct': round(100.0 * n / len(miembros), 1) if miembros else 0})
        salida.append(fila)
    return salida


def _lunes(d):
    return d - timedelta(days=d.weekday())


def en_vivo():
    """Lo que está pasando ahora mismo, leído de memoria (sin tocar disco)."""
    ahora = time.time()
    with _lock:
        vivas = [s for s in _sesiones.values()
                 if ahora - s['fin'] <= VENTANA_EN_VIVO and not s['trafico_bot']]
        detalle = [{
            'username': s['username'],
            'minutos': round((ahora - s['inicio']) / 60, 1),
            'pais': s['pais'], 'dispositivo': s['dispositivo'],
            'fuente': s['fuente'], 'jugo': bool(s['jugo']),
            'partidas': s['partidas'],
            'kofi': bool(s['kofi']),
            'inactivo': int(ahora - s['fin']),
        } for s in sorted(vivas, key=lambda x: -x['fin'])[:60]]
    return {'visitas': len(vivas),
            'con_cuenta': sum(1 for d in detalle if d['username']),
            'jugando': sum(1 for d in detalle if d['jugo']),
            'kofi': sum(1 for d in detalle if d['kofi']),
            'detalle': detalle}


def csv_dias(desde, hasta):
    desde, hasta = _rango(desde, hasta)
    _asegurar_dia_vivo(desde, hasta)
    cols = ('dia', 'visitas', 'visitantes', 'duracion_total', 'activo_total', 'rebotes',
            'interactuaron', 'jugaron', 'partidas', 'partidas_fin', 'segundos_juego',
            'registros', 'logins', 'visitas_cuenta', 'cuentas', 'kofi', 'kofi_clics')
    lineas = [';'.join(cols)]
    with _conn() as c:
        for r in c.execute("SELECT * FROM Dia WHERE dia BETWEEN ? AND ? ORDER BY dia",
                           (desde, hasta)):
            lineas.append(';'.join(str(r[k] if r[k] is not None else '') for k in cols))
    return '\n'.join(lineas) + '\n'


def borrar_todo():
    """Vacía la analítica. Existe porque un panel que recoge datos de uso debe
    poder tirarlos: es la herramienta del 'derecho al olvido' a lo bruto."""
    with _lock:
        _sesiones.clear()
        del _pendientes_cierre[:]
        del _eventos_pend[:]
    with _conn() as c:
        for t in ('Sesiones', 'Eventos', 'Dia', 'DiaDim', 'DiaUsuario'):
            c.execute("DELETE FROM " + t)
    return True


def olvidar_usuario(user_id):
    """Desliga a una cuenta de todo su rastro de analítica (lo llama el borrado
    de cuenta). Las visitas siguen contando en los totales, pero anónimas."""
    if not user_id:
        return 0
    with _lock:
        for s in _sesiones.values():
            if s.get('user_id') == user_id:
                s['user_id'] = None
                s['username'] = None
                s['sucia'] = True
    with _conn() as c:
        n = c.execute("UPDATE Sesiones SET user_id=NULL, username=NULL WHERE user_id=?",
                      (user_id,)).rowcount
        c.execute("UPDATE Eventos SET user_id=NULL WHERE user_id=?", (user_id,))
        c.execute("DELETE FROM DiaUsuario WHERE user_id=?", (user_id,))
    return n


# ==========================================================================
# Tareas de fondo
# ==========================================================================

def _bucle_volcado():
    while True:
        _socketio.sleep(INTERVALO_VOLCADO)
        try:
            _barrer_inactivas()
            volcar()
        except Exception as e:
            print(f"⚠️ analítica: fallo volcando ({e})")


def _bucle_mantenimiento():
    while True:
        try:
            consolidar_pendientes()
            purgar()
        except Exception as e:
            print(f"⚠️ analítica: fallo en mantenimiento ({e})")
        _socketio.sleep(INTERVALO_MANTENIMIENTO)


# ==========================================================================
# Registro de rutas
# ==========================================================================

# Rutas que no cuentan como visita: estáticos, la propia analítica, el panel y
# el sondeo del socket (que dispara decenas de peticiones por minuto).
_IGNORAR = ('/static/', '/socket.io/', '/api/a/', '/admin', '/favicon')


def init_analitica(app, socketio, ctx):
    global _socketio, _ctx, _arrancado
    _socketio = socketio
    _ctx = ctx or {}
    init_db()

    admin_requerido = _ctx.get('admin_requerido') or (lambda f: f)

    # ----------------------------------------------------------------------
    # 1. Recogida
    # ----------------------------------------------------------------------

    @app.before_request
    def _contar_visita():
        ruta = request.path or '/'
        if request.method != 'GET' or any(ruta.startswith(p) for p in _IGNORAR):
            return
        # Solo páginas: una petición de la API no es una visita.
        if ruta != '/' and not ruta.endswith('.html'):
            return
        pagina(ruta)

    @app.route('/api/a/latido', methods=['POST'])
    def a_latido():
        """El cliente late cada 30 s mientras la pestaña está visible, y manda un
        último latido con sendBeacon al cerrar. De aquí sale el tiempo de
        permanencia real (sin contar pestañas abiertas y olvidadas)."""
        datos = request.get_json(silent=True) or {}
        try:
            activo = int(datos.get('activo') or 0)
        except (TypeError, ValueError):
            activo = 0
        activo = max(0, min(activo, 120))       # tope: nadie suma minutos de golpe
        s = _sesion_actual(crear=False)
        if s is not None:
            with _lock:
                s['activo'] += activo
                s['fin'] = time.time()
                s['sucia'] = True
        return ('', 204)

    @app.route('/api/a/evento', methods=['POST'])
    def a_evento():
        datos = request.get_json(silent=True) or {}
        tipo = str(datos.get('tipo') or '')[:40]
        if tipo not in EVENTOS_CLIENTE:
            return ('', 204)
        s = _sesion_actual(crear=False)
        if s is None:
            return ('', 204)
        # Tope por visita: un cliente manipulado no puede inflar el histograma.
        if s['eventos'] > 400:
            return ('', 204)
        evento(tipo, etiqueta=str(datos.get('etiqueta') or '')[:60] or None)
        return ('', 204)

    # ----------------------------------------------------------------------
    # 2. Panel (todo detrás de admin_requerido)
    # ----------------------------------------------------------------------

    def _fechas():
        return _rango(request.args.get('desde'), request.args.get('hasta'))

    @app.route('/admin/api/analitica/resumen', methods=['GET'])
    @admin_requerido
    def an_resumen():
        desde, hasta = _fechas()
        actual = resumen(desde, hasta)
        pd, ph = periodo_anterior(desde, hasta)
        previo = resumen(pd, ph)
        return jsonify({'exito': True, 'actual': actual,
                        'previo': {'desde': pd, 'hasta': ph, 'totales': previo['totales']},
                        'embudo': embudo(desde, hasta),
                        'retencion_dias': DIAS_CRUDOS})

    @app.route('/admin/api/analitica/dimension', methods=['GET'])
    @admin_requerido
    def an_dimension():
        desde, hasta = _fechas()
        dim = request.args.get('dim', 'fuente')
        if dim not in set(_DIMENSIONES_SESION) | {'modo', 'evento', 'kofi'}:
            return jsonify({'exito': False, 'mensaje': 'dimension_desconocida'}), 400
        return jsonify({'exito': True, 'dim': dim,
                        'filas': dimension(dim, desde, hasta,
                                           limite=request.args.get('limite', 40, type=int))})

    @app.route('/admin/api/analitica/usuarios', methods=['GET'])
    @admin_requerido
    def an_usuarios():
        desde, hasta = _fechas()
        return jsonify({'exito': True, 'usuarios': usuarios(
            desde, hasta,
            orden=request.args.get('orden', 'activo_total'),
            limite=request.args.get('limite', 100, type=int),
            busca=request.args.get('q', ''))})

    @app.route('/admin/api/analitica/usuarios/<int:user_id>', methods=['GET'])
    @admin_requerido
    def an_usuario(user_id):
        return jsonify({'exito': True, 'detalle': detalle_usuario(user_id)})

    @app.route('/admin/api/analitica/retencion', methods=['GET'])
    @admin_requerido
    def an_retencion():
        return jsonify({'exito': True,
                        'cohortes': retencion(request.args.get('semanas', 8, type=int))})

    @app.route('/admin/api/analitica/en_vivo', methods=['GET'])
    @admin_requerido
    def an_en_vivo():
        return jsonify({'exito': True, 'vivo': en_vivo()})

    @app.route('/admin/api/analitica/csv', methods=['GET'])
    @admin_requerido
    def an_csv():
        desde, hasta = _fechas()
        return Response(
            csv_dias(desde, hasta), mimetype='text/csv',
            headers={'Content-Disposition':
                     f'attachment; filename=callmus_analitica_{desde}_{hasta}.csv'})

    @app.route('/admin/api/analitica/borrar', methods=['POST'])
    @admin_requerido
    def an_borrar():
        borrar_todo()
        auditar = _ctx.get('auditar')
        if auditar:
            auditar('analitica_borrada', None, None)
        return jsonify({'exito': True})

    # ----------------------------------------------------------------------
    # 3. Arranque
    # ----------------------------------------------------------------------
    if not _arrancado:
        _arrancado = True
        socketio.start_background_task(_bucle_volcado)
        socketio.start_background_task(_bucle_mantenimiento)
        print(f"📈 Analítica activa ({DB_ANALITICA}, crudo {DIAS_CRUDOS} días, sin cookies).")

# ==========================================================================
# sistema.py — Salud de la máquina (pestaña «Servidor» del panel)
# --------------------------------------------------------------------------
# CallMus vive en una e2-micro del nivel gratuito de Google Cloud: 1 GB de RAM,
# núcleo compartido y ~15 GB de disco. Con ese margen, «se ha caído el servidor»
# casi siempre es una de cuatro cosas, y ninguna se ve desde el juego:
#
#   1. La RAM se agota  -> el kernel mata el proceso y se pierden TODAS las
#      salas, que viven solo en memoria (ver Architecture.md).
#   2. El swap empieza a trabajar de verdad -> el proceso no muere, pero cada
#      fallo de página congela el ÚNICO hilo de eventlet, o sea todas las
#      partidas a la vez.
#   3. El disco se llena -> SQLite deja de poder escribir.
#   4. El egreso de red se pasa del gigabyte mensual gratuito -> llega factura.
#
# Este módulo muestrea esas cuatro cosas cada minuto, guarda 24 h a resolución
# fina en memoria y un resumen por hora en disco, para poder mirar hacia atrás
# después de un pico (que es justo cuando no había nadie mirando el panel).
#
# --- Por qué sin dependencias ---------------------------------------------
# Todo sale de /proc y de os.statvfs, que son stdlib. Añadir psutil por esto
# sería pagar RAM en la máquina donde estamos midiendo la RAM. La contrapartida
# es que /proc no existe en macOS: en el portátil de desarrollo la pestaña
# enseña el disco y marca el resto como «no disponible», que es exactamente lo
# que hace falta, porque lo que importa medir es la máquina de producción.
#
# --- Dónde se guarda -------------------------------------------------------
# En analitica.db, no en mus.db: es telemetría operativa, no datos del juego, y
# la separación que decidió analitica.py vale igual aquí. Son tablas propias
# (Sistema*) con su propia conexión; `analitica.borrar_todo()` trabaja sobre una
# lista explícita de tablas, así que no las toca.
# ==========================================================================

import os
import sqlite3
import threading
import time
from collections import deque
from datetime import datetime, timedelta

from flask import jsonify, request

import base_datos

DB_SISTEMA = os.environ.get('ANALYTICS_DB', 'analitica.db')

# Cada cuánto se toma una muestra. Un minuto es suficiente para ver un pico de
# uso y lo bastante barato como para no salir en las propias métricas.
INTERVALO_MUESTREO = 60
# Muestras finas que se guardan en memoria (1440 x 60 s = 24 h).
MUESTRAS_MEMORIA = 1440
# Cada cuánto se consolida la hora cerrada en disco y se purga lo viejo.
INTERVALO_CONSOLIDACION = 600
# Días de resumen horario que se conservan.
DIAS_HISTORICO = int(os.environ.get('SISTEMA_RETENCION_DIAS', '180'))

# Interfaces que no cuentan como tráfico real de salida.
_IFACES_IGNORADAS = ('lo', 'docker', 'veth', 'br-', 'virbr', 'tun', 'tap')

# Umbrales por defecto; se pueden cambiar en caliente desde «Variables y bot».
UMBRALES = {
    'sis_umbral_ram':     85.0,    # % de RAM usada
    'sis_umbral_swap':    25.0,    # % de swap ocupado
    'sis_umbral_disco':   85.0,    # % de disco usado
    'sis_egreso_gb':       1.0,    # GB de egreso gratis al mes (nivel gratuito)
}

_lock = threading.Lock()
_socketio = None
_ctx = {}
_arrancado = False

# Anillo de muestras finas. deque con maxlen se encarga solo de tirar lo viejo.
_muestras = deque(maxlen=MUESTRAS_MEMORIA)

# Contadores que se rellenan entre muestra y muestra y se ponen a cero al
# tomarla. Son enteros: incrementarlos no puede fallar ni bloquear.
_contadores = {'http': 0, 'http_socketio': 0, 'http_api': 0,
               'sock_rx': 0, 'sock_tx': 0}

# Última lectura cruda de los contadores acumulativos, para sacar deltas.
_previo = {'t': None, 'rx': None, 'tx': None, 'swpin': None, 'swpout': None}


# ==========================================================================
# 1. Lectores (stdlib; devuelven None si la plataforma no los tiene)
# ==========================================================================

def _leer_meminfo():
    """/proc/meminfo -> {clave: kB}. None fuera de Linux."""
    try:
        datos = {}
        with open('/proc/meminfo', 'r') as f:
            for linea in f:
                partes = linea.split()
                if len(partes) >= 2:
                    datos[partes[0].rstrip(':')] = int(partes[1])
        return datos
    except (OSError, ValueError):
        return None


def memoria():
    """RAM y swap en MB y %. None si no hay /proc."""
    mi = _leer_meminfo()
    if not mi or not mi.get('MemTotal'):
        return None
    total = mi['MemTotal']
    # MemAvailable es la estimación buena del kernel (cuenta la caché
    # recuperable); MemFree a secas asusta sin motivo en cuanto hay caché.
    disponible = mi.get('MemAvailable', mi.get('MemFree', 0))
    swap_total = mi.get('SwapTotal', 0)
    swap_libre = mi.get('SwapFree', 0)
    return {
        'total_mb': round(total / 1024, 1),
        'usada_mb': round((total - disponible) / 1024, 1),
        'disponible_mb': round(disponible / 1024, 1),
        'pct': round((total - disponible) * 100.0 / total, 1),
        'swap_total_mb': round(swap_total / 1024, 1),
        'swap_usada_mb': round((swap_total - swap_libre) / 1024, 1),
        'swap_pct': round((swap_total - swap_libre) * 100.0 / swap_total, 1) if swap_total else 0.0,
    }


def rss_proceso():
    """MB residentes del propio servidor. Es el número que hay que vigilar:
    dice cuánto de la RAM de la máquina se la está comiendo CallMus."""
    try:
        with open('/proc/self/status', 'r') as f:
            for linea in f:
                if linea.startswith('VmRSS:'):
                    return round(int(linea.split()[1]) / 1024, 1)
    except (OSError, ValueError, IndexError):
        pass
    return None


def _vmstat():
    """Páginas movidas al/desde swap desde el arranque. El % de swap ocupado
    engaña: se queda alto mucho después de que el apuro pasara. Lo que duele es
    el TRASIEGO, y eso son estos dos contadores."""
    try:
        datos = {}
        with open('/proc/vmstat', 'r') as f:
            for linea in f:
                partes = linea.split()
                if len(partes) == 2 and partes[0] in ('pswpin', 'pswpout'):
                    datos[partes[0]] = int(partes[1])
        return datos or None
    except (OSError, ValueError):
        return None


def disco(ruta='.'):
    """Uso del sistema de archivos donde vive el proyecto. os.statvfs existe en
    Linux y en macOS, así que esta sí funciona también en desarrollo."""
    try:
        st = os.statvfs(ruta)
    except (OSError, AttributeError):
        return None
    total = st.f_blocks * st.f_frsize
    # f_bavail (libre para el usuario), no f_bfree: el kernel reserva un 5%
    # para root que nosotros nunca vamos a poder usar.
    libre = st.f_bavail * st.f_frsize
    usado = total - libre
    if not total:
        return None
    return {
        'total_gb': round(total / 2**30, 2),
        'usado_gb': round(usado / 2**30, 2),
        'libre_gb': round(libre / 2**30, 2),
        'pct': round(usado * 100.0 / total, 1),
    }


def _red_cruda():
    """Bytes totales rx/tx desde el arranque, sumando interfaces reales."""
    try:
        rx = tx = 0
        with open('/proc/net/dev', 'r') as f:
            for linea in f:
                if ':' not in linea:
                    continue
                nombre, resto = linea.split(':', 1)
                nombre = nombre.strip()
                if any(nombre.startswith(p) for p in _IFACES_IGNORADAS):
                    continue
                campos = resto.split()
                if len(campos) >= 9:
                    rx += int(campos[0])
                    tx += int(campos[8])
        return {'rx': rx, 'tx': tx}
    except (OSError, ValueError, IndexError):
        return None


def carga():
    """Carga media. Con núcleo compartido, un 1.00 sostenido ya es cola."""
    try:
        uno, cinco, quince = os.getloadavg()
        return {'1m': round(uno, 2), '5m': round(cinco, 2), '15m': round(quince, 2)}
    except (OSError, AttributeError):
        return None


def hay_proc():
    """¿Estamos en una máquina con /proc (o sea, en producción)?"""
    return os.path.isdir('/proc/self')


# ==========================================================================
# 2. Base de datos
# ==========================================================================

def _conn():
    c = sqlite3.connect(DB_SISTEMA, timeout=10)
    c.row_factory = sqlite3.Row
    return c


# Métricas que se resumen por hora. Para cada una se guarda media y máximo: la
# media dice cómo se vive normalmente y el máximo es el pico, que es lo que se
# busca cuando algo ha ido mal.
_METRICAS = ('ram_pct', 'rss_mb', 'swap_pct', 'disco_pct', 'rx_bps', 'tx_bps',
             'http_rpm', 'sock_rpm', 'salas', 'conexiones', 'carga1')


def init_db():
    """Crea el esquema. Idempotente."""
    cols = ',\n            '.join(
        f"{m}_med REAL, {m}_max REAL" for m in _METRICAS)
    with _conn() as c:
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA synchronous=NORMAL")
        c.execute(f'''
            CREATE TABLE IF NOT EXISTS SistemaHora (
            hora TEXT PRIMARY KEY,
            muestras INTEGER,
            {cols}
            )''')
        # Egreso acumulado por mes. Se guarda aparte porque los contadores de
        # /proc/net/dev se ponen a cero en cada reinicio: lo que hay que
        # conservar es la SUMA de los deltas, no la última lectura.
        c.execute('''
            CREATE TABLE IF NOT EXISTS SistemaRed (
            mes TEXT PRIMARY KEY,
            rx INTEGER NOT NULL DEFAULT 0,
            tx INTEGER NOT NULL DEFAULT 0
            )''')
        c.commit()


def _mes_actual():
    return datetime.now().strftime('%Y-%m')


def _sumar_egreso(rx, tx):
    """Acumula los bytes de este intervalo en el mes en curso."""
    if rx <= 0 and tx <= 0:
        return
    with _conn() as c:
        c.execute("""INSERT INTO SistemaRed(mes, rx, tx) VALUES(?,?,?)
                     ON CONFLICT(mes) DO UPDATE SET rx = rx + excluded.rx,
                                                    tx = tx + excluded.tx""",
                  (_mes_actual(), int(max(rx, 0)), int(max(tx, 0))))
        c.commit()


def egreso_mes(mes=None):
    """{rx, tx} acumulados del mes (bytes). Ceros si aún no hay fila."""
    try:
        with _conn() as c:
            r = c.execute("SELECT rx, tx FROM SistemaRed WHERE mes = ?",
                          (mes or _mes_actual(),)).fetchone()
        return {'rx': r['rx'], 'tx': r['tx']} if r else {'rx': 0, 'tx': 0}
    except sqlite3.Error:
        return {'rx': 0, 'tx': 0}


# ==========================================================================
# 3. Muestreo
# ==========================================================================

def _instantanea_juego():
    """Lo que está pasando en el juego ahora mismo. Va en la misma serie que la
    RAM a propósito: el objetivo es poder cruzar «subió la RAM» con «había ocho
    salas abiertas» sin tener que adivinarlo."""
    salas = _ctx.get('salas') or {}
    salas4 = _ctx.get('salas4') or {}
    jugadores = _ctx.get('jugadores') or {}
    conectados = _ctx.get('usuarios_conectados') or {}
    jugando = (sum(1 for s in salas.values() if s.get('estado') == 'jugando') +
               sum(1 for s in salas4.values() if s.get('estado') == 'jugando'))
    return {
        'salas': len(salas) + len(salas4),
        'jugando': jugando,
        'conexiones': len(jugadores),
        'online': len(conectados),
    }


def muestrear():
    """Toma una muestra y la mete en el anillo. La llama el greenlet de fondo."""
    ahora = time.time()
    mem = memoria()
    dsk = disco()
    red = _red_cruda()
    vms = _vmstat()
    cg = carga()

    with _lock:
        transcurrido = ahora - (_previo['t'] or ahora)
        # Deltas de red. Si el contador BAJA es que la máquina se ha reiniciado:
        # se toma la lectura actual como el delta en vez de un número negativo.
        rx_bps = tx_bps = None
        d_rx = d_tx = 0
        if red:
            if _previo['rx'] is not None and transcurrido > 0:
                d_rx = red['rx'] - _previo['rx']
                d_tx = red['tx'] - _previo['tx']
                if d_rx < 0 or d_tx < 0:
                    d_rx, d_tx = red['rx'], red['tx']
                rx_bps = round(d_rx / transcurrido, 1)
                tx_bps = round(d_tx / transcurrido, 1)
            _previo['rx'], _previo['tx'] = red['rx'], red['tx']

        swap_in = swap_out = None
        if vms:
            if _previo['swpin'] is not None and transcurrido > 0:
                di = vms.get('pswpin', 0) - _previo['swpin']
                do = vms.get('pswpout', 0) - _previo['swpout']
                if di >= 0 and do >= 0:
                    swap_in = round(di / transcurrido, 1)
                    swap_out = round(do / transcurrido, 1)
            _previo['swpin'] = vms.get('pswpin', 0)
            _previo['swpout'] = vms.get('pswpout', 0)

        # Los contadores se leen y se ponen a cero de una vez.
        minutos = max(transcurrido / 60.0, 1e-9)
        c = dict(_contadores)
        for k in _contadores:
            _contadores[k] = 0
        _previo['t'] = ahora

        juego = _instantanea_juego()
        m = {
            't': ahora,
            'ram_pct': mem['pct'] if mem else None,
            'ram_usada_mb': mem['usada_mb'] if mem else None,
            'rss_mb': rss_proceso(),
            'swap_pct': mem['swap_pct'] if mem else None,
            'swap_usada_mb': mem['swap_usada_mb'] if mem else None,
            'swap_in': swap_in,
            'swap_out': swap_out,
            'disco_pct': dsk['pct'] if dsk else None,
            'rx_bps': rx_bps,
            'tx_bps': tx_bps,
            'http_rpm': round(c['http'] / minutos, 1),
            'http_api_rpm': round(c['http_api'] / minutos, 1),
            'http_sio_rpm': round(c['http_socketio'] / minutos, 1),
            'sock_rpm': round(c['sock_rx'] / minutos, 1),
            'sock_tx_rpm': round(c['sock_tx'] / minutos, 1),
            'carga1': cg['1m'] if cg else None,
            'salas': juego['salas'],
            'jugando': juego['jugando'],
            'conexiones': juego['conexiones'],
            'online': juego['online'],
        }
        _muestras.append(m)

    # Fuera del lock: esto escribe en disco.
    if d_rx or d_tx:
        try:
            _sumar_egreso(d_rx, d_tx)
        except sqlite3.Error as e:
            print(f"⚠️ sistema: no se pudo acumular el egreso ({e})")
    return m


def consolidar():
    """Vuelca a disco el resumen de las horas ya cerradas que estén en memoria.

    Solo se escriben horas COMPLETAS (nunca la que está en curso), y con INSERT
    OR REPLACE, así que repetir la pasada no duplica ni corrompe nada."""
    hora_actual = datetime.now().strftime('%Y-%m-%dT%H')
    with _lock:
        muestras = list(_muestras)
    if not muestras:
        return 0

    por_hora = {}
    for m in muestras:
        h = datetime.fromtimestamp(m['t']).strftime('%Y-%m-%dT%H')
        if h != hora_actual:
            por_hora.setdefault(h, []).append(m)
    if not por_hora:
        return 0

    columnas = ['hora', 'muestras']
    for met in _METRICAS:
        columnas += [f'{met}_med', f'{met}_max']
    marcas = ','.join('?' * len(columnas))

    filas = []
    for h, ms in por_hora.items():
        fila = [h, len(ms)]
        for met in _METRICAS:
            vals = [m[met] for m in ms if m.get(met) is not None]
            if vals:
                fila += [round(sum(vals) / len(vals), 2), round(max(vals), 2)]
            else:
                fila += [None, None]
        filas.append(fila)

    with _conn() as c:
        c.executemany(f"INSERT OR REPLACE INTO SistemaHora({','.join(columnas)}) "
                      f"VALUES({marcas})", filas)
        c.commit()
    return len(filas)


def purgar():
    """Tira el histórico horario más viejo que DIAS_HISTORICO."""
    limite = (datetime.now() - timedelta(days=DIAS_HISTORICO)).strftime('%Y-%m-%dT%H')
    with _conn() as c:
        n = c.execute("DELETE FROM SistemaHora WHERE hora < ?", (limite,)).rowcount
        c.commit()
    return n


# ==========================================================================
# 4. Lectura para el panel
# ==========================================================================

def _umbral(clave):
    return base_datos.config_get_float(clave, UMBRALES[clave])


def _estado(valor, umbral, critico_extra=10.0):
    """'ok' | 'aviso' | 'critico' para pintar la tarjeta."""
    if valor is None or umbral is None:
        return 'nd'
    if valor >= umbral + critico_extra:
        return 'critico'
    if valor >= umbral:
        return 'aviso'
    return 'ok'


def snapshot():
    """Foto de ahora mismo + estado de cada umbral. Es lo que pinta la pestaña.

    No usa la última muestra del anillo (podría tener hasta un minuto): lee en
    directo, que es barato, y coge del anillo solo lo que necesita historia
    (los ritmos por minuto y el tráfico)."""
    mem = memoria()
    dsk = disco()
    cg = carga()
    with _lock:
        ultima = _muestras[-1] if _muestras else None
        n_muestras = len(_muestras)

    egr = egreso_mes()
    gb_libres = _umbral('sis_egreso_gb')
    tx_gb = egr['tx'] / 2**30
    pct_egreso = round(tx_gb * 100.0 / gb_libres, 1) if gb_libres > 0 else None

    datos = {
        'disponible': hay_proc(),
        'ahora': time.time(),
        'muestras': n_muestras,
        'intervalo': INTERVALO_MUESTREO,
        'memoria': mem,
        'rss_mb': rss_proceso(),
        'disco': dsk,
        'carga': cg,
        'juego': _instantanea_juego(),
        'red': {
            'rx_bps': ultima.get('rx_bps') if ultima else None,
            'tx_bps': ultima.get('tx_bps') if ultima else None,
            'mes': _mes_actual(),
            'mes_rx_gb': round(egr['rx'] / 2**30, 3),
            'mes_tx_gb': round(tx_gb, 3),
            'presupuesto_gb': gb_libres,
            'pct_presupuesto': pct_egreso,
        },
        'trafico': {
            'http_rpm': ultima.get('http_rpm') if ultima else None,
            'http_api_rpm': ultima.get('http_api_rpm') if ultima else None,
            'http_sio_rpm': ultima.get('http_sio_rpm') if ultima else None,
            'sock_rpm': ultima.get('sock_rpm') if ultima else None,
            'sock_tx_rpm': ultima.get('sock_tx_rpm') if ultima else None,
        },
        'swap_actividad': {
            'in': ultima.get('swap_in') if ultima else None,
            'out': ultima.get('swap_out') if ultima else None,
        },
        'umbrales': {k: _umbral(k) for k in UMBRALES},
    }

    # El swap tiene dos alarmas distintas: cuánto hay ocupado (tolerable) y si
    # se está moviendo AHORA (eso es lo que congela el bucle de eventlet).
    trasiego = (datos['swap_actividad']['in'] or 0) + (datos['swap_actividad']['out'] or 0)
    datos['estado'] = {
        'ram': _estado(mem['pct'] if mem else None, _umbral('sis_umbral_ram')),
        'swap': ('critico' if trasiego > 0 else
                 _estado(mem['swap_pct'] if mem else None, _umbral('sis_umbral_swap'))),
        'disco': _estado(dsk['pct'] if dsk else None, _umbral('sis_umbral_disco')),
        'egreso': _estado(pct_egreso, 70.0, 30.0),
    }
    return datos


def historico(horas=24):
    """Serie temporal para las gráficas.

    Hasta 24 h se sirve el anillo en memoria (resolución de 1 min). Más allá se
    sirve el resumen horario del disco, que es lo que sobrevive a un reinicio —
    justo lo que se quiere consultar después de que el servidor se caiga."""
    horas = max(1, min(int(horas or 24), 24 * DIAS_HISTORICO))
    if horas <= 24:
        corte = time.time() - horas * 3600
        with _lock:
            serie = [m for m in _muestras if m['t'] >= corte]
        return {'fuente': 'memoria', 'resolucion_s': INTERVALO_MUESTREO, 'serie': serie}

    limite = (datetime.now() - timedelta(hours=horas)).strftime('%Y-%m-%dT%H')
    with _conn() as c:
        filas = c.execute("SELECT * FROM SistemaHora WHERE hora >= ? ORDER BY hora",
                          (limite,)).fetchall()
    serie = []
    for r in filas:
        d = dict(r)
        # Se traduce al mismo vocabulario que la serie en memoria (usando el
        # máximo de la hora) para que el front pinte ambas con el mismo código.
        punto = {'t': datetime.strptime(d['hora'], '%Y-%m-%dT%H').timestamp(),
                 'muestras': d['muestras']}
        for met in _METRICAS:
            punto[met] = d.get(f'{met}_max')
            punto[met + '_med'] = d.get(f'{met}_med')
        serie.append(punto)
    return {'fuente': 'disco', 'resolucion_s': 3600, 'serie': serie}


# ==========================================================================
# 5. Tareas de fondo
# ==========================================================================

def _bucle_muestreo():
    while True:
        _socketio.sleep(INTERVALO_MUESTREO)
        try:
            muestrear()
        except Exception as e:
            print(f"⚠️ sistema: fallo muestreando ({e})")


def _bucle_consolidacion():
    while True:
        _socketio.sleep(INTERVALO_CONSOLIDACION)
        try:
            consolidar()
            purgar()
        except Exception as e:
            print(f"⚠️ sistema: fallo consolidando ({e})")


# ==========================================================================
# 6. Instrumentación y registro de rutas
# ==========================================================================

def _instrumentar_http(app):
    """Cuenta TODAS las peticiones, envolviendo la app WSGI.

    No sirve un `before_request` de Flask: Flask-SocketIO sustituye `app.wsgi_app`
    por el middleware de engineio, que atiende `/socket.io/` él mismo y nunca se
    lo pasa a Flask. Con un before_request, el sondeo del socket —que en este
    servidor es la mayor parte del tráfico— quedaría sin contar y el panel diría
    que no pasa nada mientras el bucle se ahoga.

    Envolver aquí funciona porque init_sistema se registra al final de server.py,
    cuando `app.wsgi_app` ya es el middleware: nuestro envoltorio queda por fuera
    y ve todo. Solo suma un entero y delega."""
    original = app.wsgi_app

    def contado(environ, start_response):
        ruta = environ.get('PATH_INFO', '') or ''
        _contadores['http'] += 1
        if ruta.startswith('/socket.io/'):
            _contadores['http_socketio'] += 1
        elif ruta.startswith('/api/') or ruta.startswith('/auth/'):
            _contadores['http_api'] += 1
        return original(environ, start_response)

    app.wsgi_app = contado


def _instrumentar_socketio(socketio):
    """Cuenta eventos de Socket.IO entrantes y salientes.

    Se envuelven dos métodos del servidor de python-socketio por los que pasa
    TODO, en vez de tocar los cincuenta handlers repartidos por server.py,
    server_mus4.py y social.py. `emit` es API pública; `_trigger_event` es
    interna, así que va en su propio try: si una futura versión de la librería
    la renombra, el panel se queda sin el contador de entrada y el juego sigue
    funcionando igual. Los envoltorios solo suman un entero antes de delegar."""
    try:
        emit_original = socketio.server.emit

        def emit_contado(*a, **k):
            _contadores['sock_tx'] += 1
            return emit_original(*a, **k)

        socketio.server.emit = emit_contado
    except Exception as e:
        print(f"⚠️ sistema: sin contador de emisiones ({e})")

    try:
        trigger_original = socketio.server._trigger_event

        def trigger_contado(*a, **k):
            _contadores['sock_rx'] += 1
            return trigger_original(*a, **k)

        socketio.server._trigger_event = trigger_contado
    except Exception as e:
        print(f"⚠️ sistema: sin contador de eventos entrantes ({e})")


def init_sistema(app, socketio, ctx):
    global _socketio, _ctx, _arrancado
    _socketio = socketio
    _ctx = ctx or {}
    init_db()

    admin_requerido = _ctx.get('admin_requerido') or (lambda f: f)

    # ----------------------------------------------------------------------
    # Recogida
    # ----------------------------------------------------------------------

    _instrumentar_http(app)
    _instrumentar_socketio(socketio)

    # ----------------------------------------------------------------------
    # API del panel
    # ----------------------------------------------------------------------

    @app.route('/admin/api/sistema', methods=['GET'])
    @admin_requerido
    def sis_resumen():
        return jsonify({'exito': True, 'sistema': snapshot()})

    @app.route('/admin/api/sistema/historico', methods=['GET'])
    @admin_requerido
    def sis_historico():
        return jsonify({'exito': True,
                        **historico(request.args.get('horas', 24, type=int))})

    # ----------------------------------------------------------------------
    # Arranque
    # ----------------------------------------------------------------------
    if not _arrancado:
        _arrancado = True
        # Primera muestra inmediata: fija la base de los contadores acumulativos
        # para que la siguiente ya pueda dar deltas, y deja el panel con algo
        # que enseñar sin esperar un minuto.
        try:
            muestrear()
        except Exception as e:
            print(f"⚠️ sistema: fallo en la muestra inicial ({e})")
        socketio.start_background_task(_bucle_muestreo)
        socketio.start_background_task(_bucle_consolidacion)
        estado = "con /proc" if hay_proc() else "SIN /proc (solo disco)"
        print(f"📈 Sistema: muestreo cada {INTERVALO_MUESTREO}s, {estado}.")

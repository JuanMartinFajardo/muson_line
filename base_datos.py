import sqlite3
import secrets
import time
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

DB_NAME = 'mus.db'

def init_db():
    conexion = sqlite3.connect(DB_NAME)
    cursor = conexion.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT,
            google_id TEXT,
            country TEXT,
            birthdate TEXT,
            victorias INTEGER DEFAULT 0,
            derrotas INTEGER DEFAULT 0,
            elo REAL DEFAULT 1200.0,
            fecha_registro TEXT
        )
    ''')
    # (Las columnas añadidas después del diseño original — email, google_id,
    #  estadísticas 4p, ajustes de cuenta, codigo — las pone _migrar_columnas.)

    # ==========================================
    # TABLAS SOCIALES (Roadmap #3: amigos, mensajes, grupos)
    # ==========================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Friendships (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_low      INTEGER NOT NULL,
            user_high     INTEGER NOT NULL,
            status        TEXT NOT NULL DEFAULT 'pending',
            requested_by  INTEGER NOT NULL,
            created_at    TEXT NOT NULL,
            updated_at    TEXT NOT NULL,
            UNIQUE(user_low, user_high)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Messages (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id     INTEGER NOT NULL,
            recipient_id  INTEGER,
            group_id      INTEGER,
            body          TEXT NOT NULL,
            created_at    TEXT NOT NULL,
            read_at       TEXT
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_msg_dm    ON Messages(recipient_id, sender_id, id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_msg_group ON Messages(group_id, id)')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Groups (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            owner_id      INTEGER NOT NULL,
            created_at    TEXT NOT NULL,
            invite_policy TEXT NOT NULL DEFAULT 'admins'
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS GroupMembers (
            group_id     INTEGER NOT NULL,
            user_id      INTEGER NOT NULL,
            role         TEXT NOT NULL DEFAULT 'member',
            joined_at    TEXT NOT NULL,
            last_read_id INTEGER DEFAULT 0,
            UNIQUE(group_id, user_id)
        )
    ''')
    # Historial por partida (necesario para el ELO propio de cada grupo, Roadmap #3/#19).
    # Solo se registran partidas humano vs humano donde ambos son usuarios registrados.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Partidas (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha       TEXT NOT NULL,
            ganador_id  INTEGER NOT NULL,
            perdedor_id INTEGER NOT NULL,
            vs_bot      INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_partidas_jug ON Partidas(ganador_id, perdedor_id, fecha)')

    # Historial de partidas de 4 jugadores (2v2). Roadmap #6.
    # Guardamos ambos equipos y el marcador final del match (juegos ganados por
    # cada equipo, p.ej. 2-1 o 3-0) para poder atribuir a cada jugador el número
    # de juegos ganados (útil para clasificaciones de grupo). Jugadores invitados
    # (sin cuenta) se guardan como NULL. No toca el ELO 1v1.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Partidas4 (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha          TEXT NOT NULL,
            match_id       TEXT,
            al_mejor_de    INTEGER,
            ganador1_id    INTEGER,
            ganador2_id    INTEGER,
            perdedor1_id   INTEGER,
            perdedor2_id   INTEGER,
            juegos_ganador INTEGER NOT NULL,
            juegos_perdedor INTEGER NOT NULL
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_partidas4_fecha ON Partidas4(fecha)')

    # ==========================================
    # PANEL DE ADMINISTRACIÓN (Roadmap #13)
    # ==========================================

    # Variables globales editables en caliente (checkpoint del bot, retardo del
    # bot, texto de mantenimiento…). Clave→valor de texto: quien la lee decide
    # cómo interpretarla, para poder añadir ajustes sin tocar el esquema.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Config (
            key        TEXT PRIMARY KEY,
            value      TEXT,
            updated_at TEXT,
            updated_by TEXT
        )
    ''')

    # Registro de TODO lo que hace un administrador. Es la contrapartida de darle
    # poder para banear, editar ELOs o borrar cuentas: nada de eso es anónimo.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS AdminAudit (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha    TEXT NOT NULL,
            admin    TEXT NOT NULL,
            accion   TEXT NOT NULL,
            objetivo TEXT,
            detalle  TEXT,
            ip       TEXT
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_fecha ON AdminAudit(fecha)')

    # Soporte: un hilo por incidencia, con mensajes de ida y vuelta hasta que
    # alguien lo da por resuelto. `estado` gobierna las bandejas del panel.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS SupportTickets (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            asunto      TEXT NOT NULL,
            tipo        TEXT NOT NULL DEFAULT 'otro',
            estado      TEXT NOT NULL DEFAULT 'abierto',
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL,
            leido_admin INTEGER DEFAULT 0,
            leido_user  INTEGER DEFAULT 1
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tickets_estado ON SupportTickets(estado, updated_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tickets_user   ON SupportTickets(user_id, updated_at)')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS SupportMessages (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id  INTEGER NOT NULL,
            autor      TEXT NOT NULL,           -- 'user' | 'admin'
            autor_nombre TEXT,
            body       TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_smsg_ticket ON SupportMessages(ticket_id, id)')

    # Avisos del administrador a los jugadores. Dos formas de vida:
    #   'notificacion' → llega una vez (toast si está conectado, bandeja si no)
    #   'pin'          → se queda fijado en el menú hasta que caduque o se quite
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Anuncios (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo       TEXT NOT NULL DEFAULT 'notificacion',
            titulo     TEXT,
            cuerpo     TEXT NOT NULL,
            audiencia  TEXT NOT NULL DEFAULT 'todos',   -- 'todos' | 'grupo' | 'usuarios'
            group_id   INTEGER,
            destinatarios TEXT,                          -- CSV de Usuarios.id si audiencia='usuarios'
            creado_por TEXT,
            created_at TEXT NOT NULL,
            expira_en  TEXT,
            activo     INTEGER DEFAULT 1
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_anuncios_activo ON Anuncios(activo, tipo)')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS AnuncioLeido (
            anuncio_id INTEGER NOT NULL,
            user_id    INTEGER NOT NULL,
            leido_en   TEXT NOT NULL,
            UNIQUE(anuncio_id, user_id)
        )
    ''')

    # ==========================================
    # BARAJAS TEMÁTICAS (Roadmap #5)
    # ==========================================

    # Una fila = un TEMA, es decir el juego de 11 imágenes (10 cartas + dorso)
    # que ocupa uno de los cuatro huecos de palo de la baraja del jugador. Los
    # cuatro temas clásicos (oros, copas, espadas, bastos) también viven aquí,
    # marcados con origen='clasica', para que el panel pueda restringirlos o
    # renombrarlos igual que a los subidos; sus imágenes siguen donde estaban.
    #
    #   acceso: 'todos'       → cualquiera, también sin cuenta
    #           'cuenta'      → hace falta haber iniciado sesión
    #           'restringido' → sólo quien esté en DeckAcceso (y los admins)
    #   activo: 0 lo retira del selector sin borrar los archivos ni las
    #           configuraciones que ya lo usaban.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Decks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            slug        TEXT UNIQUE NOT NULL,
            nombre      TEXT NOT NULL,
            nombre_en   TEXT,
            descripcion TEXT,
            acceso      TEXT NOT NULL DEFAULT 'todos',
            activo      INTEGER NOT NULL DEFAULT 1,
            orden       INTEGER NOT NULL DEFAULT 100,
            origen      TEXT NOT NULL DEFAULT 'subida',   -- 'clasica' | 'subida'
            patron      TEXT,                             -- cara: ruta con {vv}; NULL = carpeta del slug
            patron_dorso TEXT,                            -- dorso; NULL = carpeta del slug
            creado_por  TEXT,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_decks_orden ON Decks(activo, orden, id)')

    # Permisos individuales de los temas 'restringido'. La fila desaparece con el
    # tema; si se borra la cuenta, el permiso queda huérfano pero es inofensivo
    # (nadie puede volver a ser ese id).
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS DeckAcceso (
            deck_id       INTEGER NOT NULL,
            user_id       INTEGER NOT NULL,
            concedido_por TEXT,
            created_at    TEXT NOT NULL,
            UNIQUE(deck_id, user_id)
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_deckacceso_user ON DeckAcceso(user_id)')

    conexion.commit()
    _migrar_columnas(conexion)
    _migrar_social(conexion)
    _migrar_decks(conexion)
    _sembrar_barajas_clasicas(conexion)
    conexion.close()


def _migrar_social(conexion):
    """Migraciones idempotentes para las tablas sociales en bases de datos antiguas."""
    cursor = conexion.cursor()
    cursor.execute("PRAGMA table_info(Groups)")
    columnas = {fila[1] for fila in cursor.fetchall()}
    if 'invite_policy' not in columnas:
        cursor.execute("ALTER TABLE Groups ADD COLUMN invite_policy TEXT NOT NULL DEFAULT 'admins'")
    conexion.commit()

def _migrar_decks(conexion):
    """Migraciones idempotentes de la tabla de barajas."""
    cursor = conexion.cursor()
    cursor.execute("PRAGMA table_info(Decks)")
    columnas = {fila[1] for fila in cursor.fetchall()}
    if 'patron_dorso' not in columnas:
        cursor.execute("ALTER TABLE Decks ADD COLUMN patron_dorso TEXT")
        cursor.execute("UPDATE Decks SET patron_dorso = '/static/img/card_back.webp' "
                       "WHERE origen = 'clasica'")
    conexion.commit()


#: Los cuatro temas que ya venían con el juego. `patron` apunta a los archivos de
#: siempre (`static/img/card_<palo>_<NN>.webp`), así que sembrarlos no mueve ni un
#: byte: sólo los hace visibles y administrables desde el panel.
BARAJAS_CLASICAS = [
    ('coins',  'Oros',    'Coins',  10),
    ('cups',   'Copas',   'Cups',   11),
    ('swords', 'Espadas', 'Swords', 12),
    ('clubs',  'Bastos',  'Clubs',  13),
]


def _sembrar_barajas_clasicas(conexion):
    """Registra los cuatro temas clásicos si aún no están. Idempotente: no toca
    los que ya existen, para no pisar el acceso que le haya puesto un admin."""
    cursor = conexion.cursor()
    ahora = datetime.now().isoformat()
    for slug, nombre, nombre_en, orden in BARAJAS_CLASICAS:
        cursor.execute("""
            INSERT INTO Decks(slug, nombre, nombre_en, descripcion, acceso, activo,
                              orden, origen, patron, patron_dorso, creado_por,
                              created_at, updated_at)
            VALUES(?,?,?,?,'todos',1,?,'clasica',?,?,?,?,?)
            ON CONFLICT(slug) DO NOTHING
        """, (slug, nombre, nombre_en, 'Baraja española original de CallMus.',
              orden, f'/static/img/card_{slug}_{{vv}}.webp',
              '/static/img/card_back.webp', None, ahora, ahora))
    conexion.commit()


def _migrar_columnas(conexion):
    """Añade columnas nuevas a bases de datos antiguas sin perder datos existentes."""
    cursor = conexion.cursor()
    cursor.execute("PRAGMA table_info(Usuarios)")
    columnas = {fila[1] for fila in cursor.fetchall()}

    if 'email' not in columnas:
        cursor.execute("ALTER TABLE Usuarios ADD COLUMN email TEXT")
    if 'google_id' not in columnas:
        cursor.execute("ALTER TABLE Usuarios ADD COLUMN google_id TEXT")

    # Estadísticas de Mus a 4 (2v2). Roadmap #6. Separadas del ELO 1v1:
    #   victorias_4p = matches ganados; juegos_4p = juegos individuales ganados
    #   (sumados desde el marcador final de cada match, p.ej. +2 al ganar 2-1).
    if 'victorias_4p' not in columnas:
        cursor.execute("ALTER TABLE Usuarios ADD COLUMN victorias_4p INTEGER DEFAULT 0")
    if 'derrotas_4p' not in columnas:
        cursor.execute("ALTER TABLE Usuarios ADD COLUMN derrotas_4p INTEGER DEFAULT 0")
    if 'juegos_4p' not in columnas:
        cursor.execute("ALTER TABLE Usuarios ADD COLUMN juegos_4p INTEGER DEFAULT 0")

    # Ajustes de cuenta (Roadmap #22).
    #   tiene_password: 0 en las cuentas creadas desde cero con Google, que llevan
    #     un hash aleatorio inservible. Solo decide QUÉ formulario se enseña; para
    #     autorizar un cambio vale igualmente la contraseña o un código al correo.
    #   username_cambiado_en: fecha del último cambio de nombre (periodo de espera).
    if 'tiene_password' not in columnas:
        cursor.execute("ALTER TABLE Usuarios ADD COLUMN tiene_password INTEGER DEFAULT 1")
        cursor.execute("UPDATE Usuarios SET tiene_password = 0 WHERE google_id IS NOT NULL")
    if 'username_cambiado_en' not in columnas:
        cursor.execute("ALTER TABLE Usuarios ADD COLUMN username_cambiado_en TEXT")

    # Identificador público permanente (Roadmap #23).
    #   codigo: 6 caracteres que NO cambian nunca, ni al renombrarse ni al borrar la
    #     cuenta, y que no se reciclan (la fila nunca se elimina, así que el índice
    #     único basta para garantizarlo). Es lo que distingue a dos jugadores que en
    #     momentos distintos han usado el mismo nombre.
    #   eliminada_en: fecha del borrado. La fila sobrevive por el historial, pero
    #     deja de ser un jugador: no sale en la clasificación ni se le puede añadir.
    if 'codigo' not in columnas:
        cursor.execute("ALTER TABLE Usuarios ADD COLUMN codigo TEXT")
    if 'eliminada_en' not in columnas:
        cursor.execute("ALTER TABLE Usuarios ADD COLUMN eliminada_en TEXT")

    # Panel de administración (Roadmap #13).
    #   is_admin: acceso a /admin. El primer administrador se promueve al arrancar
    #     desde la variable de entorno ADMIN_USERNAME; a partir de ahí se otorga
    #     desde el propio panel.
    #   banned / ban_motivo / ban_en: la cuenta sigue existiendo (su historial es
    #     el de sus rivales) pero no puede iniciar sesión ni abrir un socket.
    if 'is_admin' not in columnas:
        cursor.execute("ALTER TABLE Usuarios ADD COLUMN is_admin INTEGER DEFAULT 0")
    if 'banned' not in columnas:
        cursor.execute("ALTER TABLE Usuarios ADD COLUMN banned INTEGER DEFAULT 0")
    if 'ban_motivo' not in columnas:
        cursor.execute("ALTER TABLE Usuarios ADD COLUMN ban_motivo TEXT")
    if 'ban_en' not in columnas:
        cursor.execute("ALTER TABLE Usuarios ADD COLUMN ban_en TEXT")

    # Barajas temáticas (Roadmap #5). JSON con el tema elegido para cada hueco de
    # palo y para el dorso: {"coins": "ducks", ..., "dorso": "coffee"}. Es puro
    # adorno y sólo lo ve su dueño, así que un valor corrupto o que apunte a un
    # tema retirado no rompe nada: el cliente cae a la baraja clásica.
    if 'deck_config' not in columnas:
        cursor.execute("ALTER TABLE Usuarios ADD COLUMN deck_config TEXT")

    # Rellena el código de las cuentas anteriores a esta columna. El bucle es
    # idempotente por sí solo (busca las que aún no lo tienen), así que aunque una
    # migración a medias deje columnas sin rellenar, el siguiente arranque lo cierra.
    cursor.execute("SELECT id FROM Usuarios WHERE codigo IS NULL OR codigo = ''")
    for (uid,) in cursor.fetchall():
        cursor.execute("UPDATE Usuarios SET codigo = ? WHERE id = ?",
                       (_generar_codigo_libre(cursor), uid))

    # Cuentas borradas con el esquema anterior, que se llamaban 'EliminadoNN' y no
    # llevaban marca. Se reconocen porque ese nombre solo lo ponía el borrado y deja
    # la fila sin correo, sin Google y sin contraseña utilizable. Se pasan al esquema
    # nuevo para que dejen de ocupar un nombre y salgan de la clasificación.
    cursor.execute("""SELECT id, codigo FROM Usuarios
                      WHERE eliminada_en IS NULL AND email IS NULL AND google_id IS NULL
                        AND COALESCE(tiene_password, 1) = 0
                        AND username GLOB 'Eliminado[0-9]*'""")
    for uid, codigo in cursor.fetchall():
        cursor.execute("UPDATE Usuarios SET username = ?, eliminada_en = ? WHERE id = ?",
                       ('#' + codigo, datetime.now().strftime("%Y-%m-%d"), uid))

    # Índices únicos (case-insensitive) para email y google_id.
    # Se crean como parciales para que los NULL no colisionen entre sí.
    cursor.execute('''
        CREATE UNIQUE INDEX IF NOT EXISTS idx_usuarios_email
        ON Usuarios (email COLLATE NOCASE) WHERE email IS NOT NULL
    ''')
    cursor.execute('''
        CREATE UNIQUE INDEX IF NOT EXISTS idx_usuarios_google
        ON Usuarios (google_id) WHERE google_id IS NOT NULL
    ''')
    cursor.execute('''
        CREATE UNIQUE INDEX IF NOT EXISTS idx_usuarios_codigo
        ON Usuarios (codigo) WHERE codigo IS NOT NULL
    ''')
    conexion.commit()


# --- Identificador público permanente (Roadmap #23) ---------------------------

# Alfabeto sin caracteres que se confunden al leerlos en voz alta o copiarlos:
# nada de 0/O, 1/I/L. 32^6 ≈ 1.000 millones de combinaciones.
_ALFABETO_CODIGO = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'
LONGITUD_CODIGO = 6


def _generar_codigo_libre(cursor):
    """Código público que no tenga ya ninguna cuenta (ni viva ni borrada)."""
    while True:
        codigo = ''.join(secrets.choice(_ALFABETO_CODIGO) for _ in range(LONGITUD_CODIGO))
        cursor.execute('SELECT 1 FROM Usuarios WHERE codigo = ?', (codigo,))
        if not cursor.fetchone():
            return codigo


def normalizar_codigo(texto):
    """'#a7k-2qx' → 'A7K2QX'. Devuelve None si no parece un código."""
    if not texto:
        return None
    limpio = ''.join(c for c in texto.upper() if c in _ALFABETO_CODIGO)
    return limpio if len(limpio) == LONGITUD_CODIGO else None


def obtener_usuario_por_codigo(codigo):
    """Busca una cuenta viva por su código público. Devuelve (id, username) o None."""
    codigo = normalizar_codigo(codigo)
    if not codigo:
        return None
    with _conn() as c:
        r = c.execute('SELECT id, username FROM Usuarios '
                      'WHERE codigo = ? AND eliminada_en IS NULL', (codigo,)).fetchone()
        return (r['id'], r['username']) if r else None

# --- FUNCIONES MATEMÁTICAS ELO ---
def calcular_probabilidad(elo_jugador, elo_oponente):
    return 1 / (1 + 10 ** ((elo_oponente - elo_jugador) / 400))

def procesar_partida_mus(elo_a, elo_b, victorias_a, victorias_b, k=16):
    prob_a = calcular_probabilidad(elo_a, elo_b)
    prob_b = calcular_probabilidad(elo_b, elo_a)
    
    # En una partida normal de mus, el ganador se lleva 1 punto (victoria) y el otro 0
    s_a = 1 if victorias_a > victorias_b else (0 if victorias_a < victorias_b else 0.5)
    s_b = 1 if victorias_b > victorias_a else (0 if victorias_b < victorias_a else 0.5)
    
    nuevo_elo_a = elo_a + k * (s_a - prob_a)
    nuevo_elo_b = elo_b + k * (s_b - prob_b)
    variacion = abs(nuevo_elo_a - elo_a)
    
    return round(nuevo_elo_a, 1), round(nuevo_elo_b, 1), round(variacion, 1)
# ---------------------------------

def registrar_partida_completa(ganador_user, perdedor_user):
    """Guarda victorias, derrotas y, si AMBOS están registrados, actualiza sus ELOs"""
    conexion = sqlite3.connect(DB_NAME)
    cursor = conexion.cursor()
    
    # Actualizar victorias, derrotas y ELO *solo* si ambos son jugadores reales registrados
    if ganador_user and perdedor_user:
        cursor.execute('SELECT id, elo FROM Usuarios WHERE username = ?', (ganador_user,))
        res_g = cursor.fetchone()
        cursor.execute('SELECT id, elo FROM Usuarios WHERE username = ?', (perdedor_user,))
        res_p = cursor.fetchone()

        if res_g and res_p:
            id_g, elo_g = res_g
            id_p, elo_p = res_p
            # 1. Sumar victorias y derrotas
            cursor.execute('UPDATE Usuarios SET victorias = victorias + 1 WHERE username = ?', (ganador_user,))
            cursor.execute('UPDATE Usuarios SET derrotas = derrotas + 1 WHERE username = ?', (perdedor_user,))

            # 2. Actualizar ELO global
            # ganador tiene 1 victoria, perdedor 0
            nuevo_elo_g, nuevo_elo_p, _ = procesar_partida_mus(elo_g, elo_p, 1, 0)

            cursor.execute('UPDATE Usuarios SET elo = ? WHERE username = ?', (nuevo_elo_g, ganador_user))
            cursor.execute('UPDATE Usuarios SET elo = ? WHERE username = ?', (nuevo_elo_p, perdedor_user))

            # 3. Registrar la partida (para la clasificación propia de cada grupo).
            #    fecha ISO para poder compararla con GroupMembers.joined_at lexicográficamente.
            cursor.execute('INSERT INTO Partidas(fecha, ganador_id, perdedor_id, vs_bot) VALUES(?,?,?,0)',
                           (datetime.now().isoformat(), id_g, id_p))

    conexion.commit()
    conexion.close()


def registrar_partida_4(usernames_ganadores, usernames_perdedores,
                        juegos_ganador, juegos_perdedor,
                        match_id=None, al_mejor_de=None):
    """Registra el resultado de una partida de 4 jugadores (2v2). Roadmap #6.

    - usernames_*: listas de 2 usernames (o None para invitados sin cuenta).
    - juegos_ganador/juegos_perdedor: marcador final del match (p.ej. 2 y 1).

    Guarda una fila en Partidas4 con ambos equipos y el marcador, y actualiza las
    estadísticas 4p de cada jugador registrado: +1 match ganado/perdido y +N juegos
    individuales según el marcador. No modifica el ELO ni las stats 1v1.
    """
    conexion = sqlite3.connect(DB_NAME)
    cursor = conexion.cursor()

    def id_de(username):
        if not username:
            return None
        cursor.execute('SELECT id FROM Usuarios WHERE username = ?', (username,))
        fila = cursor.fetchone()
        return fila[0] if fila else None

    g = [id_de(u) for u in (usernames_ganadores or [])]
    p = [id_de(u) for u in (usernames_perdedores or [])]
    while len(g) < 2:
        g.append(None)
    while len(p) < 2:
        p.append(None)

    cursor.execute('''
        INSERT INTO Partidas4(fecha, match_id, al_mejor_de,
                              ganador1_id, ganador2_id, perdedor1_id, perdedor2_id,
                              juegos_ganador, juegos_perdedor)
        VALUES(?,?,?,?,?,?,?,?,?)
    ''', (datetime.now().isoformat(), match_id, al_mejor_de,
          g[0], g[1], p[0], p[1], juegos_ganador, juegos_perdedor))

    # Cada jugador se apunta los juegos que ganó su equipo en el marcador final.
    for uid in g:
        if uid is not None:
            cursor.execute(
                'UPDATE Usuarios SET victorias_4p = COALESCE(victorias_4p,0) + 1, '
                'juegos_4p = COALESCE(juegos_4p,0) + ? WHERE id = ?',
                (juegos_ganador, uid))
    for uid in p:
        if uid is not None:
            cursor.execute(
                'UPDATE Usuarios SET derrotas_4p = COALESCE(derrotas_4p,0) + 1, '
                'juegos_4p = COALESCE(juegos_4p,0) + ? WHERE id = ?',
                (juegos_perdedor, uid))

    conexion.commit()
    conexion.close()


def existe_usuario(username, email):
    """Comprueba, ANTES de mandar el código, si el usuario o el email ya existen.
    Devuelve (existe:bool, mensaje:str)."""
    conexion = sqlite3.connect(DB_NAME)
    cursor = conexion.cursor()
    cursor.execute('SELECT 1 FROM Usuarios WHERE username = ? COLLATE NOCASE', (username,))
    if cursor.fetchone():
        conexion.close()
        return True, "El nombre de usuario ya está en uso."
    if email:
        cursor.execute('SELECT 1 FROM Usuarios WHERE email = ? COLLATE NOCASE', (email,))
        if cursor.fetchone():
            conexion.close()
            return True, "Ya existe una cuenta con ese correo."
    conexion.close()
    return False, ""

def registrar_usuario(username, password, country, birthdate, email=None):
    conexion = sqlite3.connect(DB_NAME)
    cursor = conexion.cursor()
    hash_pass = generate_password_hash(password)
    fecha_actual = datetime.now().strftime("%Y-%m-%d")

    try:
        cursor.execute('''
            INSERT INTO Usuarios (username, password_hash, email, country, birthdate,
                                  fecha_registro, codigo)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (username, hash_pass, email, country, birthdate, fecha_actual,
              _generar_codigo_libre(cursor)))
        conexion.commit()
        exito, mensaje = True, "Usuario registrado correctamente."
    except sqlite3.IntegrityError as e:
        # Diferenciamos si el choque fue por username o por email
        if 'email' in str(e).lower():
            exito, mensaje = False, "Ya existe una cuenta con ese correo."
        else:
            exito, mensaje = False, "El nombre de usuario ya está en uso."
    finally:
        conexion.close()
    return exito, mensaje

def verificar_login(identificador, password):
    """Acepta username O email como identificador.
    Devuelve el username canónico si las credenciales son válidas, o None."""
    conexion = sqlite3.connect(DB_NAME)
    cursor = conexion.cursor()
    cursor.execute('''
        SELECT username, password_hash FROM Usuarios
        WHERE (username = ? COLLATE NOCASE OR email = ? COLLATE NOCASE)
          AND eliminada_en IS NULL
    ''', (identificador, identificador))
    resultado = cursor.fetchone()
    conexion.close()

    if resultado is None:
        return None
    if check_password_hash(resultado[1], password):
        return resultado[0]
    return None

def obtener_email(username):
    conexion = sqlite3.connect(DB_NAME)
    cursor = conexion.cursor()
    cursor.execute('SELECT email FROM Usuarios WHERE username = ? COLLATE NOCASE', (username,))
    fila = cursor.fetchone()
    conexion.close()
    return fila[0] if fila else None

def email_registrado(email):
    """Devuelve el username asociado a un email, o None. Se usa en el reset de contraseña."""
    conexion = sqlite3.connect(DB_NAME)
    cursor = conexion.cursor()
    cursor.execute('SELECT username FROM Usuarios WHERE email = ? COLLATE NOCASE', (email,))
    fila = cursor.fetchone()
    conexion.close()
    return fila[0] if fila else None

def actualizar_password(email, nueva_password):
    """Cambia la contraseña de la cuenta ligada a ese email (flujo de recuperación)."""
    conexion = sqlite3.connect(DB_NAME)
    cursor = conexion.cursor()
    hash_pass = generate_password_hash(nueva_password)
    cursor.execute('UPDATE Usuarios SET password_hash = ?, tiene_password = 1 '
                   'WHERE email = ? COLLATE NOCASE', (hash_pass, email))
    filas = cursor.rowcount
    conexion.commit()
    conexion.close()
    return filas > 0

def _generar_username_libre(cursor, base):
    """Deriva un username único a partir de una base (p.ej. el nombre de Google)."""
    limpio = ''.join(c for c in base if c.isalnum()) or 'jugador'
    limpio = limpio[:20]
    candidato = limpio
    intento = 0
    while True:
        cursor.execute('SELECT 1 FROM Usuarios WHERE username = ? COLLATE NOCASE', (candidato,))
        if not cursor.fetchone():
            return candidato
        intento += 1
        sufijo = str(intento)
        candidato = (limpio[:20 - len(sufijo)]) + sufijo

def registrar_o_loguear_google(google_id, email, nombre, crear=True):
    """Encuentra la cuenta por google_id o email.

    Con `crear=True` (botón de *registrarse*) la crea si no existe; con `crear=False`
    (botón de *iniciar sesión*) devuelve None en vez de fabricar una cuenta a espaldas
    del usuario — que es lo que hacía parecer que una cuenta borrada "revivía" al
    volver a pulsar Entrar con Google (Roadmap #23).
    Devuelve el username canónico, o None si no hay cuenta y no se puede crear.
    """
    conexion = sqlite3.connect(DB_NAME)
    cursor = conexion.cursor()

    # 1. ¿Ya la vinculamos antes por google_id? (Las cuentas borradas pierden el
    #    google_id, así que nunca reaparecen por aquí.)
    cursor.execute('SELECT username FROM Usuarios WHERE google_id = ? AND eliminada_en IS NULL',
                   (google_id,))
    fila = cursor.fetchone()
    if fila:
        conexion.close()
        return fila[0]

    # 2. ¿Hay una cuenta con ese email (registro clásico previo)? La vinculamos.
    if email:
        cursor.execute('SELECT username FROM Usuarios WHERE email = ? COLLATE NOCASE '
                       'AND eliminada_en IS NULL', (email,))
        fila = cursor.fetchone()
        if fila:
            cursor.execute('UPDATE Usuarios SET google_id = ? WHERE username = ?', (google_id, fila[0]))
            conexion.commit()
            conexion.close()
            return fila[0]

    if not crear:
        conexion.close()
        return None

    # 3. Cuenta nueva. Password aleatoria inutilizable (login solo vía Google hasta que resetee).
    username = _generar_username_libre(cursor, nombre or (email.split('@')[0] if email else 'jugador'))
    hash_pass = generate_password_hash(secrets.token_urlsafe(32))
    fecha_actual = datetime.now().strftime("%Y-%m-%d")
    cursor.execute('''
        INSERT INTO Usuarios (username, password_hash, email, google_id, fecha_registro,
                              tiene_password, codigo)
        VALUES (?, ?, ?, ?, ?, 0, ?)
    ''', (username, hash_pass, email, google_id, fecha_actual, _generar_codigo_libre(cursor)))
    conexion.commit()
    conexion.close()
    return username

def obtener_usuario(username):
    """Perfil completo del propio usuario (lo consume /auth/sesion). Incluye el
    correo y el estado de la cuenta porque solo se le manda a su dueño."""
    conexion = sqlite3.connect(DB_NAME)
    conexion.row_factory = sqlite3.Row
    cursor = conexion.cursor()
    cursor.execute('SELECT username, email, country, birthdate, victorias, derrotas, elo, fecha_registro, '
                   'COALESCE(victorias_4p,0) AS victorias_4p, COALESCE(derrotas_4p,0) AS derrotas_4p, '
                   'COALESCE(juegos_4p,0) AS juegos_4p, COALESCE(tiene_password,1) AS tiene_password, '
                   'username_cambiado_en, google_id, codigo, '
                   'COALESCE(is_admin,0) AS is_admin FROM Usuarios '
                   'WHERE username = ? AND eliminada_en IS NULL', (username,))
    fila = cursor.fetchone()
    conexion.close()

    if fila:
        usuario = dict(fila)
        total = usuario['victorias'] + usuario['derrotas']
        usuario['winrate'] = round((usuario['victorias'] / total) * 100, 1) if total > 0 else 0.0
        # google_id es un identificador de terceros: al cliente solo le hace falta
        # saber si la cuenta está vinculada, no el valor.
        usuario['google'] = bool(usuario.pop('google_id', None))
        usuario['tiene_password'] = bool(usuario['tiene_password'])
        usuario['is_admin'] = bool(usuario['is_admin'])
        usuario['dias_para_cambiar_username'] = _dias_restantes_username(usuario.pop('username_cambiado_en', None))
        return usuario
    return None

def obtener_leaderboard():
    conexion = sqlite3.connect(DB_NAME)
    conexion.row_factory = sqlite3.Row
    cursor = conexion.cursor()
    # Las cuentas borradas conservan su fila por el historial, pero no son jugadores:
    # fuera de la clasificación (Roadmap #23).
    cursor.execute('SELECT username, codigo, victorias, derrotas, elo FROM Usuarios '
                   'WHERE eliminada_en IS NULL')
    filas = cursor.fetchall()
    conexion.close()

    leaderboard = []
    for fila in filas:
        usuario = dict(fila)
        total = usuario['victorias'] + usuario['derrotas']
        winrate = round((usuario['victorias'] / total) * 100, 1) if total > 0 else 0.0

        leaderboard.append({
            'username': usuario['username'],
            'codigo': usuario['codigo'],
            'elo': usuario['elo'],
            'victorias': usuario['victorias'],
            'winrate': winrate
        })
    return leaderboard


# ==========================================================================
# AJUSTES DE CUENTA (Roadmap #22)
# --------------------------------------------------------------------------
# Cambiar nombre, correo y contraseña, y borrar la cuenta. Todas devuelven
# (exito:bool, codigo:str); `codigo` es una clave de traducción, no un texto,
# para que sea el cliente quien lo enseñe en el idioma que toque.
# ==========================================================================

DIAS_ESPERA_CAMBIO_USERNAME = 30


def _dias_restantes_username(fecha_iso):
    """Días que faltan para poder volver a cambiar de nombre (0 = ya puede)."""
    if not fecha_iso:
        return 0
    try:
        ultimo = datetime.strptime(fecha_iso, "%Y-%m-%d")
    except ValueError:
        return 0
    pasados = (datetime.now() - ultimo).days
    return max(0, DIAS_ESPERA_CAMBIO_USERNAME - pasados)


def verificar_password_usuario(username, password):
    """True si esa es la contraseña actual de la cuenta. Las cuentas de Google sin
    contraseña llevan un hash aleatorio, así que siempre darán False."""
    if not password:
        return False
    conexion = sqlite3.connect(DB_NAME)
    cursor = conexion.cursor()
    cursor.execute('SELECT password_hash FROM Usuarios WHERE username = ? COLLATE NOCASE', (username,))
    fila = cursor.fetchone()
    conexion.close()
    return bool(fila) and check_password_hash(fila[0], password)


def cambiar_username(username_actual, nuevo):
    """Renombra la cuenta. El resto de tablas guardan el id, así que amistades,
    grupos e historial de partidas sobreviven al cambio."""
    conexion = sqlite3.connect(DB_NAME)
    cursor = conexion.cursor()
    try:
        cursor.execute('SELECT id, username_cambiado_en FROM Usuarios WHERE username = ? COLLATE NOCASE',
                       (username_actual,))
        fila = cursor.fetchone()
        if not fila:
            return False, 'err_cuenta_no_encontrada'
        if _dias_restantes_username(fila[1]) > 0:
            return False, 'err_username_espera'

        # Dejamos pasar el cambio de mayúsculas/minúsculas del propio nombre.
        cursor.execute('SELECT id FROM Usuarios WHERE username = ? COLLATE NOCASE', (nuevo,))
        choque = cursor.fetchone()
        if choque and choque[0] != fila[0]:
            return False, 'err_username_en_uso'

        cursor.execute('UPDATE Usuarios SET username = ?, username_cambiado_en = ? WHERE id = ?',
                       (nuevo, datetime.now().strftime("%Y-%m-%d"), fila[0]))
        conexion.commit()
        return True, 'ok_username_cambiado'
    except sqlite3.IntegrityError:
        return False, 'err_username_en_uso'
    finally:
        conexion.close()


def cambiar_email(username, nuevo_email):
    """Fija el correo de la cuenta (ya verificado por el servidor con un código)."""
    conexion = sqlite3.connect(DB_NAME)
    cursor = conexion.cursor()
    try:
        cursor.execute('SELECT id FROM Usuarios WHERE email = ? COLLATE NOCASE', (nuevo_email,))
        fila = cursor.fetchone()
        if fila:
            cursor.execute('SELECT id FROM Usuarios WHERE username = ? COLLATE NOCASE', (username,))
            propio = cursor.fetchone()
            if not propio or propio[0] != fila[0]:
                return False, 'err_email_en_uso'

        cursor.execute('UPDATE Usuarios SET email = ? WHERE username = ? COLLATE NOCASE',
                       (nuevo_email, username))
        conexion.commit()
        return (cursor.rowcount > 0), ('ok_email_cambiado' if cursor.rowcount else 'err_cuenta_no_encontrada')
    except sqlite3.IntegrityError:
        return False, 'err_email_en_uso'
    finally:
        conexion.close()


def cambiar_password_usuario(username, nueva_password):
    """Cambia la contraseña de una cuenta identificada por su nombre. Marca
    tiene_password para que una cuenta de Google deje de pedir código."""
    conexion = sqlite3.connect(DB_NAME)
    cursor = conexion.cursor()
    cursor.execute('UPDATE Usuarios SET password_hash = ?, tiene_password = 1 '
                   'WHERE username = ? COLLATE NOCASE',
                   (generate_password_hash(nueva_password), username))
    filas = cursor.rowcount
    conexion.commit()
    conexion.close()
    return filas > 0


def anonimizar_usuario(username):
    """Borrado de cuenta. Elimina los datos personales (correo, país, fecha de
    nacimiento, vínculo con Google) y todo su rastro social, pero CONSERVA la fila
    con un nombre anónimo: Partidas/Partidas4 apuntan a este id y borrarlo dejaría
    a sus rivales con un historial y un ELO sin sentido.

    El nombre SÍ se libera para que otro pueda cogerlo (Roadmap #23): la fila pasa
    a llamarse '#CODIGO', que no es un username registrable (el regex de registro
    solo admite alfanuméricos), así que ni ocupa el nombre ni puede chocar con uno
    nuevo. Lo que identifica de verdad a ese jugador en el historial es su `codigo`,
    que no cambia ni se recicla nunca.
    Devuelve (exito, codigo_msg, nombre_anonimo)."""
    uid = obtener_id_usuario(username)
    if not uid:
        return False, 'err_cuenta_no_encontrada', None

    # 1. Salir de todos sus grupos reutilizando la misma lógica que el botón de
    #    salir: si era el dueño, la propiedad pasa al miembro más antiguo, y si el
    #    grupo se queda vacío desaparece.
    with _conn() as c:
        grupos = [g['group_id'] for g in
                  c.execute('SELECT group_id FROM GroupMembers WHERE user_id = ?', (uid,)).fetchall()]
    for gid in grupos:
        salir_del_grupo(gid, uid)

    conexion = _conn()
    cursor = conexion.cursor()
    try:
        # 2. Amistades y mensajes (directos y de grupo).
        cursor.execute('DELETE FROM Friendships WHERE user_low = ? OR user_high = ?', (uid, uid))
        cursor.execute('DELETE FROM Messages WHERE sender_id = ? OR recipient_id = ?', (uid, uid))

        # 3. La fila queda anónima, marcada como borrada y sin forma de volver a entrar.
        #    El código se conserva: es la etiqueta con la que el historial distingue a
        #    este jugador de quien herede su nombre.
        fila = cursor.execute('SELECT codigo FROM Usuarios WHERE id = ?', (uid,)).fetchone()
        codigo = (fila['codigo'] if fila else None) or _generar_codigo_libre(cursor)
        anonimo = '#' + codigo
        cursor.execute('''UPDATE Usuarios
                          SET username = ?, codigo = ?, password_hash = ?, email = NULL,
                              google_id = NULL, country = NULL, birthdate = NULL,
                              tiene_password = 0, eliminada_en = ?
                          WHERE id = ?''',
                       (anonimo, codigo, generate_password_hash(secrets.token_urlsafe(32)),
                        datetime.now().strftime("%Y-%m-%d"), uid))
        conexion.commit()
        return True, 'ok_cuenta_eliminada', anonimo
    finally:
        conexion.close()


# ==========================================================================
# CAPA SOCIAL (Roadmap #3): amigos, mensajes directos, grupos y clasificación
# --------------------------------------------------------------------------
# Todas las funciones guardan IDs de usuario (Usuarios.id), nunca usernames,
# como claves foráneas. Consultas siempre parametrizadas.
# ==========================================================================

MAX_MSG_LEN = 500
MAX_AMIGOS = 200
MAX_GRUPOS = 50
NOMBRE_GRUPO_MIN = 3
NOMBRE_GRUPO_MAX = 40


def _conn():
    c = sqlite3.connect(DB_NAME)
    c.row_factory = sqlite3.Row
    return c


def obtener_id_usuario(username):
    """Id de una cuenta VIVA. Las borradas se llaman '#CODIGO' y quedan fuera para
    que nadie pueda buscarlas ni mandarles solicitudes."""
    if not username:
        return None
    with _conn() as c:
        r = c.execute("SELECT id FROM Usuarios WHERE username = ? COLLATE NOCASE "
                      "AND eliminada_en IS NULL", (username,)).fetchone()
        return r['id'] if r else None


def obtener_username_por_id(user_id):
    with _conn() as c:
        r = c.execute("SELECT username FROM Usuarios WHERE id = ?", (user_id,)).fetchone()
        return r['username'] if r else None


def obtener_jugador_publico(user_id):
    """Ficha mínima para enseñar a terceros (historial, listados). Un jugador borrado
    se devuelve con `eliminada=True` y sin nombre, para que quien lo pinte lo marque
    como cuenta eliminada en vez de confundirlo con quien haya heredado su nombre."""
    with _conn() as c:
        r = c.execute("SELECT id, username, codigo, eliminada_en FROM Usuarios WHERE id = ?",
                      (user_id,)).fetchone()
    if not r:
        return None
    eliminada = r['eliminada_en'] is not None
    return {'id': r['id'], 'codigo': r['codigo'], 'eliminada': eliminada,
            'username': None if eliminada else r['username']}


# ---------------------------------------------------------------------------
# 1. Amistades
# ---------------------------------------------------------------------------

def _existe_usuario_id(c, user_id):
    return c.execute("SELECT 1 FROM Usuarios WHERE id = ?", (user_id,)).fetchone() is not None


def contar_amigos(user_id):
    with _conn() as c:
        r = c.execute("""SELECT COUNT(*) n FROM Friendships
                         WHERE (user_low=? OR user_high=?) AND status='accepted'""",
                      (user_id, user_id)).fetchone()
        return r['n']


def enviar_solicitud_amistad(from_id, to_id):
    """Crea una solicitud pendiente. Devuelve (ok:bool, codigo:str)."""
    if from_id == to_id:
        return (False, 'self')
    low, high = min(from_id, to_id), max(from_id, to_id)
    now = datetime.now().isoformat()
    with _conn() as c:
        if not _existe_usuario_id(c, to_id):
            return (False, 'no_existe')
        existing = c.execute(
            "SELECT status, requested_by FROM Friendships WHERE user_low=? AND user_high=?",
            (low, high)).fetchone()
        if existing:
            if existing['status'] == 'accepted':
                return (False, 'already_friends')
            if existing['status'] == 'blocked':
                return (False, 'blocked')
            return (False, 'already_pending')
        if contar_amigos(from_id) >= MAX_AMIGOS:
            return (False, 'limite')
        c.execute("""INSERT INTO Friendships(user_low,user_high,status,requested_by,created_at,updated_at)
                     VALUES(?,?,'pending',?,?,?)""", (low, high, from_id, now, now))
    return (True, 'sent')


def responder_solicitud(user_id, other_id, aceptar):
    """Solo el destinatario (no el solicitante) puede responder."""
    low, high = min(user_id, other_id), max(user_id, other_id)
    now = datetime.now().isoformat()
    with _conn() as c:
        row = c.execute("SELECT requested_by,status FROM Friendships WHERE user_low=? AND user_high=?",
                        (low, high)).fetchone()
        if not row or row['status'] != 'pending' or row['requested_by'] == user_id:
            return False
        if aceptar:
            c.execute("UPDATE Friendships SET status='accepted', updated_at=? WHERE user_low=? AND user_high=?",
                      (now, low, high))
        else:
            c.execute("DELETE FROM Friendships WHERE user_low=? AND user_high=?", (low, high))
    return True


def eliminar_amistad(user_id, other_id):
    low, high = min(user_id, other_id), max(user_id, other_id)
    with _conn() as c:
        c.execute("DELETE FROM Friendships WHERE user_low=? AND user_high=? AND status!='blocked'",
                  (low, high))
    return True


def bloquear_usuario(user_id, other_id):
    low, high = min(user_id, other_id), max(user_id, other_id)
    now = datetime.now().isoformat()
    with _conn() as c:
        existe = c.execute("SELECT 1 FROM Friendships WHERE user_low=? AND user_high=?",
                           (low, high)).fetchone()
        if existe:
            c.execute("""UPDATE Friendships SET status='blocked', requested_by=?, updated_at=?
                         WHERE user_low=? AND user_high=?""", (user_id, now, low, high))
        else:
            c.execute("""INSERT INTO Friendships(user_low,user_high,status,requested_by,created_at,updated_at)
                         VALUES(?,?,'blocked',?,?,?)""", (low, high, user_id, now, now))
    return True


def son_amigos(a_id, b_id):
    if a_id == b_id:
        return False
    low, high = min(a_id, b_id), max(a_id, b_id)
    with _conn() as c:
        r = c.execute("SELECT 1 FROM Friendships WHERE user_low=? AND user_high=? AND status='accepted'",
                      (low, high)).fetchone()
        return r is not None


def listar_amigos(user_id):
    """Amigos aceptados con sus estadísticas públicas (el punto online se añade en la ruta)."""
    with _conn() as c:
        rows = c.execute("""
            SELECT u.id, u.username, u.codigo, u.elo, u.victorias, u.derrotas
            FROM Friendships f
            JOIN Usuarios u ON u.id = CASE WHEN f.user_low=? THEN f.user_high ELSE f.user_low END
            WHERE (f.user_low=? OR f.user_high=?) AND f.status='accepted'
            ORDER BY u.username COLLATE NOCASE
        """, (user_id, user_id, user_id)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            total = d['victorias'] + d['derrotas']
            d['winrate'] = round(d['victorias'] / total * 100, 1) if total else 0.0
            out.append(d)
        return out


def listar_solicitudes_pendientes(user_id):
    """Solicitudes entrantes (alguien me pidió amistad)."""
    with _conn() as c:
        rows = c.execute("""
            SELECT u.id, u.username FROM Friendships f
            JOIN Usuarios u ON u.id = f.requested_by
            WHERE (f.user_low=? OR f.user_high=?) AND f.status='pending' AND f.requested_by != ?
            ORDER BY f.created_at DESC
        """, (user_id, user_id, user_id)).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# 2. Mensajes directos
# ---------------------------------------------------------------------------

def enviar_mensaje_dm(sender_id, recipient_id, body):
    body = (body or '').strip()
    if not body or len(body) > MAX_MSG_LEN:
        return (False, None)
    if not son_amigos(sender_id, recipient_id):
        return (False, None)
    now = datetime.now().isoformat()
    with _conn() as c:
        cur = c.execute("""INSERT INTO Messages(sender_id,recipient_id,body,created_at)
                           VALUES(?,?,?,?)""", (sender_id, recipient_id, body, now))
        msg_id = cur.lastrowid
    return (True, {'id': msg_id, 'sender_id': sender_id, 'recipient_id': recipient_id,
                   'body': body, 'created_at': now})


def obtener_conversacion(user_id, friend_id, before_id=None, limit=50):
    """Historial de DM paginado (cronológico). Marca como leídos los recibidos."""
    with _conn() as c:
        params = [user_id, friend_id, friend_id, user_id]
        clause = ""
        if before_id:
            clause = "AND id < ?"
            params.append(before_id)
        rows = c.execute(f"""
            SELECT * FROM Messages
            WHERE recipient_id IS NOT NULL
              AND ((sender_id=? AND recipient_id=?) OR (sender_id=? AND recipient_id=?)) {clause}
            ORDER BY id DESC LIMIT ?""", (*params, limit)).fetchall()
        c.execute("UPDATE Messages SET read_at=? WHERE recipient_id=? AND sender_id=? AND read_at IS NULL",
                  (datetime.now().isoformat(), user_id, friend_id))
        return [dict(r) for r in rows][::-1]


def contar_no_leidos(user_id):
    """{sender_id: n} de DMs sin leer, para las insignias."""
    with _conn() as c:
        rows = c.execute("""SELECT sender_id, COUNT(*) n FROM Messages
                            WHERE recipient_id=? AND read_at IS NULL GROUP BY sender_id""",
                         (user_id,)).fetchall()
        return {r['sender_id']: r['n'] for r in rows}


# ---------------------------------------------------------------------------
# 3. Grupos
# ---------------------------------------------------------------------------

def contar_grupos_de(user_id):
    with _conn() as c:
        r = c.execute("SELECT COUNT(*) n FROM GroupMembers WHERE user_id=?", (user_id,)).fetchone()
        return r['n']


def crear_grupo(owner_id, name):
    name = (name or '').strip()
    if not (NOMBRE_GRUPO_MIN <= len(name) <= NOMBRE_GRUPO_MAX):
        return (False, 'nombre')
    if contar_grupos_de(owner_id) >= MAX_GRUPOS:
        return (False, 'limite')
    now = datetime.now().isoformat()
    with _conn() as c:
        gid = c.execute("INSERT INTO Groups(name,owner_id,created_at) VALUES(?,?,?)",
                        (name, owner_id, now)).lastrowid
        c.execute("INSERT INTO GroupMembers(group_id,user_id,role,joined_at) VALUES(?,?, 'owner', ?)",
                  (gid, owner_id, now))
    return (True, gid)


def obtener_grupo(group_id):
    with _conn() as c:
        r = c.execute("SELECT id, name, owner_id, created_at, invite_policy FROM Groups WHERE id=?",
                      (group_id,)).fetchone()
        return dict(r) if r else None


def es_miembro(group_id, user_id):
    with _conn() as c:
        r = c.execute("SELECT 1 FROM GroupMembers WHERE group_id=? AND user_id=?",
                      (group_id, user_id)).fetchone()
        return r is not None


def rol_en_grupo(group_id, user_id):
    with _conn() as c:
        r = c.execute("SELECT role FROM GroupMembers WHERE group_id=? AND user_id=?",
                      (group_id, user_id)).fetchone()
        return r['role'] if r else None


def puede_administrar_grupo(group_id, user_id):
    return rol_en_grupo(group_id, user_id) in ('owner', 'admin')


def puede_invitar(group_id, user_id):
    """Según la política del grupo: solo admins, o cualquier miembro."""
    g = obtener_grupo(group_id)
    if not g:
        return False
    if g.get('invite_policy') == 'all':
        return es_miembro(group_id, user_id)
    return puede_administrar_grupo(group_id, user_id)


def añadir_miembro(group_id, user_id, by_id):
    """Quién puede añadir depende de invite_policy. UNIQUE evita duplicados."""
    if not puede_invitar(group_id, by_id):
        return (False, 'permiso')
    if not obtener_grupo(group_id):
        return (False, 'no_existe')
    if es_miembro(group_id, user_id):
        return (False, 'ya_miembro')
    if contar_grupos_de(user_id) >= MAX_GRUPOS:
        return (False, 'limite')
    now = datetime.now().isoformat()
    with _conn() as c:
        c.execute("""INSERT OR IGNORE INTO GroupMembers(group_id,user_id,role,joined_at)
                     VALUES(?,?, 'member', ?)""", (group_id, user_id, now))
    return (True, 'ok')


def salir_del_grupo(group_id, user_id):
    """Si el owner se va: transfiere la propiedad al miembro más antiguo, o borra el grupo si queda vacío."""
    with _conn() as c:
        row = c.execute("SELECT role FROM GroupMembers WHERE group_id=? AND user_id=?",
                        (group_id, user_id)).fetchone()
        if not row:
            return False
        era_owner = (row['role'] == 'owner')
        c.execute("DELETE FROM GroupMembers WHERE group_id=? AND user_id=?", (group_id, user_id))
        restantes = c.execute("""SELECT user_id FROM GroupMembers WHERE group_id=?
                                 ORDER BY joined_at ASC""", (group_id,)).fetchall()
        if not restantes:
            c.execute("DELETE FROM Groups WHERE id=?", (group_id,))
        elif era_owner:
            nuevo = restantes[0]['user_id']
            c.execute("UPDATE GroupMembers SET role='owner' WHERE group_id=? AND user_id=?",
                      (group_id, nuevo))
            c.execute("UPDATE Groups SET owner_id=? WHERE id=?", (nuevo, group_id))
    return True


def listar_grupos_de(user_id):
    """Grupos a los que pertenezco, con nº de miembros y no leídos (por last_read_id)."""
    with _conn() as c:
        rows = c.execute("""
            SELECT g.id, g.name, g.owner_id, gm.role, gm.last_read_id
            FROM GroupMembers gm JOIN Groups g ON g.id = gm.group_id
            WHERE gm.user_id=? ORDER BY g.name COLLATE NOCASE
        """, (user_id,)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            n_miembros = c.execute("SELECT COUNT(*) n FROM GroupMembers WHERE group_id=?",
                                   (d['id'],)).fetchone()['n']
            no_leidos = c.execute("""SELECT COUNT(*) n FROM Messages
                                     WHERE group_id=? AND id>? AND sender_id!=?""",
                                  (d['id'], d['last_read_id'] or 0, user_id)).fetchone()['n']
            d['miembros'] = n_miembros
            d['no_leidos'] = no_leidos
            out.append(d)
        return out


def listar_miembros(group_id):
    with _conn() as c:
        rows = c.execute("""
            SELECT u.id, u.username, gm.role FROM GroupMembers gm
            JOIN Usuarios u ON u.id = gm.user_id
            WHERE gm.group_id=? ORDER BY
              CASE gm.role WHEN 'owner' THEN 0 WHEN 'admin' THEN 1 ELSE 2 END,
              u.username COLLATE NOCASE
        """, (group_id,)).fetchall()
        return [dict(r) for r in rows]


def enviar_mensaje_grupo(sender_id, group_id, body):
    body = (body or '').strip()
    if not body or len(body) > MAX_MSG_LEN:
        return (False, None)
    if not es_miembro(group_id, sender_id):
        return (False, None)
    now = datetime.now().isoformat()
    with _conn() as c:
        cur = c.execute("""INSERT INTO Messages(sender_id,group_id,body,created_at)
                           VALUES(?,?,?,?)""", (sender_id, group_id, body, now))
        msg_id = cur.lastrowid
        # el que envía ya ha "leído" hasta su propio mensaje
        c.execute("UPDATE GroupMembers SET last_read_id=? WHERE group_id=? AND user_id=?",
                  (msg_id, group_id, sender_id))
    return (True, {'id': msg_id, 'sender_id': sender_id, 'group_id': group_id,
                   'body': body, 'created_at': now})


def obtener_mensajes_grupo(group_id, user_id, before_id=None, limit=50):
    if not es_miembro(group_id, user_id):
        return None
    with _conn() as c:
        params = [group_id]
        clause = ""
        if before_id:
            clause = "AND id < ?"
            params.append(before_id)
        rows = c.execute(f"""
            SELECT m.*, u.username AS sender_name FROM Messages m
            JOIN Usuarios u ON u.id = m.sender_id
            WHERE m.group_id=? {clause}
            ORDER BY m.id DESC LIMIT ?""", (*params, limit)).fetchall()
        mensajes = [dict(r) for r in rows][::-1]
        if mensajes:
            nuevo_cursor = max(m['id'] for m in mensajes)
            c.execute("""UPDATE GroupMembers SET last_read_id=?
                         WHERE group_id=? AND user_id=? AND last_read_id < ?""",
                      (nuevo_cursor, group_id, user_id, nuevo_cursor))
        return mensajes


def cambiar_rol_miembro(group_id, actor_id, target_id, nuevo_rol):
    """Owner/admin cambia el rol de otro miembro. Nunca sobre el propietario original."""
    if nuevo_rol not in ('admin', 'member'):
        return (False, 'bad')
    if not puede_administrar_grupo(group_id, actor_id):
        return (False, 'permiso')
    g = obtener_grupo(group_id)
    if not g:
        return (False, 'no_existe')
    if target_id == g['owner_id']:
        return (False, 'owner')          # el creador original es intocable
    if not es_miembro(group_id, target_id):
        return (False, 'no_miembro')
    with _conn() as c:
        c.execute("UPDATE GroupMembers SET role=? WHERE group_id=? AND user_id=?",
                  (nuevo_rol, group_id, target_id))
    return (True, 'ok')


def expulsar_miembro(group_id, actor_id, target_id):
    """Owner/admin expulsa a un miembro. Nunca al propietario ni a uno mismo."""
    if not puede_administrar_grupo(group_id, actor_id):
        return (False, 'permiso')
    g = obtener_grupo(group_id)
    if not g:
        return (False, 'no_existe')
    if target_id == g['owner_id']:
        return (False, 'owner')
    if target_id == actor_id:
        return (False, 'self')
    if not es_miembro(group_id, target_id):
        return (False, 'no_miembro')
    with _conn() as c:
        c.execute("DELETE FROM GroupMembers WHERE group_id=? AND user_id=?", (group_id, target_id))
    return (True, 'ok')


def actualizar_invite_policy(group_id, actor_id, policy):
    """Solo admins/owner cambian quién puede añadir miembros ('admins' | 'all')."""
    if policy not in ('admins', 'all'):
        return (False, 'bad')
    if not puede_administrar_grupo(group_id, actor_id):
        return (False, 'permiso')
    with _conn() as c:
        c.execute("UPDATE Groups SET invite_policy=? WHERE id=?", (policy, group_id))
    return (True, 'ok')


def leaderboard_grupo(group_id):
    """Clasificación PROPIA del grupo.

    El ELO y el winrate se calculan **solo** con las partidas jugadas entre miembros
    del grupo, y únicamente las disputadas después de que ambos jugadores estuvieran ya
    en el grupo (fecha de la partida >= joined_at de los dos). Cada jugador arranca de
    1200 y se reproduce el historial intra-grupo en orden cronológico. Mismo formato de
    salida que obtener_leaderboard() para reutilizar el render del cliente.
    """
    with _conn() as c:
        miembros = c.execute("""
            SELECT gm.user_id, gm.joined_at, u.username
            FROM GroupMembers gm JOIN Usuarios u ON u.id = gm.user_id
            WHERE gm.group_id = ?""", (group_id,)).fetchall()
        if not miembros:
            return []
        join_at = {m['user_id']: m['joined_at'] for m in miembros}
        nombre = {m['user_id']: m['username'] for m in miembros}
        ids = list(join_at.keys())

        # Partidas entre dos miembros del grupo, en orden cronológico.
        ph = ",".join("?" * len(ids))
        partidas = c.execute(f"""
            SELECT fecha, ganador_id, perdedor_id FROM Partidas
            WHERE ganador_id IN ({ph}) AND perdedor_id IN ({ph})
            ORDER BY fecha ASC""", (*ids, *ids)).fetchall()

    elo = {uid: 1200.0 for uid in ids}
    victorias = {uid: 0 for uid in ids}
    derrotas = {uid: 0 for uid in ids}

    for p in partidas:
        g, d, f = p['ganador_id'], p['perdedor_id'], p['fecha']
        # Solo cuenta si la partida ocurrió después de que AMBOS se unieran al grupo.
        if f < join_at[g] or f < join_at[d]:
            continue
        nuevo_g, nuevo_d, _ = procesar_partida_mus(elo[g], elo[d], 1, 0)
        elo[g], elo[d] = nuevo_g, nuevo_d
        victorias[g] += 1
        derrotas[d] += 1

    out = []
    for uid in ids:
        total = victorias[uid] + derrotas[uid]
        out.append({'username': nombre[uid], 'elo': round(elo[uid], 1),
                    'victorias': victorias[uid],
                    'winrate': round(victorias[uid] / total * 100, 1) if total else 0.0})
    out.sort(key=lambda x: (-x['elo'], x['username'].lower()))
    return out


# ==========================================================================
# PANEL DE ADMINISTRACIÓN (Roadmap #13)
# --------------------------------------------------------------------------
# Capa de datos del panel: permisos, cuentas, variables globales, auditoría,
# soporte y anuncios. Igual que el resto del módulo, todo va parametrizado y
# las funciones devuelven estructuras planas para que `admin.py` solo tenga que
# serializarlas.
# ==========================================================================

MAX_TICKET_ASUNTO = 120
MAX_TICKET_BODY = 4000
TIPOS_TICKET = ('bug', 'cuenta', 'sugerencia', 'abuso', 'otro')
ESTADOS_TICKET = ('abierto', 'respondido', 'resuelto')


# --- 1. Permisos ------------------------------------------------------------

def es_admin(username):
    """True si esa cuenta viva tiene el bit de administrador."""
    if not username:
        return False
    with _conn() as c:
        r = c.execute("SELECT COALESCE(is_admin,0) a FROM Usuarios "
                      "WHERE username = ? COLLATE NOCASE AND eliminada_en IS NULL",
                      (username,)).fetchone()
        return bool(r and r['a'])


def esta_baneado(username):
    """(baneado:bool, motivo:str|None). Una cuenta baneada no puede entrar ni
    abrir un socket, pero conserva su fila y su historial."""
    if not username:
        return (False, None)
    with _conn() as c:
        r = c.execute("SELECT COALESCE(banned,0) b, ban_motivo FROM Usuarios "
                      "WHERE username = ? COLLATE NOCASE", (username,)).fetchone()
        if not r or not r['b']:
            return (False, None)
        return (True, r['ban_motivo'])


def marcar_admin(username, valor=True):
    """Otorga o retira el bit de administrador. Devuelve (ok, codigo)."""
    uid = obtener_id_usuario(username)
    if not uid:
        return (False, 'err_cuenta_no_encontrada')
    with _conn() as c:
        c.execute("UPDATE Usuarios SET is_admin = ? WHERE id = ?", (1 if valor else 0, uid))
        c.commit()
    return (True, 'ok')


def contar_admins():
    with _conn() as c:
        return c.execute("SELECT COUNT(*) n FROM Usuarios "
                         "WHERE COALESCE(is_admin,0)=1 AND eliminada_en IS NULL").fetchone()['n']


# --- 2. Cuentas -------------------------------------------------------------

_CAMPOS_ADMIN_USUARIO = (
    "id, username, codigo, email, elo, victorias, derrotas, "
    "COALESCE(victorias_4p,0) victorias_4p, COALESCE(derrotas_4p,0) derrotas_4p, "
    "fecha_registro, COALESCE(is_admin,0) is_admin, COALESCE(banned,0) banned, "
    "ban_motivo, eliminada_en, google_id"
)


def _fila_usuario_admin(r):
    d = dict(r)
    d['is_admin'] = bool(d['is_admin'])
    d['banned'] = bool(d['banned'])
    d['eliminada'] = d.pop('eliminada_en') is not None
    d['google'] = bool(d.pop('google_id', None))
    total = (d['victorias'] or 0) + (d['derrotas'] or 0)
    d['winrate'] = round(d['victorias'] / total * 100, 1) if total else 0.0
    return d


def buscar_usuarios(texto='', limite=50, incluir_eliminadas=False):
    """Búsqueda para el panel: por nombre, correo o código público. Sin texto
    devuelve las cuentas más recientes."""
    texto = (texto or '').strip()
    condiciones = [] if incluir_eliminadas else ['eliminada_en IS NULL']
    args = []
    if texto:
        codigo = normalizar_codigo(texto)
        if codigo:
            condiciones.append('codigo = ?')
            args.append(codigo)
        else:
            condiciones.append('(username LIKE ? COLLATE NOCASE OR email LIKE ? COLLATE NOCASE)')
            args += [f'%{texto}%', f'%{texto}%']
    where = ('WHERE ' + ' AND '.join(condiciones)) if condiciones else ''
    limite = max(1, min(int(limite or 50), 200))
    with _conn() as c:
        filas = c.execute(f"SELECT {_CAMPOS_ADMIN_USUARIO} FROM Usuarios {where} "
                          f"ORDER BY id DESC LIMIT ?", (*args, limite)).fetchall()
    return [_fila_usuario_admin(r) for r in filas]


def obtener_usuario_admin(user_id):
    with _conn() as c:
        r = c.execute(f"SELECT {_CAMPOS_ADMIN_USUARIO} FROM Usuarios WHERE id = ?",
                      (user_id,)).fetchone()
    return _fila_usuario_admin(r) if r else None


def admin_banear(user_id, banear=True, motivo=None):
    """Activa o levanta el baneo. Devuelve (ok, username)."""
    with _conn() as c:
        r = c.execute("SELECT username FROM Usuarios WHERE id = ?", (user_id,)).fetchone()
        if not r:
            return (False, None)
        c.execute("UPDATE Usuarios SET banned = ?, ban_motivo = ?, ban_en = ? WHERE id = ?",
                  (1 if banear else 0,
                   (motivo or '').strip()[:200] if banear else None,
                   datetime.now().isoformat() if banear else None,
                   user_id))
        c.commit()
    return (True, r['username'])


def admin_editar_estadisticas(user_id, elo=None, victorias=None, derrotas=None):
    """Corrección manual de ELO/victorias/derrotas (partidas mal registradas,
    trampas revertidas…). Solo toca los campos que se pasan."""
    campos, args = [], []
    if elo is not None:
        campos.append('elo = ?')
        args.append(round(float(elo), 1))
    if victorias is not None:
        campos.append('victorias = ?')
        args.append(max(0, int(victorias)))
    if derrotas is not None:
        campos.append('derrotas = ?')
        args.append(max(0, int(derrotas)))
    if not campos:
        return False
    with _conn() as c:
        cur = c.execute(f"UPDATE Usuarios SET {', '.join(campos)} WHERE id = ?", (*args, user_id))
        c.commit()
        return cur.rowcount > 0


# --- 3. Variables globales (tabla Config) -----------------------------------
#
# Estas variables se leen EN CALIENTE desde el bucle de juego: `bot_delay` en
# cada turno de bot (server.py, server_mus4.py), `senas_orden` en cada seña y
# `senas_foco_*` en cada mirada (server_mus4.py). Cada lectura abría un
# sqlite3.connect() nuevo, y sqlite3 es una extensión en C que eventlet NO puede
# parchear: esa llamada bloquea el hilo entero, es decir TODAS las partidas del
# proceso, no solo la que la pidió. Con varias mesas a la vez eso se nota.
#
# La tabla la toca un administrador de uvas a peras, así que se cachea en
# memoria. Como solo hay un worker eventlet (ver Setup-and-Deployment), basta
# con que config_set/config_delete invaliden el caché al escribir: el panel
# sigue viéndose "en caliente", instantáneo, sin reiniciar. El TTL es solo una
# red de seguridad por si alguien edita la tabla por fuera del panel.

_CONFIG_TTL = 30.0
_config_cache = {}          # clave -> (valor_crudo, momento_de_lectura)


def config_invalidar_cache():
    """Suelta el caché de Config. Lo llaman config_set y config_delete."""
    _config_cache.clear()


def config_get(clave, defecto=None):
    ahora = time.time()
    guardado = _config_cache.get(clave)
    if guardado is not None and (ahora - guardado[1]) < _CONFIG_TTL:
        crudo = guardado[0]
    else:
        with _conn() as c:
            r = c.execute("SELECT value FROM Config WHERE key = ?", (clave,)).fetchone()
        # Se cachea el valor CRUDO (None incluido), nunca el ya sustituido por
        # el defecto: cada llamante pasa el suyo y no tienen por qué coincidir.
        crudo = r['value'] if r else None
        _config_cache[clave] = (crudo, ahora)
    return crudo if crudo is not None else defecto


def config_get_float(clave, defecto):
    try:
        return float(config_get(clave, defecto))
    except (TypeError, ValueError):
        return defecto


def config_set(clave, valor, por=None):
    with _conn() as c:
        c.execute("""INSERT INTO Config(key, value, updated_at, updated_by) VALUES(?,?,?,?)
                     ON CONFLICT(key) DO UPDATE SET value=excluded.value,
                        updated_at=excluded.updated_at, updated_by=excluded.updated_by""",
                  (clave, None if valor is None else str(valor),
                   datetime.now().isoformat(), por))
        c.commit()
    config_invalidar_cache()
    return True


def config_delete(clave):
    with _conn() as c:
        c.execute("DELETE FROM Config WHERE key = ?", (clave,))
        c.commit()
    config_invalidar_cache()
    return True


def config_all():
    with _conn() as c:
        filas = c.execute("SELECT key, value, updated_at, updated_by FROM Config "
                          "ORDER BY key").fetchall()
    return [dict(r) for r in filas]


# --- 4. Auditoría -----------------------------------------------------------

def registrar_auditoria(admin, accion, objetivo=None, detalle=None, ip=None):
    with _conn() as c:
        c.execute("INSERT INTO AdminAudit(fecha, admin, accion, objetivo, detalle, ip) "
                  "VALUES(?,?,?,?,?,?)",
                  (datetime.now().isoformat(), admin, accion,
                   objetivo, detalle, ip))
        c.commit()


def listar_auditoria(limite=100):
    limite = max(1, min(int(limite or 100), 500))
    with _conn() as c:
        filas = c.execute("SELECT * FROM AdminAudit ORDER BY id DESC LIMIT ?", (limite,)).fetchall()
    return [dict(r) for r in filas]


# --- 5. Soporte -------------------------------------------------------------

def crear_ticket(user_id, asunto, cuerpo, tipo='otro'):
    """Abre un hilo de soporte con su primer mensaje. Devuelve (ok, id|codigo)."""
    asunto = (asunto or '').strip()
    cuerpo = (cuerpo or '').strip()
    if not asunto or not cuerpo:
        return (False, 'vacio')
    if len(asunto) > MAX_TICKET_ASUNTO or len(cuerpo) > MAX_TICKET_BODY:
        return (False, 'demasiado_largo')
    if tipo not in TIPOS_TICKET:
        tipo = 'otro'
    ahora = datetime.now().isoformat()
    autor_nombre = obtener_username_por_id(user_id)
    with _conn() as c:
        cur = c.execute("""INSERT INTO SupportTickets
                           (user_id, asunto, tipo, estado, created_at, updated_at,
                            leido_admin, leido_user)
                           VALUES(?,?,?,'abierto',?,?,0,1)""",
                        (user_id, asunto, tipo, ahora, ahora))
        ticket_id = cur.lastrowid
        c.execute("""INSERT INTO SupportMessages(ticket_id, autor, autor_nombre, body, created_at)
                     VALUES(?,'user',?,?,?)""",
                  (ticket_id, autor_nombre, cuerpo, ahora))
        c.commit()
    return (True, ticket_id)


def responder_ticket(ticket_id, autor, autor_nombre, cuerpo):
    """Añade un mensaje al hilo. `autor` es 'user' o 'admin'; el estado se mueve a
    'respondido' cuando contesta el administrador y a 'abierto' cuando escribe el
    usuario, de modo que la bandeja del panel siempre enseña lo que falta atender.
    Devuelve (ok, mensaje|codigo)."""
    cuerpo = (cuerpo or '').strip()
    if not cuerpo:
        return (False, 'vacio')
    if len(cuerpo) > MAX_TICKET_BODY:
        return (False, 'demasiado_largo')
    if autor not in ('user', 'admin'):
        return (False, 'autor_invalido')
    ahora = datetime.now().isoformat()
    with _conn() as c:
        t = c.execute("SELECT id FROM SupportTickets WHERE id = ?", (ticket_id,)).fetchone()
        if not t:
            return (False, 'no_existe')
        cur = c.execute("""INSERT INTO SupportMessages(ticket_id, autor, autor_nombre, body, created_at)
                           VALUES(?,?,?,?,?)""",
                        (ticket_id, autor, autor_nombre, cuerpo, ahora))
        if autor == 'admin':
            c.execute("""UPDATE SupportTickets SET estado='respondido', updated_at=?,
                         leido_user=0, leido_admin=1 WHERE id=?""", (ahora, ticket_id))
        else:
            c.execute("""UPDATE SupportTickets SET estado='abierto', updated_at=?,
                         leido_admin=0, leido_user=1 WHERE id=?""", (ahora, ticket_id))
        c.commit()
        return (True, {'id': cur.lastrowid, 'ticket_id': ticket_id, 'autor': autor,
                       'autor_nombre': autor_nombre, 'body': cuerpo, 'created_at': ahora})


def cambiar_estado_ticket(ticket_id, estado):
    if estado not in ESTADOS_TICKET:
        return False
    with _conn() as c:
        cur = c.execute("UPDATE SupportTickets SET estado = ?, updated_at = ? WHERE id = ?",
                        (estado, datetime.now().isoformat(), ticket_id))
        c.commit()
        return cur.rowcount > 0


def _fila_ticket(r):
    d = dict(r)
    d['leido_admin'] = bool(d.get('leido_admin'))
    d['leido_user'] = bool(d.get('leido_user'))
    return d


def listar_tickets(estado=None, limite=100):
    """Bandeja del administrador. Sin `estado` devuelve todos menos los resueltos."""
    limite = max(1, min(int(limite or 100), 300))
    where = "WHERE t.estado = ?" if estado in ESTADOS_TICKET else "WHERE t.estado != 'resuelto'"
    args = [estado] if estado in ESTADOS_TICKET else []
    with _conn() as c:
        filas = c.execute(f"""
            SELECT t.*, u.username, u.codigo, u.eliminada_en,
                   (SELECT COUNT(*) FROM SupportMessages m WHERE m.ticket_id = t.id) n_mensajes
            FROM SupportTickets t LEFT JOIN Usuarios u ON u.id = t.user_id
            {where} ORDER BY t.updated_at DESC LIMIT ?""", (*args, limite)).fetchall()
    return [_fila_ticket(r) for r in filas]


def listar_tickets_de(user_id):
    with _conn() as c:
        filas = c.execute("""SELECT t.*,
                             (SELECT COUNT(*) FROM SupportMessages m WHERE m.ticket_id = t.id) n_mensajes
                             FROM SupportTickets t WHERE t.user_id = ?
                             ORDER BY t.updated_at DESC LIMIT 50""", (user_id,)).fetchall()
    return [_fila_ticket(r) for r in filas]


def obtener_ticket(ticket_id):
    with _conn() as c:
        r = c.execute("""SELECT t.*, u.username, u.codigo FROM SupportTickets t
                         LEFT JOIN Usuarios u ON u.id = t.user_id WHERE t.id = ?""",
                      (ticket_id,)).fetchone()
    return _fila_ticket(r) if r else None


def mensajes_ticket(ticket_id):
    with _conn() as c:
        filas = c.execute("SELECT * FROM SupportMessages WHERE ticket_id = ? ORDER BY id",
                          (ticket_id,)).fetchall()
    return [dict(r) for r in filas]


def marcar_ticket_leido(ticket_id, por):
    """`por` es 'admin' o 'user': quien abre el hilo deja de tener novedades."""
    columna = 'leido_admin' if por == 'admin' else 'leido_user'
    with _conn() as c:
        c.execute(f"UPDATE SupportTickets SET {columna} = 1 WHERE id = ?", (ticket_id,))
        c.commit()


def contar_tickets_pendientes():
    """Hilos con algo por leer del lado del administrador."""
    with _conn() as c:
        return c.execute("SELECT COUNT(*) n FROM SupportTickets "
                         "WHERE COALESCE(leido_admin,0)=0 AND estado != 'resuelto'").fetchone()['n']


def contar_soporte_no_leido(user_id):
    """Respuestas del administrador que el usuario todavía no ha abierto."""
    with _conn() as c:
        return c.execute("SELECT COUNT(*) n FROM SupportTickets "
                         "WHERE user_id = ? AND COALESCE(leido_user,1)=0", (user_id,)).fetchone()['n']


# --- 6. Anuncios ------------------------------------------------------------

def crear_anuncio(tipo, titulo, cuerpo, creado_por, audiencia='todos',
                  group_id=None, destinatarios=None, expira_en=None):
    """Crea un aviso. Devuelve (ok, id|codigo).

    `destinatarios` es una lista de Usuarios.id (solo si audiencia='usuarios');
    se guarda como CSV porque son listas cortas que solo se leen enteras."""
    cuerpo = (cuerpo or '').strip()
    if not cuerpo:
        return (False, 'vacio')
    if tipo not in ('notificacion', 'pin'):
        return (False, 'tipo_invalido')
    if audiencia not in ('todos', 'grupo', 'usuarios'):
        return (False, 'audiencia_invalida')
    if audiencia == 'grupo' and not group_id:
        return (False, 'sin_grupo')
    csv_dest = None
    if audiencia == 'usuarios':
        ids = [int(i) for i in (destinatarios or [])]
        if not ids:
            return (False, 'sin_destinatarios')
        csv_dest = ','.join(str(i) for i in ids)
    with _conn() as c:
        cur = c.execute("""INSERT INTO Anuncios
                           (tipo, titulo, cuerpo, audiencia, group_id, destinatarios,
                            creado_por, created_at, expira_en, activo)
                           VALUES(?,?,?,?,?,?,?,?,?,1)""",
                        (tipo, (titulo or '').strip()[:120], cuerpo[:2000], audiencia,
                         group_id, csv_dest, creado_por, datetime.now().isoformat(), expira_en))
        c.commit()
        return (True, cur.lastrowid)


def desactivar_anuncio(anuncio_id):
    with _conn() as c:
        cur = c.execute("UPDATE Anuncios SET activo = 0 WHERE id = ?", (anuncio_id,))
        c.commit()
        return cur.rowcount > 0


def listar_anuncios(limite=50):
    with _conn() as c:
        filas = c.execute("SELECT * FROM Anuncios ORDER BY id DESC LIMIT ?", (limite,)).fetchall()
    out = []
    for r in filas:
        d = dict(r)
        d['activo'] = bool(d['activo'])
        d['caducado'] = bool(d['expira_en'] and d['expira_en'] < datetime.now().isoformat())
        out.append(d)
    return out


def destinatarios_de(anuncio_id):
    """Usernames a los que va dirigido un anuncio (para empujarlo por socket)."""
    with _conn() as c:
        a = c.execute("SELECT audiencia, group_id, destinatarios FROM Anuncios WHERE id = ?",
                      (anuncio_id,)).fetchone()
        if not a:
            return []
        if a['audiencia'] == 'todos':
            filas = c.execute("SELECT username FROM Usuarios WHERE eliminada_en IS NULL").fetchall()
        elif a['audiencia'] == 'grupo':
            filas = c.execute("""SELECT u.username FROM GroupMembers g JOIN Usuarios u ON u.id = g.user_id
                                 WHERE g.group_id = ? AND u.eliminada_en IS NULL""",
                              (a['group_id'],)).fetchall()
        else:
            ids = [i for i in (a['destinatarios'] or '').split(',') if i]
            if not ids:
                return []
            ph = ','.join('?' * len(ids))
            filas = c.execute(f"SELECT username FROM Usuarios WHERE id IN ({ph}) "
                              f"AND eliminada_en IS NULL", ids).fetchall()
    return [r['username'] for r in filas]


def anuncios_para(user_id):
    """Lo que este jugador debe ver ahora mismo: los `pin` vivos que le tocan y
    las `notificacion` que aún no ha marcado como leídas.

    Sin `user_id` (invitado) solo se devuelven los avisos fijados dirigidos a
    todo el mundo: son los únicos que no dependen de saber quién eres, y así el
    cartel de mantenimiento también llega a quien juega sin cuenta."""
    ahora = datetime.now().isoformat()
    if not user_id:
        with _conn() as c:
            filas = c.execute("""SELECT id, titulo, cuerpo, created_at, expira_en FROM Anuncios
                                 WHERE activo = 1 AND tipo = 'pin' AND audiencia = 'todos'
                                   AND (expira_en IS NULL OR expira_en > ?)
                                 ORDER BY id DESC LIMIT 20""", (ahora,)).fetchall()
        return {'pins': [dict(r, leido=False) for r in filas], 'notificaciones': []}

    with _conn() as c:
        filas = c.execute("""
            SELECT a.* FROM Anuncios a
            WHERE a.activo = 1
              AND (a.expira_en IS NULL OR a.expira_en > ?)
              AND (
                    a.audiencia = 'todos'
                 OR (a.audiencia = 'grupo'
                     AND EXISTS (SELECT 1 FROM GroupMembers g
                                 WHERE g.group_id = a.group_id AND g.user_id = ?))
                 OR (a.audiencia = 'usuarios'
                     AND (',' || a.destinatarios || ',') LIKE ?)
              )
            ORDER BY a.id DESC LIMIT 50""",
            (ahora, user_id, f'%,{user_id},%')).fetchall()
        leidos = {r['anuncio_id'] for r in
                  c.execute("SELECT anuncio_id FROM AnuncioLeido WHERE user_id = ?",
                            (user_id,)).fetchall()}

    pins, notis = [], []
    for r in filas:
        d = {'id': r['id'], 'titulo': r['titulo'], 'cuerpo': r['cuerpo'],
             'created_at': r['created_at'], 'expira_en': r['expira_en']}
        if r['tipo'] == 'pin':
            d['leido'] = r['id'] in leidos
            pins.append(d)
        elif r['id'] not in leidos:
            notis.append(d)
    return {'pins': pins, 'notificaciones': notis}


def marcar_anuncio_leido(anuncio_id, user_id):
    with _conn() as c:
        c.execute("INSERT OR IGNORE INTO AnuncioLeido(anuncio_id, user_id, leido_en) "
                  "VALUES(?,?,?)", (anuncio_id, user_id, datetime.now().isoformat()))
        c.commit()
    return True


# --- 7. Resumen para la portada del panel -----------------------------------

def estadisticas_globales():
    hoy = datetime.now().strftime("%Y-%m-%d")
    with _conn() as c:
        def uno(sql, args=()):
            return c.execute(sql, args).fetchone()['n']
        return {
            'usuarios': uno("SELECT COUNT(*) n FROM Usuarios WHERE eliminada_en IS NULL"),
            'usuarios_hoy': uno("SELECT COUNT(*) n FROM Usuarios WHERE fecha_registro LIKE ?", (hoy + '%',)),
            'baneados': uno("SELECT COUNT(*) n FROM Usuarios WHERE COALESCE(banned,0)=1"),
            'admins': uno("SELECT COUNT(*) n FROM Usuarios WHERE COALESCE(is_admin,0)=1 AND eliminada_en IS NULL"),
            'partidas': uno("SELECT COUNT(*) n FROM Partidas"),
            'partidas_hoy': uno("SELECT COUNT(*) n FROM Partidas WHERE fecha LIKE ?", (hoy + '%',)),
            'partidas4': uno("SELECT COUNT(*) n FROM Partidas4"),
            'partidas4_hoy': uno("SELECT COUNT(*) n FROM Partidas4 WHERE fecha LIKE ?", (hoy + '%',)),
            'tickets_pendientes': contar_tickets_pendientes(),
            'anuncios_activos': uno("SELECT COUNT(*) n FROM Anuncios WHERE activo = 1"),
            'barajas': uno("SELECT COUNT(*) n FROM Decks WHERE activo = 1"),
        }


# --- 8. Barajas temáticas (Roadmap #5) --------------------------------------
#
# Aquí sólo está el acceso a la tabla. Quién puede usar cada tema, dónde están
# sus imágenes y cómo se valida una subida es cosa de `decks.py`.

ACCESOS_DECK = ('todos', 'cuenta', 'restringido')


def decks_todos(incluir_inactivos=True):
    """Todos los temas registrados, ordenados como se enseñan en el selector."""
    sql = "SELECT * FROM Decks"
    if not incluir_inactivos:
        sql += " WHERE activo = 1"
    sql += " ORDER BY orden, id"
    with _conn() as c:
        return [dict(r) for r in c.execute(sql).fetchall()]


def deck_por_slug(slug):
    with _conn() as c:
        r = c.execute("SELECT * FROM Decks WHERE slug = ?", (slug,)).fetchone()
    return dict(r) if r else None


def deck_por_id(deck_id):
    with _conn() as c:
        r = c.execute("SELECT * FROM Decks WHERE id = ?", (deck_id,)).fetchone()
    return dict(r) if r else None


def deck_crear(slug, nombre, nombre_en=None, descripcion=None, acceso='todos',
               orden=100, creado_por=None, patron=None, patron_dorso=None):
    """Alta de un tema subido. Devuelve su id, o None si el slug ya existía."""
    ahora = datetime.now().isoformat()
    try:
        with _conn() as c:
            cur = c.execute("""
                INSERT INTO Decks(slug, nombre, nombre_en, descripcion, acceso, activo,
                                  orden, origen, patron, patron_dorso, creado_por,
                                  created_at, updated_at)
                VALUES(?,?,?,?,?,1,?,'subida',?,?,?,?,?)
            """, (slug, nombre, nombre_en, descripcion,
                  acceso if acceso in ACCESOS_DECK else 'todos',
                  int(orden), patron, patron_dorso, creado_por, ahora, ahora))
            c.commit()
            return cur.lastrowid
    except sqlite3.IntegrityError:
        return None


def deck_actualizar(deck_id, **campos):
    """Cambia metadatos de un tema. Sólo se aceptan las claves listadas: el slug
    no se toca nunca (es la carpeta donde viven las imágenes y lo que hay
    guardado en las configuraciones de los jugadores)."""
    permitidas = ('nombre', 'nombre_en', 'descripcion', 'acceso', 'activo', 'orden')
    sets, args = [], []
    for clave in permitidas:
        if clave not in campos:
            continue
        valor = campos[clave]
        if clave == 'acceso' and valor not in ACCESOS_DECK:
            continue
        if clave in ('activo', 'orden'):
            valor = int(valor)
        sets.append(f"{clave} = ?")
        args.append(valor)
    if not sets:
        return False
    sets.append("updated_at = ?")
    args.append(datetime.now().isoformat())
    with _conn() as c:
        cur = c.execute(f"UPDATE Decks SET {', '.join(sets)} WHERE id = ?",
                        (*args, deck_id))
        c.commit()
        return cur.rowcount > 0


def deck_borrar(deck_id):
    """Borra el registro y sus permisos. Los archivos los borra `decks.py`; las
    configuraciones que apuntaban al tema caen solas a la baraja clásica."""
    with _conn() as c:
        c.execute("DELETE FROM DeckAcceso WHERE deck_id = ?", (deck_id,))
        cur = c.execute("DELETE FROM Decks WHERE id = ?", (deck_id,))
        c.commit()
        return cur.rowcount > 0


def deck_accesos(deck_id):
    """Cuentas con permiso individual sobre un tema restringido."""
    with _conn() as c:
        filas = c.execute("""
            SELECT a.user_id, u.username, u.codigo, a.concedido_por, a.created_at
            FROM DeckAcceso a JOIN Usuarios u ON u.id = a.user_id
            WHERE a.deck_id = ? ORDER BY u.username COLLATE NOCASE
        """, (deck_id,)).fetchall()
    return [dict(r) for r in filas]


def deck_conceder(deck_id, user_id, por=None):
    with _conn() as c:
        c.execute("""INSERT INTO DeckAcceso(deck_id, user_id, concedido_por, created_at)
                     VALUES(?,?,?,?) ON CONFLICT(deck_id, user_id) DO NOTHING""",
                  (deck_id, user_id, por, datetime.now().isoformat()))
        c.commit()
    return True


def deck_revocar(deck_id, user_id):
    with _conn() as c:
        cur = c.execute("DELETE FROM DeckAcceso WHERE deck_id = ? AND user_id = ?",
                        (deck_id, user_id))
        c.commit()
        return cur.rowcount > 0


def deck_slugs_permitidos(user_id):
    """Slugs de los temas restringidos que este jugador tiene concedidos."""
    if not user_id:
        return set()
    with _conn() as c:
        filas = c.execute("""SELECT d.slug FROM DeckAcceso a JOIN Decks d ON d.id = a.deck_id
                             WHERE a.user_id = ?""", (user_id,)).fetchall()
    return {r['slug'] for r in filas}


def deck_config_get(username):
    """JSON crudo de la baraja del jugador (o None). Lo interpreta quien lo pide."""
    with _conn() as c:
        r = c.execute("SELECT deck_config FROM Usuarios WHERE username = ? COLLATE NOCASE "
                      "AND eliminada_en IS NULL", (username,)).fetchone()
    return r['deck_config'] if r else None


def deck_config_set(username, json_texto):
    with _conn() as c:
        cur = c.execute("UPDATE Usuarios SET deck_config = ? WHERE username = ? COLLATE NOCASE "
                        "AND eliminada_en IS NULL", (json_texto, username))
        c.commit()
        return cur.rowcount > 0


init_db()
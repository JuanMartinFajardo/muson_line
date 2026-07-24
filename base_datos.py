import sqlite3
import secrets
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

    conexion.commit()
    _migrar_columnas(conexion)
    _migrar_social(conexion)
    conexion.close()


def _migrar_social(conexion):
    """Migraciones idempotentes para las tablas sociales en bases de datos antiguas."""
    cursor = conexion.cursor()
    cursor.execute("PRAGMA table_info(Groups)")
    columnas = {fila[1] for fila in cursor.fetchall()}
    if 'invite_policy' not in columnas:
        cursor.execute("ALTER TABLE Groups ADD COLUMN invite_policy TEXT NOT NULL DEFAULT 'admins'")
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
    conexion.commit()

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
            INSERT INTO Usuarios (username, password_hash, email, country, birthdate, fecha_registro)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (username, hash_pass, email, country, birthdate, fecha_actual))
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
        WHERE username = ? COLLATE NOCASE OR email = ? COLLATE NOCASE
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
    cursor.execute('UPDATE Usuarios SET password_hash = ? WHERE email = ? COLLATE NOCASE',
                   (hash_pass, email))
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

def registrar_o_loguear_google(google_id, email, nombre):
    """Encuentra la cuenta por google_id o email; si no existe, la crea.
    Devuelve el username canónico."""
    conexion = sqlite3.connect(DB_NAME)
    cursor = conexion.cursor()

    # 1. ¿Ya la vinculamos antes por google_id?
    cursor.execute('SELECT username FROM Usuarios WHERE google_id = ?', (google_id,))
    fila = cursor.fetchone()
    if fila:
        conexion.close()
        return fila[0]

    # 2. ¿Hay una cuenta con ese email (registro clásico previo)? La vinculamos.
    if email:
        cursor.execute('SELECT username FROM Usuarios WHERE email = ? COLLATE NOCASE', (email,))
        fila = cursor.fetchone()
        if fila:
            cursor.execute('UPDATE Usuarios SET google_id = ? WHERE username = ?', (google_id, fila[0]))
            conexion.commit()
            conexion.close()
            return fila[0]

    # 3. Cuenta nueva. Password aleatoria inutilizable (login solo vía Google hasta que resetee).
    username = _generar_username_libre(cursor, nombre or (email.split('@')[0] if email else 'jugador'))
    hash_pass = generate_password_hash(secrets.token_urlsafe(32))
    fecha_actual = datetime.now().strftime("%Y-%m-%d")
    cursor.execute('''
        INSERT INTO Usuarios (username, password_hash, email, google_id, fecha_registro)
        VALUES (?, ?, ?, ?, ?)
    ''', (username, hash_pass, email, google_id, fecha_actual))
    conexion.commit()
    conexion.close()
    return username

def obtener_usuario(username):
    conexion = sqlite3.connect(DB_NAME)
    conexion.row_factory = sqlite3.Row 
    cursor = conexion.cursor()
    cursor.execute('SELECT username, country, birthdate, victorias, derrotas, elo, fecha_registro FROM Usuarios WHERE username = ?', (username,))
    fila = cursor.fetchone()
    conexion.close()
    
    if fila:
        usuario = dict(fila)
        total = usuario['victorias'] + usuario['derrotas']
        usuario['winrate'] = round((usuario['victorias'] / total) * 100, 1) if total > 0 else 0.0
        return usuario
    return None

def obtener_leaderboard():
    conexion = sqlite3.connect(DB_NAME)
    conexion.row_factory = sqlite3.Row
    cursor = conexion.cursor()
    cursor.execute('SELECT username, victorias, derrotas, elo FROM Usuarios')
    filas = cursor.fetchall()
    conexion.close()
    
    leaderboard = []
    for fila in filas:
        usuario = dict(fila)
        total = usuario['victorias'] + usuario['derrotas']
        winrate = round((usuario['victorias'] / total) * 100, 1) if total > 0 else 0.0
            
        leaderboard.append({
            'username': usuario['username'],
            'elo': usuario['elo'],
            'victorias': usuario['victorias'],
            'winrate': winrate
        })
    return leaderboard


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
    if not username:
        return None
    with _conn() as c:
        r = c.execute("SELECT id FROM Usuarios WHERE username = ? COLLATE NOCASE",
                      (username,)).fetchone()
        return r['id'] if r else None


def obtener_username_por_id(user_id):
    with _conn() as c:
        r = c.execute("SELECT username FROM Usuarios WHERE id = ?", (user_id,)).fetchone()
        return r['username'] if r else None


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
            SELECT u.id, u.username, u.elo, u.victorias, u.derrotas
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


init_db()
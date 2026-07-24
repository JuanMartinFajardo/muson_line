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
    conexion.commit()
    _migrar_columnas(conexion)
    conexion.close()

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
        cursor.execute('SELECT elo FROM Usuarios WHERE username = ?', (ganador_user,))
        res_g = cursor.fetchone()
        cursor.execute('SELECT elo FROM Usuarios WHERE username = ?', (perdedor_user,))
        res_p = cursor.fetchone()
        
        if res_g and res_p:
            # 1. Sumar victorias y derrotas
            cursor.execute('UPDATE Usuarios SET victorias = victorias + 1 WHERE username = ?', (ganador_user,))
            cursor.execute('UPDATE Usuarios SET derrotas = derrotas + 1 WHERE username = ?', (perdedor_user,))
            
            # 2. Actualizar ELO
            elo_g, elo_p = res_g[0], res_p[0]
            # ganador tiene 1 victoria, perdedor 0
            nuevo_elo_g, nuevo_elo_p, _ = procesar_partida_mus(elo_g, elo_p, 1, 0)
            
            cursor.execute('UPDATE Usuarios SET elo = ? WHERE username = ?', (nuevo_elo_g, ganador_user))
            cursor.execute('UPDATE Usuarios SET elo = ? WHERE username = ?', (nuevo_elo_p, perdedor_user))
            
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

init_db()
import sqlite3
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
            country TEXT,
            birthdate TEXT,
            victorias INTEGER DEFAULT 0,
            derrotas INTEGER DEFAULT 0,
            elo REAL DEFAULT 1200.0,
            fecha_registro TEXT
        )
    ''')
    conexion.commit()
    conexion.close()

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
    
    # 1. Sumar victorias y derrotas (incluso si han jugado contra un invitado)
    if ganador_user:
        cursor.execute('UPDATE Usuarios SET victorias = victorias + 1 WHERE username = ?', (ganador_user,))
    if perdedor_user:
        cursor.execute('UPDATE Usuarios SET derrotas = derrotas + 1 WHERE username = ?', (perdedor_user,))
        
    # 2. Actualizar ELO *solo* si ambos son jugadores reales registrados
    if ganador_user and perdedor_user:
        cursor.execute('SELECT elo FROM Usuarios WHERE username = ?', (ganador_user,))
        res_g = cursor.fetchone()
        cursor.execute('SELECT elo FROM Usuarios WHERE username = ?', (perdedor_user,))
        res_p = cursor.fetchone()
        
        if res_g and res_p:
            elo_g, elo_p = res_g[0], res_p[0]
            # ganador tiene 1 victoria, perdedor 0
            nuevo_elo_g, nuevo_elo_p, _ = procesar_partida_mus(elo_g, elo_p, 1, 0)
            
            cursor.execute('UPDATE Usuarios SET elo = ? WHERE username = ?', (nuevo_elo_g, ganador_user))
            cursor.execute('UPDATE Usuarios SET elo = ? WHERE username = ?', (nuevo_elo_p, perdedor_user))
            
    conexion.commit()
    conexion.close()

def registrar_usuario(username, password, country, birthdate):
    conexion = sqlite3.connect(DB_NAME)
    cursor = conexion.cursor()
    hash_pass = generate_password_hash(password)
    fecha_actual = datetime.now().strftime("%Y-%m-%d") 
    
    try:
        cursor.execute('''
            INSERT INTO Usuarios (username, password_hash, country, birthdate, fecha_registro)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, hash_pass, country, birthdate, fecha_actual))
        conexion.commit()
        exito, mensaje = True, "Usuario registrado correctamente."
    except sqlite3.IntegrityError:
        exito, mensaje = False, "El nombre de usuario ya está en uso."
    finally:
        conexion.close()
    return exito, mensaje

def verificar_login(username, password):
    conexion = sqlite3.connect(DB_NAME)
    cursor = conexion.cursor()
    cursor.execute('SELECT password_hash FROM Usuarios WHERE username = ?', (username,))
    resultado = cursor.fetchone()
    conexion.close()
    
    if resultado is None: return False 
    return check_password_hash(resultado[0], password)

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
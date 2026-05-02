import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

DB_NAME = 'mus.db'

def init_db():
    """Crea la base de datos y la tabla si es la primera vez que se ejecuta"""
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
            fecha_registro TEXT
        )
    ''')
    
    conexion.commit()
    conexion.close()

def registrar_usuario(username, password, country, birthdate):
    """Guarda un usuario nuevo. Devuelve (True, 'mensaje') o (False, 'error')"""
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
        exito = True
        mensaje = "Usuario registrado correctamente."
    except sqlite3.IntegrityError:
        exito = False
        mensaje = "El nombre de usuario ya está en uso."
    finally:
        conexion.close()
        
    return exito, mensaje

def verificar_login(username, password):
    """Comprueba si el usuario existe y la contraseña es correcta"""
    conexion = sqlite3.connect(DB_NAME)
    cursor = conexion.cursor()
    
    cursor.execute('SELECT password_hash FROM Usuarios WHERE username = ?', (username,))
    resultado = cursor.fetchone()
    conexion.close()
    
    if resultado is None:
        return False 
        
    hash_guardado = resultado[0]
    return check_password_hash(hash_guardado, password)

def obtener_usuario(username):
    """Devuelve los datos públicos del usuario y calcula su winrate al vuelo"""
    conexion = sqlite3.connect(DB_NAME)
    conexion.row_factory = sqlite3.Row 
    cursor = conexion.cursor()
    
    # Añadimos también que extraiga la fecha_registro si nos hace falta en el futuro
    cursor.execute('SELECT username, country, birthdate, victorias, derrotas, fecha_registro FROM Usuarios WHERE username = ?', (username,))
    fila = cursor.fetchone()
    conexion.close()
    
    if fila:
        usuario = dict(fila)
        v = usuario['victorias']
        d = usuario['derrotas']
        total = v + d
        
        if total > 0:
            usuario['winrate'] = round((v / total) * 100, 1)
        else:
            usuario['winrate'] = 0.0
            
        return usuario
    return None

def registrar_resultado_partida(username, es_victoria):
    """Suma 1 a las victorias o derrotas del jugador"""
    conexion = sqlite3.connect(DB_NAME)
    cursor = conexion.cursor()
    
    if es_victoria:
        cursor.execute('UPDATE Usuarios SET victorias = victorias + 1 WHERE username = ?', (username,))
    else:
        cursor.execute('UPDATE Usuarios SET derrotas = derrotas + 1 WHERE username = ?', (username,))
        
    conexion.commit()
    conexion.close()

def obtener_leaderboard():
    """Devuelve la lista de todos los usuarios con sus victorias y winrate"""
    conexion = sqlite3.connect(DB_NAME)
    conexion.row_factory = sqlite3.Row
    cursor = conexion.cursor()
    
    cursor.execute('SELECT username, victorias, derrotas FROM Usuarios')
    filas = cursor.fetchall()
    conexion.close()
    
    leaderboard = []
    for fila in filas:
        usuario = dict(fila)
        v = usuario['victorias']
        d = usuario['derrotas']
        total = v + d
        
        if total > 0:
            winrate = round((v / total) * 100, 1)
        else:
            winrate = 0.0
            
        leaderboard.append({
            'username': usuario['username'],
            'victorias': v,
            'winrate': winrate
        })
        
    return leaderboard

init_db()
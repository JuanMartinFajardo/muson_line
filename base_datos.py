import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

# El archivo físico donde se guardará todo (se creará solo)
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
            derrotas INTEGER DEFAULT 0
        )
    ''')
    conexion.commit()
    conexion.close()

def registrar_usuario(username, password, country, birthdate):
    """Guarda un usuario nuevo. Devuelve (True, 'mensaje') o (False, 'error')"""
    conexion = sqlite3.connect(DB_NAME)
    cursor = conexion.cursor()
    
    # TRITURADORA: Encriptamos la contraseña antes de guardarla
    hash_pass = generate_password_hash(password)
    
    try:
        cursor.execute('''
            INSERT INTO Usuarios (username, password_hash, country, birthdate)
            VALUES (?, ?, ?, ?)
        ''', (username, hash_pass, country, birthdate))
        conexion.commit()
        exito = True
        mensaje = "Usuario registrado correctamente."
    except sqlite3.IntegrityError:
        # SQLite lanza este error automáticamente si el 'username' ya existe (por el UNIQUE)
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
        return False # El usuario no existe
        
    # Comparamos la contraseña escrita con el hash de la base de datos
    hash_guardado = resultado[0]
    return check_password_hash(hash_guardado, password)

def obtener_usuario(username):
    """Devuelve los datos públicos del usuario y calcula su winrate al vuelo"""
    conexion = sqlite3.connect(DB_NAME)
    conexion.row_factory = sqlite3.Row # Para acceder a las columnas por nombre
    cursor = conexion.cursor()
    
    cursor.execute('SELECT username, country, birthdate, victorias, derrotas FROM Usuarios WHERE username = ?', (username,))
    fila = cursor.fetchone()
    conexion.close()
    
    if fila:
        usuario = dict(fila)
        v = usuario['victorias']
        d = usuario['derrotas']
        total = v + d
        
        # Calculamos el porcentaje de victoria de forma segura
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

# Al importar este archivo, Python comprobará automáticamente si la DB existe, y si no, la crea.
init_db()
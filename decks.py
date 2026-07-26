# ==========================================================================
# decks.py — Barajas temáticas (Roadmap #5)
# --------------------------------------------------------------------------
# Un TEMA es el juego de 11 imágenes (las 10 cartas y el dorso) que ocupa uno
# de los cuatro huecos de palo. El jugador arma su baraja eligiendo cuatro
# temas independientes, uno por hueco, más el dorso; en el mus el palo no
# puntúa, así que mezclar temas no afecta a la partida.
#
# Reparto de responsabilidades:
#   base_datos.py → la tabla (metadatos, acceso, permisos individuales)
#   decks.py      → dónde están las imágenes, quién puede usar cada tema y
#                   cómo se valida e instala una subida
#   admin.py      → las rutas del panel
#   server.py     → las rutas del jugador
#   static/decks.js → el selector y la resolución de rutas en el cliente
#
# Todo lo que sube un administrador se **reprocesa**: se abre con Pillow, se
# reescala al tamaño canónico y se vuelve a codificar en webp. Nunca se sirve
# el archivo original tal cual, así que un .webp con sorpresa dentro no llega
# jamás al navegador de un jugador.
# ==========================================================================

import io
import json
import os
import re
import shutil
import zipfile

from PIL import Image

import base_datos

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIR_DECKS = os.path.join(BASE_DIR, 'static', 'img', 'decks')
URL_DECKS = '/static/img/decks'

# --- Contrato de la baraja (DECK_SPEC §1 y §2) ------------------------------

#: Las diez cartas del mus, en el orden en que se enseñan.
VALORES = ('01', '02', '03', '04', '05', '06', '07', '10', '11', '12')

#: Los cuatro huecos de palo. Son claves lógicas: el servidor sigue mandando el
#: palo en castellano y es el cliente quien traduce (`Oros` → `coins`).
HUECOS = ('coins', 'cups', 'swords', 'clubs')

#: Nombres de archivo aceptados dentro de un tema.
PIEZAS = VALORES + ('back', 'thumb')

TAMANO_CARTA = (208, 319)     # @1x, el mismo que la baraja original
TAMANO_THUMB = (104, 160)     # el que pide el selector

#: Presupuesto de peso del DECK_SPEC §6: 150 KB por tema (11 archivos), 190 KB
#: de techo duro. El panel lo enseña como aviso, nunca como bloqueo: un tema
#: pesado se ve igual, sólo tarda más en llegar por una conexión mala.
PRESUPUESTO_TEMA = {'objetivo': 150 * 1024, 'techo': 190 * 1024}

# --- Límites de subida ------------------------------------------------------

MAX_ARCHIVO = 4 * 1024 * 1024        # 4 MB por imagen suelta
MAX_ZIP = 24 * 1024 * 1024           # 24 MB de zip comprimido
MAX_ZIP_DESCOMPRIMIDO = 96 * 1024 * 1024   # techo contra las "bombas zip"
MAX_MIEMBROS_ZIP = 60
MAX_PIXELES = 40 * 1024 * 1024       # techo contra las "bombas de descompresión" de Pillow

RE_SLUG = re.compile(r'^[a-z0-9][a-z0-9-]{1,30}[a-z0-9]$')
EXTENSIONES = ('.webp', '.png', '.jpg', '.jpeg')

Image.MAX_IMAGE_PIXELS = MAX_PIXELES


class ErrorDeck(Exception):
    """Fallo previsto de una subida. El mensaje es una clave para el panel."""


# ==========================================================================
# 1. Rutas de las imágenes
# ==========================================================================

def _carpeta(slug):
    return os.path.join(DIR_DECKS, slug)


def ruta_cara(deck, valor):
    """URL de una carta. `valor` es '01'…'12' (o el entero equivalente)."""
    vv = f"{int(valor):02d}" if not isinstance(valor, str) else valor
    patron = deck.get('patron')
    if patron:
        return patron.replace('{vv}', vv)
    return f"{URL_DECKS}/{deck['slug']}/{vv}.webp"


def ruta_dorso(deck):
    return deck.get('patron_dorso') or f"{URL_DECKS}/{deck['slug']}/back.webp"


def ruta_thumb(deck):
    """Miniatura del selector. Si el tema no trae una, enseña su as: según el
    DECK_SPEC el as es la carta cartel del tema, así que nunca queda feo."""
    propia = os.path.join(_carpeta(deck['slug']), 'thumb.webp')
    if os.path.exists(propia):
        return f"{URL_DECKS}/{deck['slug']}/thumb.webp"
    return ruta_cara(deck, '01')


def piezas_presentes(deck):
    """Qué imágenes tiene realmente el tema en disco. El panel lo usa para
    avisar de un tema incompleto antes de que lo vea un jugador."""
    faltan = []
    for pieza in VALORES + ('back',):
        url = ruta_dorso(deck) if pieza == 'back' else ruta_cara(deck, pieza)
        real = os.path.join(BASE_DIR, url.lstrip('/').replace('/', os.sep))
        if not os.path.exists(real):
            faltan.append(pieza)
    return faltan


# ==========================================================================
# 2. Quién puede usar cada tema
# ==========================================================================

def _bloqueo(deck, user_id, es_admin, permitidos):
    """None si el jugador puede usar el tema; si no, el motivo."""
    if es_admin:
        return None
    acceso = deck.get('acceso') or 'todos'
    if acceso == 'todos':
        return None
    if acceso == 'cuenta':
        return None if user_id else 'cuenta'
    if acceso == 'restringido':
        return None if deck['slug'] in permitidos else 'restringido'
    return 'restringido'   # acceso desconocido: se cierra, no se abre


def deck_publico(deck, bloqueado=None, idioma='es'):
    """La ficha que ve el jugador. Nunca lleva nada del panel (quién lo subió,
    cuándo, a quién más se le ha concedido…)."""
    nombre = deck['nombre']
    if idioma == 'en' and deck.get('nombre_en'):
        nombre = deck['nombre_en']
    return {
        'slug': deck['slug'],
        'nombre': nombre,
        'nombre_es': deck['nombre'],
        'nombre_en': deck.get('nombre_en') or deck['nombre'],
        'descripcion': deck.get('descripcion') or '',
        'clasica': deck.get('origen') == 'clasica',
        'thumb': ruta_thumb(deck),
        'dorso': ruta_dorso(deck),
        'cartas': {vv: ruta_cara(deck, vv) for vv in VALORES},
        'bloqueado': bool(bloqueado),
        'motivo': bloqueado,
    }


def temas_para(username=None, es_admin=False, idioma='es'):
    """Catálogo que se le manda a un jugador: los temas activos, cada uno con
    su marca de bloqueo. Los retirados (activo=0) no salen ni bloqueados —
    para eso está esa casilla."""
    user_id = base_datos.obtener_id_usuario(username) if username else None
    permitidos = base_datos.deck_slugs_permitidos(user_id)
    salida = []
    for deck in base_datos.decks_todos(incluir_inactivos=False):
        salida.append(deck_publico(deck, _bloqueo(deck, user_id, es_admin, permitidos), idioma))
    return salida


def slugs_usables(username=None, es_admin=False):
    """Sólo los temas que este jugador puede elegir de verdad."""
    user_id = base_datos.obtener_id_usuario(username) if username else None
    permitidos = base_datos.deck_slugs_permitidos(user_id)
    return {d['slug'] for d in base_datos.decks_todos(incluir_inactivos=False)
            if _bloqueo(d, user_id, es_admin, permitidos) is None}


# ==========================================================================
# 3. La configuración del jugador
# ==========================================================================

#: Baraja por defecto: cada hueco con su tema clásico y el dorso de siempre.
CONFIG_DEFECTO = {**{h: h for h in HUECOS}, 'dorso': 'coins'}


def normalizar_config(bruto, usables=None):
    """Deja la configuración en algo seguro de pintar: sólo los cinco huecos
    conocidos, sólo temas que existan y que el jugador pueda usar, y el resto
    a la baraja clásica. Acepta el JSON crudo de la base de datos o un dict."""
    if isinstance(bruto, str):
        try:
            bruto = json.loads(bruto)
        except (ValueError, TypeError):
            bruto = None
    if not isinstance(bruto, dict):
        bruto = {}

    config = dict(CONFIG_DEFECTO)
    for hueco in HUECOS + ('dorso',):
        valor = bruto.get(hueco)
        if not isinstance(valor, str):
            continue
        valor = valor.strip()
        if usables is not None and valor not in usables:
            continue      # tema retirado, o al que ya no tiene acceso
        config[hueco] = valor
    return config


def config_de(username, usables=None):
    if not username:
        return dict(CONFIG_DEFECTO)
    if usables is None:
        usables = slugs_usables(username)
    return normalizar_config(base_datos.deck_config_get(username), usables)


def guardar_config(username, config, usables=None):
    if usables is None:
        usables = slugs_usables(username)
    limpia = normalizar_config(config, usables)
    base_datos.deck_config_set(username, json.dumps(limpia))
    return limpia


# ==========================================================================
# 4. La baraja que se ve en la mesa
# --------------------------------------------------------------------------
# La piel de una carta la elige su DUEÑO: en la mesa ves las cartas del rival
# con la baraja del rival, no con la tuya, y él ve las tuyas con la tuya. Para
# eso la elección tiene que viajar, así que aquí está el registro que la guarda
# mientras dura la conexión.
#
# La llave es el sid del socket, no el nombre de usuario, porque también hay que
# servir al invitado, que no tiene fila en la base de datos: su navegador manda
# la baraja al conectarse (evento `mi_baraja`) y se valida aquí antes de
# enseñársela a nadie. Con cuenta el navegador manda lo mismo, pero si no lo
# hace (cliente viejo, o el aviso llega después que la mesa) se cae a lo que
# tenga guardado.
# ==========================================================================

_EN_MESA = {}      # sid -> configuración ya normalizada


def recordar_baraja(sid, bruto, username=None, es_admin=False):
    """Guarda la baraja que dice tener un navegador. Pasa por
    `normalizar_config`, así que nadie puede enseñar un tema retirado ni uno al
    que no tenga acceso por mucho que lo mande."""
    config = normalizar_config(bruto, slugs_usables(username, es_admin))
    if sid:
        _EN_MESA[sid] = config
    return config


def baraja_en_mesa(sid, username=None):
    """Con qué baraja hay que pintar las cartas de ese jugador."""
    config = _EN_MESA.get(sid)
    if config is not None:
        return config
    config = config_de(username) if username else dict(CONFIG_DEFECTO)
    if sid:
        _EN_MESA[sid] = config      # cacheado: el estado de la mesa pasa por aquí a menudo
    return config


def olvidar_baraja(sid):
    """Al desconectar. Ese sid no vuelve."""
    _EN_MESA.pop(sid, None)


# ==========================================================================
# 5. Subidas
# ==========================================================================

def validar_slug(slug):
    slug = (slug or '').strip().lower()
    if not RE_SLUG.match(slug):
        raise ErrorDeck('slug_invalido')
    return slug


def _nombre_pieza(nombre_archivo):
    """Reduce el nombre que venga a una de las piezas conocidas, o None.
    Admite tanto `01.webp` como `card_coins_01.webp` o `back.png`, que es lo
    que suele salir de un renderizador."""
    base = os.path.basename(nombre_archivo or '').strip().lower()
    if not base or base.startswith('.'):
        return None
    raiz, ext = os.path.splitext(base)
    if ext not in EXTENSIONES:
        return None
    raiz = raiz.replace('card_', '').replace('carta_', '')
    if raiz in ('back', 'dorso', 'reverso'):
        return 'back'
    if raiz in ('thumb', 'miniatura', 'thumbnail'):
        return 'thumb'
    # `..._01`, `01`, `1`
    m = re.search(r'(\d{1,2})$', raiz)
    if not m:
        return None
    vv = f"{int(m.group(1)):02d}"
    return vv if vv in VALORES else None


def _reencodear(datos, destino, tamano):
    """Abre la imagen, comprueba que lo es, la lleva al tamaño canónico y la
    guarda como webp. Aquí muere cualquier cosa que no sea una imagen."""
    try:
        with Image.open(io.BytesIO(datos)) as img:
            img.verify()                       # detecta el archivo corrupto…
        with Image.open(io.BytesIO(datos)) as img:
            img = img.convert('RGBA')          # …y esto lo decodifica de verdad
            if img.size != tamano:
                img = img.resize(tamano, Image.LANCZOS)
            os.makedirs(os.path.dirname(destino), exist_ok=True)
            img.save(destino, 'WEBP', quality=82, method=6, exact=True)
    except ErrorDeck:
        raise
    except Exception:
        raise ErrorDeck('imagen_invalida')
    return os.path.getsize(destino)


def instalar_pieza(slug, pieza, datos):
    """Instala una sola imagen (alta suelta o sustitución de una carta)."""
    if pieza not in PIEZAS:
        raise ErrorDeck('pieza_desconocida')
    if len(datos) > MAX_ARCHIVO:
        raise ErrorDeck('archivo_grande')
    tamano = TAMANO_THUMB if pieza == 'thumb' else TAMANO_CARTA
    destino = os.path.join(_carpeta(slug), f'{pieza}.webp')
    return _reencodear(datos, destino, tamano)


def instalar_zip(slug, datos_zip):
    """Instala un tema entero desde un zip. Devuelve las piezas escritas.

    Sólo se miran los nombres de archivo reconocibles y se ignora todo lo demás
    (carpetas, .DS_Store, READMEs). El zip nunca se extrae al disco: cada
    miembro se lee en memoria y se vuelve a codificar."""
    if len(datos_zip) > MAX_ZIP:
        raise ErrorDeck('zip_grande')
    escritas, total = [], 0
    try:
        with zipfile.ZipFile(io.BytesIO(datos_zip)) as z:
            miembros = [m for m in z.infolist() if not m.is_dir()]
            if len(miembros) > MAX_MIEMBROS_ZIP:
                raise ErrorDeck('zip_con_demasiados_archivos')
            if sum(m.file_size for m in miembros) > MAX_ZIP_DESCOMPRIMIDO:
                raise ErrorDeck('zip_grande')
            for miembro in miembros:
                pieza = _nombre_pieza(miembro.filename)
                if not pieza or pieza in [p for p, _ in escritas]:
                    continue
                if miembro.file_size > MAX_ARCHIVO:
                    raise ErrorDeck('archivo_grande')
                datos = z.read(miembro)
                total += instalar_pieza(slug, pieza, datos)
                escritas.append((pieza, miembro.filename))
    except zipfile.BadZipFile:
        raise ErrorDeck('zip_invalido')
    if not escritas:
        raise ErrorDeck('zip_sin_cartas')
    return [p for p, _ in escritas], total


def borrar_archivos(slug):
    """Borra la carpeta del tema. Sólo se llama con un slug ya validado y
    nunca sobre los temas clásicos, cuyas imágenes están fuera de aquí."""
    carpeta = _carpeta(slug)
    # Cinturón y tirantes: la ruta resuelta tiene que caer dentro de DIR_DECKS.
    if os.path.realpath(carpeta).startswith(os.path.realpath(DIR_DECKS) + os.sep):
        shutil.rmtree(carpeta, ignore_errors=True)
        return True
    return False


def peso_en_disco(slug):
    """Bytes que ocupa un tema, para el aviso de presupuesto del DECK_SPEC §6."""
    carpeta = _carpeta(slug)
    if not os.path.isdir(carpeta):
        return 0
    return sum(os.path.getsize(os.path.join(carpeta, f))
               for f in os.listdir(carpeta)
               if os.path.isfile(os.path.join(carpeta, f)))

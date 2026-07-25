# mus_senas.py — Señas del Mus a 4 jugadores (2v2).
#
# Módulo PURO: dice qué seña corresponde a una mano. No sabe nada de sockets ni
# de salas (eso vive en server_mus4.py) ni de caras (eso vive en
# static/senas4.js). Se apoya en las funciones puras del motor de 2 jugadores a
# través de mus_core, así que no duplica ninguna evaluación de mano.
#
# La regla del juego: el botón de "hacer una seña" NO deja elegir. Se hace la
# seña MÁS ALTA que la mano permita, según un orden de prioridad que el
# administrador puede reordenar desde /admin (variable `senas_orden`).
#
# Ojo con el orden por defecto: `tres_reyes` y `tres_ases` van ANTES que
# `medias` a propósito. Los tres predicados se cumplen a la vez con un trío de
# reyes, y quien mande es el primero de la lista.

from collections import Counter

from mus_core import get_valores_mus, get_suma_juego, get_pares_info

# En el mus los 3 valen como reyes (12) y los 2 como ases (1); get_valores_mus
# ya hace esa traducción, así que aquí sólo contamos.
REY = 12
AS = 1

# Orden de prioridad por defecto (de más alta a más baja). `ciego` es el comodín
# final: su predicado siempre se cumple, así que la mano que no llega a nada
# acaba ahí.
ORDEN_POR_DEFECTO = [
    'solomillo',    # tres reyes + un as  → un beso
    'duples',       # dos parejas         → levantar las cejas
    '31',           # juego de 31         → guiño
    'tres_reyes',   # tres reyes          → morderse un lado del labio
    'tres_ases',    # tres ases           → sacar la lengua de lado
    'medias',       # trío de cualquier otra cosa → torcer la boca
    'dos_reyes',    # dos reyes           → morderse el centro del labio
    'dos_ases',     # dos ases            → sacar la lengua
    '30',           # juego de 30         → encoger los hombros
    'ciego',        # nada de lo anterior → cerrar los ojos
]


def _rasgos(cartas):
    """Resume una mano en los cuatro datos que necesitan todos los predicados."""
    cuenta = Counter(get_valores_mus(cartas))
    info = get_pares_info(cartas) or {}
    return {
        'reyes': cuenta[REY],
        'ases': cuenta[AS],
        # tipo de pares del motor: 0 nada · 1 pareja · 2 trío · 3 duples
        # (dos parejas o cuatro iguales).
        'tipo_pares': info.get('tipo', 0),
        'suma': get_suma_juego(cartas),
    }


# Cada seña es un predicado independiente sobre esos rasgos. Que dos se cumplan
# a la vez es normal (tres reyes son también dos reyes): desempata el orden.
PREDICADOS = {
    'solomillo':  lambda r: r['reyes'] >= 3 and r['ases'] >= 1,
    'duples':     lambda r: r['tipo_pares'] == 3,
    '31':         lambda r: r['suma'] == 31,
    'tres_reyes': lambda r: r['reyes'] >= 3,
    'tres_ases':  lambda r: r['ases'] >= 3,
    'medias':     lambda r: r['tipo_pares'] == 2,
    'dos_reyes':  lambda r: r['reyes'] >= 2,
    'dos_ases':   lambda r: r['ases'] >= 2,
    '30':         lambda r: r['suma'] == 30,
    'ciego':      lambda r: True,
}

SENAS = tuple(ORDEN_POR_DEFECTO)


def normalizar_orden(crudo):
    """Convierte lo que haya escrito el administrador en un orden utilizable.

    Acepta una lista o una cadena separada por comas o saltos de línea. Es
    deliberadamente tolerante: ignora nombres que no existen, quita repetidos y
    añade al final, en el orden por defecto, las señas que falten. Así una
    errata en el panel nunca deja una seña inalcanzable ni rompe la partida."""
    if isinstance(crudo, str):
        pedidas = [p.strip() for p in crudo.replace('\n', ',').split(',') if p.strip()]
    else:
        pedidas = [str(p).strip() for p in (crudo or [])]

    orden, vistas = [], set()
    for nombre in pedidas:
        if nombre in PREDICADOS and nombre not in vistas:
            vistas.add(nombre)
            orden.append(nombre)
    for nombre in ORDEN_POR_DEFECTO:
        if nombre not in vistas:
            vistas.add(nombre)
            orden.append(nombre)
    return orden


def orden_configurado():
    """Orden vigente: el de /admin si lo hay, si no el de por defecto."""
    try:
        import base_datos
        crudo = base_datos.config_get('senas_orden', '') or ''
    except Exception:
        crudo = ''
    return normalizar_orden(crudo)


def sena_de(cartas, orden=None):
    """Seña que le toca hacer a esta mano: la primera del orden que se cumpla.

    Devuelve None sin cartas (entre rondas no hay nada que señalar)."""
    if not cartas:
        return None
    rasgos = _rasgos(cartas)
    for nombre in (orden or ORDEN_POR_DEFECTO):
        predicado = PREDICADOS.get(nombre)
        if predicado and predicado(rasgos):
            return nombre
    return 'ciego'


def es_sena(nombre):
    """¿Es un nombre de seña válido? (para validar lo que denuncia un cliente)."""
    return nombre in PREDICADOS

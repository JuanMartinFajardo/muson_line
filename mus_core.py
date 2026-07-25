# mus_core.py — capa compartida fina entre el motor de 2 jugadores (PartidaMus)
# y el de 4 jugadores (PartidaMus4). NO duplica lógica: reexporta las funciones
# puras que ya viven en mus_mecanicas.py para no tocar ese archivo (usado también
# por el pipeline de entrenamiento). Ver wiki/Implementing-Mus-4-Players.md §2.

from mus_mecanicas import (
    crear_baraja,
    get_valores_mus,
    tiene_pares,
    get_pares_info,
    get_suma_juego,
    tiene_juego,
    es_la_real,
    comparar_cartas,
    comp_pares_info,
    comp_juego,
    comp_punto,
    obtener_ruta_imagen,
    J_RANK,
)

__all__ = [
    'crear_baraja', 'get_valores_mus', 'tiene_pares', 'get_pares_info',
    'get_suma_juego', 'tiene_juego', 'es_la_real', 'comparar_cartas',
    'comp_pares_info', 'comp_juego', 'comp_punto', 'obtener_ruta_imagen',
    'J_RANK', 'mejor_hand_equipo',
]


def mejor_hand_equipo(cartas_por_jugador, comparador, is_grande=None):
    """Devuelve el índice de asiento cuya mano es la mejor de un equipo para un lance.

    cartas_por_jugador: {seat: cartas}. comparador: una de las funciones comp_* /
    comparar_cartas del motor de 2 jugadores. Reduce el equipo a su mano
    representativa reutilizando los comparadores por pares (devuelven 'mano'/'postre',
    donde 'postre' = ganó el segundo argumento).

    Los asientos se recorren en el orden en que llegan en el dict; para que el
    desempate por cercanía a la mano sea correcto, quien construya el dict debe
    ordenar los asientos empezando por el más cercano a la mano (ver
    PartidaMus4._orden_equipo_desde_mano).
    """
    seats = list(cartas_por_jugador)
    if not seats:
        return None
    best = seats[0]
    for s in seats[1:]:
        if is_grande is None:
            gan = comparador(cartas_por_jugador[best], cartas_por_jugador[s])
        else:
            gan = comparador(cartas_por_jugador[best], cartas_por_jugador[s], is_grande)
        # 'mano' => ganó el primer argumento (best, más cercano a la mano) → se mantiene.
        # 'postre' => ganó el segundo (s) → pasa a ser el mejor.
        if gan == 'postre':
            best = s
    return best

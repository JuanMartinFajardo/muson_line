# encoder.py — Codificación de estado para el bot de 4 jugadores. Fase 1.5.
#
# Bloques A–E de wiki/Bot-AI-4p-ML-Strategy.md §4.2. La entrada es SIEMPRE el
# diccionario de observación que devuelve `PartidaMus4.vista(seat)` — el mismo
# contrato que ya usa el bot heurístico desde la Fase 0.
#
# Por qué esto importa más de lo que parece: el fallo §3.4 del audit ("skew
# entrenamiento/servicio") nace de tener DOS codificaciones, una en el gimnasio
# y otra en el servidor, que se separan sin que nadie se entere. Aquí hay una
# sola función, `codificar(vista)`, y la usan por igual el entorno de
# entrenamiento (mus_env4.py), el bot al servir y el exportador de datasets
# (tools/logs2dataset.py). Si cambia el encoder, cambia para todos a la vez y
# los datasets se regeneran re-jugando los logs.
#
# Reglas de diseño:
#   * Todo relativo al asiento y al equipo (posición respecto a la mano, "mi
#     equipo" / "el rival", rivales por posición relativa). Así una sola red
#     sirve para los cuatro asientos (§4.2: el juego es simétrico bajo
#     renombrado de asientos) y el coste en muestras se divide por cuatro.
#   * Los rasgos caros de descubrir se dan hechos (tiene pares, categoría de
#     pares, valor de juego): que la red gaste capacidad en aprender las reglas
#     del mus no aporta nada.
#   * Los tri-estados (una declaración puede ser sí / no / aún no cantada) van
#     en DOS dimensiones (conocido, valor). Meter "no se sabe" como 0.5 sería
#     mentirle a la red diciendo que es un punto medio entre sí y no.
#   * El bloque E queda a cero hasta la Fase 6 (señas). Está aquí desde hoy para
#     que el ajuste fino de entonces CONTINÚE desde el checkpoint sin señas en
#     vez de tener que reentrenar: con entradas a cero la función es idéntica.

import numpy as np

# Espacio de acciones (orden canónico, el mismo de train_cfr.py y de la arena).
ACCIONES = ('pasar', 'envidar', 'ver', 'nover', 'subir', 'ordago')
ACCION_A_IDX = {a: i for i, a in enumerate(ACCIONES)}
N_ACCIONES = len(ACCIONES)

LANCES = ('Grande', 'Chica', 'Pares', 'Juego', 'Punto')

# Normalizadores. 40 es el objetivo de la partida; 12 el rango de la carta más
# alta en valores de mus; 40 la suma de juego máxima.
_P = 40.0
_CARTA = 12.0


def _tri(valor):
    """Tri-estado → (conocido, valor). None = aún no cantado."""
    if valor is None:
        return (0.0, 0.0)
    return (1.0, 1.0 if valor else 0.0)


def _onehot(indice, n):
    v = [0.0] * n
    if indice is not None and 0 <= indice < n:
        v[indice] = 1.0
    return v


# ==========================================================================
# Nombres de las features, en el mismo orden que las produce `codificar`.
# Los necesita la Fase 5 (importancia por permutación, cargas de PCA, SHAP):
# un ranking de features sin nombres no responde a nada.
# ==========================================================================
def _nombres():
    n = []
    # --- Bloque A: yo ---
    n += [f'A_dist_mano_{i}' for i in range(4)]
    n += [f'A_carta_{i}' for i in range(4)]
    n += ['A_tiene_pares', 'A_pares_tipo', 'A_pares_premio']
    n += ['A_tiene_juego', 'A_suma_juego', 'A_juego_valor']
    n += ['A_descartes_hechos']
    # --- Bloque B: público ---
    n += [f'B_lance_{l}' for l in LANCES]
    n += ['B_rondas_mus', 'B_juego_es_punto']
    for rel in (1, 2, 3):
        etiqueta = 'comp' if rel == 2 else f'rival{rel}'
        n += [f'B_{etiqueta}_pares_conocido', f'B_{etiqueta}_pares',
              f'B_{etiqueta}_juego_conocido', f'B_{etiqueta}_juego',
              f'B_{etiqueta}_descartes']
    # --- Bloque C: apuestas ---
    n += ['C_subida', 'C_es_ordago', 'C_apuesta_vista', 'C_bote_lance']
    n += [f'C_owner_{l}' for l in ('Grande', 'Chica', 'Pares', 'Juego')]
    n += ['C_hay_apuesta', 'C_apuesta_es_mia']
    n += [f'C_ultimo_apostador_rel_{i}' for i in range(4)]
    n += ['C_companero_puede_responder', 'C_deje', 'C_coste_ver',
          'C_obligado_a_ver', 'C_pases_consecutivos']
    # --- Bloque D: marcador ---
    n += ['D_puntos_equipo', 'D_puntos_rival', 'D_a40_propio', 'D_a40_rival',
          'D_partidas_propias', 'D_partidas_rival', 'D_al_mejor_de']
    # --- Bloque E: señas (reservado) ---
    n += ['E_pareja_pares', 'E_pareja_juego', 'E_pareja_31', 'E_pareja_reyes',
          'E_pareja_ases', 'E_confianza', 'E_cazado_rival_1', 'E_cazado_rival_3']
    return tuple(n)


NOMBRES = _nombres()
DIM = len(NOMBRES)

# Índices de inicio de cada bloque (para los análisis por bloque de la Fase 5).
BLOQUES = {}
_ini = 0
for _b in ('A', 'B', 'C', 'D', 'E'):
    _fin = _ini
    while _fin < DIM and NOMBRES[_fin].startswith(_b + '_'):
        _fin += 1
    BLOQUES[_b] = (_ini, _fin)
    _ini = _fin


def codificar(vista, salida=None):
    """`vista` (PartidaMus4.vista(seat)) → vector float32 de longitud DIM.

    `salida` permite reutilizar un array y ahorrar la asignación en el bucle
    caliente del gimnasio."""
    A, B, C, D, E = (vista['A_propio'], vista['B_publico'], vista['C_apuestas'],
                     vista['D_marcador'], vista['E_senas'])
    v = []

    # ---------------- Bloque A: yo ----------------
    v += _onehot(A['dist_mano'], 4)
    cartas = sorted(A['valores_mus'], reverse=True)[:4]
    cartas += [0] * (4 - len(cartas))          # antes del reparto la mano va vacía
    v += [c / _CARTA for c in cartas]
    v += [1.0 if A['tiene_pares'] else 0.0,
          A['pares_tipo'] / 3.0,
          A['pares_premio'] / 3.0]
    v += [1.0 if A['tiene_juego'] else 0.0,
          A['suma_juego'] / _P,
          A['juego_valor'] / 3.0]
    v += [A['descartes_hechos'] / 4.0]

    # ---------------- Bloque B: público ----------------
    lance = B['lance']
    v += _onehot(LANCES.index(lance) if lance in LANCES else None, len(LANCES))
    v += [min(B['rondas_mus'], 5) / 5.0,
          1.0 if B['juego_es_punto'] else 0.0]
    otros = {o['rel']: o for o in B['otros']}
    for rel in (1, 2, 3):
        o = otros.get(rel) or {}
        v += list(_tri(o.get('pares_dec')))
        v += list(_tri(o.get('juego_dec')))
        v += [(o.get('descartes') or 0) / 4.0]

    # ---------------- Bloque C: apuestas ----------------
    subida = C['subida_pendiente']
    v += [(_P if C['es_ordago'] else (subida or 0)) / _P,
          1.0 if C['es_ordago'] else 0.0,
          C['apuesta_vista'] / _P,
          C['bote_lance'] / _P]
    v += [C['owners'].get(l, 0.5) for l in ('Grande', 'Chica', 'Pares', 'Juego')]
    mia = C['apuesta_de_mi_equipo']
    v += [0.0 if mia is None else 1.0, 1.0 if mia else 0.0]
    v += _onehot(C['ultimo_apostador_rel'], 4)
    v += [1.0 if C['companero_puede_responder'] else 0.0,
          C['deje'] / _P,
          min(C['coste_ver'], _P) / _P,
          1.0 if C['obligado_a_ver'] else 0.0,
          C['pases_consecutivos'] / 4.0]

    # ---------------- Bloque D: marcador ----------------
    mejor_de = max(1, D['al_mejor_de'])
    v += [D['puntos_equipo'] / _P, D['puntos_rival'] / _P,
          D['a_40_propio'] / _P, D['a_40_rival'] / _P,
          D['partidas_propias'] / mejor_de, D['partidas_rival'] / mejor_de,
          mejor_de / 5.0]

    # ---------------- Bloque E: señas (cero hasta la Fase 6) ----------------
    v += [float(E['pareja_pares']), float(E['pareja_juego']), float(E['pareja_31']),
          float(E['pareja_reyes']), float(E['pareja_ases']), float(E['confianza']),
          float(E['cazado_rival_1']), float(E['cazado_rival_3'])]

    if salida is not None:
        salida[:] = v
        return salida
    return np.asarray(v, dtype=np.float32)


def mascara_acciones(vista):
    """Vector 0/1 de longitud N_ACCIONES con las acciones de APUESTA legales.

    Sale de `vista['meta']['acciones_legales']`, o sea del motor: una política
    que multiplique por esta máscara no puede proponer una jugada ilegal."""
    m = np.zeros(N_ACCIONES, dtype=np.float32)
    for a in vista['meta']['acciones_legales']:
        idx = ACCION_A_IDX.get(a)
        if idx is not None:
            m[idx] = 1.0
    return m


def indices_legales(vista):
    return [ACCION_A_IDX[a] for a in vista['meta']['acciones_legales']
            if a in ACCION_A_IDX]


if __name__ == '__main__':
    from mus_mecanicas_4 import PartidaMus4

    print(f"encoder: {DIM} dimensiones, {N_ACCIONES} acciones")
    for b, (i, f) in BLOQUES.items():
        print(f"  bloque {b}: dims {i}..{f - 1} ({f - i})")
    motor = PartidaMus4()
    motor.iniciar_ronda()
    motor.repartir_inicial()
    motor.cantar_mus(motor.mano, False)
    x = codificar(motor.vista(motor.turno_de))
    print(f"  vector de ejemplo: {x.shape} {x.dtype}, "
          f"min={x.min():.2f} max={x.max():.2f}")
    print(f"  legales: {motor.acciones_legales(motor.turno_de)} → {mascara_acciones(motor.vista(motor.turno_de))}")

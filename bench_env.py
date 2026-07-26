# bench_env.py — Rendimiento del simulador. Puerta de la Fase 1.4.
#
# El audit (wiki/Bot-AI-4p-ML-Strategy.md §3.6) señala a `copy.deepcopy` como el
# cuello de botella real del entrenamiento: el muestreo externo de CFR clona el
# entorno en CADA acción explorada del traversante, y deepcopy recorre también
# los dicts de carta (valor/palo/ruta de imagen/texto), el logger y la baraja.
# `fork()` copia solo los contenedores y comparte las cartas, que el motor mueve
# pero nunca modifica.
#
# LA PUERTA: ≥10× (objetivo 20×) en traversals por segundo. Mientras no se pase,
# no se alquila una sola hora de nube (§12): comprar CPU para pagar deepcopy es
# tirar el presupuesto.
#
# Lo que se mide es un traversal de muestreo externo COMPLETO con política
# aleatoria — no el clon aislado. Es la única cifra que se traduce en
# iteraciones por noche.
#
# Las dos filas que imprime aíslan EL CLON: lo único que cambia entre ellas es
# cómo se copia el motor. La Fase 1 trajo además una segunda mejora que beneficia
# a las dos filas por igual (evaluar pares/juego sin `collections.Counter`, y no
# construir el dict de `vista()` en cada paso), así que el "antes vs después"
# de verdad es mayor que el ratio de aquí. Medido en el motor de 2 jugadores
# contra el código anterior a la Fase 1:
#
#     antes  (deepcopy + Counter):   22,7 traversals/s
#     después (fork + dict a mano): 490,3 traversals/s   → 21,6×
#
# Para reproducir el "antes": sacar mus_mecanicas.py / mus_env.py /
# mus_discard_chooser.py del commit anterior a la Fase 1 en un directorio
# aparte y correr allí el mismo traversal con `env.clone()`.
#
#   python3 bench_env.py                 # 2p y 4p, 400 traversals cada uno
#   python3 bench_env.py --traversals 1000 --solo 4p

import argparse
import copy
import random
import time


# ==========================================================================
# Traversal de muestreo externo (la forma exacta de train_cfr.traverse)
# --------------------------------------------------------------------------
# En el nodo del traversante se exploran TODAS las acciones legales, cada una
# sobre un clon; en los demás nodos se muestrea una sola. De ahí que el coste
# del clon domine el tiempo total.
# ==========================================================================
def traverse_2p(env, jugador_traversante, clonar, profundidad=0):
    p = env.partida
    if p.fase == 'recuento':
        p.calcular_recuento()
        return p.estado[jugador_traversante]['puntos']

    legales = env.get_valid_actions()
    if not legales or profundidad > 40:
        return 0

    if p.turno_de == jugador_traversante:
        total = 0.0
        for accion in legales:
            hijo = clonar(env)
            hijo.step(accion)
            total += traverse_2p(hijo, jugador_traversante, clonar, profundidad + 1)
        return total / len(legales)

    hijo = clonar(env)
    hijo.step(random.choice(legales))
    return traverse_2p(hijo, jugador_traversante, clonar, profundidad + 1)


def traverse_4p(env, seat_traversante, clonar, profundidad=0):
    """Igual, pero el traversante es un ASIENTO, no un equipo.

    Es lo que prescribe §4.2 ("las travesías alternan el asiento traversante, 4
    rotaciones por iteración"): una red compartida, un dueño de conjunto de
    información por asiento. Expandir todas las acciones de LOS DOS compañeros en
    la misma travesía multiplicaría el árbol sin ganar nada — el compañero es,
    para el muestreo externo, otro jugador más al que se le muestrea la jugada."""
    p = env.partida
    if p.fase == 'recuento':
        p.calcular_recuento()
        return env.utilidad_equipo(p.equipo_de[seat_traversante])

    legales = env.acciones_legales()
    if not legales or profundidad > 60:
        return 0.0

    if p.turno_de == seat_traversante:
        total = 0.0
        for accion in legales:
            hijo = clonar(env)
            hijo.step(accion)
            total += traverse_4p(hijo, seat_traversante, clonar, profundidad + 1)
        return total / len(legales)

    hijo = clonar(env)
    hijo.step(random.choice(legales))
    return traverse_4p(hijo, seat_traversante, clonar, profundidad + 1)


# ==========================================================================
# Medición
# ==========================================================================
def medir(nombre_env, crear_env, traverse, traversante, clonar, n, semilla):
    """Traversals por segundo, con el reset FUERA del cronómetro del traversal.

    El reset (repartir, mus, descartes heurísticos) es coste fijo del entorno y
    no lo toca el cambio de clonado; medirlo dentro diluiría la comparación."""
    random.seed(semilla)
    env = crear_env()

    t_reset = t_trav = 0.0
    for _ in range(n):
        t0 = time.perf_counter()
        env.reset()
        t1 = time.perf_counter()
        traverse(env, traversante(env), clonar)
        t2 = time.perf_counter()
        t_reset += t1 - t0
        t_trav += t2 - t1
    return {'env': nombre_env, 'n': n, 'reset_s': t_reset, 'trav_s': t_trav,
            'tps': n / t_trav if t_trav else float('inf')}


def comparar(nombre, crear_env, traverse, traversante, n, semilla):
    # Comparación limpia: LO ÚNICO que cambia entre las dos medidas es cómo se
    # copia el motor. El resto del entorno (tablas de EV, distribución de
    # estados) se comparte en ambos casos, igual que hacía el código antiguo
    # cuando esas tablas eran globales de módulo.
    deep = medir(nombre, crear_env, traverse, traversante,
                 lambda e: e.fork(copy.deepcopy), n, semilla)
    fork = medir(nombre, crear_env, traverse, traversante,
                 lambda e: e.fork(), n, semilla)
    ratio = fork['tps'] / deep['tps'] if deep['tps'] else float('inf')
    print(f"\n{nombre}  ({n} traversals de muestreo externo, política aleatoria)")
    print(f"  deepcopy : {deep['tps']:8.1f} traversals/s   ({deep['trav_s']:.2f}s)")
    print(f"  fork()   : {fork['tps']:8.1f} traversals/s   ({fork['trav_s']:.2f}s)")
    print(f"  reset    : {fork['reset_s'] / n * 1000:.2f} ms/mano (fuera de la medida)")
    print(f"  → speedup {ratio:.1f}×")
    return ratio


def main():
    ap = argparse.ArgumentParser(description="Puerta de rendimiento de la Fase 1.4.")
    ap.add_argument('--traversals', type=int, default=400)
    ap.add_argument('--semilla', type=int, default=5)
    ap.add_argument('--solo', choices=['2p', '4p'], default=None)
    ap.add_argument('--gate', type=float, default=10.0, help='speedup mínimo exigido')
    args = ap.parse_args()

    ratios = {}

    if args.solo != '4p':
        from mus_env import MusBettingEnv
        ratios['2p'] = comparar(
            "2 jugadores — mus_env.MusBettingEnv", MusBettingEnv,
            traverse_2p, lambda e: e.partida.turno_de,
            args.traversals, args.semilla)

    if args.solo != '2p':
        from mus_env4 import MusBettingEnv4
        ratios['4p'] = comparar(
            "2v2 — mus_env4.MusBettingEnv4", MusBettingEnv4,
            traverse_4p, lambda e: e.partida.turno_de,
            args.traversals, args.semilla)

    peor = min(ratios.values())
    print(f"\n{'=' * 62}")
    print(f"PUERTA FASE 1.4 (≥{args.gate:.0f}×, objetivo 20×): "
          f"peor caso {peor:.1f}×  →  {'✅ PASA' if peor >= args.gate else '❌ NO PASA'}")
    if peor < args.gate:
        print("  No se alquila nube hasta pasarla (§12). Siguiente palanca:")
        print("  agrupar las consultas a la red por traversal, y luego workers "
              "de multiprocessing.")
    print('=' * 62)
    return 0 if peor >= args.gate else 1


if __name__ == '__main__':
    raise SystemExit(main())

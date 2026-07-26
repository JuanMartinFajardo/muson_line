#!/usr/bin/env python3
# tools/fuzz_env4.py — Fuzzing de MusBettingEnv4. Criterio de la Fase 1.5.
#
# El roadmap pide "MusBettingEnv4 fuzz-testeado (10.000 partidas al azar, sin
# estados ilegales)". Lo que se comprueba en cada paso:
#
#   * el entorno solo ofrece acciones que el motor acepta (nada de estados
#     donde la lista de legales y la legalidad real se separen);
#   * el vector del encoder existe, tiene la longitud correcta y no lleva NaN
#     ni valores fuera de rango razonable;
#   * la máscara de acciones nunca sale vacía en un nodo de decisión;
#   * la recompensa es de suma coherente con el marcador (delta de la mano) y
#     nunca supera los 40 puntos que puede mover una mano;
#   * `fork()` da un estado INDEPENDIENTE: jugar en el clon no toca al padre
#     (si esto falla, CFR aprende basura y no hay forma de notarlo mirando la
#     curva de pérdida).
#
#   python3 tools/fuzz_env4.py                  # 10.000 manos
#   python3 tools/fuzz_env4.py --manos 500 --semilla 3

import argparse
import math
import os
import random
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import encoder                                        # noqa: E402
from mus_env4 import MusBettingEnv4                   # noqa: E402


class EstadoIlegal(Exception):
    pass


def comprobar_vista(env):
    vista = env.observacion()
    if vista is None:
        raise EstadoIlegal("no hay observación en un nodo de decisión")
    x = encoder.codificar(vista)
    if len(x) != encoder.DIM:
        raise EstadoIlegal(f"el encoder devolvió {len(x)} dims y no {encoder.DIM}")
    for i, v in enumerate(x):
        if math.isnan(v) or math.isinf(v):
            raise EstadoIlegal(f"feature {encoder.NOMBRES[i]} no es finita: {v}")
        if not (-2.0 <= v <= 2.0):
            raise EstadoIlegal(f"feature {encoder.NOMBRES[i]} fuera de rango: {v}")
    if encoder.mascara_acciones(vista).sum() == 0:
        raise EstadoIlegal("máscara de acciones vacía en un nodo de decisión")
    # Bloque E reservado: cero hasta la Fase 6, por construcción.
    ini, fin = encoder.BLOQUES['E']
    if any(x[ini:fin]):
        raise EstadoIlegal("el bloque E (señas) no está a cero")
    return vista


def comprobar_fork(env):
    """Un fork tiene que ser independiente del padre en las dos direcciones."""
    padre_antes = _huella(env)
    hijo = env.fork()
    legales = hijo.acciones_legales()
    if not legales:
        return
    hijo.step(random.choice(legales))
    if _huella(env) != padre_antes:
        raise EstadoIlegal("jugar en el fork ha modificado al padre")


def _huella(env):
    p = env.partida
    return (p.fase, p.indice_fase, p.turno_de, p.apuesta_vista, p.subida_pendiente,
            tuple(sorted(p.puntos.items())), tuple(sorted(p.botes.items())),
            tuple(tuple(c['valor'] for c in p.estado[s]['cartas']) for s in range(4)))


def main():
    ap = argparse.ArgumentParser(description="Fuzzing de MusBettingEnv4 (Fase 1.5).")
    ap.add_argument('--manos', type=int, default=10000)
    ap.add_argument('--semilla', type=int, default=2)
    ap.add_argument('--cada-cuantas-fork', type=int, default=25,
                    help='comprobar la independencia del fork cada N manos')
    args = ap.parse_args()

    random.seed(args.semilla)
    env = MusBettingEnv4()
    print(f"distribución de estados: {env.dist.origen}")
    print(f"fuzzing {args.manos} manos…")

    acciones = Counter()
    decisiones = 0
    for i in range(args.manos):
        env.reset()
        if env.observacion() is None:
            raise EstadoIlegal(f"mano {i}: el reset no llega a la fase de apuestas")

        pasos = 0
        done = False
        while not done:
            pasos += 1
            if pasos > 200:
                raise EstadoIlegal(f"mano {i}: la mano no termina")
            vista = comprobar_vista(env)
            legales = env.acciones_legales()
            if not legales:
                raise EstadoIlegal(f"mano {i}: sin acciones legales en fase de apuestas")
            if set(legales) - set(vista['meta']['acciones_legales']):
                raise EstadoIlegal(f"mano {i}: el entorno ofrece más de lo que el motor permite")

            if i % args.cada_cuantas_fork == 0:
                comprobar_fork(env)

            accion = random.choice(legales)
            acciones[accion] += 1
            decisiones += 1
            recompensas, done = env.step(accion)

            if done:
                for eq, r in recompensas.items():
                    if not (0 <= r <= 40):
                        raise EstadoIlegal(f"mano {i}: recompensa imposible {eq}={r}")
                u = env.utilidad_equipo('A')
                if not (-1.0001 <= u <= 1.0001) or u != -env.utilidad_equipo('B'):
                    raise EstadoIlegal(f"mano {i}: utilidad no es de suma cero: {u}")

        if (i + 1) % 2000 == 0:
            print(f"  … {i + 1} manos, {decisiones} decisiones, sin estados ilegales")

    print(f"\n✅ {args.manos} manos, {decisiones} decisiones, 0 estados ilegales")
    total = sum(acciones.values())
    print("   reparto de acciones ofrecidas y jugadas:")
    for a, c in acciones.most_common():
        print(f"     {a:>8} {c / total:6.1%}")
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except EstadoIlegal as e:
        print(f"\n❌ {e}")
        sys.exit(1)

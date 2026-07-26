#!/usr/bin/env python3
# tools/arena4.py — Arena de 2v2. Fase 1.6 del roadmap de IA.
#
# Todo lo que se afirme sobre la fuerza de un bot sale de aquí. Tres decisiones
# de diseño que son la diferencia entre una cifra y una anécdota:
#
#   1. ASIENTOS PERMUTADOS. Ser mano gana empates y abrir el lance no es
#      neutral: cada emparejamiento se juega en las dos configuraciones (el
#      agente A en {0,2} y luego en {1,3}) y se promedia. Sin esto se mide el
#      asiento, no el bot.
#   2. REPARTOS SEMBRADOS (números aleatorios comunes). Los dos emparejamientos
#      arrancan del mismo `random.Random(semilla)` del motor, así que ven los
#      mismos repartos mientras las decisiones coincidan. Reduce muchísimo la
#      varianza: la diferencia que se mide es la de las políticas, no la de las
#      cartas.
#   3. PUNTOS POR MANO ± ERROR ESTÁNDAR, no "% de matches ganados". El winrate
#      de match tira mucha información a la basura (una paliza y un 40-39 valen
#      igual) y necesita 10× más partidas para la misma precisión. Los puntos
#      por mano son la unidad en la que están escritas las puertas del roadmap
#      ("gana al heurístico por ≥1,5 puntos/mano").
#
#   python3 tools/arena4.py --matches 300
#   python3 tools/arena4.py --agentes heuristico aleatorio --matches 600
#   python3 tools/arena4.py --agentes agresivo conservador musero --matches 200

import argparse
import itertools
import math
import os
import random
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mus_mecanicas_4 import PartidaMus4                        # noqa: E402
from bot_ml_4 import SmartBot4, MusBotBase, PERSONALIDADES      # noqa: E402

MAX_PASOS_POR_MATCH = 40000


# ==========================================================================
# Agentes
# ==========================================================================
class BotAleatorio(MusBotBase):
    """Elige uniformemente entre las acciones legales. Es el suelo del ranking:
    cualquier bot que no le gane por goleada está roto."""

    def __init__(self, sid, asiento, rng=None):
        # No se llama a super(): `MusBotBase.__init__` valida la personalidad
        # contra los presets de #12 y "aleatorio" no es uno de ellos — es la
        # ausencia de política, no una personalidad.
        self.sid = sid
        self.asiento = asiento
        self.personalidad = 'aleatorio'
        self.rng = rng or random

    def obtener_accion(self, vista):
        legales = list(vista['meta']['acciones_legales'])
        if not legales:
            return None
        accion = self.rng.choice(legales)
        meta = {'personalidad': 'aleatorio'}
        if accion == 'descartar':
            n = len(vista['A_propio']['valores'])
            k = self.rng.randint(1, n)
            meta['indices'] = self.rng.sample(range(n), k)
        cantidad = 2 if accion in ('envidar', 'subir') else 0
        return (accion, cantidad, meta)


def fabrica(nombre):
    """nombre → función (sid, asiento) -> bot."""
    if nombre == 'aleatorio':
        return lambda sid, seat: BotAleatorio(sid, seat)
    if nombre == 'heuristico':
        return lambda sid, seat: SmartBot4(sid, seat, 'equilibrado')
    if nombre in PERSONALIDADES:
        return lambda sid, seat, p=nombre: SmartBot4(sid, seat, p)
    raise SystemExit(f"agente desconocido: {nombre!r} "
                     f"(hay: aleatorio, heuristico, {', '.join(PERSONALIDADES)})")


AGENTES_POR_DEFECTO = ('heuristico', 'aleatorio')


# ==========================================================================
# Un match
# ==========================================================================
class JugadaIlegal(Exception):
    pass


def _aplicar(motor, seat, accion, cantidad, meta):
    """Mismo orden de prioridades que server_mus4.procesar_accion_4."""
    if accion not in motor.acciones_legales(seat):
        raise JugadaIlegal(f"asiento {seat}: '{accion}' ilegal en fase={motor.fase}")
    if accion == 'pedrete':
        motor.procesar_pedrete(seat)
    elif accion == 'repartir':
        motor.repartir_inicial()
    elif accion in ('mus', 'no_mus'):
        motor.cantar_mus(seat, accion == 'mus')
    elif accion == 'descartar':
        indices = meta.get('indices') or [0]
        motor.procesar_descarte(seat, indices)
    elif accion == 'listo_siguiente_ronda':
        if seat not in motor.jugadores_listos:
            motor.jugadores_listos.append(seat)
    else:
        motor.accion_apuesta(seat, accion, cantidad)


def jugar_match(fab_A, fab_B, semilla, al_mejor_de=1, invertir=False):
    """Un match con el agente A en un equipo y B en el otro.

    `invertir=False` pone A en el equipo A (asientos 0 y 2); `invertir=True` lo
    pone en el B (1 y 3). Con la misma semilla, las dos mitades del par ven el
    mismo mazo: es la permutación de asientos del punto 1 de la cabecera.

    Devuelve (puntos_de_A, puntos_de_B, manos, ganador_de_A)."""
    motor = PartidaMus4()
    motor.rng = random.Random(semilla)
    motor.mano = motor.rng.randrange(4)
    motor.al_mejor_de = al_mejor_de
    motor.iniciar_ronda()

    eq_de_A = 'B' if invertir else 'A'
    eq_de_B = 'A' if invertir else 'B'
    bots = {}
    for seat in range(4):
        eq = motor.equipo_de[seat]
        fab = fab_A if eq == eq_de_A else fab_B
        bots[seat] = fab(f'ARENA_{seat}', seat)

    puntos = {eq_de_A: 0, eq_de_B: 0}     # acumulado de puntos GANADOS por mano
    manos = 0
    previos = dict(motor.puntos)

    pasos = 0
    while not motor.match_finalizado:
        pasos += 1
        if pasos > MAX_PASOS_POR_MATCH:
            raise JugadaIlegal("el match no termina")

        if motor.mensaje_transicion:
            motor.mensaje_transicion = None
            motor.preparar_subfase()
            continue

        if motor.fase == 'recuento':
            motor.calcular_recuento()
            for eq in ('A', 'B'):
                puntos[eq] += motor.puntos[eq] - previos[eq]
            manos += 1
            if motor.match_finalizado:
                break
            if motor.puntos['A'] >= 40 or motor.puntos['B'] >= 40:
                motor.reiniciar_partida()
            else:
                motor.siguiente_ronda()
            motor.jugadores_listos = []
            previos = dict(motor.puntos)
            continue

        actuó = False
        for seat in range(4):
            decision = bots[seat].obtener_accion(motor.vista(seat))
            if not decision:
                continue
            _aplicar(motor, seat, *decision)
            actuó = True
            break
        if not actuó:
            raise JugadaIlegal(f"nadie puede jugar: fase={motor.fase}")

    gana_A = motor.partidas_ganadas[eq_de_A] > motor.partidas_ganadas[eq_de_B]
    return puntos[eq_de_A], puntos[eq_de_B], manos, gana_A


# ==========================================================================
# Emparejamiento y estadística
# ==========================================================================
def enfrentar(nombre_A, nombre_B, n_matches, al_mejor_de, semilla_base):
    """Puntos por mano de A frente a B, promediado sobre las dos colocaciones."""
    fab_A, fab_B = fabrica(nombre_A), fabrica(nombre_B)
    muestras = []          # diferencia de puntos por mano, un dato por match
    victorias = Counter()
    manos_total = 0

    for i in range(n_matches):
        semilla = semilla_base + i
        for invertir in (False, True):
            random.seed(semilla * 7919 + int(invertir))   # azar de los bots
            pa, pb, manos, gana_A = jugar_match(
                fab_A, fab_B, semilla, al_mejor_de, invertir)
            if manos:
                muestras.append((pa - pb) / manos)
            manos_total += manos
            victorias['A' if gana_A else 'B'] += 1

    n = len(muestras)
    media = sum(muestras) / n if n else 0.0
    if n > 1:
        var = sum((x - media) ** 2 for x in muestras) / (n - 1)
        err = math.sqrt(var / n)
    else:
        err = float('nan')
    return {'A': nombre_A, 'B': nombre_B, 'ppm': media, 'stderr': err,
            'n': n, 'manos': manos_total,
            'winrate_A': victorias['A'] / max(1, victorias['A'] + victorias['B'])}


def main():
    ap = argparse.ArgumentParser(description="Arena 2v2 con asientos permutados (Fase 1.6).")
    ap.add_argument('--agentes', nargs='+', default=list(AGENTES_POR_DEFECTO))
    ap.add_argument('--matches', type=int, default=200,
                    help='matches por colocación (cada par juega 2× esto)')
    ap.add_argument('--al-mejor-de', type=int, default=1)
    ap.add_argument('--semilla', type=int, default=1000)
    args = ap.parse_args()

    if len(args.agentes) < 2:
        ap.error("hacen falta al menos dos agentes")

    print(f"Arena 2v2 · {len(args.agentes)} agentes · {args.matches} matches por "
          f"colocación (×2 colocaciones) · al mejor de {args.al_mejor_de}")
    print("Positivo = el primero gana puntos por mano al segundo.\n")

    filas = []
    for a, b in itertools.combinations(args.agentes, 2):
        r = enfrentar(a, b, args.matches, args.al_mejor_de, args.semilla)
        filas.append(r)
        sig = abs(r['ppm']) / r['stderr'] if r['stderr'] and not math.isnan(r['stderr']) else 0
        print(f"  {a:>14} vs {b:<14} {r['ppm']:+6.3f} ± {r['stderr']:.3f} pts/mano"
              f"   (|t|={sig:4.1f}, {r['n']} matches, {r['manos']} manos, "
              f"winrate {r['winrate_A']:.1%})")

    # Tabla de puntos por mano acumulados por agente (un Elo mínimo y honesto:
    # con más generaciones esto se convierte en el round-robin del §7.4).
    print("\nResumen (media de puntos/mano contra todos los rivales):")
    acum = {a: [] for a in args.agentes}
    for r in filas:
        acum[r['A']].append(r['ppm'])
        acum[r['B']].append(-r['ppm'])
    for a, v in sorted(acum.items(), key=lambda kv: -sum(kv[1]) / max(1, len(kv[1]))):
        print(f"  {a:>14} {sum(v) / max(1, len(v)):+6.3f} pts/mano")
    return 0


if __name__ == '__main__':
    sys.exit(main())

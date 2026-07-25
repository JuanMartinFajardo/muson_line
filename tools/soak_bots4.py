#!/usr/bin/env python3
# tools/soak_bots4.py — Prueba de resistencia de los bots de 4 jugadores.
#
# Criterio de aceptación de la Fase 0 (wiki/Bot-AI-4p-Roadmap.md): una mesa 2v2
# con bots juega matches completos sin una sola jugada ilegal, y las
# personalidades producen tasas de apuesta medibles y distintas.
#
# Este script NO usa el servidor: mueve PartidaMus4 directamente con el mismo
# bucle que server_mus4 (misma prioridad de acciones, mismo auto-avance de las
# transiciones), así que es reproducible y rápido.
#
#   python3 tools/soak_bots4.py --matches 500 --al-mejor-de 1
#   python3 tools/soak_bots4.py --matches 60 --al-mejor-de 3
#   python3 tools/soak_bots4.py --personalidades agresivo conservador

import argparse
import os
import random
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mus_mecanicas_4 import PartidaMus4          # noqa: E402
from bot_ml_4 import SmartBot4, PERSONALIDADES   # noqa: E402

MAX_PASOS_POR_MATCH = 40000   # cortafuegos contra un bucle infinito


class JugadaIlegal(Exception):
    pass


def aplicar(motor, seat, accion, cantidad, meta):
    """Ejecuta la acción del bot igual que server_mus4.procesar_accion_4."""
    if accion not in motor.acciones_legales(seat):
        raise JugadaIlegal(
            f"asiento {seat} intentó '{accion}' con fase={motor.fase} "
            f"lance={motor.FASES_APUESTA[motor.indice_fase] if motor.indice_fase < 4 else '-'} "
            f"turno={motor.turno_de} legales={motor.acciones_legales(seat)}")

    if accion == 'pedrete':
        motor.procesar_pedrete(seat)
    elif accion == 'repartir':
        motor.repartir_inicial()
    elif accion in ('mus', 'no_mus'):
        motor.cantar_mus(seat, accion == 'mus')
    elif accion == 'descartar':
        indices = meta.get('indices') or []
        if not indices:
            raise JugadaIlegal(f"asiento {seat} descartó 0 cartas tras pedir mus")
        motor.procesar_descarte(seat, indices)
    elif accion == 'listo_siguiente_ronda':
        if seat not in motor.jugadores_listos:
            motor.jugadores_listos.append(seat)
        if len(set(motor.jugadores_listos)) >= 4:
            if motor.puntos['A'] >= 40 or motor.puntos['B'] >= 40:
                motor.reiniciar_partida()
            else:
                motor.siguiente_ronda()
            motor.jugadores_listos = []
    else:
        motor.accion_apuesta(seat, accion, cantidad)


def jugar_match(personalidades, al_mejor_de, stats):
    motor = PartidaMus4()
    motor.al_mejor_de = al_mejor_de
    motor.generate_log = False
    motor.nombres = {s: f'Bot{s}-{personalidades[s]}' for s in range(4)}
    motor.usernames = {s: None for s in range(4)}
    motor.iniciar_ronda()

    bots = {s: SmartBot4(f'BOT_SOAK_{s}', s, personalidades[s]) for s in range(4)}

    pasos = 0
    while not motor.match_finalizado:
        pasos += 1
        if pasos > MAX_PASOS_POR_MATCH:
            raise JugadaIlegal("el match no termina: posible bucle de estado")

        # El servidor auto-avanza los mensajes de transición pasados 3 s.
        if motor.mensaje_transicion:
            motor.mensaje_transicion = None
            motor.preparar_subfase()
            continue

        if motor.fase == 'recuento':
            # Es el recuento quien fija puntos, partidas y match_finalizado.
            motor.calcular_recuento()
            if motor.match_finalizado:
                break

        actuó = False
        for seat in range(4):
            decision = bots[seat].obtener_accion(motor.vista(seat))
            if not decision:
                continue
            accion, cantidad, meta = decision
            if motor.fase == 'apuestas' and accion in (
                    'pasar', 'envidar', 'subir', 'ver', 'nover', 'ordago'):
                stats[personalidades[seat]][accion] += 1
                stats[personalidades[seat]]['_decisiones'] += 1
            elif accion in ('mus', 'no_mus'):
                stats[personalidades[seat]][accion] += 1
                stats[personalidades[seat]]['_mus'] += 1
            aplicar(motor, seat, accion, cantidad, meta)
            actuó = True
            break

        if not actuó:
            raise JugadaIlegal(
                f"nadie puede jugar: fase={motor.fase} turno={motor.turno_de} "
                f"transicion={motor.mensaje_transicion}")

    ganador = 'A' if motor.partidas_ganadas['A'] > motor.partidas_ganadas['B'] else 'B'
    return ganador, motor.ronda_n


def main():
    ap = argparse.ArgumentParser(description="Soak de bots 4p (Fase 0).")
    ap.add_argument('--matches', type=int, default=500)
    ap.add_argument('--al-mejor-de', type=int, default=1)
    ap.add_argument('--semilla', type=int, default=7)
    ap.add_argument('--personalidades', nargs=4, default=None,
                    metavar='P', help='personalidad por asiento 0..3')
    args = ap.parse_args()

    random.seed(args.semilla)

    if args.personalidades:
        for p in args.personalidades:
            if p not in PERSONALIDADES:
                ap.error(f"personalidad desconocida: {p} (hay {list(PERSONALIDADES)})")
        personalidades = {s: args.personalidades[s] for s in range(4)}
    else:
        # Por defecto enfrentamos agresivos (equipo A) contra conservadores
        # (equipo B): así el mismo soak mide la diferencia de personalidades.
        personalidades = {0: 'agresivo', 1: 'conservador', 2: 'agresivo', 3: 'conservador'}

    print(f"Asientos: {personalidades}")
    print(f"{args.matches} matches al mejor de {args.al_mejor_de}…")

    stats = {p: Counter() for p in set(personalidades.values())}
    victorias = Counter()
    rondas = 0

    for n in range(args.matches):
        try:
            ganador, r = jugar_match(personalidades, args.al_mejor_de, stats)
        except JugadaIlegal as e:
            print(f"\n❌ FALLO en el match {n + 1}: {e}")
            return 1
        victorias[ganador] += 1
        rondas += r
        if (n + 1) % 50 == 0:
            print(f"  … {n + 1} matches, {rondas} manos, sin jugadas ilegales")

    print(f"\n✅ {args.matches} matches completos, {rondas} manos, 0 jugadas ilegales.")
    print(f"   Matches ganados: equipo A {victorias['A']} · equipo B {victorias['B']}")

    print("\nTasas de apuesta por personalidad (sobre decisiones de apuesta):")
    print(f"  {'personalidad':<14}{'decisiones':>11}{'envidar':>9}{'subir':>8}"
          f"{'ordago':>8}{'ver':>7}{'nover':>8}{'agresivas':>11}")
    for p, c in sorted(stats.items()):
        total = c['_decisiones'] or 1
        agresivas = (c['envidar'] + c['subir'] + c['ordago']) / total
        print(f"  {p:<14}{c['_decisiones']:>11}"
              f"{c['envidar'] / total:>9.1%}{c['subir'] / total:>8.1%}"
              f"{c['ordago'] / total:>8.1%}{c['ver'] / total:>7.1%}"
              f"{c['nover'] / total:>8.1%}{agresivas:>11.1%}")

    print("\nCanto del mus (el eje que mueve el preset 'musero'):")
    print(f"  {'personalidad':<14}{'cantos':>9}{'pide mus':>11}{'corta':>9}")
    for p, c in sorted(stats.items()):
        total = c['_mus'] or 1
        print(f"  {p:<14}{c['_mus']:>9}{c['mus'] / total:>11.1%}{c['no_mus'] / total:>9.1%}")
    return 0


if __name__ == '__main__':
    sys.exit(main())

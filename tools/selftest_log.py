#!/usr/bin/env python3
# tools/selftest_log.py — Prueba de ida y vuelta del log v2 (Fase 1.2).
#
# Juega matches al azar con AMBOS motores (2p y 2v2), los registra en v2 y los
# vuelve a meter por la re-jugada exigiendo que el flujo de eventos regenerado
# coincida evento a evento. Es el script "estilo CI" que pide el roadmap: se
# pasa antes de tocar cualquiera de los dos motores o el formato del log.
#
# Juega AL AZAR a propósito (entre las acciones legales, no entre todas): así
# recorre los rincones raros que un bot heurístico casi nunca visita — órdagos
# encadenados, dejes forzados, pedretes, barajas agotadas, punto en vez de juego.
#
#   python3 tools/selftest_log.py                 # 60 matches de cada modo
#   python3 tools/selftest_log.py --matches 300 --semilla 3

import argparse
import os
import random
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mus_mecanicas import PartidaMus                     # noqa: E402
from mus_mecanicas_4 import PartidaMus4                  # noqa: E402
from log_verify import verificar                         # noqa: E402

MAX_PASOS = 60000
APUESTAS = ('pasar', 'envidar', 'subir', 'ver', 'nover', 'ordago')


def _descarte_al_azar(n_cartas):
    """Al menos una carta: quien pide mus está obligado a tirar."""
    k = random.randint(1, n_cartas)
    return random.sample(range(n_cartas), k)


def jugar_4p(dir_log, al_mejor_de):
    motor = PartidaMus4()
    motor.al_mejor_de = al_mejor_de
    motor.activar_log(seats=[{'s': s, 'kind': 'bot', 'pers': 'aleatorio'} for s in range(4)],
                      rules={'al_mejor_de': al_mejor_de}, dir_logs=dir_log)
    motor.iniciar_ronda()

    for _ in range(MAX_PASOS):
        if motor.match_finalizado:
            return motor.log.ruta
        if motor.mensaje_transicion:
            motor.mensaje_transicion = None
            motor.preparar_subfase()
            continue
        if motor.fase == 'recuento':
            motor.calcular_recuento()
            if motor.match_finalizado:
                return motor.log.ruta
            if motor.puntos['A'] >= 40 or motor.puntos['B'] >= 40:
                motor.reiniciar_partida()
            else:
                motor.siguiente_ronda()
            motor.jugadores_listos = []
            continue

        actuó = False
        for seat in range(4):
            legales = [a for a in motor.acciones_legales(seat)
                       if a != 'listo_siguiente_ronda']
            if not legales:
                continue
            accion = random.choice(legales)
            if accion == 'repartir':
                motor.repartir_inicial()
            elif accion == 'pedrete':
                motor.procesar_pedrete(seat)
            elif accion in ('mus', 'no_mus'):
                motor.cantar_mus(seat, accion == 'mus')
            elif accion == 'descartar':
                motor.procesar_descarte(seat, _descarte_al_azar(len(motor.estado[seat]['cartas'])))
            else:
                motor.accion_apuesta(seat, accion, random.choice([1, 2, 5]))
            actuó = True
            break
        if not actuó:
            raise RuntimeError(f"4p bloqueado: fase={motor.fase} turno={motor.turno_de}")
    raise RuntimeError("4p no termina")


def jugar_2p(dir_log, al_mejor_de):
    motor = PartidaMus('S0', 'S1')
    motor.al_mejor_de = al_mejor_de
    motor.activar_log(rules={'al_mejor_de': al_mejor_de}, dir_logs=dir_log)
    motor.iniciar_ronda()

    for _ in range(MAX_PASOS):
        if motor.match_finalizado:
            return motor.log.ruta
        if motor.mensaje_transicion:
            motor.mensaje_transicion = None
            motor.preparar_subfase()
            continue
        if motor.fase == 'recuento':
            motor.calcular_recuento()
            if motor.match_finalizado:
                return motor.log.ruta
            # Igual que server.py: `reiniciar_partida` no toca recuento_calculado,
            # el que lo baja es quien avanza la ronda.
            if any(motor.estado[p]['puntos'] >= 40 for p in motor.asientos):
                motor.reiniciar_partida()
            else:
                motor.cambiar_roles()
                motor.iniciar_ronda()
            motor.jugadores_listos = []
            motor.recuento_calculado = False
            continue

        actuó = False
        for jugador in motor.asientos:
            legales = [a for a in motor.acciones_legales(jugador)
                       if a != 'listo_siguiente_ronda']
            if not legales:
                continue
            accion = random.choice(legales)
            if accion == 'repartir':
                motor.repartir_inicial()
            elif accion == 'pedrete':
                motor.procesar_pedrete(jugador)
            elif accion in ('mus', 'no_mus'):
                motor.cantar_mus(jugador, accion == 'mus')
            elif accion == 'descartar':
                motor.procesar_descarte(jugador, _descarte_al_azar(len(motor.estado[jugador]['cartas'])))
            else:
                motor.accion_apuesta(jugador, accion, random.choice([1, 2, 5]))
            actuó = True
            break
        if not actuó:
            raise RuntimeError(f"2p bloqueado: fase={motor.fase} turno={motor.turno_de}")
    raise RuntimeError("2p no termina")


def main():
    ap = argparse.ArgumentParser(description="Ida y vuelta del log v2 en ambos motores.")
    ap.add_argument('--matches', type=int, default=60, help='matches por modo')
    ap.add_argument('--al-mejor-de', type=int, default=1)
    ap.add_argument('--semilla', type=int, default=1)
    ap.add_argument('--conservar', action='store_true',
                    help='no borrar el directorio temporal (para inspeccionarlo)')
    args = ap.parse_args()

    random.seed(args.semilla)
    tmp = tempfile.mkdtemp(prefix='mus_selftest_')
    fallos = 0
    try:
        for modo, jugar in (('4p', jugar_4p), ('2p', jugar_2p)):
            print(f"▶ {modo}: {args.matches} matches al azar (al mejor de {args.al_mejor_de})…")
            for n in range(args.matches):
                ruta = jugar(os.path.join(tmp, modo), args.al_mejor_de)
                bien, problemas = verificar(ruta)
                if not bien:
                    fallos += 1
                    print(f"  ❌ match {n + 1} ({os.path.basename(ruta)}):")
                    for p in problemas:
                        print(f"      · {p}")
                    if fallos >= 3:
                        break
            print(f"  {'✅' if not fallos else '❌'} {modo} hecho")
            if fallos >= 3:
                break
    finally:
        if args.conservar:
            print(f"logs en {tmp}")
        else:
            shutil.rmtree(tmp, ignore_errors=True)

    print(f"\n{'✅ log v2 reproducible en ambos motores' if not fallos else f'❌ {fallos} matches no reproducibles'}")
    return 1 if fallos else 0


if __name__ == '__main__':
    sys.exit(main())

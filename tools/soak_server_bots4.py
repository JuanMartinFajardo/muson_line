#!/usr/bin/env python3
# tools/soak_server_bots4.py — Soak del CAMINO REAL del servidor 4p con bots.
#
# soak_bots4.py prueba el cerebro de los bots contra el motor. Esto prueba lo
# otro: los handlers de server_mus4 (crear sala con bots, difusión de estado,
# planificador de turnos de bot, cierre de sala) con un socketio de mentira.
#
#   python3 tools/soak_server_bots4.py --matches 25 --bots 3
#
# El "humano" del asiento 0 lo juega otro SmartBot4 llamando a procesar_accion_4
# como lo haría el cliente, así que se recorre exactamente el mismo código.

import argparse
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import server_mus4 as S                          # noqa: E402
from bot_ml_4 import SmartBot4                   # noqa: E402


class SocketioFalso:
    """Recoge las tareas de fondo en vez de lanzarlas: el test decide cuándo
    corren y cuáles (las de los bots sí, las de los temporizadores no: aquí no
    hay nadie ausente y dispararlas sería simular un AFK que no existe)."""

    def __init__(self):
        self.tareas = []
        self.emitidos = []

    def emit(self, evento, datos=None, room=None):
        self.emitidos.append(evento)

    def sleep(self, _s):
        return None

    def start_background_task(self, fn, *a, **kw):
        self.tareas.append((fn, a, kw))

    def on(self, _evento):
        return lambda f: f

    # --- utilidades del test ---
    def tomar_tareas_de_bot(self):
        """Saca de la cola las tareas de _programar_bots (y tira el resto).

        Se separa de ejecutarlas a propósito: entre "se programó la jugada del
        bot" y "el bot juega" hay un retardo real, y el test necesita poder
        colar difusiones de estado en medio, que es donde apareció el fallo."""
        pendientes, self.tareas = self.tareas, []
        return [(fn, a, kw) for fn, a, kw in pendientes
                if '_programar_bots' in getattr(fn, '__qualname__', '')]


class PeticionFalsa:
    def __init__(self, sid):
        self.sid = sid


def preparar(codigo_sid='HUM'):
    sio = SocketioFalso()
    # Miles de partidas de prueba NO deben acabar en logs/v2: ese corpus es el de
    # partidas de verdad, la materia prima del entrenamiento (Fase 1.1). Se apaga
    # ANTES de crear la mesa: `activar_log` escribe la cabecera al abrir.
    S.LOG_V2 = False
    S.socketio = sio
    S.jugadores = {}
    S.salas = {}
    S.salas4 = {}
    S.session = {}
    S.emit = lambda *a, **kw: None
    S.join_room = lambda *a, **kw: None
    S.leave_room = lambda *a, **kw: None
    S.request = PeticionFalsa(codigo_sid)
    return sio


def jugar_match(sio, n_bots, al_mejor_de, personalidad):
    S.handle_crear_sala_4({
        'nombre': 'Humano',
        'al_mejor_de': al_mejor_de,
        'publico': False,
        'asiento': 0,
        'bots': list(range(1, n_bots + 1)),
        'personalidad': personalidad,
    })
    codigo = next(iter(S.salas4))
    room = S.salas4[codigo]

    assert len(room['bots']) == n_bots, f"esperaba {n_bots} bots, hay {len(room['bots'])}"

    # Los asientos que no son bot los ocupamos a mano (jugadores "humanos" que
    # se habrían unido con unirse_sala_4) para poder arrancar la partida.
    for seat in range(1, 4):
        if room['asientos'][seat] is None:
            room['asientos'][seat] = f'HUM{seat}'
            room['nombres'][seat] = f'Humano {seat}'
            room['usernames'][seat] = None
    if room['estado'] != 'jugando':
        S._iniciar_partida(codigo)

    humanos = {s: SmartBot4(f'HUM{s}', s, 'equilibrado')
               for s in range(4) if s not in room['bots']}

    motor = room['motor']
    pasos = 0
    while not motor.match_finalizado:
        pasos += 1
        if pasos > 60000:
            raise AssertionError("la partida no avanza (posible bloqueo)")

        # 1. Jugada de bot pendiente (programada con el estado anterior)…
        pendientes = sio.tomar_tareas_de_bot()

        # …y, ANTES de que le toque, un humano impaciente que vuelve a pulsar
        # «siguiente ronda»: difunde estado sin que la partida avance. El bot
        # tiene que jugar igualmente (con el candado por `turno_token` la tarea
        # caducaba, los bots no jugaban nunca y la mesa se clavaba en el recuento).
        if motor.fase == 'recuento' and 0 in motor.jugadores_listos:
            S.procesar_accion_4(0, codigo, {'accion': 'listo_siguiente_ronda'})
            sio.tomar_tareas_de_bot()   # la difusión repetida no encola otra jugada

        if pendientes:
            for fn, a, kw in pendientes:
                fn(*a, **kw)
            continue

        # 2. El servidor auto-avanza las transiciones (aquí, sin esperar).
        if motor.mensaje_transicion:
            S.procesar_accion_4(0, codigo, {'accion': 'continuar_transicion'})
            continue

        # 3. Turno de las personas: mismo camino que un click del cliente.
        actuó = False
        for seat, cerebro in humanos.items():
            decision = cerebro.obtener_accion(motor.vista(seat))
            if not decision:
                continue
            accion, cantidad, extra = decision
            datos = {'accion': accion, 'cantidad': cantidad}
            if accion == 'descartar':
                datos['indices'] = extra.get('indices', [])
            S.procesar_accion_4(seat, codigo, datos)
            actuó = True
            break
        if actuó:
            continue

        if motor.fase == 'recuento' and not motor.match_finalizado:
            raise AssertionError(f"recuento bloqueado: listos={motor.jugadores_listos}")
        raise AssertionError(
            f"nadie puede jugar: fase={motor.fase} turno={motor.turno_de} "
            f"legales={ {s: motor.acciones_legales(s) for s in range(4)} }")

    return codigo, motor


def main():
    ap = argparse.ArgumentParser(description="Soak del servidor 4p con bots.")
    ap.add_argument('--matches', type=int, default=25)
    ap.add_argument('--bots', type=int, default=3, choices=[1, 2, 3])
    ap.add_argument('--al-mejor-de', type=int, default=1)
    ap.add_argument('--personalidad', default='equilibrado')
    ap.add_argument('--semilla', type=int, default=3)
    args = ap.parse_args()

    random.seed(args.semilla)
    print(f"{args.matches} matches con {args.bots} bot(s) por mesa, "
          f"al mejor de {args.al_mejor_de}…")

    for n in range(args.matches):
        sio = preparar()
        codigo, motor = jugar_match(sio, args.bots, args.al_mejor_de, args.personalidad)

        # Al terminar, el humano se va: la sala tiene que desaparecer entera.
        S.request = PeticionFalsa('HUM')
        S.handle_abandonar_sala_4()
        for seat in range(1, 4):
            if S.salas4.get(codigo):
                S.request = PeticionFalsa(f'HUM{seat}')
                S.handle_abandonar_sala_4()
        if codigo in S.salas4:
            print(f"❌ La sala {codigo} sigue viva sin personas dentro: "
                  f"{S.salas4[codigo]['asientos']}")
            return 1
        if (n + 1) % 10 == 0:
            print(f"  … {n + 1} matches completos por el camino del servidor")

    print(f"\n✅ {args.matches} matches jugados con el servidor real: sin bloqueos, "
          f"sin jugadas ilegales y las salas se cierran al irse las personas.")
    return 0


if __name__ == '__main__':
    sys.exit(main())

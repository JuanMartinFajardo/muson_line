#!/usr/bin/env python3
# tools/log_verify.py — Integridad de los logs v2. Fase 1.2 del roadmap de IA.
#
# Criterio de aceptación de la Fase 1: "una partida 4p completa registrada en v2
# se re-juega byte a byte a través de log_verify". Aquí está la comprobación en
# su sentido fuerte: se mete el log por el motor determinista (mus_replay.py) y
# se compara el flujo de eventos REGENERADO con el del fichero, evento a evento.
#
# Si coinciden, dos cosas quedan probadas a la vez:
#   1. el log contiene toda la información necesaria para reconstruir la partida
#      (o sea: podremos extraer features que aún no hemos inventado), y
#   2. el motor de hoy sigue resolviendo el mus igual que el del día del
#      registro — es un test de regresión gratis sobre tráfico real.
#
# Fuera de la comparación quedan `ms`/`ts` (el ritmo humano no es reproducible
# por definición) y los eventos `pi`/`seat`, que los pone el servidor y no el
# motor. Además se contrastan por separado las cuentas del fichero: el marcador
# de cada `eor` y el `n_events` del `eom`.
#
#   python3 tools/log_verify.py                    # todo logs/v2
#   python3 tools/log_verify.py --dir /tmp/v2 -v
#   python3 tools/log_verify.py logs/v2/AB12CD.jsonl

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mus_log import leer, listar, DIR_LOGS_V2                    # noqa: E402
from mus_replay import Replay, normalizar, diferencias           # noqa: E402


def verificar(ruta, verboso=False):
    """(ok, [problemas]) para un fichero v2."""
    problemas = []
    eventos = leer(ruta)
    if not eventos:
        return False, ["fichero vacío"]

    # --- 1. Coherencia interna del fichero ---
    ultimo = eventos[-1]
    if ultimo.get('t') != 'eom':
        problemas.append("no termina en `eom`: match sin acabar o fichero truncado")
    elif ultimo.get('n_events') != len(eventos):
        problemas.append(f"n_events={ultimo.get('n_events')} pero hay {len(eventos)} líneas")

    # --- 2. Re-jugada ---
    try:
        r = Replay(eventos)
        motor = r.ejecutar()
    except Exception as e:
        return False, problemas + [f"la re-jugada falló: {type(e).__name__}: {e}"]

    orig = normalizar(eventos)
    nuevo = normalizar(r.log.eventos)
    if len(orig) != len(nuevo):
        problemas.append(f"la re-jugada produce {len(nuevo)} eventos y el log tiene {len(orig)}")
    for i, a, b in diferencias(orig, nuevo, maximo=3 if not verboso else 20):
        problemas.append(f"evento #{i} difiere:\n      log: {a}\n      motor: {b}")

    # --- 3. Marcador (redundante con lo anterior, pero da un mensaje útil) ---
    for ev in eventos:
        if ev.get('t') == 'eor' and not isinstance(ev.get('scores'), list):
            problemas.append(f"ronda {ev.get('r')}: `scores` mal formado")

    if verboso and not problemas:
        modo = eventos[0].get('mode')
        rondas = sum(1 for e in eventos if e.get('t') == 'eor')
        print(f"    {os.path.basename(ruta)}: {modo}, {rondas} manos, "
              f"{r.n_decisiones} decisiones, {len(eventos)} eventos · "
              f"marcador final {getattr(motor, 'puntos', None) or 'ok'}")

    return not problemas, problemas


def main():
    ap = argparse.ArgumentParser(description="Verifica logs v2 re-jugándolos (Fase 1.2).")
    ap.add_argument('ficheros', nargs='*', help='ficheros concretos (por defecto: todo --dir)')
    ap.add_argument('--dir', default=DIR_LOGS_V2, help=f'directorio de logs v2 (por defecto {DIR_LOGS_V2})')
    ap.add_argument('-v', '--verboso', action='store_true')
    args = ap.parse_args()

    rutas = args.ficheros or listar(args.dir)
    if not rutas:
        print(f"No hay logs v2 en {args.dir}.")
        return 0

    ok = fallos = 0
    for ruta in rutas:
        bien, problemas = verificar(ruta, args.verboso)
        if bien:
            ok += 1
        else:
            fallos += 1
            print(f"❌ {ruta}")
            for p in problemas:
                print(f"    · {p}")

    print(f"\n{'✅' if not fallos else '❌'} {ok}/{len(rutas)} logs íntegros"
          + (f" · {fallos} con problemas" if fallos else ""))
    return 1 if fallos else 0


if __name__ == '__main__':
    sys.exit(main())

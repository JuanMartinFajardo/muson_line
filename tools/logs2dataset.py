#!/usr/bin/env python3
# tools/logs2dataset.py — Logs v2 → dataset de decisiones. Fase 1.2.
#
# Re-juega cada log con mus_replay y saca UNA FILA POR DECISIÓN con las features
# del encoder DE HOY (encoder.py). Esa es la diferencia de fondo con el formato
# v1: allí las features quedaban congeladas al escribir, así que mejorar el
# encoder no servía de nada para los datos viejos. Aquí se regenera el dataset
# entero cada vez que cambia el encoder, sobre todo el corpus histórico.
#
# Columnas:
#   identidad   match, mode, ronda, seat, kind (human/bot), code, pers
#   decisión    fase, lance, accion, accion_idx, cantidad, ms
#   contexto    cartas (valores crudos), puntos_equipo, puntos_rival
#   etiquetas   delta_ronda (puntos que ganó su equipo en esa mano),
#               gano_partida, gano_match
#   features    f000..fNNN — el vector del encoder (solo 4p; en 2p el motor no
#               ofrece `vista`, así que esas columnas se dejan fuera)
#
#   python3 tools/logs2dataset.py -o learn/datasets/decisiones_4p.parquet
#   python3 tools/logs2dataset.py --dir /tmp/v2 --modo 4p --solo-humanos

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import encoder                                              # noqa: E402
from mus_log import leer, listar, DIR_LOGS_V2               # noqa: E402
from mus_replay import Replay                               # noqa: E402

NOMBRES_FEATURE = [f"f{i:03d}" for i in range(encoder.DIM)]


def filas_de_log(ruta, con_features=True):
    """Filas de decisión de un fichero v2 (ya con las etiquetas de resultado)."""
    eventos = leer(ruta)
    if not eventos or eventos[0].get('t') != 'hdr':
        return []
    hdr = eventos[0]
    modo = hdr.get('mode', '2p')
    ident = {}
    for s in hdr.get('seats') or []:
        ident[s.get('s')] = {'kind': s.get('kind'), 'code': s.get('code'),
                             'pers': s.get('pers'), 'ckpt': s.get('ckpt')}
    # Los cambios de ocupante a media partida se aplican en orden: la fila queda
    # atribuida a quien de verdad decidía en ese momento.
    cambios = [(i, ev) for i, ev in enumerate(eventos) if ev.get('t') == 'seat']

    filas = []

    def on_decision(motor, seat, ev, vista):
        fila = {
            'match': hdr.get('match'),
            'mode': modo,
            'ronda': getattr(motor, 'ronda_n', 0),
            'seat': seat,
            'fase': motor.fase,
            'lance': ev.get('lance'),
            'accion': ev.get('a'),
            'accion_idx': encoder.ACCION_A_IDX.get(ev.get('a'), -1),
            'cantidad': ev.get('n', 0),
            'ms': ev.get('ms'),
        }
        fila.update(ident.get(seat) or {'kind': None, 'code': None,
                                        'pers': None, 'ckpt': None})
        if modo == '4p':
            eq = motor.equipo_de[seat]
            rival = 'B' if eq == 'A' else 'A'
            fila['equipo'] = eq
            fila['puntos_equipo'] = motor.puntos[eq]
            fila['puntos_rival'] = motor.puntos[rival]
            fila['cartas'] = [c['valor'] for c in motor.estado[seat]['cartas']]
            if con_features and vista is not None:
                for nombre, valor in zip(NOMBRES_FEATURE, encoder.codificar(vista)):
                    fila[nombre] = float(valor)
        else:
            jugador = motor.asientos[seat]
            rival = motor.asientos[1 - seat]
            fila['equipo'] = str(seat)
            fila['puntos_equipo'] = motor.estado[jugador]['puntos']
            fila['puntos_rival'] = motor.estado[rival]['puntos']
            fila['cartas'] = [c['valor'] for c in motor.estado[jugador]['cartas']]
        filas.append(fila)

    try:
        Replay(eventos, on_decision=on_decision).ejecutar()
    except Exception as e:
        print(f"⚠️ {os.path.basename(ruta)}: re-jugada fallida ({e}); se omite")
        return []

    _etiquetar(filas, eventos, modo)
    return filas


def _etiquetar(filas, eventos, modo):
    """Añade el resultado de la mano y del match a cada decisión.

    Es lo que convierte el log en supervisión: "esta decisión, en este estado,
    acabó dando N puntos a su equipo"."""
    # Delta de puntos por ronda, a partir de los marcadores de los `eor`.
    deltas = {}          # ronda -> (delta_equipo0, delta_equipo1)
    previos = [0, 0]
    for ev in eventos:
        if ev.get('t') != 'eor':
            continue
        scores = ev.get('scores') or [0, 0]
        deltas[ev.get('r')] = (scores[0] - previos[0], scores[1] - previos[1])
        previos = list(scores)
        if previos[0] >= 40 or previos[1] >= 40:
            previos = [0, 0]

    eom = eventos[-1] if eventos and eventos[-1].get('t') == 'eom' else {}
    ganador = eom.get('winner')

    for fila in filas:
        d = deltas.get(fila['ronda'])
        if modo == '4p':
            idx = 0 if fila['equipo'] == 'A' else 1
        else:
            idx = fila['seat']
        fila['delta_ronda'] = d[idx] if d else None
        fila['delta_rival'] = d[1 - idx] if d else None
        if ganador is None:
            fila['gano_match'] = None
        elif modo == '4p':
            fila['gano_match'] = (ganador == fila['equipo'])
        else:
            fila['gano_match'] = (ganador == fila['seat'])


def main():
    ap = argparse.ArgumentParser(description="Logs v2 → dataset de decisiones (Fase 1.2).")
    ap.add_argument('--dir', default=DIR_LOGS_V2)
    ap.add_argument('-o', '--salida', default='learn/datasets/decisiones_v2.parquet')
    ap.add_argument('--modo', choices=['2p', '4p', 'todos'], default='todos')
    ap.add_argument('--solo-humanos', action='store_true',
                    help='solo decisiones de personas (corpus de la Fase 4.1)')
    ap.add_argument('--sin-features', action='store_true',
                    help='omite las columnas del encoder (dataset ligero)')
    args = ap.parse_args()

    rutas = listar(args.dir)
    if not rutas:
        print(f"No hay logs v2 en {args.dir}.")
        return 0

    todas = []
    for ruta in rutas:
        filas = filas_de_log(ruta, con_features=not args.sin_features)
        if args.modo != 'todos':
            filas = [f for f in filas if f['mode'] == args.modo]
        if args.solo_humanos:
            filas = [f for f in filas if f.get('kind') == 'human']
        todas.extend(filas)

    if not todas:
        print("Ninguna decisión cumple el filtro.")
        return 0

    try:
        import pandas as pd
    except ImportError:
        print("❌ Hace falta pandas: pip install pandas pyarrow")
        return 1

    df = pd.DataFrame(todas)
    # `cartas` es una lista: en parquet va bien, en csv se serializa como texto.
    os.makedirs(os.path.dirname(os.path.abspath(args.salida)) or '.', exist_ok=True)

    destino = args.salida
    if destino.endswith('.parquet'):
        try:
            df.to_parquet(destino, index=False)
        except Exception as e:
            destino = destino.rsplit('.', 1)[0] + '.csv'
            print(f"⚠️ Parquet no disponible ({e}); se escribe CSV. "
                  f"Para parquet: pip install pyarrow")
            df.to_csv(destino, index=False)
    else:
        df.to_csv(destino, index=False)

    humanas = int((df['kind'] == 'human').sum()) if 'kind' in df else 0
    print(f"✅ {len(df)} decisiones de {len(rutas)} matches → {destino}")
    print(f"   {len(df.columns)} columnas · {humanas} decisiones humanas "
          f"(la Fase 4.1 pide ≥10.000) · encoder de {encoder.DIM} dims")
    if 'lance' in df:
        conteo = df['lance'].value_counts(dropna=False).to_dict()
        print(f"   por lance: {conteo}")
    return 0


if __name__ == '__main__':
    sys.exit(main())

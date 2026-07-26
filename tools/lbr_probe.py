#!/usr/bin/env python3
# tools/lbr_probe.py — Local Best Response para el mus de 2 jugadores. Fase 1.6.
#
# LBR (Lisý & Bowling 2017) es el segundo peldaño de la escalera de §7: da una
# COTA INFERIOR de explotabilidad, barata y estándar en póker. La idea:
#
#   * la sonda mantiene una creencia sobre la mano del rival — al principio todas
#     las manos posibles, y se va podando con lo que el rival hace público
#     (declaró pares, declaró juego, cuántas cartas se descartó);
#   * en cada decisión evalúa un puñado de acciones (pasar / ver / envidar /
#     órdago) suponiendo que después de ESA acción la mano se resuelve sin más
#     apuestas, y elige la de mayor valor esperado sobre la creencia;
#   * lo que consigue así es, por construcción, ≤ la explotabilidad real.
#
# O sea: si LBR le saca N puntos por mano a un bot, ese bot es explotable en al
# menos N. Al revés no vale — LBR bajo NO demuestra que el bot sea bueno (por eso
# la escalera tiene tres peldaños más). Se informa en puntos por mano, la misma
# unidad que la arena.
#
# La versión de 4 jugadores llega en la Fase 3 (necesita creencias sobre tres
# manos y el reparto por equipos); esta ya sirve para graduar la línea de 2p y
# para validar la propia herramienta contra el ancla tabular de la Fase 1.5.
#
#   python3 tools/lbr_probe.py --manos 2000                    # contra heurístico
#   python3 tools/lbr_probe.py --rival aleatorio --manos 2000
#   python3 tools/lbr_probe.py --rival cfr --checkpoint learn/cfr/xxx.pth

import argparse
import itertools
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mus_mecanicas import (PartidaMus, crear_baraja, tiene_pares, tiene_juego,   # noqa: E402
                           get_pares_info, get_suma_juego, comparar_cartas,
                           comp_pares_info, comp_juego, comp_punto)

LANCES = ('Grande', 'Chica', 'Pares', 'Juego')
# Acciones que considera la sonda. Es un conjunto RESTRINGIDO a propósito (es lo
# que hace que LBR sea barato); por eso da una cota inferior y no la exacta.
ACCIONES_LBR = ('pasar', 'ver', 'nover', 'envidar', 'ordago')


# ==========================================================================
# Creencia sobre la mano del rival
# ==========================================================================
def manos_posibles(cartas_propias, muestra=400, rng=random):
    """Muestra de manos de 4 cartas compatibles con lo que la sonda NO ve.

    Enumerar las C(36,4)=58.905 combinaciones restantes por decisión sería
    absurdamente caro para lo que aporta; se muestrea. Con 400 manos el error
    típico del valor esperado ya está por debajo de la resolución que nos
    importa (centésimas de punto por mano)."""
    mazo = crear_baraja()
    quedan = []
    usadas = list(cartas_propias)
    for c in mazo:
        for u in usadas:
            if c['valor'] == u['valor'] and c['palo'] == u['palo']:
                usadas.remove(u)
                break
        else:
            quedan.append(c)
    total = math.comb(len(quedan), 4)
    if total <= muestra:
        return [list(m) for m in itertools.combinations(quedan, 4)]
    return [rng.sample(quedan, 4) for _ in range(muestra)]


def filtrar_creencia(candidatas, pistas):
    """Poda la creencia con la información PÚBLICA vista hasta ahora.

    Esto es lo único que hace de LBR algo más que un bot codicioso: las
    declaraciones de pares y juego del mus son señales fuertísimas y gratis."""
    salida = []
    for mano in candidatas:
        if pistas.get('pares') is not None and tiene_pares(mano) != pistas['pares']:
            continue
        if pistas.get('juego') is not None and tiene_juego(mano) != pistas['juego']:
            continue
        salida.append(mano)
    return salida or candidatas          # nunca dejar la creencia vacía


# ==========================================================================
# Valor de un lance suponiendo que se resuelve ya
# ==========================================================================
def _gana_lance(lance, mis_cartas, sus_cartas, soy_mano):
    """True si mis cartas ganan el lance. Ojo al orden: los comparadores del
    motor devuelven 'mano'/'postre' y el empate lo gana la mano."""
    a, b = (mis_cartas, sus_cartas) if soy_mano else (sus_cartas, mis_cartas)
    if lance == 'Grande':
        gana_primero = comparar_cartas(a, b, True) == 'mano'
    elif lance == 'Chica':
        gana_primero = comparar_cartas(a, b, False) == 'mano'
    elif lance == 'Pares':
        gana_primero = comp_pares_info(get_pares_info(a), get_pares_info(b)) == 'mano'
    elif lance == 'Punto':
        gana_primero = comp_punto(a, b) == 'mano'
    else:
        gana_primero = comp_juego(a, b) == 'mano'
    return gana_primero if soy_mano else not gana_primero


def prob_ganar(lance, mis_cartas, creencia, soy_mano):
    if not creencia:
        return 0.5
    ganadas = sum(1 for m in creencia if _gana_lance(lance, mis_cartas, m, soy_mano))
    return ganadas / len(creencia)


def valor_accion(accion, motor, jugador, creencia, lance, soy_mano):
    """Valor esperado (en puntos de este lance) de una acción, suponiendo que
    tras ella el lance se resuelve sin más apuestas — la aproximación "local"
    de LBR."""
    p = prob_ganar(lance, motor.estado[jugador]['cartas'], creencia, soy_mano)
    bote = motor.botes.get(lance, 0)
    vista = motor.apuesta_vista
    subida = motor.subida_pendiente
    subida_num = 40 if subida == 'ÓRDAGO' else (subida or 0)
    deje = vista if vista > 0 else 1
    bonus = _bonus(lance, motor.estado[jugador]['cartas'])

    if accion == 'pasar':
        # El lance sigue vivo; el valor es el del bote actual disputado.
        return p * (bote + bonus + 1) - (1 - p) * (bote + 1)
    if accion == 'nover':
        return -deje
    if accion == 'ver':
        total = bote + vista + subida_num
        return p * (total + bonus) - (1 - p) * total
    if accion == 'envidar':
        # El rival paga con probabilidad ~p_pago; si no, nos llevamos el deje.
        envite = 2
        total = bote + vista + envite
        p_pago = 0.5
        return (1 - p_pago) * (bote + 1) + p_pago * (p * (total + bonus) - (1 - p) * total)
    if accion == 'ordago':
        p_pago = 0.35
        return (1 - p_pago) * (bote + deje) + p_pago * (p * 40 - (1 - p) * 40)
    return 0.0


def _bonus(lance, cartas):
    if lance == 'Pares' and tiene_pares(cartas):
        return get_pares_info(cartas)['premio']
    if lance == 'Juego' and tiene_juego(cartas):
        return 3 if get_suma_juego(cartas) == 31 else 2
    if lance == 'Punto':
        return 1
    return 0


# ==========================================================================
# La sonda
# ==========================================================================
class SondaLBR:
    def __init__(self, muestra=300, rng=None):
        self.muestra = muestra
        self.rng = rng or random
        self.pistas = {}
        self._creencia = None
        self._ronda = None

    def nueva_ronda(self, motor, jugador):
        self.pistas = {}
        self._creencia = manos_posibles(motor.estado[jugador]['cartas'],
                                        self.muestra, self.rng)
        self._ronda = motor.ronda_n

    def observar_declaracion(self, lance, tiene):
        self.pistas['pares' if lance == 'Pares' else 'juego'] = tiene

    def elegir(self, motor, jugador):
        if self._ronda != motor.ronda_n or self._creencia is None:
            self.nueva_ronda(motor, jugador)
        legales = [a for a in motor.acciones_legales(jugador) if a in ACCIONES_LBR]
        if not legales:
            return None
        lance = motor.fases_apuesta[motor.indice_fase]
        if lance == 'Juego' and getattr(motor, 'juego_es_punto', False):
            lance = 'Punto'
        soy_mano = (jugador == motor.id_mano)
        # La creencia se recalcula sobre las cartas de AHORA (tras el descarte).
        creencia = filtrar_creencia(
            manos_posibles(motor.estado[jugador]['cartas'], self.muestra, self.rng),
            self.pistas)
        mejor, mejor_v = legales[0], -1e9
        for a in legales:
            v = valor_accion(a, motor, jugador, creencia, lance, soy_mano)
            if v > mejor_v:
                mejor, mejor_v = a, v
        return mejor


# ==========================================================================
# Rivales a sondear
# ==========================================================================
def rival_aleatorio(motor, jugador, rng):
    legales = [a for a in motor.acciones_legales(jugador)
               if a in ('pasar', 'envidar', 'ver', 'nover', 'subir', 'ordago')]
    return rng.choice(legales) if legales else None


# Tablas de probabilidad por mano del propio proyecto. Son EXACTAMENTE lo que
# necesita un rival de referencia de 2 jugadores: probabilities[clave] =
# [G,C,P,J siendo mano, G,C,P,J siendo postre] contra una mano rival cualquiera.
_IDX_LANCE = {'Grande': 0, 'Chica': 1, 'Pares': 2, 'Juego': 3, 'Punto': 3}


def _prob_tabla(motor, jugador, lance):
    from bot_ml_4 import cargar_tablas
    from mus_mecanicas import get_valores_mus
    tablas = cargar_tablas()
    cartas = motor.estado[jugador]['cartas']
    if len(cartas) != 4 or lance not in _IDX_LANCE:
        return 0.5
    probs = tablas['probabilities'].get(str(sorted(get_valores_mus(cartas), reverse=True)))
    if not probs or len(probs) < 8:
        return 0.5
    desplazamiento = 0 if jugador == motor.id_mano else 4
    return probs[_IDX_LANCE[lance] + desplazamiento]


def rival_heuristico(motor, jugador, rng):
    """Referencia de 2 jugadores calibrada con las tablas de probabilidad.

    Es el rival contra el que la cota tiene que salir CLARAMENTE menor que
    contra el aleatorio; si no, lo que está mal es la sonda, no el bot. Un
    umbral inventado a ojo no sirve de referencia: un bot demasiado pasivo se
    deja explotar más que el azar y el número deja de decir nada."""
    legales = [a for a in motor.acciones_legales(jugador)
               if a in ('pasar', 'envidar', 'ver', 'nover', 'subir', 'ordago')]
    if not legales:
        return None
    lance = motor.fases_apuesta[motor.indice_fase]
    if lance == 'Juego' and getattr(motor, 'juego_es_punto', False):
        lance = 'Punto'
    p = _prob_tabla(motor, jugador, lance)

    if 'ver' in legales:
        vista = motor.apuesta_vista
        subida = 40 if motor.subida_pendiente == 'ÓRDAGO' else (motor.subida_pendiente or 0)
        bote = motor.botes.get(lance, 0)
        pot = bote + vista + subida
        deje = vista if vista > 0 else 1
        # Pot-odds: pagar sale a cuenta si p·pot − (1−p)·pot ≥ −deje.
        umbral = (pot - deje) / (2.0 * pot) if pot > 0 else 0.5
        if 'subir' in legales and p >= 0.80:
            return 'subir'
        if p >= umbral or 'nover' not in legales:
            return 'ver'
        return 'nover'

    if 'envidar' in legales and p >= 0.62:
        return 'envidar'
    return 'pasar' if 'pasar' in legales else legales[0]


RIVALES = {'aleatorio': rival_aleatorio, 'heuristico': rival_heuristico}


# ==========================================================================
# Bucle de medición
# ==========================================================================
def medir(rival, manos, semilla, muestra):
    rng = random.Random(semilla)
    politica_rival = RIVALES[rival]
    sonda = SondaLBR(muestra=muestra, rng=rng)

    deltas = []          # puntos que LBR le saca al rival, por mano
    hechas = 0
    while hechas < manos:
        motor = PartidaMus('LBR', 'RIVAL')
        motor.rng = random.Random(rng.randrange(1 << 30))
        motor.al_mejor_de = 1
        # La sonda se sienta la mitad de las manos de mano y la mitad de postre.
        if hechas % 2 == 0:
            motor.id_mano, motor.id_postre = 'LBR', 'RIVAL'
        else:
            motor.id_mano, motor.id_postre = 'RIVAL', 'LBR'
        motor.iniciar_ronda()

        antes = {'LBR': motor.estado['LBR']['puntos'],
                 'RIVAL': motor.estado['RIVAL']['puntos']}
        pasos = 0
        declarado = set()
        while motor.fase != 'recuento' and pasos < 400:
            pasos += 1
            if motor.mensaje_transicion:
                motor.mensaje_transicion = None
                motor.preparar_subfase()
                continue
            if motor.fase == 'espera_reparto':
                motor.repartir_inicial()
                sonda.nueva_ronda(motor, 'LBR')
                continue
            if motor.fase == 'mus':
                # El mus no es el objeto de la sonda: se corta siempre para medir
                # solo el juego de apuestas (que es lo que el bot ha aprendido).
                motor.cantar_mus(motor.turno_de, False)
                continue
            if motor.fase == 'descarte':
                for j in ('LBR', 'RIVAL'):
                    if not motor.estado[j]['descartes_listos']:
                        motor.procesar_descarte(j, [0])
                continue
            if motor.fase != 'apuestas':
                break

            lance = motor.fases_apuesta[motor.indice_fase]
            if lance in ('Pares', 'Juego') and lance not in declarado:
                declarado.add(lance)
                pred = tiene_pares if lance == 'Pares' else tiene_juego
                sonda.observar_declaracion(lance, pred(motor.estado['RIVAL']['cartas']))

            turno = motor.turno_de
            if turno == 'LBR':
                accion = sonda.elegir(motor, 'LBR')
            else:
                accion = politica_rival(motor, turno, rng)
            if accion is None:
                break
            motor.accion_apuesta(turno, accion, 2 if accion in ('envidar', 'subir') else 0)

        if motor.fase == 'recuento':
            motor.calcular_recuento()
        d = ((motor.estado['LBR']['puntos'] - antes['LBR'])
             - (motor.estado['RIVAL']['puntos'] - antes['RIVAL']))
        deltas.append(d)
        hechas += 1

    n = len(deltas)
    media = sum(deltas) / n
    var = sum((x - media) ** 2 for x in deltas) / (n - 1) if n > 1 else 0.0
    return media, math.sqrt(var / n) if n else float('nan'), n


def main():
    ap = argparse.ArgumentParser(description="Cota inferior de explotabilidad por LBR (2p).")
    ap.add_argument('--rival', choices=sorted(RIVALES), default='heuristico')
    ap.add_argument('--manos', type=int, default=1000)
    ap.add_argument('--muestra', type=int, default=300,
                    help='manos rivales muestreadas por decisión')
    ap.add_argument('--semilla', type=int, default=17)
    args = ap.parse_args()

    print(f"LBR vs {args.rival} · {args.manos} manos · creencia de {args.muestra} manos")
    media, err, n = medir(args.rival, args.manos, args.semilla, args.muestra)
    print(f"\n  ganancia de la sonda: {media:+.3f} ± {err:.3f} puntos/mano ({n} manos)")
    print(f"  cota inferior de explotabilidad: {max(0.0, media):.3f} puntos/mano")
    if media <= 0:
        print("  La sonda NO encuentra explotación: la cota es vacua (0). Eso no dice\n"
              "  que el rival sea fuerte, solo que este juego local restringido no le\n"
              "  saca nada — para afirmar algo hacen falta los otros peldaños de §7\n"
              "  (mejor respuesta exacta 2p, RL-BR, arena de checkpoints).")
    else:
        print("  El rival es explotable AL MENOS en esa cantidad. La explotabilidad\n"
              "  real es mayor o igual: LBR mira un solo paso y un conjunto de\n"
              "  acciones reducido.")
    return 0


if __name__ == '__main__':
    sys.exit(main())

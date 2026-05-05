import json
import pandas as pd
from probability_calculator import (
    calcular_probabilidad_grande,
    calcular_probabilidad_chica,
    calcular_probabilidad_pares,
    calcular_probabilidad_juego,
    evaluar_pares,         
    calcular_valor_juego   
)

def crear_dataset_definitivo(archivo_entrada, archivo_salida):
    datos_procesados = []
    memoria_jugadores = {}
    
    with open(archivo_entrada, 'r', encoding='utf-8') as f:
        for linea in f:
            turno = json.loads(linea)
            jugador = turno['jugador']
            rival = turno['rival'] # Identificamos al rival
            ronda_actual = turno['ronda_n']
            fase = turno['fase']
            cartas_propias = turno['cartas_propias']
            
            # 1. INICIALIZAR MEMORIAS (Tanto la nuestra como la del rival)
            if jugador not in memoria_jugadores or memoria_jugadores[jugador]['ronda'] != ronda_actual:
                memoria_jugadores[jugador] = {'ronda': ronda_actual, 'mis_descartes': [], 'descartes_rival': 0, 'hubo_fase_pares': False}
                
            if rival not in memoria_jugadores or memoria_jugadores[rival]['ronda'] != ronda_actual:
                memoria_jugadores[rival] = {'ronda': ronda_actual, 'mis_descartes': [], 'descartes_rival': 0, 'hubo_fase_pares': False}
                
            memoria = memoria_jugadores[jugador]
            if fase == 'Pares': memoria['hubo_fase_pares'] = True
            
            # 2. NORMALIZACIÓN DE CARTAS Y EXTRACCIÓN DE VARIABLES
            cartas_norm = [12 if c == 3 else 1 if c == 2 else c for c in cartas_propias]
            cartas_ordenadas = sorted(cartas_norm, reverse=True)
            
            cat_pares, val_pares = evaluar_pares(cartas_norm)
            estado_juego = calcular_valor_juego(cartas_norm)
            
            # Deducción lógica del rival
            rival_pares_asumido = 0 
            if fase == 'Pares':
                rival_pares_asumido = 1
            elif fase == 'Juego':
                if memoria['hubo_fase_pares']: rival_pares_asumido = 1
                elif cat_pares > 0: rival_pares_asumido = -1
                else: rival_pares_asumido = 0

            # 3. CÁLCULO DE PROBABILIDADES
            try:
                prob_grande = calcular_probabilidad_grande(cartas_propias, memoria['mis_descartes'], turno['es_mano']).get('prob_ganar', 0.0)
                prob_chica = calcular_probabilidad_chica(cartas_propias, memoria['mis_descartes'], turno['es_mano']).get('prob_ganar', 0.0)
                prob_pares = calcular_probabilidad_pares(cartas_propias, (rival_pares_asumido == 1), turno['es_mano'], memoria['mis_descartes']).get('prob_ganar', 0.0)
                
                res_j = calcular_probabilidad_juego(cartas_propias, rival_pares_asumido, (fase == 'Juego'), turno['es_mano'], memoria['mis_descartes'])
                prob_juego = res_j.get('prob_ganar', 0.0) if isinstance(res_j, dict) else 0.0
                es_juego_real = 1 if isinstance(res_j, dict) and res_j.get('fase') == 'JUEGO' else 0
            except:
                prob_grande, prob_chica, prob_pares, prob_juego, es_juego_real = 0.0, 0.0, 0.0, 0.0, 0

            # 4. CONSTRUIR LA FILA DEL DATASET
            fila = {
                "match_id": turno['match_id'],
                "ronda_n": turno['ronda_n'],
                "jugador": jugador,
                "fase": fase,
                "es_mano": 1 if turno['es_mano'] else 0,
                "puntos_propios": turno['puntos_propios'],
                "puntos_rival": turno['puntos_rival'],
                
                "c1": cartas_ordenadas[0],
                "c2": cartas_ordenadas[1],
                "c3": cartas_ordenadas[2],
                "c4": cartas_ordenadas[3],
                
                "tengo_pares": 1 if cat_pares > 0 else 0,
                "tipo_pares": cat_pares,
                "tengo_juego": 1 if estado_juego['tiene_juego'] else 0,
                "suma_puntos": estado_juego['suma'],
                
                # ¡NUEVO! Cuántas cartas ha tirado el rival en esta ronda
                "descartes_rival": memoria['descartes_rival'],
                
                "rival_pares_deducido": rival_pares_asumido,
                "es_juego_real": es_juego_real,
                "prob_grande": prob_grande,
                "prob_chica": prob_chica,
                "prob_pares": prob_pares,
                "prob_juego": prob_juego,
                
                "accion_realizada": turno['accion'],
                "cantidad_apostada": turno['cantidad'],
                "gano_ronda": 1 if turno['gano_ronda'] else 0
            }
            datos_procesados.append(fila)

            # 5. ACTUALIZAR MEMORIAS AL FINAL DEL TURNO
            if turno['accion'] == 'descarte' and turno['detalles'] and 'cartas_tiradas' in turno['detalles']:
                cartas_tiradas = turno['detalles']['cartas_tiradas']
                
                # Yo recuerdo qué cartas exactas he tirado (para calcular mis probabilidades)
                memoria_jugadores[jugador]['mis_descartes'].extend(cartas_tiradas)
                
                # ¡NUEVO! Le apunto al rival CUÁNTAS cartas he tirado (para que lo sepa en su turno)
                memoria_jugadores[rival]['descartes_rival'] += len(cartas_tiradas)

    df = pd.DataFrame(datos_procesados)
    acciones_a_ignorar = ['repartir', 'continuar_transicion', 'listo_siguiente_ronda']
    df = df[~df['accion_realizada'].isin(acciones_a_ignorar)]
    
    df.to_csv(archivo_salida, index=False)
    print(f"✅ Dataset con descartes del rival creado en {archivo_salida}")
    return df

if __name__ == '__main__':
    crear_dataset_definitivo('1C9OGW_2.jsonl', 'dataset_mus_mascado.csv')
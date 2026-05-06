import random
import pandas as pd
import joblib
import os
from learn.probability_calculator import (
    calcular_probabilidad_grande,
    calcular_probabilidad_chica,
    calcular_probabilidad_pares,
    calcular_probabilidad_juego,
    evaluar_pares,
    calcular_valor_juego
)

class SmartBot:
    def __init__(self, sid="BOT_ML"):
        self.sid = sid
        self.memoria = {'mis_descartes': [], 'descartes_rival': 0, 'hubo_fase_pares': False, 'ronda': -1}
        
        # 1. Cargar Cerebro de Mus
        self.modelo_mus = None
        if os.path.exists('learn/models/modelo_decisor_mus.pkl'):
            self.modelo_mus = joblib.load('learn/models/modelo_decisor_mus.pkl')
            print("🧠 [BOT] Cerebro de Mus cargado.")
            
        # 2. Cargar Cerebro de Descartes
        self.modelo_descartes = None
        if os.path.exists('learn/models/modelo_descartes.pkl'):
            self.modelo_descartes = joblib.load('learn/models/modelo_descartes.pkl')
            print("🧠 [BOT] Cerebro de Descartes cargado.")

        # 3. Cargar Cerebro de Apuestas
        self.modelo_apuestas = None
        if os.path.exists('learn/models/modelo_apuestas.pkl'):
            self.modelo_apuestas = joblib.load('learn/models/modelo_apuestas.pkl')
            print("🧠 [BOT] Cerebro de Apuestas cargado.")
        else:
            print("⚠️ [BOT] No se encontró el modelo. Usando modo aleatorio.")

    def actualizar_memoria(self, partida):
        if self.memoria['ronda'] != partida.ronda_n:
            self.memoria = {'mis_descartes': [], 'descartes_rival': 0, 'hubo_fase_pares': False, 'ronda': partida.ronda_n}

    def predecir_mus(self, partida, cartas, estado):
        es_mano = 1 if partida.id_mano == self.sid else 0
        cartas_norm = [12 if c['valor'] == 3 else 1 if c['valor'] == 2 else c['valor'] for c in cartas]
        c_ord = sorted(cartas_norm, reverse=True)
        
        cat_pares, val_pares = evaluar_pares(cartas_norm)
        estado_juego = calcular_valor_juego(cartas_norm)
        
        try:
            prob_g = calcular_probabilidad_grande(cartas, self.memoria['mis_descartes'], es_mano==1).get('prob_ganar', 0.0)
            prob_c = calcular_probabilidad_chica(cartas, self.memoria['mis_descartes'], es_mano==1).get('prob_ganar', 0.0)
            prob_p = calcular_probabilidad_pares(cartas, False, es_mano==1, self.memoria['mis_descartes']).get('prob_ganar', 0.0)
            res_j = calcular_probabilidad_juego(cartas, 0, False, es_mano==1, self.memoria['mis_descartes'])
            prob_j = res_j.get('prob_ganar', 0.0) if isinstance(res_j, dict) else 0.0
        except:
            prob_g, prob_c, prob_p, prob_j = 0.0, 0.0, 0.0, 0.0

        if prob_g > 85.0 or prob_j > 85.0 or cat_pares >= 2:
            print("⚡ [IA MUS] Cartas brutales detectadas. Corto mus por salvaguarda.")
            return 'no_mus'

        features = [
            es_mano, c_ord[0], c_ord[1], c_ord[2], c_ord[3],
            1 if cat_pares > 0 else 0, cat_pares, 
            1 if estado_juego['tiene_juego'] else 0, estado_juego['suma'],
            self.memoria['descartes_rival'], prob_g, prob_c, prob_p, prob_j
        ]
        
        df_input = pd.DataFrame([features], columns=[
            'es_mano', 'c1', 'c2', 'c3', 'c4', 
            'tengo_pares', 'tipo_pares', 'tengo_juego', 'suma_puntos',
            'descartes_rival', 'prob_grande', 'prob_chica', 'prob_pares', 'prob_juego'
        ])
        
        if hasattr(self.modelo_mus, 'predict_proba'):
            probs = self.modelo_mus.predict_proba(df_input)[0]
            if len(probs) > 1 and probs[1] > 0.25: 
                return 'no_mus'
            return 'mus'
            
        prediccion = self.modelo_mus.predict(df_input)[0]
        return 'no_mus' if prediccion == 1 else 'mus'

    def predecir_descarte(self, partida, cartas):
        es_mano = 1 if partida.id_mano == self.sid else 0
        
        # 1. Asociamos el valor de cada carta con su índice original en la mano
        cartas_con_indices = [(i, 12 if c['valor'] == 3 else 1 if c['valor'] == 2 else c['valor']) for i, c in enumerate(cartas)]
        
        # 2. Ordenamos por valor (para que coincida con cómo entrenamos al modelo)
        cartas_ordenadas_con_indices = sorted(cartas_con_indices, key=lambda x: x[1], reverse=True)
        c_ord = [x[1] for x in cartas_ordenadas_con_indices]
        
        cat_pares, val_pares = evaluar_pares(c_ord)
        estado_juego = calcular_valor_juego(c_ord)
        
        try:
            prob_g = calcular_probabilidad_grande(cartas, self.memoria['mis_descartes'], es_mano==1).get('prob_ganar', 0.0)
            prob_c = calcular_probabilidad_chica(cartas, self.memoria['mis_descartes'], es_mano==1).get('prob_ganar', 0.0)
            prob_p = calcular_probabilidad_pares(cartas, False, es_mano==1, self.memoria['mis_descartes']).get('prob_ganar', 0.0)
            res_j = calcular_probabilidad_juego(cartas, 0, False, es_mano==1, self.memoria['mis_descartes'])
            prob_j = res_j.get('prob_ganar', 0.0) if isinstance(res_j, dict) else 0.0
        except:
            prob_g, prob_c, prob_p, prob_j = 0.0, 0.0, 0.0, 0.0

        # Features exactas del modelo de descarte (13 features)
        features = [
            es_mano, c_ord[0], c_ord[1], c_ord[2], c_ord[3],
            1 if cat_pares > 0 else 0, cat_pares, 
            1 if estado_juego['tiene_juego'] else 0, estado_juego['suma'],
            prob_g, prob_c, prob_p, prob_j
        ]
        
        df_input = pd.DataFrame([features], columns=[
            'es_mano', 'c1', 'c2', 'c3', 'c4', 'tengo_pares', 'tipo_pares', 
            'tengo_juego', 'suma_puntos', 'prob_grande', 'prob_chica', 'prob_pares', 'prob_juego'
        ])
        
        # Predecir máscara (el modelo devuelve un int, ej: 11 o 1111)
        mascara_raw = self.modelo_descartes.predict(df_input)[0]
        
        # Lo convertimos a texto y forzamos 4 dígitos (11 -> "0011")
        mascara_str = str(mascara_raw).zfill(4)
        
        # Mapear los '1' de la máscara a los índices originales
        indices_a_tirar = []
        for i, bit in enumerate(mascara_str):
            if bit == '1':
                indice_original = cartas_ordenadas_con_indices[i][0]
                indices_a_tirar.append(indice_original)
                
        return indices_a_tirar

    def predecir_apuesta(self, partida, cartas, subida_pendiente):
        es_mano = 1 if partida.id_mano == self.sid else 0
        cartas_norm = [12 if c['valor'] == 3 else 1 if c['valor'] == 2 else c['valor'] for c in cartas]
        c_ord = sorted(cartas_norm, reverse=True)
        
        cat_pares, val_pares = evaluar_pares(cartas_norm)
        estado_juego = calcular_valor_juego(cartas_norm)
        
        try:
            prob_g = calcular_probabilidad_grande(cartas, self.memoria['mis_descartes'], es_mano==1).get('prob_ganar', 0.0)
            prob_c = calcular_probabilidad_chica(cartas, self.memoria['mis_descartes'], es_mano==1).get('prob_ganar', 0.0)
            prob_p = calcular_probabilidad_pares(cartas, False, es_mano==1, self.memoria['mis_descartes']).get('prob_ganar', 0.0)
            res_j = calcular_probabilidad_juego(cartas, 0, False, es_mano==1, self.memoria['mis_descartes'])
            prob_j = res_j.get('prob_ganar', 0.0) if isinstance(res_j, dict) else 0.0
        except:
            prob_g, prob_c, prob_p, prob_j = 0.0, 0.0, 0.0, 0.0

        # Mapeamos la fase actual
        # En la lógica interna, el bot lee la subfase de: partida.fases_apuesta[partida.indice_fase]
        fase_actual = partida.fases_apuesta[partida.indice_fase]
        mapa_fases = {'Grande': 1, 'Chica': 2, 'Pares': 3, 'Juego': 4}
        fase_num = mapa_fases.get(fase_actual, 1)


        subida_ia = 40 if subida_pendiente == 'ÓRDAGO' else subida_pendiente

        features = [
            fase_num, es_mano, c_ord[0], c_ord[1], c_ord[2], c_ord[3],
            1 if cat_pares > 0 else 0, cat_pares, 
            1 if estado_juego['tiene_juego'] else 0, estado_juego['suma'],
            self.memoria['descartes_rival'], prob_g, prob_c, prob_p, prob_j,
            # Le pasamos el estado real de la mesa al modelo
            partida.botes.get('Grande', 0),
            partida.botes.get('Chica', 0),
            partida.botes.get('Pares', 0),
            subida_ia
        ]
        
        df_input = pd.DataFrame([features], columns=[
            'fase_num', 'es_mano', 'c1', 'c2', 'c3', 'c4', 
            'tengo_pares', 'tipo_pares', 'tengo_juego', 'suma_puntos',
            'descartes_rival', 'prob_grande', 'prob_chica', 'prob_pares', 'prob_juego',
            'bote_grande', 'bote_chica', 'bote_pares', 'subida_pendiente'
        ])
        
        # Obtenemos las probabilidades de todas las acciones posibles
        probs = self.modelo_apuestas.predict_proba(df_input)[0]
        clases = self.modelo_apuestas.classes_
        
        # Filtramos las acciones válidas según el contexto
        if subida_pendiente == 0:
            acciones_validas = ['pasar', 'envidar', 'ordago']
        else:
            acciones_validas = ['ver', 'nover', 'subir', 'ordago']
            
        # Nos quedamos con la acción válida que tenga mayor probabilidad
        mejor_accion = 'pasar' if subida_pendiente == 0 else 'nover' # Por defecto, somos cautos
        mejor_prob = -1
        
        for accion, prob in zip(clases, probs):
            if accion in acciones_validas and prob > mejor_prob:
                mejor_prob = prob
                mejor_accion = accion
                
        return mejor_accion

    def obtener_accion(self, partida):
        self.actualizar_memoria(partida)
        fase = partida.fase
        estado = partida.estado[self.sid]
        cartas = estado['cartas']

        if fase in ['mus', 'descarte'] and cartas:
            valores = sorted([c['valor'] for c in cartas])
            if valores == [4, 5, 6, 7]:
                print("🎉 [BOT] ¡Pedrete cantado!")
                return {'accion': 'pedrete'}

        if partida.mensaje_transicion: return {'accion': 'continuar_transicion'}
        if fase == 'recuento': return {'accion': 'listo_siguiente_ronda'}

        # ==========================================
        # FASE DE DESCARTE (¡NUEVO!)
        # ==========================================
        if fase == 'descarte':
            if not estado['descartes_listos']:
                if self.modelo_descartes is not None:
                    indices = self.predecir_descarte(partida, cartas)
                    print(f"🎴 [IA DESCARTE] Tirando {len(indices)} cartas. Índices: {indices}")
                else:
                    # Respaldo aleatorio
                    num_descartes = random.randint(0, 4)
                    indices = random.sample(range(4), num_descartes)
                
                self.memoria['mis_descartes'].extend([cartas[i]['valor'] for i in indices])
                return {'accion': 'descartar', 'indices': indices}

        if partida.turno_de != self.sid: return None
        if fase == 'espera_reparto': return {'accion': 'repartir'}

        if fase == 'mus':
            if estado['quiere_mus'] is None:
                if self.modelo_mus is not None:
                    decision = self.predecir_mus(partida, cartas, estado)
                    print(f"🤖 [IA MUS] Decisión final: {decision.upper()}")
                    return {'accion': decision}
                else:
                    return {'accion': random.choice(['mus', 'no_mus'])}

        # 5. Apuestas (¡CON IA!)
        if fase == 'apuestas':
            subida = partida.subida_pendiente
            max_apuesta = 40 - estado['puntos']
            
            # Decidimos la acción inteligente
            if self.modelo_apuestas is not None:
                eleccion = self.predecir_apuesta(partida, cartas, subida)
                print(f"🎲 [IA APUESTA] Fase: {partida.fases_apuesta[partida.indice_fase]} | Decisión: {eleccion.upper()}")
            else:
                # Respaldo aleatorio si no hay modelo
                if subida == 0: eleccion = random.choice(['pasar', 'envidar'])
                else: eleccion = random.choice(['ver', 'nover', 'subir'])
            
            # Calculamos la cantidad si la IA decide apostar/subir
            if eleccion == 'envidar':
                cant = random.randint(2, min(5, max_apuesta)) if max_apuesta >= 2 else 2
                return {'accion': 'envidar', 'cantidad': cant}
            elif eleccion == 'subir':
                tope = max_apuesta - partida.apuesta_vista
                cant = random.randint(1, min(5, tope)) if tope >= 1 else 1
                return {'accion': 'subir', 'cantidad': cant}
            else:
                return {'accion': eleccion}
        return None
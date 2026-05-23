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
import numpy as np
import torch
# Importamos la arquitectura de la red y el traductor de estados
from redes_mus import StrategyNetwork, estado_a_vector
from mus_mecanicas import tiene_pares, tiene_juego

ACTION_MAP = {'pasar': 0, 'envidar': 1, 'ver': 2, 'nover': 3, 'subir': 4, 'ordago': 5}

class SmartBot:
    def __init__(self, sid="BOT_ML"):
        self.sid = sid
        self.memoria = {'mis_descartes': [], 'descartes_rival': 0, 'hubo_fase_pares': False, 'ronda': -1}
        
        # 1. Cargar Cerebro de Mus
        self.modelo_apuestas_cfr = None
        ruta_cfr = 'deep_cfr_mus_bot.pth'
        
        if os.path.exists(ruta_cfr):
            self.modelo_apuestas_cfr = StrategyNetwork(11) # 11 es el input_size
            self.modelo_apuestas_cfr.load_state_dict(torch.load(ruta_cfr))
            self.modelo_apuestas_cfr.eval() # Lo ponemos en modo "solo lectura"
            print("🧠 [BOT] Cerebro Deep CFR (Equilibrio de Nash) cargado para Apuestas.")
        else:
            print("⚠️ [BOT] No se encontró el modelo CFR.")
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
        
        if isinstance(mascara_raw, float):
            mascara_raw = int(mascara_raw)

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


        # =========================================================
        # 🛡️ LAS LEYES DEL MUS (SALVAGUARDAS DE REGLAS)
        # No dejamos que la IA opine si la jugada es ilegal
        # =========================================================
        if fase_actual == 'Pares' and cat_pares == 0:
            print("🛑 [IA APUESTA] No tengo pares. Paso automáticamente.")
            return 'pasar' if subida_pendiente == 0 else 'nover'
            
        if fase_actual == 'Juego' and not estado_juego['tiene_juego']:
            print("🛑 [IA APUESTA] No tengo juego. Paso automáticamente.")
            return 'pasar' if subida_pendiente == 0 else 'nover'
        # =========================================================


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


    def get_valid_actions_cfr(self, partida, cartas, subida_pendiente):
        """Filters illegal moves and applies the dynamic action abstraction rule."""
        fase_actual = partida.fases_apuesta[partida.indice_fase]
        
        # Rule constraints: check if player has pairs or game
        if fase_actual == 'Pares' and not tiene_pares(cartas):
            return ['pasar'] if subida_pendiente == 0 else ['nover']
        if fase_actual == 'Juego' and not tiene_juego(cartas):
            return ['pasar'] if subida_pendiente == 0 else ['nover']

        # Dynamic action abstraction based on points remaining to win
        puntos_propios = partida.estado[self.sid]['puntos']
        puntos_restantes = 40 - puntos_propios
        bote_actual = partida.apuesta_vista + (subida_pendiente if isinstance(subida_pendiente, int) else 0)

        if subida_pendiente == 0:
            if puntos_restantes <= 2:
                return ['pasar', 'ordago']
            return ['pasar', 'envidar', 'ordago']
        elif subida_pendiente == 'ÓRDAGO':
            return ['ver', 'nover']
        else:
            if bote_actual >= 8 or bote_actual >= puntos_restantes:
                return ['ver', 'nover', 'ordago']
            else:
                return ['ver', 'nover', 'subir', 'ordago']

    def decidir_apuesta_cfr(self, partida, cartas, subida_pendiente):
        """Runs inference on the Strategy Network and samples an action based on Nash Equilibrium."""
        cartas_norm = [12 if c['valor'] == 3 else 1 if c['valor'] == 2 else c['valor'] for c in cartas]
        c_ord = sorted(cartas_norm, reverse=True)
        subida_ia = 40 if subida_pendiente == 'ÓRDAGO' else subida_pendiente

        # Reconstruct the exact Information Set dictionary used during training
        estado_dict = {
            'es_mano': 1 if self.sid == partida.id_mano else 0,
            'cartas': c_ord,
            'indice_fase': partida.indice_fase,
            'subida_pendiente': subida_ia,
            'bote_grande': partida.botes.get('Grande', 0),
            'bote_chica': partida.botes.get('Chica', 0),
            'bote_pares': partida.botes.get('Pares', 0),
            'apuesta_vista': partida.apuesta_vista
        }

        # Format input state into a PyTorch tensor
        tensor_input = estado_a_vector(estado_dict)

        # Predict mixed strategy distribution
        with torch.no_grad():
            raw_probabilities = self.modelo_apuestas_cfr(tensor_input).squeeze(0).numpy()

        # Get valid actions for the current state and map them to network indices
        valid_actions = self.get_valid_actions_cfr(partida, cartas, subida_pendiente)
        valid_indices = [ACTION_MAP[a] for a in valid_actions]

        # Filter out illegal actions and re-normalize probabilities
        filtered_probs = np.zeros(6)
        for idx in valid_indices:
            filtered_probs[idx] = raw_probabilities[idx]

        sum_probs = filtered_probs.sum()
        if sum_probs > 0:
            filtered_probs /= sum_probs
        else:
            # Fallback uniform distribution if network predictions colapsed
            for idx in valid_indices:
                filtered_probs[idx] = 1.0 / len(valid_indices)

        # Sample final action using the weighted probabilities
        actions_list = ['pasar', 'envidar', 'ver', 'nover', 'subir', 'ordago']
        chosen_action = random.choices(actions_list, weights=filtered_probs, k=1)[0]
        return chosen_action


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

        # 5. Apuestas (¡CON IA DEEP CFR!)
        if fase == 'apuestas':
            subida = partida.subida_pendiente
            max_apuesta = 40 - estado['puntos']
            
            # Decidimos la acción inteligente usando el Equilibrio de Nash
            if self.modelo_apuestas_cfr is not None:
                eleccion = self.decidir_apuesta_cfr(partida, cartas, subida)
                print(f"🎲 [IA DEEP CFR] Fase: {partida.fases_apuesta[partida.indice_fase]} | Decisión: {eleccion.upper()}")
            else:
                # Respaldo aleatorio si no hay modelo entrenado
                if subida == 0: eleccion = random.choice(['pasar', 'envidar'])
                else: eleccion = random.choice(['ver', 'nover', 'subir'])
            
            # Calculamos la cantidad si la IA decide apostar/subir (Mantenemos discretizado a 2)
            if eleccion == 'envidar':
                return {'accion': 'envidar', 'cantidad': 2}
            elif eleccion == 'subir':
                return {'accion': 'subir', 'cantidad': 2}
            else:
                return {'accion': eleccion}
        return None
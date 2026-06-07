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
import json



ACTION_MAP = {'pasar': 0, 'envidar': 1, 'ver': 2, 'nover': 3, 'subir': 4, 'ordago': 5}

def cargar_modelo(ruta):
    modelo = StrategyNetwork(input_size=18)
    # Soporte para cargar tanto un state_dict directo como un checkpoint maestro
    datos = torch.load(ruta, weights_only=False)
    if 'strategy_net_state' in datos:
        modelo.load_state_dict(datos['strategy_net_state'])
    else:
        modelo.load_state_dict(datos)
    modelo.eval()
    return modelo


class SmartBot:
    def __init__(self, sid="BOT_ML"):
        self.sid = sid
        self.memoria = {'mis_descartes': [], 'descartes_rival': 0, 'hubo_fase_pares': False, 'ronda': -1}
        self.meta_variables = self.update_meta_variables(show=False)  # Inicializamos las meta-variables con valores aleatorios
        

        # 1. Cargar Cerebro de Apuestas CFR
        self.modelo_apuestas_cfr = None
        name_model = 'deep_cfr_mus_bot_cfr5_iter_1800'  #'checkpoint_mus_latest' #'deep_cfr_mus_bot_iter_1400'
        ruta_cfr = f"learn/cfr/{name_model}.pth"
        self.modelo_apuestas_cfr = cargar_modelo(ruta_cfr)

        # We import another CFR model that is more bluffer and impredictable.
        name_model_2 = 'deep_cfr_mus_bot_iter_1400'  #'checkpoint_mus_latest' #'deep_cfr_mus_bot_iter_1400'
        ruta_cfr_2 = f"learn/cfr_generations/cfr4/{name_model_2}.pth"
        self.modelo_apuestas_cfr_2 = cargar_modelo(ruta_cfr_2)

        self.expected_values_mus = {}
        ruta_json = 'learn/global_variables/mus_data.json' # Ajusta la ruta si está en otra carpeta
        if os.path.exists(ruta_json):
            with open(ruta_json, 'r') as f:
                datos = json.load(f)
                self.expected_values_mus = datos.get('expected_values', {})
            print("🧠 [BOT] Tabla de Expected Values cargada para decisión de Mus.")
        else:
            print("⚠️ [BOT] No se encontró mus_data.json.")
            
        # 2. Cargar Cerebro de Descartes
        self.modelo_descartes = None
        if os.path.exists('learn/models/modelo_descartes.pkl'):
            self.modelo_descartes = joblib.load('learn/models/modelo_descartes.pkl')
            print("🧠 [BOT] Cerebro de Descartes cargado.")

    def update_meta_variables(self, show = False):
        """Actualiza las meta-variables de la IA al final de cada mano para introducir variabilidad en su comportamiento.
        self.meta_variables['musero'] = random.random()  # Cambia el umbral de corte del mus
        self.meta_variables['bluffer'] = max(0.7, random.random())  # Asegura que siempre tenga algo de bluffer
        self.meta_variables['aleatorio'] = random.random()  # Cambia la cantidad de ruido en las decisiones
        self.meta_variables['fish'] = random.random()  # Cambia la probabilidad de cometer errores tontos"""
        new_meta = {'musero': random.random(), 'bluffer': min(0.35, random.random()), 'aleatorio': min(0.4, random.random()), 'fish': random.random()}
        if show: print(f"🔄 Meta-variables actualizadas: {new_meta}")
        return new_meta

    def actualizar_memoria(self, partida):
        if self.memoria['ronda'] != partida.ronda_n:
            self.memoria = {'mis_descartes': [], 'descartes_rival': 0, 'hubo_fase_pares': False, 'ronda': partida.ronda_n}


    def predecir_mus(self, partida, cartas, estado):
        """Decide si cortar el mus basándose en el Expected Value precalculado."""
        es_mano = (partida.id_mano == self.sid)
        
        # 1. Normalizar y ordenar las cartas para que coincidan con las llaves del JSON
        cartas_norm = [12 if c['valor'] == 3 else 1 if c['valor'] == 2 else c['valor'] for c in cartas]
        c_ord = sorted(cartas_norm, reverse=True)
        
        # Al hacer str(lista), en Python se formatea exactamente como "[12, 12, 12, 12]"
        llave_mano = str(c_ord)
        
        # 2. Buscar el EV en el diccionario (por defecto 0.0 si no se encuentra)
        ev_valores = self.expected_values_mus.get(llave_mano, [0.0, 0.0])
        
        # 3. Elegir el EV correcto según la posición
        ev_final = ev_valores[0] if es_mano else ev_valores[1]
        
        impulso_farol = self.meta_variables['bluffer'] * random.random()
    
        # 3. Ruido puro para que no sea matemático y robótico 100%
        # random.uniform(-1, 1) puede subir o bajar la percepción
        ruido = self.meta_variables['aleatorio'] * random.uniform(-1.0, 1.0) * 0.2
        
        # 4. Cálculo del EV percibido en este turno concreto
        ev_percibido = ev_final + impulso_farol + ruido
        
        # 5. Toma de decisión
        if ev_percibido >= self.meta_variables['musero']:
            return "no_mus"
        else:
            return "mus"


    def predecir_descartes_ia(self, partida, cartas):
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


    def predecir_descarte(self, partida, cartas):
            """Calcula el descarte matemáticamente óptimo consultando la tabla de EV"""
            from mus_discard_chooser import get_best_discard_strategy
            
            es_mano = (partida.id_mano == self.sid)
            
            # Extraemos los valores crudos de las cartas (3, 12, 1, 4...)
            hand_vals = [c['valor'] for c in cartas]
            
            # Llamamos a tu algoritmo pasándole la tabla que ya está en RAM
            resultado_descarte = get_best_discard_strategy(
                my_hand=hand_vals, 
                ev_lookup_table=self.expected_values_mus, 
                am_i_mano=es_mano
            )
            
            # Extraemos la lista de índices de forma segura (como hicimos en el entorno)
            best_action = resultado_descarte.get('best_action', {})
            if isinstance(best_action, dict) and 'discard' in best_action:
                indices_brutos = best_action['discard']
            else:
                indices_brutos = best_action if best_action else []
                
            # Convertimos los índices a enteros y los devolvemos
            return [int(i) for i in indices_brutos]


    def get_valid_actions_cfr(self, partida, cartas, subida_pendiente):
            """Filters illegal moves and applies the dynamic action abstraction rule."""
            fase_actual = partida.fases_apuesta[partida.indice_fase]
            rival = partida.id_postre if self.sid == partida.id_mano else partida.id_mano
            
            # Rule constraints: check if player has pairs or game
            if fase_actual == 'Pares' and not tiene_pares(cartas):
                return ['pasar'] if subida_pendiente == 0 else ['nover']
            if fase_actual == 'Juego' and not tiene_juego(cartas) and not getattr(partida, 'juego_es_punto', False):
                return ['pasar'] if subida_pendiente == 0 else ['nover']

            # NUEVO: Lógica de topes globales y deje forzado
            puntos_propios = partida.estado[self.sid]['puntos']
            puntos_rival = partida.estado[rival]['puntos']
            pts_maximos = max(puntos_propios, puntos_rival)
            puntos_restantes_global = 40 - pts_maximos

            bote_actual = partida.apuesta_vista + (subida_pendiente if isinstance(subida_pendiente, int) else 0)
            
            # Calculamos si tirar las cartas cuesta la partida
            deje = partida.apuesta_vista if partida.apuesta_vista > 0 else 1
            obligado_a_ver = (puntos_rival + deje >= 40)

            if subida_pendiente == 0:
                if puntos_restantes_global <= 2:
                    return ['pasar', 'ordago']
                return ['pasar', 'envidar', 'ordago']
                
            elif subida_pendiente == 'ÓRDAGO':
                # Si el deje cuesta la partida, eliminamos la opción de 'nover' del cerebro
                return ['ver'] if obligado_a_ver else ['ver', 'nover']
                
            else:
                acciones = ['ver']
                if not obligado_a_ver:
                    acciones.append('nover')
                    
                # Si las apuestas superan los puntos restantes globales, eliminamos 'subir'
                if bote_actual >= 8 or bote_actual >= puntos_restantes_global:
                    acciones.append('ordago')
                else:
                    acciones.extend(['subir', 'ordago'])
                    
                return acciones

    def decidir_apuesta_cfr(self, partida, cartas, subida_pendiente):
        """Runs inference on the Strategy Network and samples an action based on Nash Equilibrium."""
        cartas_norm = [12 if c['valor'] == 3 else 1 if c['valor'] == 2 else c['valor'] for c in cartas]
        c_ord = sorted(cartas_norm, reverse=True)
        subida_ia = 40 if subida_pendiente == 'ÓRDAGO' else subida_pendiente
        rival = partida.id_postre if self.sid == partida.id_mano else partida.id_mano


        # Reconstruct the exact Information Set dictionary used during training
        estado_dict = {
            'es_mano': 1 if self.sid == partida.id_mano else 0,
            'cartas': c_ord,
            'indice_fase': partida.indice_fase,
            'subida_pendiente': subida_ia,
            'bote_grande': partida.botes.get('Grande', 0),
            'bote_chica': partida.botes.get('Chica', 0),
            'bote_pares': partida.botes.get('Pares', 0),
            'apuesta_vista': partida.apuesta_vista,
            
            'puntos_propios': partida.estado[self.sid]['puntos'],
            'puntos_rival': partida.estado[rival]['puntos'],
            
            # Usamos la variable directa que acabamos de crear en el motor
            'rondas_mus': partida.rondas_mus,
            'descartes_rival': partida.estado[rival].get('descartes_hechos', 0),
            
            # Lógica Inline: 1.0 si es mío, 0.0 si es del rival, 0.5 si nadie lo ha ganado (None)
            'owner_grande': 1.0 if partida.ganadores_fase.get('Grande') == self.sid else (0.0 if partida.ganadores_fase.get('Grande') is not None else 0.5),
            'owner_chica': 1.0 if partida.ganadores_fase.get('Chica') == self.sid else (0.0 if partida.ganadores_fase.get('Chica') is not None else 0.5),
            'owner_pares': 1.0 if partida.ganadores_fase.get('Pares') == self.sid else (0.0 if partida.ganadores_fase.get('Pares') is not None else 0.5)
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
        if fase == 'recuento':
            self.update_meta_variables(show=True)  # Actualizamos las meta-variables al final de cada mano            
            return {'accion': 'listo_siguiente_ronda'}
        

        # ==========================================
        # FASE DE DESCARTE (¡NUEVO!)
        # ==========================================
        if fase == 'descarte':
            if not estado['descartes_listos']:
                if self.modelo_descartes is not None:
                    indices = self.predecir_descarte(partida, cartas)
                    print(f"🎴 [BOT DESCARTE] Tirando {len(indices)} cartas. Índices: {indices}")
                else:
                    # Respaldo aleatorio
                    indices = self.predecir_descarte(partida, cartas)
                    print(f"🎴 [BOT DESCARTE] Tirando {len(indices)} cartas. Índices: {indices}")
                
                self.memoria['mis_descartes'].extend([cartas[i]['valor'] for i in indices])
                return {'accion': 'descartar', 'indices': indices}

        if partida.turno_de != self.sid: return None
        if fase == 'espera_reparto': return {'accion': 'repartir'}

        if fase == 'mus':
            if estado['quiere_mus'] is None:
                decision = self.predecir_mus(partida, cartas, estado)
                print(f"🤖 [IA MUS] Decisión final: {decision.upper()}")
                return {'accion': decision}


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
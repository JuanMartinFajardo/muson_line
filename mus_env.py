import copy
import numpy as np
from mus_mecanicas import PartidaMus, tiene_pares, tiene_juego
import random
import json
import os
from mus_discard_chooser import get_best_discard_strategy
from mus_mecanicas import tiene_pares, tiene_juego

expected_values_mus = {}
# Usamos una ruta absoluta relativa al archivo para evitar fallos de ejecución
ruta_json = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'learn/global_variables/mus_data.json')

if os.path.exists(ruta_json):
    with open(ruta_json, 'r') as f:
        datos = json.load(f)
        expected_values_mus = datos.get('expected_values', {})
    print("💾 [GIMNASIO] Tabla de Expected Values cargada en caché global.")
else:
    print("⚠️ [GIMNASIO] Alerta: No se encontró mus_data.json. Las decisiones de mus colapsarán.")


class MusBettingEnv:
    def __init__(self):
        # Mapeo de acciones posibles a índices (0 a 5)
        self.acciones_lista = ['pasar', 'envidar', 'ver', 'nover', 'subir', 'ordago']
        self.partida = None


    def reset(self):
        """Inicia una partida nueva y la adelanta hasta la fase de apuestas"""
        self.partida = PartidaMus("IA_1", "IA_2")
        self.partida.generate_log = False
        self.partida.iniciar_ronda()
        self._fast_forward_to_apuestas()
        return self.get_information_set()

    def _fast_forward_to_apuestas(self):
        self.partida.estado["IA_1"]['puntos'] = random.randint(0, 39)
        self.partida.estado["IA_2"]['puntos'] = random.randint(0, 39)
        
        # Inventamos un contexto de descartes previo para que la IA lo estudie
        self.partida.rondas_mus = random.randint(0, 4)

        while self.partida.fase in ['espera_reparto', 'mus', 'descarte']:
            if self.partida.fase == 'espera_reparto':
                self.partida.repartir_inicial()
                
            elif self.partida.fase == 'mus':
                # --- NUEVA LÓGICA DE MUS BASADA EN EV ---
                jugador = self.partida.turno_de
                es_mano = (jugador == self.partida.id_mano)
                cartas = self.partida.estado[jugador]['cartas']
                
                # Normalizamos igual que en el bot
                cartas_norm = [12 if c['valor'] == 3 else 1 if c['valor'] == 2 else c['valor'] for c in cartas]
                c_ord = sorted(cartas_norm, reverse=True)
                llave_mano = str(c_ord)
                
                # Consultamos el diccionario
                ev_valores = expected_values_mus.get(llave_mano, [0.0, 0.0])
                ev_final = ev_valores[0] if es_mano else ev_valores[1]
                
                # Si rinde más de 0.5, cortamos mus (False), de lo contrario damos mus (True)
                if ev_final > 0.5:
                    self.partida.cantar_mus(jugador, False)
                else:
                    self.partida.cantar_mus(jugador, True)
                    
            elif self.partida.fase == 'descarte':
                # NUEVA LÓGICA INTELIGENTE DE DESCARTE
                for p in ["IA_1", "IA_2"]:
                    if not self.partida.estado[p]['descartes_listos']:
                        # Importamos tu función de descarte

                        
                        cartas = self.partida.estado[p]['cartas']
                        # Extraemos los valores crudos de las cartas (3, 12, 1, etc.)
                        hand_vals = [c['valor'] for c in cartas]
                        es_mano = (p == self.partida.id_mano)
                        
                        # El algoritmo evalúa las 16 combinaciones posibles basándose en la tabla EV
                        indices_a_tirar = get_best_discard_strategy(
                            my_hand=hand_vals, 
                            ev_lookup_table=expected_values_mus, 
                            am_i_mano=es_mano
                        )
                        best_action = indices_a_tirar['best_action']
                        
                        # Si best_action es un diccionario, extraemos la lista de la llave 'discard'
                        if isinstance(best_action, dict) and 'discard' in best_action:
                            indices_brutos = best_action['discard']
                        else:
                            indices_brutos = best_action # Por si acaso a veces devuelve la lista directamente
                        
                        # Convertimos a enteros
                        indices_a_tirar = [int(i) for i in indices_brutos]
                        self.partida.procesar_descarte(p, indices_a_tirar)

    def get_valid_actions(self):
        """Devuelve las acciones legales en el nodo actual"""
        if self.partida.fase != 'apuestas':
            return []
            
        subida = self.partida.subida_pendiente
        jugador = self.partida.turno_de
        cartas = self.partida.estado[jugador]['cartas']
        fase_actual = self.partida.fases_apuesta[self.partida.indice_fase]
        rival = self.partida.id_postre if jugador == self.partida.id_mano else self.partida.id_mano
        
        # 1. Filtros de las Leyes del Mus
        if fase_actual == 'Pares' and not tiene_pares(cartas):
            return ['pasar'] if subida == 0 else ['nover']
        if fase_actual == 'Juego' and not tiene_juego(cartas) and not getattr(self.partida, 'juego_es_punto', False):
            return ['pasar'] if subida == 0 else ['nover']

        # 2. Lógica de Poda Dinámica y Leyes de Deje
        puntos_propios = self.partida.estado[jugador]['puntos']
        puntos_rival = self.partida.estado[rival]['puntos']
        pts_maximos = max(puntos_propios, puntos_rival)
        puntos_restantes_global = 40 - pts_maximos

        bote_actual = self.partida.apuesta_vista + (subida if isinstance(subida, int) else 0)
        
        deje = self.partida.apuesta_vista if self.partida.apuesta_vista > 0 else 1
        obligado_a_ver = (puntos_rival + deje >= 40)

        if subida == 0:
            if puntos_restantes_global <= 2:
                return ['pasar', 'ordago']
            return ['pasar', 'envidar', 'ordago']
            
        elif subida == 'ÓRDAGO':
            return ['ver'] if obligado_a_ver else ['ver', 'nover']
            
        else:
            acciones = ['ver']
            if not obligado_a_ver:
                acciones.append('nover')
                
            if bote_actual >= 8 or bote_actual >= puntos_restantes_global:
                acciones.append('ordago')
            else:
                acciones.extend(['subir', 'ordago'])
                
            return acciones

    def step(self, accion_str):
        """Aplica la acción, avanza el juego y devuelve el resultado"""
        jugador = self.partida.turno_de
        
        # Discretizamos las apuestas para simplificar el árbol matemático
        cantidad = 0
        if accion_str == 'envidar': cantidad = 2
        elif accion_str == 'subir': cantidad = 2
        
        # Ejecutamos la acción en tu motor original
        self.partida.accion_apuesta(jugador, accion_str, cantidad)
        
        # Auto-resolver las transiciones de "Nadie tiene pares" o "No tiene juego"
        while self.partida.fase == 'apuestas' and self.partida.mensaje_transicion is not None:
            self.partida.mensaje_transicion = None
            self.partida.preparar_subfase()

        # Comprobamos si la ronda ha terminado
        done = (self.partida.fase == 'recuento')
        
        # Calculamos recompensas
        recompensas = { "IA_1": 0, "IA_2": 0 }
        if done:
            self.partida.calcular_recuento()
            recompensas["IA_1"] = self.partida.estado["IA_1"]['puntos']
            recompensas["IA_2"] = self.partida.estado["IA_2"]['puntos']
            
        return self.get_information_set(), recompensas, done

    def get_information_set(self):
        if self.partida.fase == 'recuento': return None
        
        jugador = self.partida.turno_de
        rival = self.partida.id_postre if jugador == self.partida.id_mano else self.partida.id_mano
        
        cartas = self.partida.estado[jugador]['cartas']
        c_vals = sorted([12 if c['valor']==3 else 1 if c['valor']==2 else c['valor'] for c in cartas], reverse=True)
        subida = 40 if self.partida.subida_pendiente == 'ÓRDAGO' else self.partida.subida_pendiente
        
        # SOLUCIÓN AL PUNTO 3 (Propiedad de los botes)
        def get_owner(fase_nombre):
            ganador = self.partida.ganadores_fase.get(fase_nombre)
            if ganador is None: return 0.5 # En el aire
            return 1.0 if ganador == jugador else 0.0 # Mío o del rival
        
        estado = {
            'jugador': jugador,
            'es_mano': 1 if jugador == self.partida.id_mano else 0,
            'cartas': c_vals,
            'indice_fase': self.partida.indice_fase,
            'subida_pendiente': subida,
            'bote_grande': self.partida.botes.get('Grande', 0),
            'bote_chica': self.partida.botes.get('Chica', 0),
            'bote_pares': self.partida.botes.get('Pares', 0),
            'apuesta_vista': self.partida.apuesta_vista,
            'puntos_propios': self.partida.estado[jugador]['puntos'],
            'puntos_rival': self.partida.estado[rival]['puntos'],
            # SOLUCIÓN AL PUNTO 1 (Rondas de mus y descartes)
            'rondas_mus': getattr(self.partida, 'rondas_mus', 0),
            'descartes_rival': self.partida.estado[rival].get('descartes_hechos', 0),
            # PROPIEDADES
            'owner_grande': get_owner('Grande'),
            'owner_chica': get_owner('Chica'),
            'owner_pares': get_owner('Pares')
        }
        return estado

    def clone(self):
        """Bifurca el universo. Vital para explorar diferentes ramas en CFR."""
        return copy.deepcopy(self)
    

if __name__ == "__main__":
    import random
    import time
    
    env = MusBettingEnv()
    
    inicio = time.time()
    num_partidas = 10000
    
    print(f"🚀 Iniciando simulación rápida de {num_partidas} partidas...")
    for i in range(num_partidas):
        info_set = env.reset()
        done = False
        
        while not done:
            acciones_legales = env.get_valid_actions()
            accion_elegida = random.choice(acciones_legales)
            info_set, recompensas, done = env.step(accion_elegida)
            
    fin = time.time()
    print(f"✅ Completado en {fin - inicio:.2f} segundos.")
    print(f"⚡ Velocidad: {num_partidas / (fin - inicio):.0f} partidas por segundo.")
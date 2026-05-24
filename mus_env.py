import copy
import numpy as np
from mus_mecanicas import PartidaMus, tiene_pares, tiene_juego
import random

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
                if random.random() > 0.5:
                    self.partida.cantar_mus(self.partida.turno_de, False)
                else:
                    self.partida.cantar_mus(self.partida.turno_de, True)
                    
            elif self.partida.fase == 'descarte':
                # ¡CORRECCIÓN! Iteramos sobre ambos jugadores independientemente del turno
                for p in ["IA_1", "IA_2"]:
                    # Solo le hacemos descartar si no lo ha hecho ya en esta ronda
                    if not self.partida.estado[p]['descartes_listos']:
                        num_cartas = random.randint(1, 4)
                        indices = random.sample(range(4), num_cartas)
                        self.partida.procesar_descarte(p, indices)

    def get_valid_actions(self):
        """Devuelve las acciones legales en el nodo actual"""
        if self.partida.fase != 'apuestas':
            return []
            
        subida = self.partida.subida_pendiente
        jugador = self.partida.turno_de
        cartas = self.partida.estado[jugador]['cartas']
        fase_actual = self.partida.fases_apuesta[self.partida.indice_fase]
        
        from mus_mecanicas import tiene_pares, tiene_juego
        
        # 1. Filtros de las Leyes del Mus
        if fase_actual == 'Pares' and not tiene_pares(cartas):
            return ['pasar'] if subida == 0 else ['nover']
        if fase_actual == 'Juego' and not tiene_juego(cartas):
            return ['pasar'] if subida == 0 else ['nover']

        # 2. Lógica de Poda Dinámica (Límite de 8 piedras o fin de partida)
        puntos_propios = self.partida.estado[jugador]['puntos']
        puntos_restantes = 40 - puntos_propios
        bote_actual = self.partida.apuesta_vista + (subida if isinstance(subida, int) else 0)

        if subida == 0:
            # Si nos quedan 2 puntos o menos, cualquier apuesta cierra la partida matemáticamente
            if puntos_restantes <= 2:
                return ['pasar', 'ordago']
            return ['pasar', 'envidar', 'ordago']
            
        elif subida == 'ÓRDAGO':
            return ['ver', 'nover']
            
        else:
            # Cortamos la opción de 'subir' si llegamos al tope de 8 piedras,
            # o si el bote actual ya cubre los puntos que nos quedan para ganar.
            if bote_actual >= 8 or bote_actual >= puntos_restantes:
                return ['ver', 'nover', 'ordago']
            else:
                return ['ver', 'nover', 'subir', 'ordago']

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
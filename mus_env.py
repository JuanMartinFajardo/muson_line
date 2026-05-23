import copy
import numpy as np
from mus_mecanicas import PartidaMus, tiene_pares, tiene_juego

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
        """Fuerza las decisiones iniciales para ir directo a la Grande"""
        while self.partida.fase in ['espera_reparto', 'mus', 'descarte']:
            if self.partida.fase == 'espera_reparto':
                self.partida.repartir_inicial()
            elif self.partida.fase == 'mus':
                # El jugador al que le toque corta el mus automáticamente
                self.partida.cantar_mus(self.partida.turno_de, False)
            elif self.partida.fase == 'descarte':
                self.partida.procesar_descarte(self.partida.turno_de, [])

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
        """
        Extrae todo lo que el jugador activo sabe y lo convierte en un estado plano.
        Esta función será el INPUT de la Red Neuronal más adelante.
        """
        if self.partida.fase == 'recuento': return None
        
        jugador = self.partida.turno_de
        cartas = self.partida.estado[jugador]['cartas']
        c_vals = sorted([12 if c['valor']==3 else 1 if c['valor']==2 else c['valor'] for c in cartas], reverse=True)
        
        subida = 40 if self.partida.subida_pendiente == 'ÓRDAGO' else self.partida.subida_pendiente
        
        estado = {
            'jugador': jugador,
            'es_mano': 1 if jugador == self.partida.id_mano else 0,
            'cartas': c_vals,
            'indice_fase': self.partida.indice_fase, # 0:Grande, 1:Chica, 2:Pares, 3:Juego
            'subida_pendiente': subida,
            'bote_grande': self.partida.botes.get('Grande', 0),
            'bote_chica': self.partida.botes.get('Chica', 0),
            'bote_pares': self.partida.botes.get('Pares', 0),
            'apuesta_vista': self.partida.apuesta_vista
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
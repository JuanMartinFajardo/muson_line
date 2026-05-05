import random

class BotAleatorio:
    def __init__(self, sid="BOT_EASY"):
        self.sid = sid

    def obtener_accion(self, partida):
        fase = partida.fase
        estado = partida.estado[self.sid]
        cartas = estado['cartas']

        # 1. Comprobar Pedrete (Prioridad absoluta)
        # Solo se puede cantar en fase de mus o descarte si se tienen 4,5,6,7
        if fase in ['mus', 'descarte'] and cartas:
            valores = sorted([c['valor'] for c in cartas])
            if valores == [4, 5, 6, 7]:
                return {'accion': 'pedrete'}

        # 2. Transiciones automáticas (Pausas de 3 segundos en el frontend)
        if partida.mensaje_transicion:
            return {'accion': 'continuar_transicion'}

        # 3. Espera de reparto inicial
        if fase == 'espera_reparto':
            return {'accion': 'repartir'}

        # 4. Fase de Recuento (Siguiente partida/juego)
        if fase == 'recuento':
            return {'accion': 'listo_siguiente_ronda'}

        # 5. Fase de Mus
        if fase == 'mus':
            if estado['quiere_mus'] is None:
                return {'accion': random.choice(['mus', 'no_mus'])}

        # 6. Fase de Descarte
        if fase == 'descarte':
            if not estado['descartes_listos']:
                # El bot elige tirar entre 0 y 4 cartas de forma aleatoria
                num_descartes = random.randint(0, 4)
                indices = random.sample(range(4), num_descartes)
                return {'accion': 'descartar', 'indices': indices}

        # 7. Fase de Apuestas (Grande, Chica, Pares, Juego)
        if fase == 'apuestas':
            subida = partida.subida_pendiente
            puntos_bot = estado['puntos']
            apuesta_vista = partida.apuesta_vista
            max_apuesta = 40 - puntos_bot

            # Si no hay subida pendiente, el bot inicia la apuesta
            if subida == 0:
                opciones = ['pasar', 'envidar', 'ordago']
                eleccion = random.choice(opciones)
                
                if eleccion == 'envidar':
                    # Envida entre 2 y 5 (o el máximo que pueda)
                    cant = random.randint(2, min(5, max_apuesta)) if max_apuesta >= 2 else 2
                    return {'accion': 'envidar', 'cantidad': cant}
                return {'accion': eleccion}
            
            # Si hay subida pendiente, el bot tiene que responder
            else:
                if subida == 'ÓRDAGO':
                    return {'accion': random.choice(['ver', 'nover'])}
                else:
                    opciones = ['ver', 'nover', 'subir', 'ordago']
                    eleccion = random.choice(opciones)
                    
                    if eleccion == 'subir':
                        tope = max_apuesta - apuesta_vista
                        if tope >= 1:
                            cant = random.randint(1, min(5, tope))
                        else:
                            cant = 1
                        return {'accion': 'subir', 'cantidad': cant}
                    return {'accion': eleccion}

        return None # No debería llegar aquí si es su turno
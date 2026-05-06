import random

class BotAleatorio:
    def __init__(self, sid="BOT_EASY"):
        self.sid = sid
        #self.name = "RandomBot"

    def obtener_accion(self, partida):
        fase = partida.fase
        estado = partida.estado[self.sid]
        cartas = estado['cartas']

        # 1. Comprobar Pedrete (Prioridad absoluta)
        if fase in ['mus', 'descarte'] and cartas:
            valores = sorted([c['valor'] for c in cartas])
            if valores == [4, 5, 6, 7]:
                return {'accion': 'pedrete'}

        # 2. Transiciones automáticas
        if partida.mensaje_transicion:
            return {'accion': 'continuar_transicion'}

        # 3. Fase de Recuento
        if fase == 'recuento':
            return {'accion': 'listo_siguiente_ronda'}

        # 4. Fase de Descarte (¡NUEVA POSICIÓN!)
        # En el descarte no hay turnos, ambos tiran a la vez de forma asíncrona.
        if fase == 'descarte':
            if not estado['descartes_listos']:
                num_descartes = random.randint(0, 4)
                indices = random.sample(range(4), num_descartes)
                return {'accion': 'descartar', 'indices': indices}

        # --- BLOQUEO DE TURNO ---
        # Si llegamos aquí y NO es el turno del bot, no debe hacer nada.
        if partida.turno_de != self.sid:
            return None

        # 5. Espera de reparto inicial
        if fase == 'espera_reparto':
            return {'accion': 'repartir'}

        # 6. Fase de Mus
        if fase == 'mus':
            if estado['quiere_mus'] is None:
                return {'accion': random.choice(['mus', 'no_mus'])}

        # 7. Fase de Apuestas (Grande, Chica, Pares, Juego)
        if fase == 'apuestas':
            subida = partida.subida_pendiente
            puntos_bot = estado['puntos']
            apuesta_vista = partida.apuesta_vista
            max_apuesta = 40 - puntos_bot

            if subida == 0:
                opciones = ['pasar', 'envidar', 'ordago']
                eleccion = random.choice(opciones)
                
                if eleccion == 'envidar':
                    cant = random.randint(2, min(5, max_apuesta)) if max_apuesta >= 2 else 2
                    return {'accion': 'envidar', 'cantidad': cant}
                return {'accion': eleccion}
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

        return None
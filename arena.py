import torch
import numpy as np
import random
import matplotlib.pyplot as plt
from mus_mecanicas import PartidaMus, tiene_pares, tiene_juego
from redes_mus import StrategyNetwork, estado_a_vector

# ==========================================
# CONFIGURACIÓN DE LA ARENA
# ==========================================
NUM_PARTIDAS = 5999
name_model_1 = 'checkpoint_mus_latest'
name_model_2 = 'deep_cfr_mus_bot_iter_50'
PATH_MODELO_1 = f"learn/cfr/{name_model_1}.pth"
PATH_MODELO_2 = f"learn/cfr0/{name_model_2}.pth"  

ACTION_MAP = {'pasar': 0, 'envidar': 1, 'ver': 2, 'nover': 3, 'subir': 4, 'ordago': 5}
INDEX_TO_ACTION = {v: k for k, v in ACTION_MAP.items()}

# ==========================================
# 1. CARGA DE MODELOS
# ==========================================
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

print("🥊 Cargando gladiadores en la Arena...")
try:
    modelo_1 = cargar_modelo(PATH_MODELO_1)
    modelo_2 = cargar_modelo(PATH_MODELO_2)
    print("✅ Modelos listos.")
except Exception as e:
    print(f"❌ Error cargando modelos: {e}")
    exit()

# ==========================================
# 2. FUNCIONES AUXILIARES DE INFERENCIA
# ==========================================
def obtener_acciones_validas(partida, jugador):
    subida = partida.subida_pendiente
    cartas = partida.estado[jugador]['cartas']
    fase_actual = partida.fases_apuesta[partida.indice_fase]
    
    if fase_actual == 'Pares' and not tiene_pares(cartas): return ['pasar'] if subida == 0 else ['nover']
    if fase_actual == 'Juego' and not tiene_juego(cartas): return ['pasar'] if subida == 0 else ['nover']

    p_propios = partida.estado[jugador]['puntos']
    p_restantes = 40 - p_propios
    bote_actual = partida.apuesta_vista + (subida if isinstance(subida, int) else 0)

    if subida == 0:
        return ['pasar', 'ordago'] if p_restantes <= 2 else ['pasar', 'envidar', 'ordago']
    elif subida == 'ÓRDAGO': return ['ver', 'nover']
    else:
        return ['ver', 'nover', 'ordago'] if (bote_actual >= 8 or bote_actual >= p_restantes) else ['ver', 'nover', 'subir', 'ordago']

def elegir_accion(modelo, partida, jugador):
    rival = partida.id_postre if jugador == partida.id_mano else partida.id_mano
    cartas = partida.estado[jugador]['cartas']
    c_vals = sorted([12 if c['valor']==3 else 1 if c['valor']==2 else c['valor'] for c in cartas], reverse=True)
    subida = 40 if partida.subida_pendiente == 'ÓRDAGO' else partida.subida_pendiente
    
    def get_owner(fase):
        g = partida.ganadores_fase.get(fase)
        return 0.5 if g is None else (1.0 if g == jugador else 0.0)

    estado_dict = {
        'es_mano': 1 if jugador == partida.id_mano else 0,
        'cartas': c_vals,
        'indice_fase': partida.indice_fase,
        'subida_pendiente': subida,
        'bote_grande': partida.botes.get('Grande', 0),
        'bote_chica': partida.botes.get('Chica', 0),
        'bote_pares': partida.botes.get('Pares', 0),
        'apuesta_vista': partida.apuesta_vista,
        'puntos_propios': partida.estado[jugador]['puntos'],
        'puntos_rival': partida.estado[rival]['puntos'],
        'rondas_mus': getattr(partida, 'rondas_mus', 0),
        'descartes_rival': partida.estado[rival].get('descartes_hechos', 0),
        'owner_grande': get_owner('Grande'),
        'owner_chica': get_owner('Chica'),
        'owner_pares': get_owner('Pares')
    }

    tensor = estado_a_vector(estado_dict)
    
    with torch.no_grad():
        probs_raw = modelo(tensor).squeeze(0).numpy()
        
    acciones_validas = obtener_acciones_validas(partida, jugador)
    valid_indices = [ACTION_MAP[a] for a in acciones_validas]
    
    probs_filtradas = np.zeros(6)
    for idx in valid_indices:
        probs_filtradas[idx] = max(0.0, probs_raw[idx])
        
    suma = probs_filtradas.sum()
    if suma > 0: probs_filtradas /= suma
    else:
        for idx in valid_indices: probs_filtradas[idx] = 1.0 / len(valid_indices)

    eleccion_idx = random.choices(range(6), weights=probs_filtradas, k=1)[0]
    accion = INDEX_TO_ACTION[eleccion_idx]
    
    cantidad = 2 if accion in ['envidar', 'subir'] else 0
    return accion, cantidad

# ==========================================
# 3. EL BUCLE DE LA ARENA (LA SIMULACIÓN)
# ==========================================
# ==========================================
# 3. EL BUCLE DE LA ARENA (LA SIMULACIÓN)
# ==========================================
def jugar_partida(m1, m2):
    # Forzamos los nombres para saber quién es quién
    partida = PartidaMus("MODELO_1", "MODELO_2")
    partida.generate_log = False
    partida.iniciar_ronda()
    
    while True:
        jugador = partida.turno_de
        
        if partida.fase == 'espera_reparto':
            partida.repartir_inicial()
            
        elif partida.fase == 'mus':
            # Comportamiento semi-aleatorio para generar diversidad de situaciones
            corta_mus = (random.random() > 0.5)
            partida.cantar_mus(jugador, not corta_mus)
            
        elif partida.fase == 'descarte':
            # ¡CORRECCIÓN AL BUCLE INFINITO DE DESCARTES!
            for p in ["MODELO_1", "MODELO_2"]:
                if not partida.estado[p]['descartes_listos']:
                    num_cartas = random.randint(1, 4)
                    indices = random.sample(range(4), num_cartas)
                    partida.procesar_descarte(p, indices)
                    
        elif partida.fase == 'apuestas':
            # 1. Consumir automáticamente los avisos de "Nadie tiene pares" o "No juego"
            while partida.fase == 'apuestas' and partida.mensaje_transicion is not None:
                partida.mensaje_transicion = None
                partida.preparar_subfase()
            
            # 2. Si la fase cambió a recuento tras la subfase, abortamos esta vuelta
            if partida.fase != 'apuestas':
                continue
                
            # 3. Refrescamos quién tiene el turno (la subfase pudo haberlo cambiado)
            jugador = partida.turno_de

            # ¡AQUÍ ES DONDE PIENSAN LAS REDES!
            modelo_activo = m1 if jugador == "MODELO_1" else m2
            accion, cantidad = elegir_accion(modelo_activo, partida, jugador)
            partida.accion_apuesta(jugador, accion, cantidad)
            pts1 = partida.estado["MODELO_1"]['puntos']
            pts2 = partida.estado["MODELO_2"]['puntos']
            
        elif partida.fase == 'recuento':
            partida.calcular_recuento()
            pts1 = partida.estado["MODELO_1"]['puntos']
            pts2 = partida.estado["MODELO_2"]['puntos']
            # Si alguien ha llegado a 40, se acaba la partida y devolvemos el ganador
            if pts1 >= 40 or pts2 >= 40:
                return 1 if pts1 >= 40 else 2
                
            partida.cambiar_roles()
            partida.iniciar_ronda()
            partida.recuento_calculado = False
            partida.jugadores_listos = []

# ==========================================
# 4. EJECUCIÓN Y GRÁFICAS
# ==========================================
if __name__ == "__main__":
    victorias_1 = 0
    victorias_2 = 0
    
    historial_v1 = [0]
    historial_v2 = [0]
    
    print(f"⚔️ ¡Comienza el combate! Al mejor de {NUM_PARTIDAS} partidas.")
    
    for i in range(1, NUM_PARTIDAS + 1):
        ganador = jugar_partida(modelo_1, modelo_2)
        if ganador == 1: victorias_1 += 1
        else: victorias_2 += 1
        
        historial_v1.append(victorias_1)
        historial_v2.append(victorias_2)
        
        # Imprimir progreso cada 50 partidas
        if i % 50 == 0:
            ventaja = "M1" if victorias_1 > victorias_2 else "M2"
            print(f"Partida {i}/{NUM_PARTIDAS} | Marcador: M1 [{victorias_1} - {victorias_2}] M2 | Lidera {ventaja}")

    print("\n🏁 FINAL DEL COMBATE")
    print(f"🏆 Modelo 1: {victorias_1} victorias ({victorias_1/NUM_PARTIDAS*100:.1f}%)")
    print(f"🏆 Modelo 2: {victorias_2} victorias ({victorias_2/NUM_PARTIDAS*100:.1f}%)")
    
    # Dibujar la gráfica
# ==========================================
    # 4. EJECUCIÓN Y GRÁFICAS (TASA DE VICTORIA)
    # ==========================================
    # ... (el print del FINAL DEL COMBATE se queda igual) ...
    
    A = np.array(historial_v1)
    B = np.array(historial_v2)
    total_partidas = A + B
    
    # Calculamos A / (A + B). Donde total_partidas es 0 (el inicio), forzamos a que valga 0.5
    C = np.divide(A, total_partidas, out=np.full_like(A, 0.5, dtype=float), where=(total_partidas != 0))

    plt.figure(figsize=(10, 6))
    
    # Línea principal del Win Rate
    plt.plot(C, color='blue', linewidth=2, label='Win Rate Modelo 1')
    
    # Añadimos una línea horizontal en el 0.5 para ver rápidamente quién va ganando
    plt.axhline(y=0.5, color='gray', linestyle='--', alpha=0.7, label='Empate Perfecto (0.5)')
    
    # Fijamos el eje Y de 0 a 1 para no perder la perspectiva
    plt.ylim(0, 1) 
    
    plt.title(f'Convergencia de Tasa de Victoria (M1 vs M2)\nResultado Final: {victorias_1} - {victorias_2}', fontsize=14)
    plt.xlabel('Número de Partidas Jugadas', fontsize=12)
    plt.ylabel('Win Rate (Modelo 1)', fontsize=12)
    
    plt.legend(loc='upper right', fontsize=10)
    plt.grid(True, linestyle='--', alpha=0.7)
    
    plt.show()
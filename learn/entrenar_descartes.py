import os
import glob
import json
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import joblib
from learn.probability_calculator import (
    calcular_probabilidad_grande, calcular_probabilidad_chica,
    calcular_probabilidad_pares, calcular_probabilidad_juego,
    evaluar_pares, calcular_valor_juego
)

def crear_mascara_descarte(cartas_propias, cartas_tiradas):
    """
    Convierte las cartas tiradas en una máscara binaria de 4 dígitos (ej: '0011')
    basándose en la mano ordenada de mayor a menor.
    """
    # CORREGIDO: Las cartas en el JSONL ya son enteros, no diccionarios
    norm_mano = [12 if c == 3 else 1 if c == 2 else c for c in cartas_propias]
    mano_ordenada = sorted(norm_mano, reverse=True)
    
    tiradas_norm = [12 if c == 3 else 1 if c == 2 else c for c in cartas_tiradas]
    
    mask = [0, 0, 0, 0]
    temp_mano = mano_ordenada.copy()
    
    for t in tiradas_norm:
        if t in temp_mano:
            idx = temp_mano.index(t)
            mask[idx] = 1
            temp_mano[idx] = -1 # Marcamos como usada para evitar dobles borrados (ej: si hay dos 12s)
            
    return "".join(map(str, mask))

def entrenar_modelo_descartes(carpeta_logs):
    print(f"🔍 Extrayendo descartes de los logs en '{carpeta_logs}'...")
    archivos = glob.glob(os.path.join(carpeta_logs, '*.jsonl'))
    
    datos = []
    memoria_jugadores = {}
    
    for ruta in archivos:
        with open(ruta, 'r', encoding='utf-8') as f:
            for linea in f:
                turno = json.loads(linea)
                jugador = turno['jugador']
                
                # Gestión de memoria para los descartes previos
                if jugador not in memoria_jugadores or memoria_jugadores[jugador]['ronda'] != turno['ronda_n']:
                    memoria_jugadores[jugador] = {'ronda': turno['ronda_n'], 'mis_descartes': []}
                
                memoria = memoria_jugadores[jugador]

                # SOLO nos importan los turnos donde el humano se descartó
                if turno['accion'] == 'descarte' and turno['detalles'] and 'cartas_tiradas' in turno['detalles']:
                    
                    # CORREGIDO: Eliminado el c['valor']
                    cartas_norm = [12 if c == 3 else 1 if c == 2 else c for c in turno['cartas_propias']]
                    c_ord = sorted(cartas_norm, reverse=True)
                    cat_pares, val_pares = evaluar_pares(cartas_norm)
                    estado_juego = calcular_valor_juego(cartas_norm)
                    
                    # Generamos el TARGET (La etiqueta a predecir, ej: "0011")
                    target_mask = crear_mascara_descarte(turno['cartas_propias'], turno['detalles']['cartas_tiradas'])
                    
                    # Cálculos simplificados
                    try:
                        prob_g = calcular_probabilidad_grande(turno['cartas_propias'], memoria['mis_descartes'], turno['es_mano']).get('prob_ganar', 0.0)
                        prob_c = calcular_probabilidad_chica(turno['cartas_propias'], memoria['mis_descartes'], turno['es_mano']).get('prob_ganar', 0.0)
                        prob_p = calcular_probabilidad_pares(turno['cartas_propias'], False, turno['es_mano'], memoria['mis_descartes']).get('prob_ganar', 0.0)
                        res_j = calcular_probabilidad_juego(turno['cartas_propias'], 0, False, turno['es_mano'], memoria['mis_descartes'])
                        prob_j = res_j.get('prob_ganar', 0.0) if isinstance(res_j, dict) else 0.0
                    except:
                        prob_g, prob_c, prob_p, prob_j = 0.0, 0.0, 0.0, 0.0

                    datos.append({
                        "es_mano": 1 if turno['es_mano'] else 0,
                        "c1": c_ord[0], "c2": c_ord[1], "c3": c_ord[2], "c4": c_ord[3],
                        "tengo_pares": 1 if cat_pares > 0 else 0,
                        "tipo_pares": cat_pares,
                        "tengo_juego": 1 if estado_juego['tiene_juego'] else 0,
                        "suma_puntos": estado_juego['suma'],
                        "prob_grande": prob_g, "prob_chica": prob_c,
                        "prob_pares": prob_p, "prob_juego": prob_j,
                        "target_mask": target_mask  # <--- Lo que la IA debe aprender
                    })
                    
                    memoria['mis_descartes'].extend(turno['detalles']['cartas_tiradas'])

    if not datos:
        print("❌ No se encontraron acciones de descarte válidas.")
        return

    df = pd.DataFrame(datos)
    print(f"📊 Entrenando Optimizador de Descartes con {len(df)} lances...")

    features = ['es_mano', 'c1', 'c2', 'c3', 'c4', 'tengo_pares', 'tipo_pares', 
                'tengo_juego', 'suma_puntos', 'prob_grande', 'prob_chica', 'prob_pares', 'prob_juego']
    
    X = df[features]
    y = df['target_mask']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Entrenar modelo
    modelo = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
    modelo.fit(X_train, y_train)

    predicciones = modelo.predict(X_test)
    precision = accuracy_score(y_test, predicciones)
    
    print(f"\n✅ Precisión al replicar tus descartes: {precision * 100:.2f}%")
    
    archivo_modelo = 'learn/models/modelo_descartes.pkl'
    joblib.dump(modelo, archivo_modelo)
    print(f"💾 Modelo guardado como '{archivo_modelo}'.")

if __name__ == '__main__':
    entrenar_modelo_descartes('logs_ia')  # Cambia esto por la carpeta donde tengas los logs de las partidas con descartes.
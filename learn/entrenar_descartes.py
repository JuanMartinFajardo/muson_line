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



def entrenar_modelo_descartes(csv_path):
    print(f"🔍 Cargando datos de descartes desde '{csv_path}'...")
    
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print(f"❌ Error: No se ha encontrado el archivo '{csv_path}'.")
        return

    df = df[df['gano_ronda'] == 1].copy()  # Nos quedamos solo con los lances donde el jugador ganó la ronda

    # 1. Filtrar solo las filas donde hubo un descarte
    # En tus logs puede aparecer como 'descarte' o 'descartar'
    df_desc = df[df['accion_realizada'].isin(['descarte', 'descartar'])].copy()
    
    # 2. Eliminar filas donde la máscara no se guardó correctamente
    df_desc = df_desc.dropna(subset=['mascara_descarte'])
    df_desc['mascara_descarte'] = df_desc['mascara_descarte'].astype(int).astype(str).str.zfill(4)
    
    if len(df_desc) == 0:
        print("❌ No hay datos suficientes de descartes en el CSV.")
        return

    print(f"📊 Entrenando Optimizador de Descartes con {len(df_desc)} lances...")

    # 3. Definir variables (Features) y la etiqueta (Target)
    features = [
        'es_mano', 'c1', 'c2', 'c3', 'c4', 
        'tengo_pares', 'tipo_pares', 'tengo_juego', 'suma_puntos', 
        'prob_grande', 'prob_chica', 'prob_pares', 'prob_juego'
    ]
    
    X = df_desc[features]
    y = df_desc['mascara_descarte']

    # 4. Dividir datos (80% entrenar, 20% examinar)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 5. Entrenar el modelo
    modelo = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
    modelo.fit(X_train, y_train)

    # 6. Evaluación
    predicciones = modelo.predict(X_test)
    precision = accuracy_score(y_test, predicciones)
    
    print(f"\n✅ Precisión al replicar tus descartes: {precision * 100:.2f}%")
    
    archivo_modelo = 'learn/models/modelo_descartes.pkl'
    joblib.dump(modelo, archivo_modelo)
    print(f"💾 Modelo guardado como '{archivo_modelo}'.")

if __name__ == '__main__':
    entrenar_modelo_descartes('logs_ia')  # Cambia esto por la carpeta donde tengas los logs de las partidas con descartes.
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib

def entrenar_modelo_apuestas(csv_path):
    print(f"🔍 Cargando datos de apuestas desde '{csv_path}'...")
    
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print(f"❌ Error: No se ha encontrado el archivo '{csv_path}'.")
        print("Asegúrate de ejecutar primero el generador masivo de datasets.")
        return

    # 1. Filtrar solo las fases de apuestas
    fases_apuesta = ['Grande', 'Chica', 'Pares', 'Juego']
    df_ap = df[df['fase'].isin(fases_apuesta)].copy()
    
    # Nos aseguramos de que solo haya acciones de apuesta válidas
    acciones_validas = ['pasar', 'envidar', 'ver', 'nover', 'subir', 'ordago']
    df_ap = df_ap[df_ap['accion_realizada'].isin(acciones_validas)]
    
    if len(df_ap) == 0:
        print("❌ No hay datos de apuestas suficientes en el CSV.")
        return

    # 2. Mapear la fase a un número para que la IA lo entienda matemáticamente
    mapa_fases = {'Grande': 1, 'Chica': 2, 'Pares': 3, 'Juego': 4}
    df_ap['fase_num'] = df_ap['fase'].map(mapa_fases)
    
    # Limpiamos posibles valores nulos
    df_ap = df_ap.fillna(0)

    # 3. Preparar variables (Las mismas 19 features que le pasará el bot en vivo)
    features = [
        'fase_num', 'es_mano', 'c1', 'c2', 'c3', 'c4', 
        'tengo_pares', 'tipo_pares', 'tengo_juego', 'suma_puntos',
        'descartes_rival', 'prob_grande', 'prob_chica', 'prob_pares', 'prob_juego',
        'bote_grande', 'bote_chica', 'bote_pares', 'subida_pendiente'
    ]
    
    X = df_ap[features]
    y = df_ap['accion_realizada']
    
    print(f"📊 Entrenando Gestor de Apuestas con {len(X)} decisiones...")

    # 4. Dividir en entrenamiento (80%) y test (20%)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 5. Entrenar el modelo (Aumentamos los árboles para que capte mejor el contexto)
    modelo = RandomForestClassifier(n_estimators=200, max_depth=12, random_state=42, class_weight='balanced')
    modelo.fit(X_train, y_train)

    # 6. Evaluación del modelo
    predicciones = modelo.predict(X_test)
    precision = accuracy_score(y_test, predicciones)
    
    print(f"\n✅ Precisión al replicar tus apuestas: {precision * 100:.2f}%")
    print(f"🧠 Clases aprendidas: {modelo.classes_}")
    
    print("\n--- Reporte de Clasificación ---")
    print(classification_report(y_test, predicciones, zero_division=0))

    # 7. Ver en qué se fija más la IA para apostar
    importancias = pd.DataFrame({'Variable': features, 'Importancia': modelo.feature_importances_})
    print("\n🧐 Top 7 Variables más importantes para la IA al apostar:")
    print(importancias.sort_values(by='Importancia', ascending=False).head(7).to_string(index=False))

    # 8. Guardar modelo
    archivo_modelo = 'learn/models/modelo_apuestas.pkl'
    joblib.dump(modelo, archivo_modelo)
    print(f"\n💾 Modelo final guardado como '{archivo_modelo}'.")

if __name__ == '__main__':
    # Usamos el CSV global compilado de todas tus partidas
    archivo_dataset = 'learn/datasets/compiled_dataset.csv'
    entrenar_modelo_apuestas(archivo_dataset)
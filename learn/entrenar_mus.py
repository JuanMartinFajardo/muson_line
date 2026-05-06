import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import joblib

def entrenar_modelo_mus(csv_path):
    # 1. Cargar el dataset
    df = pd.read_csv(csv_path)
    
    # 2. Filtrar solo las acciones de la fase de 'mus'
    df_mus = df[df['fase'] == 'mus'].copy()
    
    # Nos aseguramos de que solo haya 'mus' o 'no_mus'
    df_mus = df_mus[df_mus['accion_realizada'].isin(['mus', 'no_mus'])]
    
    if len(df_mus) == 0:
        print("❌ No hay datos suficientes de la fase de mus en el CSV.")
        return

    print(f"📊 Entrenando con {len(df_mus)} decisiones de Mus/No Mus...")

    # 3. Definir las variables de entrada (Features) y la salida (Target)
    # Convertimos la acción a números: mus = 0, no_mus = 1
    df_mus['target'] = df_mus['accion_realizada'].map({'mus': 0, 'no_mus': 1})
    
    # Seleccionamos las columnas que la IA usará para pensar
    features = [
        'es_mano', 'c1', 'c2', 'c3', 'c4', 
        'tengo_pares', 'tipo_pares', 'tengo_juego', 'suma_puntos',
        'descartes_rival', 'prob_grande', 'prob_chica', 'prob_pares', 'prob_juego'
    ]
    
    X = df_mus[features]
    y = df_mus['target']

    # 4. Dividir datos: 80% para estudiar, 20% para hacerle un examen a la IA
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 5. Crear y entrenar el modelo
    # n_estimators=100 significa que usará "100 árboles" para tomar la decisión
    modelo = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
    modelo.fit(X_train, y_train)

    # 6. Evaluar el modelo (El Examen)
    predicciones = modelo.predict(X_test)
    precision = accuracy_score(y_test, predicciones)
    
    print("\n✅ --- RESULTADOS DEL EXAMEN ---")
    print(f"Precisión global (Accuracy): {precision * 100:.2f}%")
    print("\nMatriz de Confusión:")
    print(confusion_matrix(y_test, predicciones))
    print("\nReporte Detallado:")
    print(classification_report(y_test, predicciones, target_names=['Da Mus (0)', 'Corta Mus (1)']))

    # 7. Ver qué le importa más a la IA
    importancias = modelo.feature_importances_
    resumen_importancias = pd.DataFrame({'Variable': features, 'Importancia': importancias})
    resumen_importancias = resumen_importancias.sort_values(by='Importancia', ascending=False)
    
    print("\n🧠 --- ¿EN QUÉ SE FIJA LA IA PARA DECIDIR? ---")
    print(resumen_importancias.head(7).to_string(index=False))

    # 8. Guardar el "cerebro" en un archivo
    archivo_modelo = 'learn/models/modelo_decisor_mus.pkl'
    joblib.dump(modelo, archivo_modelo)
    print(f"\n💾 Modelo guardado exitosamente como '{archivo_modelo}'.")

if __name__ == '__main__':
    entrenar_modelo_mus('learn/datasets/compiled_dataset.csv')
from learn.procesar_carpeta import compilar_dataset_global
from learn.entrenar_mus import entrenar_modelo_mus
from learn.entrenar_descartes import entrenar_modelo_descartes
from learn.entrenar_apuestas import entrenar_modelo_apuestas

def global_model_trainer(carpeta_datos,csv_path):
    # 1. Compilar el dataset global a partir de la carpeta de datos
    print("📂 Compilating the global dataset from the data folder...")
    #compilar_dataset_global(carpeta_datos, csv_path)
    
    # 2. Entrenar el modelo para decidir si se da Mus o no
    print("\n🎯 Training the model to decide whether to say Mus or not...")
    entrenar_modelo_mus(csv_path)
    
    # 3. Entrenar el modelo para decidir qué cartas descartar
    print("\n🎯 Training the model to decide which cards to discard...")
    entrenar_modelo_descartes(csv_path)
    
    # 4. Entrenar el modelo para decidir cuánto apostar
    print("\n🎯 Training the model to decide how much to bet...")
    entrenar_modelo_apuestas(csv_path)

if __name__ == "__main__":
    carpeta_datos = "logs"  # Cambia esto por la ruta a tu carpeta de datos
    csv_path = "learn/datasets/compiled_dataset.csv"  # Ruta donde se guardará el dataset global compilado
    global_model_trainer(carpeta_datos, csv_path)
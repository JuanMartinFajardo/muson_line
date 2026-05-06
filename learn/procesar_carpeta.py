import os
import glob
import pandas as pd
# Importamos la función maestra que creamos en el paso anterior.
# Asegúrate de que esa función está en un archivo llamado generar_dataset.py
from learn.dataset_generator import crear_dataset

def compilar_dataset_global(carpeta_logs, archivo_salida_global):
    """
    Busca todos los archivos .jsonl en 'carpeta_logs', extrae las features
    avanzadas (cartas, memoria, probabilidades) y los une en un solo CSV gigante.
    """
    print(f"🔍 Buscando logs en la carpeta: '{carpeta_logs}'...")
    
    # 1. Buscar todos los archivos .jsonl en el directorio
    patron_busqueda = os.path.join(carpeta_logs, '*.jsonl')
    archivos_jsonl = glob.glob(patron_busqueda)
    
    if not archivos_jsonl:
        print(f"❌ Error: No se encontraron archivos .jsonl en '{carpeta_logs}'.")
        return
        
    print(f"📁 Encontrados {len(archivos_jsonl)} archivos de partidas.")
    
    lista_dataframes = []
    
    # 2. Procesar archivo por archivo
    for ruta_archivo in archivos_jsonl:
        nombre_archivo = os.path.basename(ruta_archivo)
        print(f"  ⏳ Procesando {nombre_archivo}...")
        
        try:
            # Reutilizamos la función que ya tenemos, pero le decimos
            # que guarde un archivo temporal invisible. No necesitamos ese CSV intermedio,
            # lo que nos interesa es el DataFrame (df) que devuelve la función.
            df_partida = crear_dataset(ruta_archivo, 'temp_dummy.csv')
            
            # Añadimos una pequeña columna para saber de qué archivo vino (útil para debug)
            df_partida['origen_log'] = nombre_archivo
            
            lista_dataframes.append(df_partida)
        except Exception as e:
            print(f"  ⚠️ Error al procesar {nombre_archivo}: {e}")
            continue

    # Borramos el archivo temporal (limpieza)
    if os.path.exists('temp_dummy.csv'):
        os.remove('temp_dummy.csv')

    # 3. Unir todos los DataFrames en uno solo
    if lista_dataframes:
        df_global = pd.concat(lista_dataframes, ignore_index=True)
        
        # Guardar el mastodonte
        df_global.to_csv(archivo_salida_global, index=False)
        print("\n=======================================================")
        print(f"✅ ¡ÉXITO! Se han compilado {len(df_global)} lances en total.")
        print(f"💾 Guardado como: '{archivo_salida_global}'")
        print("=======================================================")
        return df_global
    else:
        print("❌ No se pudo extraer ningún dato válido de los archivos.")
        return None

if __name__ == '__main__':
    # Ruta de la carpeta donde tienes los .jsonl
    carpeta = 'logs'  # Cambia esto por el nombre de tu carpeta
    # Nombre del archivo final que usaremos para entrenar
    archivo_final = 'global_extended_dataset.csv'
    
    # Asegúrate de que la carpeta existe antes de ejecutar
    if not os.path.exists(carpeta):
        print(f"❌ Error: La carpeta '{carpeta}' no existe. Créala y mete los .jsonl dentro.")
    else:
        compilar_dataset_global(carpeta, archivo_final)
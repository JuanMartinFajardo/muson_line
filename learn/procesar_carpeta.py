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
    print(f"🔍 Searching for logs in folder: '{carpeta_logs}'...")
    
    # 1. Buscar todos los archivos .jsonl en el directorio
    patron_busqueda = os.path.join(carpeta_logs, '*.jsonl')
    archivos_jsonl = glob.glob(patron_busqueda)
    
    if not archivos_jsonl:
        print(f"❌ Error: No .jsonl files found in '{carpeta_logs}'.")
        return
        
    # --- 1. LÓGICA INCREMENTAL ---
    archivos_procesados = set()
    df_existente = None
    
    if os.path.exists(archivo_salida_global):
        print(f"📄 CSV global detectado. Leyendo historial...")
        df_existente = pd.read_csv(archivo_salida_global)
        if 'origen_log' in df_existente.columns:
            archivos_procesados = set(df_existente['origen_log'].unique())
            print(f"✅ There are {len(archivos_procesados)} logs that have already been processed previously.")
    
    # Filtramos para quedarnos solo con los archivos que NO están en el set
    archivos_a_procesar = [ruta for ruta in archivos_jsonl if os.path.basename(ruta) not in archivos_procesados]
    
    if not archivos_a_procesar:
        print("✨ No hay archivos nuevos. El dataset ya está 100% actualizado.")
        return df_existente
        
    print(f"📁 Found {len(archivos_a_procesar)} new files to process.")
    
    lista_dataframes = []
    
    # 2. Procesar solo los archivos nuevos
    for ruta_archivo in archivos_a_procesar:
        nombre_archivo = os.path.basename(ruta_archivo)
        print(f"  ⏳ Procesando {nombre_archivo}...")
        
        try:
            df_partida = crear_dataset(ruta_archivo, 'temp_dummy.csv')
            df_partida['origen_log'] = nombre_archivo
            lista_dataframes.append(df_partida)
        except Exception as e:
            print(f"  ⚠️ Error while processing {nombre_archivo}: {e}")
            continue

    if os.path.exists('temp_dummy.csv'):
        os.remove('temp_dummy.csv')

    # 3. Unir los datos viejos con los nuevos
    if lista_dataframes:
        df_nuevos = pd.concat(lista_dataframes, ignore_index=True)
        
        if df_existente is not None:
            df_global = pd.concat([df_existente, df_nuevos], ignore_index=True)
        else:
            df_global = df_nuevos
            
        df_global.to_csv(archivo_salida_global, index=False)
        print("\n=======================================================")
        print(f"✅ ¡Success!  {len(df_nuevos)} new lances added.")
        print(f"📊 Total historical in the CSV: {len(df_global)} lances.")
        print(f"💾 Saved as: '{archivo_salida_global}'")
        print("=======================================================")
        return df_global
    else:
        print("❌ No valid data was generated from the new files.")
        return df_existente
    

if __name__ == '__main__':
    # Ruta de la carpeta donde tienes los .jsonl
    carpeta = 'logs'  # Cambia esto por el nombre de tu carpeta
    # Nombre del archivo final que usaremos para entrenar
    archivo_final = 'global_extended_dataset.csv'
    
    # Asegúrate de que la carpeta existe antes de ejecutar
    if not os.path.exists(carpeta):
        print(f"❌ Error: Folder '{carpeta}' does not exist. Create it and place the .jsonl files inside.")
    else:
        compilar_dataset_global(carpeta, archivo_final)
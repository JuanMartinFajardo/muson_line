import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import random
from collections import deque

# ==========================================
# 1. ARQUITECTURA DE LAS REDES NEURONALES
# ==========================================

class RegretNetwork(nn.Module):
    """
    Esta red predice el 'Arrepentimiento'. 
    Input: El estado de la mesa.
    Output: 6 números reales (uno por cada acción). Un número alto significa 
    'Me arrepentiría mucho de no haber tomado esta acción'.
    """
    def __init__(self, input_size, output_size=6):
        super(RegretNetwork, self).__init__()
        # 3 capas ocultas densas. 128 neuronas es suficiente para el Mus.
        self.fc1 = nn.Linear(input_size, 128)
        self.fc2 = nn.Linear(128, 128)
        self.fc3 = nn.Linear(128, 128)
        self.salida = nn.Linear(128, output_size)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = F.relu(self.fc3(x))
        return self.salida(x) # Sin activación final porque el arrepentimiento puede ser negativo

class StrategyNetwork(nn.Module):
    """
    Esta red es tu bot final. Predice la probabilidad de usar cada farol/jugada.
    Input: El estado de la mesa.
    Output: 6 porcentajes (suman 1.0).
    """
    def __init__(self, input_size, output_size=6):
        super(StrategyNetwork, self).__init__()
        self.fc1 = nn.Linear(input_size, 128)
        self.fc2 = nn.Linear(128, 128)
        self.fc3 = nn.Linear(128, 128)
        self.salida = nn.Linear(128, output_size)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = F.relu(self.fc3(x))
        # Usamos Softmax para que las salidas sean probabilidades (ej: 0.1, 0.8, 0.1...)
        return F.softmax(self.salida(x), dim=-1)

# ==========================================
# 2. TRANSFORMADOR DE ESTADO (Information Set -> Tensor)
# ==========================================

def estado_a_vector(estado_dict):
    """
    Convierte el diccionario que escupe el entorno en un vector matemático para la Red.
    Normalizamos un poco los valores para que a la red le cueste menos aprender.
    """
    vector = [
        estado_dict['es_mano'],
        estado_dict['cartas'][0] / 12.0, 
        estado_dict['cartas'][1] / 12.0,
        estado_dict['cartas'][2] / 12.0,
        estado_dict['cartas'][3] / 12.0,
        estado_dict['indice_fase'] / 3.0,
        estado_dict['subida_pendiente'] / 40.0,
        estado_dict['bote_grande'] / 40.0,
        estado_dict['bote_chica'] / 40.0,
        estado_dict['bote_pares'] / 40.0,
        estado_dict['apuesta_vista'] / 40.0,
        # --- VARIABLES DE CONTEXTO ---
        estado_dict['puntos_propios'] / 40.0,
        estado_dict['puntos_rival'] / 40.0,
        min(estado_dict['rondas_mus'] / 5.0, 1.0), # Tope normalizado en 5 rondas
        estado_dict['descartes_rival'] / 4.0,
        estado_dict['owner_grande'], # Ya vendrá como 0.0, 0.5 o 1.0
        estado_dict['owner_chica'],
        estado_dict['owner_pares']
    ]
    # Devolvemos un tensor de PyTorch (1 fila, 11 columnas)
    return torch.tensor([vector], dtype=torch.float32)

# ==========================================
# 3. MEMORIAS (REPLAY BUFFERS)
# ==========================================

# ==========================================
# 3. MEMORIAS (REPLAY BUFFERS) - RESERVOIR SAMPLING
# ==========================================

class ReplayBuffer:
    """
    Memoria con Reservoir Sampling. Garantiza que la red neuronal 
    haga la media de toda su vida de entrenamiento sin colapsar la RAM.
    """
    def __init__(self, capacidad=200000): # Aumentamos un poco la capacidad general
        self.capacidad = capacidad
        self.buffer = []
        self.items_vistos = 0 # Contador histórico absoluto
    
    def guardar(self, info_vector, target_vector, iteracion):
        self.items_vistos += 1
        tupla_datos = (info_vector, target_vector, iteracion)
        
        # Si hay hueco, lo metemos normal
        if len(self.buffer) < self.capacidad:
            self.buffer.append(tupla_datos)
        else:
            # RESERVOIR SAMPLING: Tiramos un dado matemático.
            # A medida que el entrenamiento avanza, es más difícil que un 
            # nuevo recuerdo sobrescriba a uno antiguo, preservando la memoria a largo plazo.
            j = random.randint(0, self.items_vistos - 1)
            if j < self.capacidad:
                self.buffer[j] = tupla_datos
        
    def sample(self, batch_size):
        lote = random.sample(self.buffer, min(batch_size, len(self.buffer)))
        
        estados = torch.cat([item[0] for item in lote])
        targets = torch.stack([torch.tensor(item[1], dtype=torch.float32) for item in lote])
        pesos = torch.tensor([item[2] for item in lote], dtype=torch.float32).unsqueeze(1)
        
        return estados, targets, pesos
        
    def __len__(self):
        return len(self.buffer)
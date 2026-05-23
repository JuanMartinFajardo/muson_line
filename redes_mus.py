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
        estado_dict['cartas'][0] / 12.0, # Normalizamos de 1 a 12 -> 0.0 a 1.0
        estado_dict['cartas'][1] / 12.0,
        estado_dict['cartas'][2] / 12.0,
        estado_dict['cartas'][3] / 12.0,
        estado_dict['indice_fase'] / 3.0, # 0, 1, 2, 3
        estado_dict['subida_pendiente'] / 40.0,
        estado_dict['bote_grande'] / 40.0,
        estado_dict['bote_chica'] / 40.0,
        estado_dict['bote_pares'] / 40.0,
        estado_dict['apuesta_vista'] / 40.0
    ]
    # Devolvemos un tensor de PyTorch (1 fila, 11 columnas)
    return torch.tensor([vector], dtype=torch.float32)

# ==========================================
# 3. MEMORIAS (REPLAY BUFFERS)
# ==========================================

class ReplayBuffer:
    """
    Una lista gigante que borra lo más antiguo cuando se llena.
    Almacena las experiencias del bot para entrenar a las redes en lotes.
    """
    def __init__(self, capacidad=500000):
        self.buffer = deque(maxlen=capacidad)
    
    def guardar(self, info_vector, target_vector, iteracion):
        # Guardamos: [El vector del estado, La respuesta correcta, Peso por iteración]
        self.buffer.append((info_vector, target_vector, iteracion))
        
    def sample(self, batch_size):
        # Saca una muestra aleatoria para entrenar (ej: 1024 jugadas a la vez)
        lote = random.sample(self.buffer, min(batch_size, len(self.buffer)))
        
        estados = torch.cat([item[0] for item in lote])
        targets = torch.stack([torch.tensor(item[1], dtype=torch.float32) for item in lote])
        pesos = torch.tensor([item[2] for item in lote], dtype=torch.float32).unsqueeze(1)
        
        return estados, targets, pesos
        
    def __len__(self):
        return len(self.buffer)
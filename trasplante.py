import torch
from redes_mus import StrategyNetwork, RegretNetwork

# 1. Cargar el modelo antiguo (Asegúrate de poner el nombre de tu archivo real de 11 vars)
viejo_estado_strategy = torch.load('deep_cfr_mus_bot_iter_1000.pth')

# 2. Crear las redes nuevas con 18 inputs
nueva_strategy = StrategyNetwork(input_size=18)
nuevo_estado_strategy = nueva_strategy.state_dict()

# 3. CIRUGÍA: Copiar pesos de la primera capa
# viejo_estado['fc1.weight'] tiene forma [128, 11]
# nuevo_estado['fc1.weight'] tiene forma [128, 18]
nuevo_estado_strategy['fc1.weight'][:, :11] = viejo_estado_strategy['fc1.weight']
nuevo_estado_strategy['fc1.bias'] = viejo_estado_strategy['fc1.bias']

# 4. Copiar el resto de las capas ocultas (son estructuralmente idénticas)
capas_comunes = ['fc2.weight', 'fc2.bias', 'fc3.weight', 'fc3.bias', 'salida.weight', 'salida.bias']
for capa in capas_comunes:
    nuevo_estado_strategy[capa] = viejo_estado_strategy[capa]

# 5. Aplicar y guardar
nueva_strategy.load_state_dict(nuevo_estado_strategy)
torch.save(nueva_strategy.state_dict(), 'deep_cfr_1000_recycled_18.pth')

print("🧠 ¡Trasplante completado! Tienes un modelo de 18 variables pre-entrenado.")
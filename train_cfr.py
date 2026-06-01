import torch
import torch.nn.functional as F
import random
import time
from mus_env import MusBettingEnv
from redes_mus import RegretNetwork, StrategyNetwork, ReplayBuffer, estado_a_vector
import os
from torch.utils.tensorboard import SummaryWriter


# ==========================================
# HYPERPARAMETERS
# ==========================================
ITERATIONS = 5_000  # Number of outer loops
TRAVERSALS_PER_ITER = 1_000  # Games played per iteration
BATCH_SIZE = 1024
LEARNING_RATE = 0.001

GENERATION_NAME = 'cfr5'

# Action string to index mapping
ACTION_MAP = {'pasar': 0, 'envidar': 1, 'ver': 2, 'nover': 3, 'subir': 4, 'ordago': 5}

# Initialize networks and buffers
input_size = 18
regret_net = RegretNetwork(input_size)
strategy_net = StrategyNetwork(input_size)

regret_buffer = ReplayBuffer(capacidad=100000)
strategy_buffer = ReplayBuffer(capacidad=100000)

optimizer_regret = torch.optim.Adam(regret_net.parameters(), lr=LEARNING_RATE)
optimizer_strategy = torch.optim.Adam(strategy_net.parameters(), lr=LEARNING_RATE)

def get_strategy_from_regret(info_vector, valid_indices):
    """
    Applies Regret Matching: Positive regrets become probabilities.
    """
    with torch.no_grad():
        regrets = regret_net(info_vector).squeeze(0)
    
    positive_regrets = torch.zeros(6)
    for idx in valid_indices:
        positive_regrets[idx] = max(0.0, regrets[idx].item())
        
    sum_regrets = positive_regrets.sum().item()
    strategy = torch.zeros(6)
    
    if sum_regrets > 0:
        strategy = positive_regrets / sum_regrets
    else:
        # If no positive regret, play random valid action
        max_regret = -float('inf')
        best_idx = valid_indices[0]
        for idx in valid_indices:
            if regrets[idx].item() > max_regret:
                max_regret = regrets[idx].item()
                best_idx = idx
        strategy[best_idx] = 1.0
            
    return strategy

def traverse(env, traversing_player, t):
    """
    Recursively travels the game tree.
    Returns the expected value (EV) of the node.
    """
    # 1. Caso Base: Nodo Terminal
    if env.partida.fase == 'recuento':
        env.partida.calcular_recuento()
        points_me = env.partida.estado[traversing_player]['puntos']
        opponent = "IA_2" if traversing_player == "IA_1" else "IA_1"
        points_opp = env.partida.estado[opponent]['puntos']
        
        # CORRECCIÓN 3: Normalizamos la recompensa entre -1 y 1
        return float(points_me - points_opp) / 40.0

    # 2. Información del estado actual
    current_player = env.partida.turno_de
    info_dict = env.get_information_set()
    info_vector = estado_a_vector(info_dict)
    
    valid_actions_str = env.get_valid_actions()
    valid_indices = [ACTION_MAP[a] for a in valid_actions_str]
    
    strategy = get_strategy_from_regret(info_vector, valid_indices)

    # ---------------------------------------------------------
    # NODO A: Turno del jugador que explora el árbol
    # ---------------------------------------------------------
    if current_player == traversing_player:
        
        # CORRECCIÓN 2: ¡YA NO GUARDAMOS LA ESTRATEGIA AQUÍ!
        
        action_values = torch.zeros(6)
        node_value = 0.0
        
        for a_str, a_idx in zip(valid_actions_str, valid_indices):
            cloned_env = env.clone()
            _, _, done = cloned_env.step(a_str)
            
            expected_value = traverse(cloned_env, traversing_player, t)
            action_values[a_idx] = expected_value
            node_value += strategy[a_idx].item() * expected_value
            
        regrets = torch.zeros(6)
        for a_idx in valid_indices:
            regrets[a_idx] = action_values[a_idx] - node_value
            
        regret_buffer.guardar(info_vector, regrets.numpy(), t)
        return node_value

    # ---------------------------------------------------------
    # NODO B: Turno del Oponente
    # ---------------------------------------------------------
    else:
        # CORRECCIÓN 2: La estrategia se guarda EXCLUSIVAMENTE en el turno del rival
        strategy_buffer.guardar(info_vector, strategy.numpy(), t)
        
        probs = [strategy[i].item() for i in valid_indices]
        chosen_idx = random.choices(valid_indices, weights=probs, k=1)[0]
        
        chosen_str = None
        for string_action, index in ACTION_MAP.items():
            if index == chosen_idx:
                chosen_str = string_action
                break
                
        cloned_env = env.clone()
        cloned_env.step(chosen_str)
        
        return traverse(cloned_env, traversing_player, t)


def train_networks(T_actual):
    loss_fn = torch.nn.MSELoss()
    
    # Train Regret Network
    if len(regret_buffer) >= BATCH_SIZE:
        states, targets, weights = regret_buffer.sample(BATCH_SIZE)
        
        # LCFR: Reescalar los pesos por 2/T
        weights = weights * (2.0 / T_actual)
        
        optimizer_regret.zero_grad()
        predictions = regret_net(states)
        loss_regret = (weights * (predictions - targets)**2).mean()
        loss_regret.backward()
        optimizer_regret.step()
        l_regret = loss_regret.item()
        
    # Train Strategy Network (Misca lógica)
    if len(strategy_buffer) >= BATCH_SIZE:
        states, targets, weights = strategy_buffer.sample(BATCH_SIZE)
        weights = weights * (2.0 / T_actual)
        
        optimizer_strategy.zero_grad()
        predictions = strategy_net(states)
        loss_strategy = (weights * (predictions - targets)**2).mean()
        loss_strategy.backward()
        optimizer_strategy.step()
        l_strategy = loss_strategy.item()

    return l_regret, l_strategy




# --- LÓGICA DE RESUMEN DE ENTRENAMIENTO ---
start_iteration = 1
ruta_checkpoint = "learn/cfr/checkpoint_mus_cfr5_latest.pth"

writer = SummaryWriter(log_dir="learn/cfr/runs/mus_experiment")

if os.path.exists(ruta_checkpoint):
    print("🔄 Se ha detectado un entrenamiento pausado. Restaurando...")
    checkpoint = torch.load(ruta_checkpoint)
    
    # Restaurar redes
    regret_net.load_state_dict(checkpoint['regret_net_state'])
    strategy_net.load_state_dict(checkpoint['strategy_net_state'])
    
    # Restaurar optimizadores
    optimizer_regret.load_state_dict(checkpoint['optimizer_regret_state'])
    optimizer_strategy.load_state_dict(checkpoint['optimizer_strategy_state'])
    
    start_iteration = checkpoint['iteration'] + 1
    print(f"✅ Reanudando desde la iteración {start_iteration}...")
else:
    # Si no hay checkpoint maestro, vemos si al menos tenemos el "Trasplante" inicial
    ruta_trasplante = 'learn/cfr/deep_cfr_mus_bot_iter_1000.pth'
    if os.path.exists(ruta_trasplante):
        strategy_net.load_state_dict(torch.load(ruta_trasplante))
        print("💉 Empezando desde iteración 1, pero usando pesos trasplantados de la v11.")

# ==========================================
# MAIN TRAINING LOOP
# ==========================================
if __name__ == "__main__":
    print("🚀 Starting Deep CFR Training...")
    start_time = time.time()
    # Cambiar el range para que empiece donde toca
    for iteration in range(start_iteration, ITERATIONS + 1):
        print(f"--- Iteration {iteration}/{ITERATIONS} ---")
        start_it_time = time.time()
        
        # 1. Generate Data (Self-Play)
        for p in ["IA_1", "IA_2"]:
            for _ in range(TRAVERSALS_PER_ITER):
                env = MusBettingEnv()
                env.reset()
                traverse(env, traversing_player=p, t=iteration)
                
        regret_net = RegretNetwork(input_size)
        optimizer_regret = torch.optim.Adam(regret_net.parameters(), lr=LEARNING_RATE)
        # 2. Train Networks
        print(f"🧠 Training networks... (Buffers: {len(regret_buffer)} regrets, {len(strategy_buffer)} strategies)")
        total_loss_r = 0.0
        total_loss_s = 0.0
        n_steps = 2_000  # Number of gradient steps per iteration
        for _ in range(n_steps): # Multiple gradient steps per iteration
            l_r, l_s = train_networks(iteration)
            total_loss_r += l_r
            total_loss_s += l_s
            
        avg_loss_r = total_loss_r / n_steps
        avg_loss_s = total_loss_s / n_steps

        writer.add_scalar('Loss/Regret', avg_loss_r, iteration)
        writer.add_scalar('Loss/Strategy', avg_loss_s, iteration)

        print(f"📊 Loss Regret: {avg_loss_r:.5f} | Loss Strategy: {avg_loss_s:.5f}")

        print(f"Iteration competed in {round(time.time()-start_it_time)} seconds")
        if iteration % 25 == 0:
            checkpoint = {
                'iteration': iteration,
                'regret_net_state': regret_net.state_dict(),
                'strategy_net_state': strategy_net.state_dict(),
                'optimizer_regret_state': optimizer_regret.state_dict(),
                'optimizer_strategy_state': optimizer_strategy.state_dict()
            }
            torch.save(checkpoint, f"learn/cfr/checkpoint_mus_{GENERATION_NAME}_latest.pth")
            if iteration % 50 == 0: torch.save(strategy_net.state_dict(), f"learn/cfr/deep_cfr_mus_bot_{GENERATION_NAME}_iter_{iteration}.pth")
            print(f"💾 Checkpoint maestro guardado en la iteración {iteration}")
            

            
    end_time = time.time()
    print(f"✅ Training completed in {(end_time - start_time)/60:.2f} minutes.")
    
    # Save the final Strategy Network (This is our final bot!)
    torch.save(strategy_net.state_dict(), f"learn/cfr/deep_cfr_mus_bot_{GENERATION_NAME}_{ITERATIONS}.pth")
    print(f"💾 Final bot saved as 'learn/cfr/deep_cfr_mus_bot_{GENERATION_NAME}_{ITERATIONS}.pth'.")
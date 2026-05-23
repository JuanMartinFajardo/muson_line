import torch
import torch.nn.functional as F
import random
import time
from mus_env import MusBettingEnv
from redes_mus import RegretNetwork, StrategyNetwork, ReplayBuffer, estado_a_vector

# ==========================================
# HYPERPARAMETERS
# ==========================================
ITERATIONS = 100  # Number of outer loops
TRAVERSALS_PER_ITER = 500  # Games played per iteration
BATCH_SIZE = 1024
LEARNING_RATE = 0.001

# Action string to index mapping
ACTION_MAP = {'pasar': 0, 'envidar': 1, 'ver': 2, 'nover': 3, 'subir': 4, 'ordago': 5}

# Initialize networks and buffers
input_size = 11
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
        num_valid = len(valid_indices)
        for idx in valid_indices:
            strategy[idx] = 1.0 / num_valid
            
    return strategy

def traverse(env, traversing_player, t):
    """
    Recursively travels the game tree.
    Returns the expected value (EV) of the node.
    """
    # 1. Base case: Terminal node (End of round)
    if env.partida.fase == 'recuento':
        env.partida.calcular_recuento()
        points_me = env.partida.estado[traversing_player]['puntos']
        opponent = "IA_2" if traversing_player == "IA_1" else "IA_1"
        points_opp = env.partida.estado[opponent]['puntos']
        
        # In zero-sum games, the reward is the difference in points
        return float(points_me - points_opp)

    # 2. Get current state information
    current_player = env.partida.turno_de
    info_dict = env.get_information_set()
    info_vector = estado_a_vector(info_dict)
    
    valid_actions_str = env.get_valid_actions()
    valid_indices = [ACTION_MAP[a] for a in valid_actions_str]
    
    # 3. Get current policy from Regret Network
    strategy = get_strategy_from_regret(info_vector, valid_indices)

    # ---------------------------------------------------------
    # NODE A: It's the Traversing Player's turn
    # We explore ALL valid actions to calculate regret
    # ---------------------------------------------------------
    if current_player == traversing_player:
        
        # Save strategy to buffer for later training
        strategy_buffer.guardar(info_vector, strategy.numpy(), t)
        
        action_values = torch.zeros(6)
        node_value = 0.0
        
        for a_str, a_idx in zip(valid_actions_str, valid_indices):
            cloned_env = env.clone()
            _, _, done = cloned_env.step(a_str)
            
            # Recursive call
            expected_value = traverse(cloned_env, traversing_player, t)
            action_values[a_idx] = expected_value
            node_value += strategy[a_idx].item() * expected_value
            
        # Calculate regret for each action and store it
        regrets = torch.zeros(6)
        for a_idx in valid_indices:
            regrets[a_idx] = action_values[a_idx] - node_value
            
        regret_buffer.guardar(info_vector, regrets.numpy(), t)
        return node_value

    # ---------------------------------------------------------
    # NODE B: It's the Opponent's turn
    # We sample ONLY ONE action to keep the tree small
    # ---------------------------------------------------------
    else:
        probs = [strategy[i].item() for i in valid_indices]
        
        # Sample one action based on probabilities
        chosen_idx = random.choices(valid_indices, weights=probs, k=1)[0]
        
        chosen_str = None
        for string_action, index in ACTION_MAP.items():
            if index == chosen_idx:
                chosen_str = string_action
                break
                
        cloned_env = env.clone()
        cloned_env.step(chosen_str)
        
        return traverse(cloned_env, traversing_player, t)


def train_networks():
    """Trains both neural networks using the replay buffers."""
    loss_fn = torch.nn.MSELoss()
    
    # Train Regret Network
    if len(regret_buffer) >= BATCH_SIZE:
        states, targets, weights = regret_buffer.sample(BATCH_SIZE)
        optimizer_regret.zero_grad()
        predictions = regret_net(states)
        
        # Weight the loss by 't' (later iterations matter more)
        loss_regret = (weights * (predictions - targets)**2).mean()
        loss_regret.backward()
        optimizer_regret.step()
        
    # Train Strategy Network
    if len(strategy_buffer) >= BATCH_SIZE:
        states, targets, weights = strategy_buffer.sample(BATCH_SIZE)
        optimizer_strategy.zero_grad()
        predictions = strategy_net(states)
        
        loss_strategy = (weights * (predictions - targets)**2).mean()
        loss_strategy.backward()
        optimizer_strategy.step()

# ==========================================
# MAIN TRAINING LOOP
# ==========================================
if __name__ == "__main__":
    print("🚀 Starting Deep CFR Training...")
    start_time = time.time()
    
    for iteration in range(1, ITERATIONS + 1):
        print(f"--- Iteration {iteration}/{ITERATIONS} ---")
        
        # 1. Generate Data (Self-Play)
        for p in ["IA_1", "IA_2"]:
            for _ in range(TRAVERSALS_PER_ITER):
                env = MusBettingEnv()
                env.reset()
                traverse(env, traversing_player=p, t=iteration)
                
        # 2. Train Networks
        print(f"🧠 Training networks... (Buffers: {len(regret_buffer)} regrets, {len(strategy_buffer)} strategies)")
        for _ in range(50): # Multiple gradient steps per iteration
            train_networks()
            
    end_time = time.time()
    print(f"✅ Training completed in {(end_time - start_time)/60:.2f} minutes.")
    
    # Save the final Strategy Network (This is our final bot!)
    torch.save(strategy_net.state_dict(), "deep_cfr_mus_bot2.pth")
    print("💾 Final bot saved as 'deep_cfr_mus_bot2.pth'.")
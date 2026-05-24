import math
import itertools
from collections import Counter
import json


def simplify_to_bucket(card):
    """
    Maps a card to its representative bucket for the fast-draw approximation.
    - Kings / 3s -> 12
    - Knights / Sotas -> 10
    - 7, 6, 5, 4 -> 5
    - Aces / 2s -> 1
    """
    if card in [3, 12]: return 12
    if card in [10, 11]: return 10
    if card in [4, 5, 6, 7]: return 5
    if card in [1, 2]: return 1
    return card

def get_best_discard_strategy(my_hand, ev_lookup_table, am_i_mano=True, known_out_cards=None):
    """
    Evaluates all 16 possible discard actions (from keeping all to discarding all)
    using bucketed probabilities to maximize the Expected Value (EV).
    
    my_hand: List of 4 integers (e.g., [12, 11, 4, 1])
    ev_lookup_table: Dictionary loaded from 'mus_data.json' -> 'expected_values'
    """
    if known_out_cards is None:
        known_out_cards = []
        
    # 1. Normalize current hand and known discarded cards
    my_hand_norm = [12 if c == 3 else 1 if c == 2 else c for c in my_hand]
    out_norm = [12 if c == 3 else 1 if c == 2 else c for c in known_out_cards]
    
    # 2. Build the remaining bucketed deck
    deck_buckets = {12: 8, 10: 8, 5: 16, 1: 8}
    for c in my_hand_norm + out_norm:
        bucket = simplify_to_bucket(c)
        if deck_buckets[bucket] > 0:
            deck_buckets[bucket] -= 1
            
    total_remaining_cards = sum(deck_buckets.values())
    ev_index = 0 if am_i_mano else 1
    
    best_ev = -float('inf')
    best_action = None
    all_evaluations = []

    # 3. Iterate through all possible discard combinations (0 to 4 cards)
    # We use indices (0 to 3) to handle duplicate cards safely.
    for num_to_discard in range(5):
        for discard_indices in itertools.combinations(range(4), num_to_discard):
            
            kept_cards = [my_hand_norm[i] for i in range(4) if i not in discard_indices]
            discarded_cards = [my_hand_norm[i] for i in discard_indices]
            
            expected_ev_for_action = 0.0
            
            # --- BASE CASE: Standing Pat (Discarding 0) ---
            if num_to_discard == 0:
                hand_key = str(sorted(my_hand_norm, reverse=True))
                # Fallback to 0.0 if hand somehow isn't in dict
                expected_ev_for_action = ev_lookup_table.get(hand_key, [0.0, 0.0])[ev_index]
                
            # --- DRAW CASE: Discarding 1 to 4 cards ---
            else:
                valid_buckets = [b for b, count in deck_buckets.items() if count > 0]
                total_draw_ways = math.comb(total_remaining_cards, num_to_discard)
                
                # Generate all mathematical draws from the 4 buckets
                for draw_combo in itertools.combinations_with_replacement(valid_buckets, num_to_discard):
                    draw_counts = Counter(draw_combo)
                    
                    is_possible = True
                    ways_to_draw = 1
                    for bucket, count in draw_counts.items():
                        if count > deck_buckets[bucket]:
                            is_possible = False
                            break
                        ways_to_draw *= math.comb(deck_buckets[bucket], count)
                        
                    if not is_possible:
                        continue
                        
                    draw_probability = ways_to_draw / total_draw_ways
                    
                    # Construct future hand. 
                    # The drawn buckets (12, 10, 5, 1) directly map to representative cards in our EV dictionary.
                    future_hand = kept_cards + list(draw_combo)
                    
                    # The JSON keys are stringified lists sorted in descending order: e.g., "[12, 12, 10, 5]"
                    future_hand_sorted = sorted(future_hand, reverse=True)
                    hand_key = str(future_hand_sorted)
                    
                    # Fetch the precalculated EV array and select Mano/Postre
                    future_ev = ev_lookup_table.get(hand_key, [0.0, 0.0])[ev_index]
                    
                    expected_ev_for_action += future_ev * draw_probability
                    
            # 4. Save and track the best action
            all_evaluations.append({
                "discarded": discarded_cards,
                "kept": kept_cards,
                "expected_ev": round(expected_ev_for_action, 5)
            })
            
            if expected_ev_for_action > best_ev:
                best_ev = expected_ev_for_action
                best_action = {
                    "discard": discarded_cards,
                    "keep": kept_cards,
                    "ev": round(best_ev, 5)
                }

    # Sort all evaluations by EV descending so the neural network/logs can easily inspect them
    all_evaluations.sort(key=lambda x: x["expected_ev"], reverse=True)
    
    return {
        "best_action": best_action,
        "all_evaluations": all_evaluations
    }



# ==========================================
# CORE MUS LOGIC
# ==========================================

def evaluate_pairs(hand):
    """Returns (Category, (Values)). Categories: 3=Duplex, 2=Trio, 1=Pair, 0=None"""
    counts = Counter(hand)
    pairs = [(count, card) for card, count in counts.items() if count >= 2]
    if not pairs:
        return (0, (0,))
    
    pairs.sort(key=lambda x: (x[0], x[1]), reverse=True)
    if pairs[0][0] == 4:
        return (3, (pairs[0][1], pairs[0][1]))
    elif len(pairs) == 2 and pairs[0][0] == 2 and pairs[1][0] == 2:
        return (3, (pairs[0][1], pairs[1][1]))
    elif pairs[0][0] == 3:
        return (2, (pairs[0][1],))
    elif pairs[0][0] == 2:
        return (1, (pairs[0][1],))

def evaluate_game(hand):
    """Calculates the sum, rank, and base stone value of the game/punto."""
    hand_sum = sum([10 if c >= 10 else c for c in hand])
    is_real = (hand.count(7) == 3 and hand.count(10) == 1)
    
    if hand_sum >= 31:
        rank = 9 if is_real else {31: 8, 32: 7, 40: 6, 37: 5, 36: 4, 35: 3, 34: 2, 33: 1}.get(hand_sum, 0)
        return {"has_game": True, "sum": hand_sum, "rank": rank, "value": 3 if hand_sum == 31 else 2}
    else:
        return {"has_game": False, "sum": hand_sum, "rank": hand_sum, "value": 0} 

def generate_draws(num_cards, available_deck):
    """Mathematical generator for permutations."""
    if num_cards == 0:
        yield (), 1
        return
        
    valid_cards = [c for c, count in available_deck.items() if count > 0]
    for combo in itertools.combinations_with_replacement(valid_cards, num_cards):
        counts = Counter(combo)
        is_valid = True
        ways = 1
        for card, amount in counts.items():
            if amount > available_deck[card]:
                is_valid = False
                break
            ways *= math.comb(available_deck[card], amount)
        if is_valid:
            yield combo, ways

# ==========================================
# META-VARIABLES & PROBABILITIES
# ==========================================

def calculate_global_constants():
    """Calculates exact prior probabilities of rival hands from a fresh 40-card deck."""
    deck = {12: 8, 11: 4, 10: 4, 7: 4, 6: 4, 5: 4, 4: 4, 1: 8}
    total_hands = 0
    stats = {'pair': 0, 'trio': 0, 'duplex': 0, '31': 0, '>31': 0}

    for combo, ways in generate_draws(4, deck):
        total_hands += ways
        
        cat, _ = evaluate_pairs(combo)
        if cat == 1: stats['pair'] += ways
        elif cat == 2: stats['trio'] += ways
        elif cat == 3: stats['duplex'] += ways

        g_state = evaluate_game(combo)
        if g_state["has_game"]:
            if g_state["sum"] == 31: stats['31'] += ways
            else: stats['>31'] += ways

    prob_rival_pares = (stats['pair'] + stats['trio'] + stats['duplex']) / total_hands
    prob_rival_juego = (stats['31'] + stats['>31']) / total_hands

    return {
        "prob_rival_par": stats['pair'] / total_hands,
        "prob_rival_trio": stats['trio'] / total_hands,
        "prob_rival_duplex": stats['duplex'] / total_hands,
        "prob_rival_31": stats['31'] / total_hands,
        "prob_rival_no_31": stats['>31'] / total_hands,
        "prob_rival_pares": prob_rival_pares,
        "prob_rival_juego": prob_rival_juego
    }

def calculate_hand_probabilities(my_hand, am_i_mano):
    """
    Calculates exact win probabilities for a specific hand against the remaining 36 cards.
    Returns: [p_win_grande, p_win_chica, p_win_pares, p_win_juego]
    """
    deck = {12: 8, 11: 4, 10: 4, 7: 4, 6: 4, 5: 4, 4: 4, 1: 8}
    for c in my_hand:
        deck[c] -= 1
        
    my_g = my_hand
    my_c = sorted(my_hand)
    my_p_cat, my_p_val = evaluate_pairs(my_hand)
    my_j_state = evaluate_game(my_hand)

    wins_g, total_g = 0, 0
    wins_c, total_c = 0, 0
    wins_p, total_p_disputes = 0, 0
    wins_j, total_j_disputes = 0, 0

    for rival_hand, ways in generate_draws(4, deck):
        total_g += ways
        total_c += ways
        
        riv_g = sorted(rival_hand, reverse=True)
        riv_c = sorted(rival_hand)
        riv_p_cat, riv_p_val = evaluate_pairs(rival_hand)
        riv_j_state = evaluate_game(rival_hand)
        
        # Grande
        for m, r in zip(my_g, riv_g):
            if m > r: wins_g += ways; break
            elif m < r: break
        else:
            if am_i_mano: wins_g += ways
                
        # Chica
        for m, r in zip(my_c, riv_c):
            if m < r: wins_c += ways; break
            elif m > r: break
        else:
            if am_i_mano: wins_c += ways
                
        # Pares (ONLY against hands that actually HAVE pares)
        if riv_p_cat > 0:
            total_p_disputes += ways
            if my_p_cat > riv_p_cat: wins_p += ways
            elif my_p_cat == riv_p_cat:
                if my_p_val > riv_p_val: wins_p += ways
                elif my_p_val == riv_p_val and am_i_mano: wins_p += ways

        # Juego/Punto (ONLY against hands in the SAME phase)
        if my_j_state["has_game"] == riv_j_state["has_game"]:
            total_j_disputes += ways
            if my_j_state["rank"] > riv_j_state["rank"]: wins_j += ways
            elif my_j_state["rank"] == riv_j_state["rank"] and am_i_mano: wins_j += ways

    p_win_g = wins_g / total_g
    p_win_c = wins_c / total_c
    p_win_p = (wins_p / total_p_disputes) if total_p_disputes > 0 else 0.0
    p_win_j = (wins_j / total_j_disputes) if total_j_disputes > 0 else 0.0

    return [p_win_g, p_win_c, p_win_p, p_win_j]

def calculate_expected_values_array(my_hand, probs_mano, probs_postre, meta):
    """
    Calculates the EV for both Mano and Postre independently using the 50% threshold logic.
    Returns: [ev_mano, ev_postre]
    """
    
    def calculate_dispute_ev(p_win, win_bonus=0, lose_penalty=0):
        """Piecewise affine function with fold penalty."""
        if p_win >= 0.5:
            # We call the bet of 2
            return p_win * (2 + win_bonus) - (1 - p_win) * (2 + lose_penalty)
        else:
            # We fold: lose 1 point automatically, plus the opponent still scores their combination bonus.
            return -1.0 - lose_penalty
            
    def get_positional_ev(probs):
        p_win_g, p_win_c, p_win_p, p_win_j = probs
        my_p_cat, _ = evaluate_pairs(my_hand)
        my_j_state = evaluate_game(my_hand)
        
        # Grande & Chica
        ev_g = calculate_dispute_ev(p_win_g)
        ev_c = calculate_dispute_ev(p_win_c)
        
        # Pares
        p_rp = meta["prob_rival_pares"]
        avg_riv_p_val = (meta["prob_rival_par"] * 1 + meta["prob_rival_trio"] * 2 + meta["prob_rival_duplex"] * 3) / p_rp
        
        if my_p_cat > 0:
            my_p_val = my_p_cat # 3 for Duplex, 2 for Trio, 1 for Pair
            ev_p = (1 - p_rp) * my_p_val + p_rp * calculate_dispute_ev(p_win_p, win_bonus=my_p_val, lose_penalty=avg_riv_p_val)
        else:
            ev_p = -p_rp * avg_riv_p_val
            
        # Juego & Punto
        p_rj = meta["prob_rival_juego"]
        avg_riv_j_val = (meta["prob_rival_31"] * 3 + meta["prob_rival_no_31"] * 2) / p_rj
        
        if my_j_state["has_game"]:
            my_j_val = my_j_state["value"]
            ev_j = (1 - p_rj) * my_j_val + p_rj * calculate_dispute_ev(p_win_j, win_bonus=my_j_val, lose_penalty=avg_riv_j_val)
        else:
            # Going to Punto. If we win Punto dispute, we get 1 bonus stone.
            ev_j = -p_rj * avg_riv_j_val + (1 - p_rj) * calculate_dispute_ev(p_win_j, win_bonus=1)
            
        return ev_g + ev_c + ev_p + ev_j

    ev_mano = get_positional_ev(probs_mano)
    ev_postre = get_positional_ev(probs_postre)
    
    return [ev_mano, ev_postre]

# ==========================================
# EXECUTION & EXPORT
# ==========================================

def generate_and_save_dictionaries(filename="learn/global_variables/mus_data.json"):
    print("Calculating global constants...")
    meta_constants = calculate_global_constants()
    
    # Generate all 330 unique hands
    base_cards = [12, 11, 10, 7, 6, 5, 4, 1]
    all_hands = []
    for combo in itertools.combinations_with_replacement(base_cards, 4):
        all_hands.append(tuple(sorted(combo, reverse=True)))
        
    # Sort strictly lexicographically in descending order
    all_hands.sort(reverse=True)
    
    prob_dict = {}
    ev_dict = {}
    
    print(f"Evaluating {len(all_hands)} unique hands. This will take a few seconds...")
    for hand in all_hands:
        probs_mano = calculate_hand_probabilities(hand, am_i_mano=True)
        probs_postre = calculate_hand_probabilities(hand, am_i_mano=False)
        
        # Combine into the 8-value array [G_mano, C_mano, P_mano, J_mano, G_postre, C_postre, P_postre, J_postre]
        combined_probs = probs_mano + probs_postre
        
        # Calculate the 2-value array [ev_mano, ev_postre]
        ev_array = calculate_expected_values_array(hand, probs_mano, probs_postre, meta_constants)
        
        # Convert tuple back to string format strictly for JSON key usage
        hand_key = str(list(hand))
        prob_dict[hand_key] = [round(p, 5) for p in combined_probs]
        ev_dict[hand_key] = [round(e, 5) for e in ev_array]
        
    export_data = {
        "meta_constants": {k: round(v, 5) for k, v in meta_constants.items()},
        "probabilities": prob_dict,
        "expected_values": ev_dict
    }
    
    with open(filename, 'w') as f:
        json.dump(export_data, f, indent=4)
        
    print(f"Successfully saved all data to {filename}")

if __name__ == "__main__":
    generate_and_save_dictionaries()
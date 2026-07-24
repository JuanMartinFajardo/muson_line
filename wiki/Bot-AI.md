# Bot and AI

The bot ("Bot IA" in game) is implemented in [bot_ml.py](../bot_ml.py) as the **`SmartBot`** class. Its intelligence has three parts, each solved differently:

| Decision | Method |
| :--- | :--- |
| **Mus / No Mus** | Precomputed expected value (EV) per hand + personality noise |
| **Which cards to discard** | Exhaustive EV maximization over the 16 possible discards ([mus_discard_chooser.py](../mus_discard_chooser.py)) |
| **Betting** | **Deep CFR strategy network** (PyTorch) approximating a Nash equilibrium |

## 1. Precomputed EV tables

`learn/global_variables/mus_data.json` stores, for each of the **330 distinct hands** (sorted, mus-normalized values as string keys like `"[12, 12, 7, 1]"`):

- win probabilities for Grande/Chica/Pares/Juego, as Mano and as Postre (8 numbers),
- `expected_values`: `[EV_as_mano, EV_as_postre]` derived from those probabilities.

`predecir_mus()` looks up the hand's EV, adds bluff/noise terms, and cuts the mus when the perceived EV exceeds the `musero` threshold.

`predecir_descarte()` calls `get_best_discard_strategy()`, which evaluates every discard by assuming replacements come from 4 **buckets** (King=12, face=10, mid=5, Ace=1 — see `simplify_to_bucket`), reducing the search to ~35 hand shapes and a few hundred dictionary lookups.

## 2. Deep CFR betting network

- **Architecture** ([redes_mus.py](../redes_mus.py)): `RegretNetwork` and `StrategyNetwork`, both 3×128 dense layers; input is an **18-dimensional normalized state vector** (`estado_a_vector`): mano flag, 4 card values, own/rival points, mus rounds, rival discards, lance index, seen bet, pending raise/órdago flag, previous-lance pots (Grande/Chica/Pares) and their owners (1/0/0.5). Output: 6 logits, one per action (`pasar, envidar, ver, nover, subir, ordago`).
- **Inference** (`decidir_apuesta_cfr`): builds the state dict from the live `PartidaMus`, runs the strategy network, masks illegal actions via `get_valid_actions_cfr()` (respects pares/juego eligibility, forced-call rule, órdago-only situations, bet caps), renormalizes, and **samples** the action from the mixed strategy. Bids/raises are discretized to amount **2**.
- **Model loading:** the checkpoint name is hardcoded in `SmartBot.__init__` (currently `learn/cfr/deep_cfr_mus_bot_cfr5_iter_2350.pth`). Changing the bot means editing this constant (Roadmap: admin panel / bot settings).

### Personality meta-variables

`update_meta_variables()` re-rolls at the end of every hand: `musero` (mus-cutting threshold), `bluffer` (≤0.35), `aleatorio` (decision noise, ≤0.4), `fish` (blunder chance — currently unused in decisions). These make the bot less robotic and are the natural hook for the Roadmap's "bot personality settings" (aggressive/conservative/musero).

## 3. Training pipeline

### Current: Deep CFR (`train_cfr.py`)

External-sampling MCCFR with **Linear CFR** weighting and continuous fine-tuning (networks are not reset between iterations):

1. Per iteration (target 5,000): 1,000 game traversals through `MusBettingEnv` ([mus_env.py](../mus_env.py)), a wrapper over `PartidaMus` that fast-forwards past the mus/discard phase (using the same EV tables) to a random betting state.
2. Traversal computes counterfactual regrets for our actions, samples opponent actions from the current strategy.
3. Both networks train with Adam over **reservoir-sampled replay buffers** (capacity 100,000) — 2,000 SGD steps per iteration, batch 1024. TensorBoard logging enabled.
4. Checkpoints saved under `learn/cfr/` per generation name (e.g. `cfr5`).

### Evaluation (`arena.py`)

Loads two checkpoints and plays ~6,000 head-to-head games (both using the same optimal mus/discard logic) to measure which betting network is stronger. Used to pick which checkpoint ships in `SmartBot`.

### Legacy: random forests (`global_trainer.py` + `learn/`)

The original approach trained scikit-learn random forests on human game logs: `procesar_carpeta.compilar_dataset_global()` merges `logs/*.jsonl` into a CSV (with derived probability features from `learn/probability_calculator.py`), then `entrenar_mus / entrenar_descartes / entrenar_apuestas` fit models. The betting model imitated players instead of learning value, which motivated the switch to Deep CFR. The scripts are kept for dataset tooling and history.

## Data collection

Every match (human or bot) appends per-turn JSON lines to `logs/<MATCH_ID>.jsonl` via `PartidaMus.registrar_movimiento_ia()` — including both hands, action, amounts, and final outcome flags. This corpus supports future retraining and the Roadmap's game-statistics feature.

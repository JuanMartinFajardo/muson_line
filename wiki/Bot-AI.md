# Bot and AI

> The next stage of the AI (2v2 bot, Deep CFR + RL layers, Nash-distance measurement,
> log format v2, signs) is designed in [Bot-AI-4p-ML-Strategy](Bot-AI-4p-ML-Strategy.md)
> with its execution plan in [Bot-AI-4p-Roadmap](Bot-AI-4p-Roadmap.md). Note: that
> analysis (§3) found this page's claim that "networks are not reset between
> iterations" to be inaccurate — `train_cfr.py` re-initializes the regret network every
> iteration (only the strategy network trains continuously).

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

## 2 bis. The 4-player bot (`SmartBot4` v1, heuristic)

Phase 0 of [Bot-AI-4p-Roadmap](Bot-AI-4p-Roadmap.md): 2v2 rooms are playable against
bots **today**, with no ML. It lives in [bot_ml_4.py](../bot_ml_4.py) — `bot_ml.py` is
untouched; only its precomputed tables are reused.

### The load-bearing part: the interface contract

```python
MusBotBase.obtener_accion(vista) -> None | (accion, cantidad, meta)
```

`vista` is the **seat-local observation dict** produced by `PartidaMus4.vista(seat)` —
never the engine itself. Its blocks follow the §4.2 encoder layout of
[Bot-AI-4p-ML-Strategy](Bot-AI-4p-ML-Strategy.md), so the Deep CFR encoder of Phase 2
consumes the same dict the bot sees at serving time (this is what kills train/serve
skew at the root):

| Block | Contents |
| :--- | :--- |
| `meta` | phase, turn, **`acciones_legales`**, pedrete availability |
| `A_propio` | seat, mano-distance, cards, precomputed pares/juego features |
| `B_publico` | lance, per-seat declarations and discards (seat-relative), mus rounds |
| `C_apuestas` | pending raise, seen bet, pots and team-relative owners, last bettor, partner-can-still-answer, pot odds inputs |
| `D_marcador` | team/rival points, points-to-40, match score |
| `E_senas` | **reserved, all zeros until Phase 6** |

`PartidaMus4.acciones_legales(seat)` enforces engine legality *and* the mus rules the
engine does not police on its own (no betting Pares/Juego without the combination). A
bot that only picks from that list cannot make an illegal move — which is what the
Phase 0 acceptance soak checks.

### The heuristic behind it (replaceable by design)

- **Mus and discards:** the same EV tables as the 2p bot, unchanged.
- **Betting:** team win probability for the lance. From the hand's percentile `p`
  against one rival, the estimate is `1 - (1 - p^k)(1 - 1/(k+1))`, where `k` is the
  number of rivals **still disputing the lance** (declarations are read from Block B,
  so a rival who declared "no pares" stops counting) and `1/(k+1)` is the prior that
  the unseen partner is the best of the unknown hands. A median hand yields ~0.5.
- Open a bet above a per-lance threshold; **call by pot odds**
  (`p ≥ (pot - deje) / 2·pot`); órdago when the endgame makes it moot
  (`team points + pot ≥ 38`) or over a live bet with a locked hand.
- **Personalities** (Roadmap #12) work from day one: `musero`, `bluffer`, `aleatorio`,
  `fish` and `bias_apuesta`, which shifts every betting threshold. Fields left `None`
  are re-rolled each hand, as in the 2p bot.

### Measured (Phase 0 acceptance)

`tools/soak_bots4.py` (bot brain vs engine) and `tools/soak_server_bots4.py` (the real
server handlers with a stubbed socket layer):

| Run | Result |
| :--- | :--- |
| 500 matches, aggressive vs conservative | 2802 hands, **0 illegal actions** |
| 500 matches, musero vs chaotic | 2634 hands, **0 illegal actions** |
| 200 best-of-3, all balanced | 2830 hands, 0 illegal; teams 101–99 (no seat/team bias) |
| Server path, 1/2/3 bots per table | 50 best-of-3 matches each, no stalls, rooms close when the last human leaves |

Personalities separate measurably on both axes: aggressive bets/raises/órdagos on
**56%** of betting decisions vs **18%** for conservative; `musero` asks for mus **66%**
of the time vs **52%** for aggressive.

### Serving notes

- A bot seat is a fake sid `BOT_<code>_<seat>` in `salas4`; the instance lives in
  `room['bots'][seat]`. Bot turns are scheduled from the state broadcast, honoring the
  admin `bot_delay`, one action per task. The guard is a `bot_pensando` flag rather
  than the broadcast token: with a token, any unrelated re-broadcast (a player
  double-clicking "next round") invalidated the pending task and starved the bots.
- A room with no humans left is destroyed — bots never play on alone.
- **Matches with bots are not recorded**: the 2v2 leaderboard stays human-only.

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

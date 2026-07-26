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

For 2v2 the successor is `tools/arena4.py` (§4.5), which adds seat permutation, seeded
decks and points/hand ± stderr. `arena.py` still reports match winrate only, which is
the weaker metric.

### Legacy: random forests (`global_trainer.py` + `learn/`)

The original approach trained scikit-learn random forests on human game logs: `procesar_carpeta.compilar_dataset_global()` merges `logs/*.jsonl` into a CSV (with derived probability features from `learn/probability_calculator.py`), then `entrenar_mus / entrenar_descartes / entrenar_apuestas` fit models. The betting model imitated players instead of learning value, which motivated the switch to Deep CFR. The scripts are kept for dataset tooling and history.

## 4. Training infrastructure (Phase 1 of the 4p roadmap) — shipped 2026-07-26

Phase 1 of [Bot-AI-4p-Roadmap](Bot-AI-4p-Roadmap.md). Nothing here changes how the bots
play; it changes what we can *measure* and *train on*.

### 4.1 Log v2 — event sourcing ([mus_log.py](../mus_log.py))

One module, both engines (`mode: "2p"` / `"4p"`), one file per match in **`logs/v2/`**.
The v1 files stay in `logs/*.jsonl`, frozen — nothing writes there any more.

The design principle (§8.2) is that the log stores **facts, not features**: the deal,
every draw, every decision, the public declarations, the per-lance resolution. Anything
a model wants is then *derived by replaying* through the engine. That is exactly what v1
could not do — it froze a fixed feature set at write time, so improving the encoder did
nothing for old data.

| Event | Carries |
| :--- | :--- |
| `hdr` | version, match id, mode, rules, **seat identities** (human/bot, account code, checkpoint, personality), teams |
| `deal` | round number, who is mano, the four hands in seat order |
| `draw` | cards drawn after a discard or pedrete — the log *is* the deck |
| `a` | one decision: `mus`/`no_mus`/`descarte`/`pedrete`/`pasar`/`envidar`/`subir`/`ver`/`nover`/`ordago`, plus `ms` since the previous event |
| `decl` | public pares/juego declaration (the strongest public signal in Mus) |
| `pi` | optional bot introspection: policy distribution and value at decision time |
| `seat` | a seat changing hands mid-match (substitution) — keeps per-person attribution exact |
| `eor` | per-lance resolution, scoreboard, final hands (showdown truth) |
| `eom` | winner, games, `n_events` as an integrity check |

Two deliberate deviations from the §8.3 draft schema, both for the better:

- **Card values are raw (1–7, 10–12), not mus-normalized.** Normalizing is one line in
  the encoder but irreversible in the log: without raw values a match cannot be
  replayed (pedrete is exactly 4-5-6-7, and deck composition depends on the 2s and 3s).
- **Discards log the indices thrown, not the card values.** The cards are already known
  from `deal`/`draw`; the indices are what a replay needs to reproduce the action.

Logging is on for every real 2v2 match (`server_mus4.LOG_V2`, with `activar_log()`
called from `_iniciar_partida`) and for 2p matches against bots and humans. The engines
default to a `NullLogger`, so the gym, the arena and the soaks write nothing.

### 4.2 Replay ([mus_replay.py](../mus_replay.py)) — what makes the format load-bearing

The engine has exactly one source of randomness, the deck. Replay swaps it for a FIFO
of the cards the log names (`deal` in dealing order, then each `draw` in file order) —
which is precisely the order the engine asks for cards. Everything else is derived.

`tools/log_verify.py` uses this for the strong form of the integrity check: replay the
match, **regenerate the event stream**, and compare event by event against the file
(`ms`/`ts` excluded — human timing is not reproducible by definition; `pi`/`seat`
excluded — the server writes those, not the engine). When they match, two things are
proven at once: the log holds everything needed to reconstruct the match, and today's
engine still resolves Mus the way it did on the day of the recording. That second half
is a regression test on real traffic, for free.

`tools/selftest_log.py` is the CI-style script: it plays random-but-legal matches with
both engines, logs them, and demands the round trip. Random play on purpose — it visits
the corners a heuristic bot almost never does (chained órdagos, forced calls, pedretes,
exhausted decks, Punto instead of Juego).

### 4.3 Fast cloning ([`fork()`](../mus_mecanicas_4.py)) and the throughput gate

The §3.6 audit finding confirmed: `copy.deepcopy` was the training bottleneck.
External-sampling CFR clones the environment at *every explored action*, and deepcopy
walked the card dicts (value/suit/image path/text), the deck and the logger.

Cards are **immutable in practice** — the engine moves them between lists but never
edits them. So `fork()` copies only the containers and *shares* the card dicts. Two
smaller wins came out of profiling the result: evaluating pares/juego without
`collections.Counter` (≈170k Counter objects per 120 traversals), and not building the
`vista()` dict on every `step()` (a third of traversal time, and CFR rarely needs it at
that moment).

`to_state()`/`from_state()` do real serialization to flat JSON-able structures, which
also hands Roadmap #18 layer 2 (saved games) its persistence for free.

**[bench_env.py](../bench_env.py) — the gate (≥10×, target 20×):**

| Environment | deepcopy | `fork()` | ratio |
| :--- | ---: | ---: | ---: |
| 2p — `MusBettingEnv` | 38.2 traversals/s | 490.3 | **12.8×** |
| 2v2 — `MusBettingEnv4` | 47.5 traversals/s | 545.4 | **11.5×** |

Those two rows isolate the clone: it is the only thing that differs between them. The
hand-evaluation and lazy-observation fixes speed up *both* rows, so the honest
end-to-end "before vs after" is larger — measured against the pre-Phase-1 code in the
2p engine: **22.7 → 490.3 traversals/s, 21.6×**, which does hit the 20× target.

**Gate passed**, so renting CPU cores (§12) is unblocked. Still open, and deliberately
deferred to Phase 2: batching net queries per traversal and multiprocessing workers.
Neither can be tuned without a real network in the loop.

### 4.4 Shared encoder ([encoder.py](../encoder.py)) and `MusBettingEnv4`

`codificar(vista) -> float32[71]` is the *only* state encoding for 4p, used by the
training environment, by serving, and by the dataset exporter. That is the root fix for
train/serve skew (§3.4): with one function there is no second copy to drift.

| Block | Dims | Contents |
| :--- | ---: | :--- |
| A — self | 15 | mano-distance one-hot, 4 card values, pares tier/prize, juego value, discards |
| B — public | 22 | lance one-hot, mus rounds, and per other seat (rival/partner/rival) the pares and juego declarations + discard count |
| C — betting | 19 | pending raise, órdago flag, seen bet, lance pot, team-relative owners ×4, whose bet is live, last bettor (seat-relative), partner-can-answer, pot odds inputs |
| D — score | 7 | team/rival points, points-to-40, match score |
| E — signs | 8 | **reserved, zero until Phase 6** |

Two conventions worth naming. Tri-states (a declaration can be yes / no / *not yet
called*) take **two** dimensions (known, value) — encoding "unknown" as 0.5 would tell
the network it is halfway between yes and no. And expensive-to-discover features (has
pares, pares tier, juego value) are handed over precomputed; spending network capacity
rediscovering the rules of Mus buys nothing. Block E exists today so the Phase 6
fine-tune *continues* from the signs-off checkpoint instead of retraining: with zeroed
inputs the function is identical by construction.

[`MusBettingEnv4`](../mus_env4.py) carries the two reward corrections from the audit.
The terminal reward is the **per-round team point delta**, not the absolute scoreboard
(§3.2 — the random starting-score offset cancelled inside the regrets but wasted
capacity and added variance). And the fast-forward no longer invents uniform
scoreboards: `DistribucionEstados` samples `(points_A, points_B, mus_rounds)` triples
**observed in real v2 logs** (§3.4). With no corpus yet it falls back to an explicit
prior and *says so* (`env.dist.origen`), so nobody mistakes "no data" for "measured".

### 4.5 Measurement harness, and what it already says

**`tools/arena4.py`** — three choices separate a number from an anecdote:
*permuted seats* (each pairing plays both placements and averages — being mano wins
ties, so without this you measure the seat, not the bot), *seeded decks* (common random
numbers via the engine's injectable `rng`, so the difference measured is between
policies, not between cards), and *points per hand ± stderr* rather than match winrate
(a 40–0 and a 40–39 are not the same result, and points/hand is the unit the roadmap's
gates are written in).

**`tools/lbr_probe.py`** — Local Best Response for 2p, the second rung of the §7 ladder:
a belief over the rival's hand pruned by public information (declarations, discard
counts), and a greedy one-step evaluation over a restricted action set. Its winnings are
a **lower bound** on exploitability.

Measured (this is the Phase 1 acceptance evidence):

| Check | Result |
| :--- | :--- |
| Log round trip, real server path | 8 best-of-3 matches through `server_mus4` handlers, 1,700+ events, **all replay byte-exactly** |
| Log round trip, random play | ~1,160 matches across both engines (`selftest_log`), **all byte-exact** |
| Bench gate | 11.5× worst case (12.8× on 2p) — **passes ≥10×** |
| `MusBettingEnv4` fuzz | 10,000 hands, 59,133 decisions, **0 illegal states**, forks provably independent |
| arena4 sanity | heuristic vs random **+14.66 ± 2.81 points/hand** (\|t\| = 5.2) |
| LBR vs random | **+12.8 ± 1.2 points/hand** — random is massively exploitable |
| LBR vs table-calibrated 2p heuristic | −0.24 ± 1.23 → bound is **0.0**: the probe finds no exploit |

One caution on that last row, because it is easy to over-read: a bound of zero does
**not** say the heuristic is near-Nash. It says this particular restricted, one-step
probe cannot beat it. Claiming strength needs the other rungs of §7 — the exact 2p best
response (Phase 1.5), the RL best response (Phase 3.1), and the checkpoint-pool arena.
LBR only ever proves a bot is *bad*, never that it is good.

Note also that the arena's +14.66 points/hand against random looks enormous because
random bots throw órdagos constantly: matches end in ~2 hands with 40-point swings. It
is a real number in a real unit, but it is not comparable to the ~1.5 points/hand gates
between *competent* bots later in the roadmap.

### 4.6 Deriving datasets ([tools/logs2dataset.py](../tools/logs2dataset.py))

Replays every v2 log and emits one row per decision: identity (match, seat, human/bot,
account code, personality), the decision (lance, action, amount, `ms`), context (hand,
scoreboard), outcome labels (points the team won that hand, match result), and the 71
encoder columns for 4p rows. Parquet when `pyarrow` is installed, CSV otherwise (an
optional dependency — the web host does not need it).

The point is regeneration: **when the encoder changes, the whole dataset is rebuilt from
the same logs**, including the historical corpus. The report line also tracks the
Phase 4.1 gate (≥10,000 human decisions) so the behaviour-cloning phase has a number to
wait on.

## Data collection

Every 2v2 match and every 2p match now append a replayable v2 event log to
`logs/v2/<MATCH_ID>.jsonl` (see §4.1). The admin log-download endpoint walks the whole
`logs/` tree, so both the frozen v1 files and the v2 corpus come out in the zip.

Legacy: v1 wrote per-turn rows via `PartidaMus.registrar_movimiento_ia()`, duplicating
the full context on every line (once per player, mirrored) and identifying players by
display name. Those 17-odd files remain readable for the random-forest tooling in
`learn/`, but they cannot be replayed, so no new feature can ever be extracted from
them — which is precisely why the format was broken cleanly rather than extended.

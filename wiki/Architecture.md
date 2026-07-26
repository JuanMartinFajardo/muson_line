# Architecture

## Overview

CallMus is a classic **monolithic real-time web app**:

```
Browser (vanilla JS + Socket.IO client)
        │  HTTP (auth, leaderboard)  +  WebSocket (all gameplay)
        ▼
Flask + Flask-SocketIO server (eventlet)  ──►  SQLite (mus.db)
        │
        ├── PartidaMus  (one game engine instance per room, in memory)
        ├── SmartBot    (PyTorch Deep CFR inference, for bot rooms)
        └── logs/v2/*.jsonl (event-sourced, replayable per-match logs)
```

There is **no build step**: the frontend is plain HTML/CSS/JS served directly by Flask (`static_folder='static'`, `template_folder='.'`). All game state lives **in server memory** (the `salas` and `jugadores` dictionaries); only user accounts and match results are persisted in SQLite.

## File map

### Runtime (server)

| File | Role |
| :--- | :--- |
| [server.py](../server.py) | Flask app, HTTP auth routes, all Socket.IO handlers, room registry, bot scheduling |
| [mus_mecanicas.py](../mus_mecanicas.py) | Pure game logic: deck, hand evaluation, comparators, and the `PartidaMus` state machine |
| [base_datos.py](../base_datos.py) | SQLite access layer: users, login, ELO, leaderboard |
| [bot_ml.py](../bot_ml.py) | `SmartBot`: decides mus/discard/bets using precomputed EV tables + a Deep CFR strategy network |
| [mus_discard_chooser.py](../mus_discard_chooser.py) | Optimal-discard algorithm (bucketed EV maximization over the 16 possible discards) |
| [redes_mus.py](../redes_mus.py) | PyTorch network definitions (`RegretNetwork`, `StrategyNetwork`, `ReplayBuffer`) and `estado_a_vector` state encoder |
| [social.py](../social.py) | Friends, DMs, groups and group leaderboards (`init_social`); also owns the single Socket.IO `connect` handler (presence + ban check) |
| [server_mus4.py](../server_mus4.py) | 4-player (2v2) room registry and handlers (`init_mus4`), engine `mus_mecanicas_4.py`; also owns the señas focus registry |
| [mus_senas.py](../mus_senas.py) | Pure: which sign a hand makes, with an admin-editable priority order ([Señas](Senas-2v2.md)) |
| [mus_log.py](../mus_log.py) | Log v2: event-sourced match logger shared by both engines, plus the replay-side card source ([Bot-AI](Bot-AI.md) §4.1) |
| [admin.py](../admin.py) | Admin panel (`init_admin`): accounts, live rooms, downloads, `Config` variables, audit, plus the player-facing support and announcement endpoints |
| [analitica.py](../analitica.py) | Usage analytics (`init_analitica`): cookieless audience measurement into its own `analitica.db`, and the panel's Analítica tab ([Analytics](Analytics.md)) |

### Training / offline (not needed to run the server)

| File | Role |
| :--- | :--- |
| [train_cfr.py](../train_cfr.py) | Deep CFR (Linear CFR, external-sampling MCCFR) training loop for the betting network |
| [mus_env.py](../mus_env.py) | `MusBettingEnv`: gym-like wrapper around `PartidaMus` used by the CFR trainer |
| [mus_env4.py](../mus_env4.py) | `MusBettingEnv4`: the 2v2 gym over `PartidaMus4`, with team-delta rewards and log-seeded state sampling |
| [encoder.py](../encoder.py) | The **single** 4p state encoding (71 dims, blocks A–E), shared by training, serving and dataset export |
| [mus_replay.py](../mus_replay.py) | Replays a v2 log through the engine; the base for log verification and dataset derivation |
| [bench_env.py](../bench_env.py) | Simulator throughput benchmark (`fork()` vs `deepcopy`) — the Phase 1 performance gate |
| [arena.py](../arena.py) | Pits two model checkpoints against each other over thousands of games to measure progress |
| [global_trainer.py](../global_trainer.py) | Legacy pipeline: compiles `logs/` into a CSV and trains the old random-forest models |
| `tools/` | `log_verify.py` (replay integrity), `selftest_log.py` (log round trip, CI-style), `logs2dataset.py` (v2 → Parquet), `fuzz_env4.py`, `arena4.py` (2v2 arena, seat-permuted), `lbr_probe.py` (2p exploitability bound), `soak_bots4.py`, `soak_server_bots4.py`, `test_analitica.py` (30 checks over `analitica.py`, incl. "no IP ever hits disk"), `decks/` |
| `learn/` | Training assets: `probability_calculator.py`, `dataset_generator.py`, `procesar_carpeta.py`, `entrenar_*.py`, CFR checkpoints (`learn/cfr/*.pth`), precomputed tables (`learn/global_variables/mus_data.json`), datasets, old models |

### Frontend

| File | Role |
| :--- | :--- |
| [index.html](../index.html) | Single page: lobby (menu screen), game screen, auth modals, leaderboard modal |
| [static/app.js](../static/app.js) | i18n dictionary (ES/EN), Socket.IO client, all game rendering and UI logic (~1500 lines) |
| [static/auth.js](../static/auth.js) | Login / signup / email-verification / logout flows (fetch to `/auth/*`) |
| [static/tutorial.js](../static/tutorial.js) | Interactive "How to play" tutorial (bilingual, see Roadmap #2) |
| [static/settings.js](../static/settings.js) | Settings window: language, account changes, deletion |
| [static/social.js](../static/social.js) | Friends, chats, groups and game invites |
| [static/soporte.js](../static/soporte.js) | Support inbox inside Settings + admin announcements (pinned banner and popups) |
| [admin.html](../admin.html) | Server-rendered admin panel (`/admin`), self-contained CSS/JS, Spanish only |
| [static/analitica.js](../static/analitica.js) | Audience measurement beacon: visible-tab time and menu events. Stores nothing on the device ([Analytics](Analytics.md)) |
| [static/senas4.js](../static/senas4.js) | Señas (2v2): focus state machine, controls, SVG faces, sign and report UI (`window.Senas4`) |
| [static/senas.css](../static/senas.css) | Señas: the face, the lit seat and the ten sign animations |
| [static/style.css](../static/style.css) | Nord-palette styling |
| `static/img/` | Card images (`card_<suit>_<value>.webp`), logo, favicon |

### Data

| Item | Role |
| :--- | :--- |
| `mus.db` | SQLite database (`Usuarios` table) |
| `analitica.db` | Separate SQLite database for usage analytics — deliberately not in `mus.db` ([Analytics](Analytics.md)) |
| `logs/v2/*.jsonl` | **Current format.** One file per match, event-sourced and exactly replayable ([Bot-AI](Bot-AI.md) §4.1) |
| `logs/*.jsonl` | Legacy v1, **frozen** (nothing writes there any more): one row per turn with the features frozen at write time, so matches cannot be replayed |
| `learn/global_variables/mus_data.json` | Precomputed win probabilities and expected values for all 330 possible hands (mano/postre) |

## Key in-memory structures (server.py)

```python
jugadores = { sid: {'nombre': str, 'sala': code, 'username': str|None} }
salas     = { code: {'estado': 'esperando'|'jugando'|'pausada'|'esperando_reemplazo',
                     'sids': [sid1, sid2],       # None marks a vacated seat
                     'motor': PartidaMus,         # once the game starts
                     'bot': SmartBot,             # only in bot rooms
                     'al_mejor_de': int, 'publico': bool,
                     'tokens': {seat: str},       # identity for reconnecting
                     'esperando_desde': float,    # only while looking for a substitute
                     'esperando_votos': set[int], # seats that accepted to wait
                     'username': str|None, 'creador_nombre': str} }
```

Room lifecycle: `esperando` → `jugando` → (`pausada`, 90 s of reconnection grace) → (`esperando_reemplazo`, 5 min advertised as an ongoing match with a free seat) → destroyed. The 4-player registry `salas4` in `server_mus4.py` follows the same states, indexed by seat instead of by sid.

Room codes are 4 random chars (`A-Z0-9`). Bot rooms use a fake SID `BOT_<code>`.

## Request/data flow for a game turn

1. Client emits `accion_juego` with `{accion, ...}` over Socket.IO.
2. `handle_accion_juego` → `procesar_accion_interna(sid, room, datos)` validates turn ownership and calls the corresponding `PartidaMus` method (`cantar_mus`, `procesar_descarte`, `accion_apuesta`, …).
3. `enviar_estado_a_jugadores(room)` builds a **per-player payload** (own cards visible, opponent's hidden except at showdown) and emits `actualizar_mesa` to the room.
4. If the room has a bot, the same function asks `SmartBot.obtener_accion(partida)`; if the bot has a move, a background task sleeps `bot_delay` seconds (the `Config` variable, default 1.5, editable from `/admin`) and re-enters `procesar_accion_interna` with the bot's SID.
5. When a game ends (`fase == 'recuento'` and someone reaches 40), the result is written to SQLite (`registrar_partida_completa`).

Logging is not part of that last step any more: the v2 logger writes **each event as it
happens** (`mus_log.MatchLogger`, flushed immediately), so a match interrupted halfway
still leaves all its completed hands on disk — which is the common case in production.

## Known architectural limitations

- **All rooms are lost on server restart** (in-memory only); games vs bot cannot be resumed after disconnect.
- **A room with every player disconnected survives until its timer fires** (grace or replacement window): it stops being advertised because the public lists skip rooms with no live player, but it stays in memory for up to 5 minutes so a refresh can reclaim the seat.
- `server.py` still mixes concerns (auth, rooms, game relay, bot orchestration) in one file. The features added since then live in their own additive modules hooked in at the bottom of `server.py` (`social.init_social`, `server_mus4.init_mus4`, `admin.init_admin`), all sharing the same Flask app, Socket.IO instance and session; tournaments (#4) should follow the same pattern. `analitica.init_analitica` is hooked in after `admin` (it reuses the panel's permission decorator) and is the one module with its own database.
- Only **one** handler per Socket.IO event is allowed (Flask-SocketIO 5.x): `connect` lives in `social.py` (presence + ban check) and `disconnect` in `server.py`, which calls into the other modules.

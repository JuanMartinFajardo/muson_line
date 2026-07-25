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
        └── logs/*.jsonl (per-match training logs)
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

### Training / offline (not needed to run the server)

| File | Role |
| :--- | :--- |
| [train_cfr.py](../train_cfr.py) | Deep CFR (Linear CFR, external-sampling MCCFR) training loop for the betting network |
| [mus_env.py](../mus_env.py) | `MusBettingEnv`: gym-like wrapper around `PartidaMus` used by the CFR trainer |
| [arena.py](../arena.py) | Pits two model checkpoints against each other over thousands of games to measure progress |
| [global_trainer.py](../global_trainer.py) | Legacy pipeline: compiles `logs/` into a CSV and trains the old random-forest models |
| `learn/` | Training assets: `probability_calculator.py`, `dataset_generator.py`, `procesar_carpeta.py`, `entrenar_*.py`, CFR checkpoints (`learn/cfr/*.pth`), precomputed tables (`learn/global_variables/mus_data.json`), datasets, old models |

### Frontend

| File | Role |
| :--- | :--- |
| [index.html](../index.html) | Single page: lobby (menu screen), game screen, auth modals, leaderboard modal |
| [static/app.js](../static/app.js) | i18n dictionary (ES/EN), Socket.IO client, all game rendering and UI logic (~1500 lines) |
| [static/auth.js](../static/auth.js) | Login / signup / email-verification / logout flows (fetch to `/auth/*`) |
| [static/tutorial.js](../static/tutorial.js) | Interactive "How to play" tutorial (currently Spanish-heavy) |
| [static/style.css](../static/style.css) | Nord-palette styling |
| `static/img/` | Card images (`card_<suit>_<value>.webp`), logo, favicon |

### Data

| Item | Role |
| :--- | :--- |
| `mus.db` | SQLite database (`Usuarios` table) |
| `logs/*.jsonl` | One file per match ID; one JSON line per game turn (used for AI training) |
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
4. If the room has a bot, the same function asks `SmartBot.obtener_accion(partida)`; if the bot has a move, a background task sleeps ~1.5 s and re-enters `procesar_accion_interna` with the bot's SID.
5. When a game ends (`fase == 'recuento'` and someone reaches 40), the result is written to SQLite (`registrar_partida_completa`) and the per-turn history is flushed to `logs/<match_id>.jsonl`.

## Known architectural limitations

- **All rooms are lost on server restart** (in-memory only); games vs bot cannot be resumed after disconnect.
- **A room with every player disconnected survives until its timer fires** (grace or replacement window): it stops being advertised because the public lists skip rooms with no live player, but it stays in memory for up to 5 minutes so a refresh can reclaim the seat.
- Secrets (Flask `SECRET_KEY`, SMTP credentials, Google OAuth keys) are **hardcoded placeholders** in `server.py` — must move to environment variables.
- `server.py` mixes concerns (auth, rooms, game relay, bot orchestration) in one file; the Roadmap features (friends, tournaments, admin) will require splitting into blueprints/modules.

# CallMus Wiki

**CallMus** is an online web app to play the **2-player version of the Spanish card game Mus**. Players can play online against each other (via room codes or a public game list) or against an AI bot trained with **Deep Counterfactual Regret Minimization (Deep CFR)**.

- **Live game modes:** Online 1v1 (private code or public lobby) and Human vs Bot.
- **Languages:** Spanish and English (client-side i18n).
- **Accounts:** Optional registration with email verification; logged-in matches feed a global **ELO leaderboard**.
- **License:** AGPL-3.0. Repository: `https://github.com/JuanMartinFajardo/muson_line`. Contact: `callmus.contact@gmail.com`.

## Wiki index

| Page | Contents |
| :--- | :--- |
| [Architecture](Architecture.md) | High-level system design, file map, data flow |
| [Game Rules](Game-Rules.md) | Rules of 2-player Mus as implemented by the app |
| [Game Engine](Game-Engine.md) | `mus_mecanicas.py` — the `PartidaMus` state machine |
| [Backend Server](Backend-Server.md) | `server.py` — HTTP routes, Socket.IO events, room management |
| [Database](Database.md) | `base_datos.py` — SQLite schema, ELO math |
| [Authentication](Authentication.md) | Account system: register/verify/login/Google OAuth (partially implemented) |
| [Frontend](Frontend.md) | `index.html`, `static/app.js`, `static/auth.js`, `static/tutorial.js`, i18n |
| [Bot and AI](Bot-AI.md) | `bot_ml.py`, Deep CFR training pipeline, `learn/` folder |
| [Setup and Deployment](Setup-and-Deployment.md) | How to install and run the server |
| [Roadmap](Roadmap.md) | Planned features with detailed implementation guides |
| [Implementing 4-Player Mus](Implementing-Mus-4-Players.md) | Full build guide for the 2v2 online variant (mechanics → UI → connections) |
| [Implementing Friends, Messaging & Groups](Implementing-Friends-Messaging-Groups.md) | Full build guide for the social layer (friends, chat, groups, group leaderboards) |

## Quick facts

- Server entry point: [server.py](../server.py) (Flask + Flask-SocketIO + eventlet, port **5001**).
- Game logic: [mus_mecanicas.py](../mus_mecanicas.py) (`PartidaMus` class — one instance per room).
- Bot: [bot_ml.py](../bot_ml.py) (`SmartBot` — Deep CFR strategy network for betting + precomputed expected-value tables for mus/discard decisions).
- Database: `mus.db` (SQLite), managed by [base_datos.py](../base_datos.py).
- Every finished game writes a per-turn training log to `logs/<MATCH_ID>.jsonl`.


Things to do in the future:
- Improve connection (prevent disconnection problem)
- For users in app or logged, save status of games (with player or AI), so that you can continue the games.
- when invited to a game by a friend and accepted, friend screen should be removed
- 
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

**Admin panel:** `/admin` (same process and port as the game — nothing extra to deploy).
Set `ADMIN_USERNAME` once to create the first administrator. See
[Roadmap #13](Roadmap.md#13-online-admin-panel--done-2026-07-25).

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
- Groups should be accepted
- name for 4player mus should be the username
- Redesign the main menu so that it is beautiful, more minimalistic, but it preserves all its functions. For example: keep settings and full-screen buttons where they are. If the user is logged-in, the friends button should be pinned next to settings button (not floating in the center as it is now). There should be a single button 'play', a button 'tutorial', a button 'deck menu' (saying 'feature not available yet' when clicking), and then leaderboard, the ko-fi button and 'about call mus'. The button play deploys a window with all the options: choose 1v1 or 2v2, play with bots, bots-player mixed, players, public game, the number of games, play with signs (not available yet, but when available only for 2vs2), create game, join a created one or an ongoing one. I want you to redesign this in a way that it is ABSOLUTELY INTUITIVE to use, and looks beautiful. Obviously you have to flag as unavailable every feature that is not yet available. It must be beautiful, but it cannot look like the average IA generated webpage, it must have some unique beautiful design. Ask me any necessary questions.
- Bot: First random bot, then bot using the 2mus architecture, then train a 4mus bot. Apply PCA to find the most relevant variables to play mus. Generate a well structured log.
- 
[[Versions]]
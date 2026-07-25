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
| [4p Bot ML Strategy](Bot-AI-4p-ML-Strategy.md) | Deep analysis: Deep CFR + RL for the 2v2 bot, Nash-distance measurement, log format v2, signs |
| [4p Bot Roadmap](Bot-AI-4p-Roadmap.md) | Phased execution plan for the 2v2 bot (P0 heuristic → P6 signs) |
| [Setup and Deployment](Setup-and-Deployment.md) | How to install and run the server |
| [Roadmap](Roadmap.md) | Planned features with detailed implementation guides |
| [Implementing 4-Player Mus](Implementing-Mus-4-Players.md) | Full build guide for the 2v2 online variant (mechanics → UI → connections) |
| [Señas (2v2)](Senas-2v2.md) | The signs game: looking around the table, the ten signs, and why the server decides who sees what |
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
- ~~Redesign the main menu~~ **done (2026-07-25)**: "midnight ink" menu with the four Spanish suits drawn in SVG, one *Jugar* button opening `#modal-play` (1v1 / 2v2, bot, best-of, public, seat, create, join by code or from the live list) and *soon* markers on the deck menu, 2v2 bots, mixed tables and signs. See [Frontend](Frontend.md#the-menu-and-the-play-window). Still to do on top of it: the deck builder ([Roadmap #5](Roadmap.md#5-special-decks-and-deck-builder-menu)).
- ~~Señas for 2v2~~ **done (2026-07-25)**: an optional 2v2 table setting. Your cards sit face down, you turn your head with the arrows/WASD/swipe, and you only see the face — and therefore the sign — of whoever you are looking at. Ten signs with the traditional gestures, one button that always makes the *highest* sign your hand allows (order editable from `/admin`), and tapping a rival opens the "I saw you" report. The server is the only one who knows who is looking at whom, so a patched client cannot spy a sign it did not watch. See [Señas (2v2)](Senas-2v2.md).
- ~~Carry the menu's look into the tables~~ **done (2026-07-25)**: both tables (1v1 and 2v2) now share the same language in [static/game.css](../static/game.css) — a plate per player with the score in serif and the games won as *piedras*, the four-lance board in gold, órdago as the only red, and the game overlays styled like the menu's windows. See [Frontend](Frontend.md#the-tables-1v1-and-2v2). Left over: the tutorial window is still the only old-looking screen reachable from the table.
- Bot: First random bot, then bot using the 2mus architecture, then train a 4mus bot. Apply PCA to find the most relevant variables to play mus. Generate a well structured log.
- 
[[Versions]]
# Backend Server — `server.py`

Flask app served with **eventlet** (`eventlet.monkey_patch()` at the very top) and **Flask-SocketIO** (`cors_allowed_origins="*"`). Default port **5001**. The same file contains HTTP auth routes, all Socket.IO gameplay events, room management, and bot orchestration.

## HTTP routes

| Route | Method | Purpose |
| :--- | :--- | :--- |
| `/` | GET | Serves `index.html` |
| `/api/leaderboard` | GET | Returns `base_datos.obtener_leaderboard()` |
| `/auth/solicitar_codigo` | POST | Step 1 of signup: validates, rejects duplicates (`existe_usuario`), rate-limits, stores a 6-digit code (with timestamp) in the in-memory `codigos_pendientes` dict and emails it |
| `/auth/registro` | POST | Step 2: verifies the (unexpired) code, creates the user with email, auto-logs-in via Flask session |
| `/auth/login` | POST | Login by **username or email** (`session['username']`; `remember` → permanent session) |
| `/auth/solicitar_reset` | POST | Step 1 of password recovery: emails a reset code if the account exists (same response either way, no enumeration) |
| `/auth/reset` | POST | Step 2: verifies the code and updates the password hash |
| `/auth/sesion` | GET | Returns the logged-in user's profile if a session exists |
| `/auth/logout` | POST | Clears the session |
| `/auth/google/login`, `/auth/google/callback` | GET | Google OAuth via Authlib — active when `GOOGLE_CLIENT_ID`/`SECRET` are set (503 otherwise). See [Authentication](Authentication.md) |

An `after_request` hook sets 1-year immutable cache headers on `/static/img/*`.

## Socket.IO events (client → server)

| Event | Handler | What it does |
| :--- | :--- | :--- |
| `pedir_publicas` | `handle_pedir_publicas` | Re-broadcasts the public-games list |
| `crear_sala` | `handle_crear_sala` | Creates a room (4-char code), registers the creator, optionally public; emits `sala_creada` |
| `crear_partida_bot` | `handle_crear_partida_bot` | Creates a room already in `'jugando'` state with a `SmartBot` instance and fake SID `BOT_<code>`; starts the game immediately |
| `unirse_sala` | `handle_unirse_sala` | Joins by code. Contains seat-recovery logic: creators can reclaim seat 0 after a refresh, guests can fill vacated seats; blocks joining your own room with the same account and double-click races. When both seats are filled, builds `PartidaMus`, emits `iniciar_partida`, and sends the first state |
| `accion_juego` | `handle_accion_juego` | All in-game actions; delegates to `procesar_accion_interna` |
| `abandonar_sala_limpiamente` | — | Voluntary exit: deletes the room so `disconnect` won't notify the rival |
| `disconnect` | `handle_disconnect` | If waiting: seat becomes `None` and an orphan-room cleaner runs after 120 s. If playing: emits `rival_desconectado` and **destroys the room** |

## Server → client events

- `sala_creada {codigo}` — room code for the lobby "waiting" panel.
- `actualizar_publicas [rooms]` — public game list.
- `iniciar_partida` — switch to the game screen.
- `actualizar_mesa {payload}` — the full per-player game state (see below).
- `error_sala {mensaje}`, `rival_desconectado`.

## `procesar_accion_interna(sid, room, datos)`

Central dispatcher for game actions. Turn-gated actions: `repartir`, `mus`, `no_mus`, and betting (`pasar`, `envidar`, `subir`, `ver`, `ordago`, `nover` — with `cantidad` for raises). Non-turn-gated: `pedrete`, `descartar` (during the discard phase, each player acts once), `continuar_transicion` (dismisses transition messages), and `listo_siguiente_ronda` (when both players are ready, either advances the round with swapped roles or resets the game after 40 pts).

## `enviar_estado_a_jugadores(codigo)`

Builds one payload per human player and emits `actualizar_mesa` **to the whole room** with a `para_sid` field so each client filters its own copy (a workaround for per-SID delivery issues). Payload highlights:

- `mis_cartas` (full card objects) vs `cartas_rival` (the client only reveals them at recuento),
- `es_mi_turno`, `soy_mano`, `fase`, `mensaje` (localizable message codes like `fase_apuestas`),
- `apuestas` (current lance, pending raise, pots, fold concessions, `soy_quien_sube`, `juego_es_punto`),
- `recuento` (list of localized scoring steps with `gano_yo` flags),
- match info (`mis_partidas`, `partidas_rival`, `al_mejor_de`, `match_finalizado`),
- `puede_pedrete` (server-side check for the 4-5-6-7 hand).

This function also has two side effects:

1. **Result persistence:** on recuento, if the game was just won and not yet recorded, calls `base_datos.registrar_partida_completa(winner, loser)` (only affects ELO when both are registered users).
2. **Bot turn:** if the room has a bot, asks `SmartBot.obtener_accion(partida)`; if there is a move, spawns a background task that sleeps 1.5 s (fixed "thinking" delay) and re-enters `procesar_accion_interna` as the bot.

## Known issues / hardcoded values

- `SECRET_KEY`, SMTP and Google OAuth credentials now come from env vars / `.env` (a dev fallback `SECRET_KEY` is used with a warning if unset). ✅ resolved.
- Google OAuth is wired via Authlib and only needs real credentials to go live. ✅ resolved.
- Bot delay fixed at 1.5 s (Roadmap: speed setting).
- Disconnection mid-game destroys the game irrecoverably (Roadmap: resume bot games, ghost-game fixes).
- `codigos_pendientes` and the per-email rate-limit counters are in-memory: codes now expire after 15 min, but state is still lost on restart and not shared across processes (would need Redis if scaled beyond one eventlet worker).

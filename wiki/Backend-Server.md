# Backend Server — `server.py`

Flask app served with **eventlet** (`eventlet.monkey_patch()` at the very top) and **Flask-SocketIO** (`cors_allowed_origins="*"`). Default port **5001**. The same file contains HTTP auth routes, all Socket.IO gameplay events, room management, and bot orchestration.

## HTTP routes

| Route | Method | Purpose |
| :--- | :--- | :--- |
| `/` | GET | Serves `index.html` |
| `/api/leaderboard` | GET | Returns `base_datos.obtener_leaderboard()` |
| `/api/debug/salas` | GET | Room/player diagnostics (state, age, idle time, seat liveness, orphan count). **404 unless `DEBUG_TOKEN` is set** and passed as `?token=` |
| `/auth/solicitar_codigo` | POST | Step 1 of signup: validates, rejects duplicates (`existe_usuario`), rate-limits, stores a 6-digit code (with timestamp) in the in-memory `codigos_pendientes` dict and emails it |
| `/auth/registro` | POST | Step 2: verifies the (unexpired) code, creates the user with email, auto-logs-in via Flask session |
| `/auth/login` | POST | Login by **username or email** (`session['username']`; `remember` → permanent session) |
| `/auth/solicitar_reset` | POST | Step 1 of password recovery: emails a reset code if the account exists (same response either way, no enumeration) |
| `/auth/reset` | POST | Step 2: verifies the code and updates the password hash |
| `/auth/sesion` | GET | Returns the logged-in user's profile if a session exists (includes `email`, `codigo`, `tiene_password`, `google` and `dias_para_cambiar_username` — it only ever goes to its owner). Clears the session cookie if it names an account that no longer exists |
| `/auth/logout` | POST | Clears the session |
| `/auth/cuenta/codigo` | POST | Emails a single-use 6-digit code to authorize an account change (the only route for Google accounts with no password) |
| `/auth/cuenta/username` | POST | Renames the account (signup rules + 30-day cooldown) and moves the session to the new name |
| `/auth/cuenta/email/solicitar` | POST | Step 1 of an email change: code to the **new** address, notification to the old one |
| `/auth/cuenta/email/confirmar` | POST | Step 2: verifies the code and writes the new address |
| `/auth/cuenta/password` | POST | Sets a new password (also how a Google account creates its first one) |
| `/auth/cuenta/eliminar` | POST | Deletes the account (anonymizes — see [Authentication](Authentication.md)); requires typing your own username |
| `/api/soporte`, `/api/soporte/<id>`, `/api/soporte/<id>/cerrar` | GET/POST | Player's side of a support thread — always scoped to `session['username']`, so nobody can read another user's ticket (Roadmap #13) |
| `/api/anuncios`, `/api/anuncios/<id>/leido` | GET/POST | Admin announcements the caller must see: pinned messages, unread one-shot notifications and the maintenance banner. Works **without** a session (guests get the public pinned ones) |
| `/admin` | GET | The admin panel page (`admin.html`); 403 without the `is_admin` flag |
| `/admin/api/**` | GET/POST | Panel API: `resumen`, `usuarios[/<id>/{ban,estadisticas,admin,reset_password,eliminar}]`, `salas[/<code>/cerrar]`, `descargas/{db,logs}`, `config`, `tickets`, `anuncios`, `auditoria`. All behind `admin_requerido`, all mutations written to `AdminAudit` (Roadmap #13) |
| `/api/a/latido`, `/api/a/evento` | POST | Audience measurement (Roadmap #24): visible-tab time and a fixed whitelist of UI events. Public, sessionless and cookieless — nothing is stored on the device, so no consent banner is needed. See [Analytics](Analytics.md) |
| `/admin/api/analitica/**` | GET/POST | Analytics panel API: `resumen`, `dimension`, `usuarios[/<id>]`, `retencion`, `en_vivo`, `csv`, `borrar`. Behind the same `admin_requerido` |
| `/auth/google/login`, `/auth/google/callback` | GET | Google OAuth via Authlib — active when `GOOGLE_CLIENT_ID`/`SECRET` are set (503 otherwise). `login` takes `?intent=login\|signup` (kept in the session): only `signup` may create an account; `login` with no match redirects to `/?auth_error=google_sin_cuenta`. See [Authentication](Authentication.md) |

An `after_request` hook sets 1-year immutable cache headers on `/static/img/*`, and
`no-store, no-cache, must-revalidate` (+ `Pragma`/`Expires`) on everything under `/auth/`
and `/api/`. The second half is not optional: without it a browser could reuse a stale
`/auth/sesion` response and show you as logged out right after logging in, or as logged
in right after logging out (Roadmap #22).

### Account settings (`/auth/cuenta/*`)

All six routes take the target user from `session['username']` — never from the request —
and reply `{exito, codigo, mensaje, …}` where `codigo` is a `dict.es`/`dict.en` key so the
client localizes it (`mensaje` is the Spanish fallback). Sensitive operations go through
`_autorizar_cambio(username, datos)`, which accepts **either** the current password
**or** a single-use code emailed to the account, kept in the same in-memory
`codigos_pendientes` dict as signup/reset codes but tagged `tipo: 'cuenta'` (email changes
use `tipo: 'cambio_email'`, keyed by the new address). Accounts created through Google have
no usable password — see [Authentication](Authentication.md).

## Socket.IO events (client → server)

| Event | Handler | What it does |
| :--- | :--- | :--- |
| `pedir_publicas` | `handle_pedir_publicas` | Re-broadcasts the public-games list |
| `crear_sala` | `handle_crear_sala` | Creates a room (4-char code), registers the creator, optionally public; emits `sala_creada` |
| `crear_partida_bot` | `handle_crear_partida_bot` | Creates a room already in `'jugando'` state with a `SmartBot` instance and fake SID `BOT_<code>`; starts the game immediately |
| `unirse_sala` | `handle_unirse_sala` | Joins by code. Contains seat-recovery logic: creators can reclaim seat 0 after a refresh, guests can fill vacated seats; blocks joining your own room with the same account and double-click races. When both seats are filled, builds `PartidaMus`, emits `iniciar_partida`, and sends the first state |
| `accion_juego` | `handle_accion_juego` | All in-game actions; delegates to `procesar_accion_interna` |
| `abandonar_sala_limpiamente` | `handle_abandonar_limpiamente` | Lobby cancel / end-of-match return: destroys the room (and its `BOT_*` entry) so `disconnect` won't notify the rival |
| `abandonar_partida` | `handle_abandonar_partida` | **Exit button** from the table (already confirmed client-side). vs-IA or finished match → room destroyed; live 1v1 → the seat is vacated and the rival is asked whether to wait |
| `esperar_reemplazo` | `handle_esperar_reemplazo` | The remaining player accepts waiting: the match starts being advertised as ongoing |
| `disconnect` | `handle_disconnect` | If waiting: seat becomes `None` and an orphan-room cleaner runs after 120 s. If playing: the room is **paused** for `GRACIA_RECONEXION_2P` (90 s) to allow reconnection; if the grace expires the seat becomes vacant instead of killing the game (see below) |

## Leaving a game and substitutions

Rooms have a fourth state, `'esperando_reemplazo'`, on top of `'esperando' | 'jugando' | 'pausada'`. A seat becomes vacant either because its player pressed the exit button (`abandonar_partida`) or because their 90 s reconnection grace ran out (`_programar_fin_gracia_2p`). In both cases `_abrir_hueco_2p` empties the seat and emits `jugador_abandono {nombre, motivo, espera}` to whoever is left.

- If nobody human is left the room is destroyed; otherwise it goes to `'esperando_reemplazo'` and is forced `publico = True` (a private room has to become visible or the seat could never be filled).
- The match is only listed once someone answers "wait" (`esperar_reemplazo` → `esperando_votos`), and only while a live player is sitting there.
- `unirse_sala` accepts these rooms and routes to `_sentar_reemplazo_2p`, which remaps the engine's sid (`_remap_sid_2p`, seat 0 = `motor.j1`, seat 1 = `motor.j2`), issues the newcomer a fresh reconnection token, and **keeps the score while re-dealing the round** — the player who left already saw those cards, and this avoids inheriting half-finished state (live raises, discards already made).
- `_programar_fin_espera_2p` ends the match after `ESPERA_REEMPLAZO` (300 s) with `rival_desconectado {motivo: 'sin_reemplazo'}`.
- Abandoning records **no result and no ELO** — persistence only happens at recuento, and it reads the username of whoever occupies the seat at that moment, so a substitute who finishes the match is credited normally.

The game is frozen throughout: `procesar_accion_interna` and the bot scheduler both require `estado == 'jugando'`.

## Room lifecycle and ghost-room sweeping

Every room carries `creada_en` and `ultima_actividad` (stamped on creation, on join, on every action in `procesar_accion_interna`, on resume, and when a substitute sits down). Two invariants keep dead rooms out of the way:

- **Nothing dead is advertised.** `emitir_lista_publicas` only lists a room that has at least one *live* seat, where `_sid_vivo(sid)` means: not `None`, not a fake `BOT_` sid, and still present in `jugadores`.
- **Every death path goes through `_destruir_sala_2p(codigo, motivo=None)`**, which pops the room, optionally emits `rival_desconectado`, sweeps **all** of `jugadores` for entries pointing at it (remapped sids and the `BOT_<code>` seat included) and calls `close_room`. Voluntary lobby exits share `_salir_de_sala_2p(sid)` — also used by `social.invitar_amigo` to evict a host who was already sitting somewhere else.

On top of the one-shot timers (`limpiar_sala_huerfana` 2 min, `_programar_fin_gracia_2p` 90 s, `_programar_fin_espera_2p` 300 s), a background sweeper `_barredor_2p` runs a `_pasada_barredor()` every `INTERVALO_BARRIDO` (300 s) as a safety net, mirroring `server_mus4._barredor`:

| State | Killed when |
| :--- | :--- |
| `esperando` | no live seat for > 2 min (`vacia_desde` grace, so a refresh still recovers the seat), or `ultima_actividad` older than `VIDA_MAX_ESPERANDO` (30 min) |
| `jugando` | idle for more than `VIDA_MAX_JUGANDO` (2 h) → `rival_desconectado {motivo: 'idle'}` |
| `pausada` | paused for more than twice the reconnection grace |
| `esperando_reemplazo` | waiting for more than twice `ESPERA_REEMPLAZO` |

The same pass drops orphan `jugadores` entries whose room exists in neither `salas` nor `server_mus4.salas4` (the two registries share this dict).

`GET /api/debug/salas?token=…` exposes all of it — per-room state, age, idle seconds, seat liveness, phase, round, plus totals and the orphan count. It **404s unless `DEBUG_TOKEN` is set** in the environment; it is meant to become the data source of the admin panel (Roadmap #13).

## Server → client events

- `sala_creada {codigo, token}` — room code (+ reconnection token) for the lobby "waiting" panel.
- `actualizar_publicas [rooms]` — public game list. Rooms in `esperando_reemplazo` carry `en_curso: true`, `marcador`, `partidas` and `expira_en` so the lobby can badge them as ongoing matches with a free seat.
- `jugador_abandono {nombre, motivo, espera}` — someone left (`motivo: 'abandono' | 'timeout'`); prompts the wait-or-leave dialog.
- `esperando_reemplazo {segundos}` — the wait was accepted; drives the countdown overlay.
- `reemplazo_encontrado {nombre}` — the seat was filled (by a substitute or by the original player reconnecting in time).
- `iniciar_partida` — switch to the game screen.
- `actualizar_mesa {payload}` — the full per-player game state (see below).
- `error_sala {mensaje}`, `rival_desconectado`.

## `procesar_accion_interna(sid, room, datos)`

Central dispatcher for game actions. Turn-gated actions: `repartir`, `mus`, `no_mus`, and betting (`pasar`, `envidar`, `subir`, `ver`, `ordago`, `nover` — with `cantidad` for raises). Non-turn-gated: `pedrete`, `descartar` (during the discard phase, each player acts once), `continuar_transicion` (dismisses transition messages), and `listo_siguiente_ronda` (when both players are ready, either advances the round with swapped roles or resets the game after 40 pts).

## `enviar_estado_a_jugadores(codigo)`

Builds one payload per human player and emits `actualizar_mesa` **to the whole room** with a `para_sid` field so each client filters its own copy (a workaround for per-SID delivery issues; note this means the rival's payload also reaches the browser — see *Known issues*). Every dereference of `jugadores` and of the engine's per-sid `estado` is defensive: a seat the engine no longer knows is skipped with a warning instead of raising `KeyError` mid-loop, which used to leave the table half-updated (a "frozen", ghost-looking game). Payload highlights:

- `mis_cartas` (full card objects) vs `cartas_rival` (the client only reveals them at recuento),
- `es_mi_turno`, `soy_mano`, `fase`, `mensaje` (localizable message codes like `fase_apuestas`),
- `apuestas` (current lance, pending raise, pots, fold concessions, `soy_quien_sube`, `juego_es_punto`),
- `recuento` (list of localized scoring steps with `gano_yo` flags),
- match info (`mis_partidas`, `partidas_rival`, `al_mejor_de`, `match_finalizado`),
- `puede_pedrete` (server-side check for the 4-5-6-7 hand).

This function also has two side effects:

1. **Result persistence:** on recuento, if the game was just won and not yet recorded, calls `base_datos.registrar_partida_completa(winner, loser)` (only affects ELO when both are registered users).
2. **Bot turn:** if the room has a bot, asks `SmartBot.obtener_accion(partida)`; if there is a move, spawns a background task that sleeps the `bot_delay` `Config` variable (default 1.5 s, clamped to 0–10, editable from `/admin`) and re-enters `procesar_accion_interna` as the bot. The task body is wrapped in `try/except` so a bot error cannot kill the greenlet and strand the table.

## Known issues / hardcoded values

- `SECRET_KEY`, SMTP and Google OAuth credentials now come from env vars / `.env` (a dev fallback `SECRET_KEY` is used with a warning if unset). ✅ resolved.
- Google OAuth is wired via Authlib and only needs real credentials to go live. ✅ resolved.
- Bot delay is the `bot_delay` `Config` variable (default 1.5 s), editable live from `/admin`. A per-room / per-player speed selector is still Roadmap #15.
- Do **not** re-`import base_datos` inside a function of `server.py`: it makes the name local to the whole function body and every other use of the module in it raises `UnboundLocalError`, killing the greenlet mid-update (this bit `enviar_estado_a_jugadores` and read as a frozen table).
- Disconnection mid-game no longer destroys the game: 90 s of grace to reconnect, then the seat is offered to a substitute for 5 more minutes. ✅ resolved.
- Ghost rooms (dead rooms in the lobby, orphan `jugadores` entries, frozen tables): all six Roadmap #21 vectors fixed — see *Room lifecycle and ghost-room sweeping* above. ✅ resolved.
- `codigos_pendientes` and the per-email rate-limit counters are in-memory: codes now expire after 15 min, but state is still lost on restart and not shared across processes (would need Redis if scaled beyond one eventlet worker).
- **Card visibility:** because `actualizar_mesa` is broadcast to the whole room and filtered client-side by `para_sid`, a modified client can read the opponent's `mis_cartas` from the socket. Not a ghost-room issue, but worth folding into the security pass (Roadmap #16) — the fix is per-SID emits, which the current comment says were unreliable and would need re-testing.

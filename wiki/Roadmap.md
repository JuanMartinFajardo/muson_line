# Roadmap

Implementation guide for planned CallMus features, written so an agent can pick up any item and execute it. Read [Architecture](Architecture.md) first; per-feature pages referenced where relevant.

**Conventions for all features:**
- Every user-visible string goes into both `dict.es` and `dict.en` in [static/app.js](../static/app.js) and is rendered via `t()` / `data-i18n`. Server → client messages that need localization are sent as `{code, ...params}` objects.
- New DB tables go in [base_datos.py](../base_datos.py) `init_db()` with `CREATE TABLE IF NOT EXISTS`.
- Secrets/config via `os.environ`, never hardcoded.
- Suggested priority order: ~~1 (login)~~ → ~~21 (bug fixes)~~ → ~~22 (settings menu)~~ → ~~23 (player codes)~~ → **14 (deck-exhausted notice) → 9 (turn timer) → 18 (resume bot games)** → ~~2 (tutorial i18n)~~ → ~~13 (admin)~~ → **16 (security) → 19 (stats)** → ~~3 (friends/groups)~~ → **4 (tournaments)** — then the rest.

---

## 1. Finish login implementation — ✅ DONE (2026-07-24)

**Current state:** implemented and verified end-to-end. See [Authentication](Authentication.md).
Email-verified signup, login by username **or** email, password recovery, and Google
OAuth all work; secrets are read from env vars / `.env`. See [log.md](../log.md) for the
change entry.

**What was done (all steps complete):**
1. ✅ **Schema + migration:** `email` and `google_id` columns added to `Usuarios`, with an
   automatic startup migration (`base_datos._migrar_columnas`, `PRAGMA table_info` → `ALTER
   TABLE` + unique indexes) so existing `mus.db` files keep working.
2. ✅ **Imports fixed in `server.py`:** `redirect, url_for` imported for the Google callback.
3. ✅ **Secrets in env vars:** `SECRET_KEY`, `SMTP_USER`, `SMTP_PASS`, `GOOGLE_CLIENT_ID`,
   `GOOGLE_CLIENT_SECRET`, with startup warnings when missing. See `.env.example` and
   [Setup-and-Deployment](Setup-and-Deployment.md).
4. ✅ **Google OAuth end-to-end:** Authlib flow wired (`registrar_o_loguear_google`), Google
   button on **both** login and signup modals. Only needs real credentials (owner task).
5. ✅ **Pre-check duplicates:** `base_datos.existe_usuario(username, email)` is called in
   `/auth/solicitar_codigo` so duplicates are reported *before* a code is sent.
6. ✅ **Code lifecycle:** codes carry a timestamp, expire after 15 min, and are rate-limited
   to 3 requests per email per hour.
7. ✅ **Password reset:** `/auth/solicitar_reset` + `/auth/reset` endpoints; "Forgot
   password?" link → 2-step recovery modal.
8. ✅ **i18n cleanup:** all auth strings moved to the `dict`/`t()` in `app.js` (es + en).
9. ✅ **Validation** (client + server): password ≥ 6, email regex, username 3–20 chars.

**Remaining (owner-only, external accounts — not code):** create the Gmail app password
for `callmus.contact@gmail.com` (`SMTP_PASS`), create the Google Cloud OAuth credentials
(`GOOGLE_CLIENT_ID`/`SECRET`), and set a random `SECRET_KEY` in production.

**Acceptance:** ✅ on a fresh clone with a fresh DB and env vars set, a user can sign up with
email verification, log in/out (by username or email), log in with Google, and reset a
password; ELO records after a logged 1v1 game.

---

## 2. Translate the tutorial — ✅ DONE (2026-07-24)

**Current state:** implemented and verified in-browser. [static/tutorial.js](../static/tutorial.js) is now
fully bilingual (ES/EN). Note the original assumption was inverted: the ~700-line tutorial was
hardcoded in **English**, while the app defaults to Spanish — so the real work was adding the
Spanish translation and wiring the tutorial into the existing language engine.

**What was done (chosen pattern: `dictTutorial` inside `tutorial.js`):**
1. ✅ All slide content (14 slides × title + body HTML) moved into a `dictTutorial = {es:[...], en:[...]}`
   object inside `tutorial.js`, keyed by the global `langActual` variable from `app.js` — a single
   source of truth for the current language, reusing (not duplicating) the existing
   `localStorage['callmus_lang']` logic. Both arrays keep the same slide count/order so the
   practice-slide skip (index 8) and `goToSlide(9)` deep-link stay valid.
2. ✅ `getSlides()` / `getTutBtns()` return the active-language slides and nav-button labels
   (Next/Prev/Finish); `renderSlide()` reads from them and localizes both nav buttons.
3. ✅ HTML markup stays inline in the dict (same approach as `privacy_p1` in `app.js`).
4. ✅ Live re-render: a listener on `#btn-lang` calls `renderSlide(currentSlideIndex)` when the
   tutorial modal is open (app.js flips `langActual` first, so the tutorial picks up the new value).
5. ✅ Terminology kept consistent with the game UI: Grande, Chica, Pares, Juego, Órdago, Mano,
   Postre, Pedrete, La Real left as proper nouns; native Spanish betting verbs used
   (envidar/paso/quiero/no quiero); pares tiers rendered as Pares/Medias/Duples.
6. ✅ The *How to Play* launcher button (`index.html`) is now localized via
   `data-i18n="btn_tutorial"` + a `btn_tutorial` key in both `dict.es` and `dict.en`.

**Acceptance:** ✅ launching the tutorial in EN shows fully English content and in ES fully Spanish;
toggling the language button live-switches the open tutorial (verified: "The Spanish Deck" ↔ "La
Baraja Española", nav button ↔ "Siguiente →") without closing it; no cross-language literals remain.

---

## 3. Friends, messaging, groups, and group leaderboards — ✅ DONE (2026-07-24)

**Current state:** implemented and verified end-to-end. Registered users can add friends,
chat in real time and offline, form groups, chat in groups, see a group-only ELO
leaderboard, and invite a friend straight into a game. See [log.md](../log.md) for the
change entry and [Implementing-Friends-Messaging-Groups](Implementing-Friends-Messaging-Groups.md)
for the design that was followed.

**What was done:**
- **Schema (`base_datos.py` `init_db()`):** `Friendships` (canonical `user_low`/`user_high`),
  `Messages` (DMs + group), `Groups` (+ `invite_policy`), `GroupMembers` (`last_read_id`
  cursor), and `Partidas` (per-match history) + indexes, all `CREATE TABLE IF NOT EXISTS`;
  plus the full set of data functions (friendships, DMs with unread counts, groups with
  owner-transfer-on-leave, role management, and a **group-scoped** `leaderboard_grupo`).
  Limits: 200 friends, 50 groups, message ≤ 500.
- **Group-scoped leaderboard:** the group ELO/winrate is **not** the global stats filtered by
  membership — it is computed from scratch (base 1200) replaying only the matches played
  *between group members* and *after both joined the group* (`Partidas.fecha >= joined_at`),
  recorded by `registrar_partida_completa`. A subtle `ⓘ` button with a light hover/tap
  tooltip explains this in the leaderboard view.
- **Group admin/roles & permissions:** owner/admins can promote members to admin, demote
  admins to member, and remove members — never the original owner; a per-group
  `invite_policy` (`admins`|`all`, admin-editable) governs who may add members.
- **`social.py` (new, additive Blueprint-style module):** `init_social(app, socketio, ctx)`
  registers all session-gated `/api/friends*`, `/api/messages/<id>`, `/api/groups*` routes;
  presence via `usuarios_conectados`; a `notificar` helper and `notificacion` types
  (`mensaje`, `mensaje_grupo`, `solicitud_amistad`, `amistad_aceptada`, `presencia`,
  `invitacion_grupo`, `invitacion_partida`); and an `invitar_amigo` socket event that
  creates a private room reusing `crear_sala` internals. Persist-first, notify-if-online.
- **`server.py`:** wires `social.init_social(...)`; the game `disconnect` handler calls
  `social.presencia_disconnect()` (Flask-SocketIO 5.x allows only one handler per event).
- **Frontend:** `index.html` gains the **👥 Amigos** button (unread badge), `#modal-social`
  (Friends/Groups tabs), a toast and an incoming game-invite popup; new `static/social.js`
  holds all social UI (message bodies rendered via `textContent`, never `innerHTML`);
  `app.js` gets the i18n keys (es+en) and `cerrarModales()` hides the social modal.

**Acceptance:** ✅ two logged users befriend each other, chat live and offline (with unread
badges), form a group, see a group-only ELO table, and start a game via invite; server-side
abuse checks (DM to non-friend, self-add, over-length, foreign-group read, no-auth) all
reject correctly.



---


<summary>Original plan (kept for reference)</summary>

**Current state:** no social features; only a global leaderboard (`/api/leaderboard`).

**Design:** all persistent, so this is primarily DB + REST + a Socket.IO presence/notification layer. Requires login (guests excluded).

**Schema (new tables in `base_datos.py`):**
```sql
Friendships(id, user_a INTEGER, user_b INTEGER, status TEXT('pending'|'accepted'), requested_by INTEGER, created_at TEXT, UNIQUE(user_a,user_b))
Messages(id, sender_id INTEGER, recipient_id INTEGER NULL, group_id INTEGER NULL, body TEXT, created_at TEXT, read INTEGER DEFAULT 0)
Groups(id, name TEXT UNIQUE, owner_id INTEGER, created_at TEXT)
GroupMembers(group_id, user_id, role TEXT('owner'|'member'), joined_at TEXT, UNIQUE(group_id,user_id))
```
Store user IDs (add lookups by `Usuarios.id`), not usernames.

**Backend steps:**

1. REST endpoints (all session-gated): `POST /api/friends/request`, `POST /api/friends/respond` (accept/decline), `GET /api/friends` (list + online status), `DELETE /api/friends/<id>`; `GET/POST /api/messages/<friend_id>` (paginated, e.g. 50 latest); `POST /api/groups`, `POST /api/groups/<id>/invite`, `POST /api/groups/<id>/join`, `GET /api/groups/<id>/leaderboard`, `GET/POST /api/groups/<id>/messages`.
2. **Presence:** maintain `usuarios_conectados = {username: sid}` updated on Socket.IO `connect`/`disconnect` (read `session.get('username')` in the connect handler). Used for online dots and real-time delivery.
3. **Real-time events:** on new message / friend request / game invite, if the recipient is connected, `socketio.emit('notificacion', {...}, room=their_sid)`. Messages are always persisted first (delivery on next login for offline users: unread counts from `Messages.read`).
4. **Friend game invites:** `POST /api/friends/<id>/invite` creates a room exactly like `crear_sala` (private) and sends a notification containing the code; the invitee's client joins with the normal `unirse_sala` flow.
5. **Group leaderboard:** the global leaderboard query filtered by `GroupMembers` — reuse `obtener_leaderboard()` with an optional `group_id` filter.
6. Validation & abuse limits: max 100 friends, max 50 groups membership, message length ≤ 500 chars, basic rate-limit on message sends.

**Frontend steps:**
1. New lobby side panel (or modal) "Friends" with tabs: *Friends* (list, online dot, buttons: message / invite to game / remove), *Requests*, *Groups* (list, create, group chat, group leaderboard table reusing the leaderboard modal renderer).
2. Chat UI: simple scrollable message list + input, per friend/group; unread badges on the Friends button.
3. All strings in both dict languages.

**Acceptance:** two logged users can befriend each other, chat in real time and offline, form a group, see a group-only ELO table, and start a game via invite.



---


## 4. Tournaments

**Depends on:** #1 (login), #3 (groups for group tournaments).

**Three variants sharing one core:** (a) **periodic tournaments** (auto-created on a schedule, open to all), (b) **friend-group tournaments** (created by a group owner for members), (c) **special tournaments** (admin-created, open to all, limited capacity).

**Schema:**
```sql
Tournaments(id, name, type TEXT('periodic'|'group'|'special'), group_id NULL, capacity INTEGER,
            status TEXT('registration'|'running'|'finished'), format TEXT('single_elim'),
            best_of INTEGER, starts_at TEXT, created_by INTEGER, created_at TEXT)
TournamentPlayers(tournament_id, user_id, seed INTEGER, eliminated INTEGER DEFAULT 0, UNIQUE(tournament_id,user_id))
TournamentMatches(id, tournament_id, round INTEGER, slot INTEGER, player1_id NULL, player2_id NULL,
                  winner_id NULL, room_code TEXT NULL, status TEXT('waiting'|'playing'|'done'|'walkover'))
```

**Backend steps:**
1. **Tournament manager module** (`torneos.py`): create tournament, register/unregister player, generate a **single-elimination bracket** when registration closes (seed by ELO; byes for non-power-of-2 counts), advance winners, detect champion.
2. **Match orchestration:** when both players of a `TournamentMatches` row are online, create a private room (reuse room creation with a flag `torneo_match_id`); on game end in `enviar_estado_a_jugadores`'s persistence block, if the room carries a tournament match ID, record the winner and advance the bracket. **Walkovers:** if a player doesn't show up within a deadline (e.g. 10 min after the round opens), the present player advances; if neither shows, higher seed advances.
3. **Scheduling for periodic tournaments:** a background task (eventlet `socketio.start_background_task` loop checking every minute, or APScheduler) that creates e.g. a daily tournament at a fixed hour and closes registration at start time.
4. **Special tournaments:** created from the admin panel (#13) with a capacity; registration closes at capacity or start time.
5. REST: `GET /api/torneos` (list by status), `POST /api/torneos/<id>/inscribirse`, `GET /api/torneos/<id>` (bracket JSON), plus group-owner creation endpoint.
6. Notifications through the #3 notification channel ("your match is ready, opponent: X").

**Frontend:** a "Tournaments" lobby section listing open/running tournaments with join buttons, and a bracket view (simple CSS grid of rounds/columns is enough; no library needed). Show "your next match" prominently with a *Play now* button that joins the prepared room.

**Acceptance:** 4 test users can join a special tournament, the bracket auto-generates, matches launch as normal games, results propagate, and a champion is declared; a daily periodic tournament self-creates.

---

## 5. Special decks and deck-builder menu

**Goal:** cosmetic (and later maybe rule-altering) card skins; players compose a custom deck by choosing which art each card uses.

**Current mechanism:** card images resolve server-side in `crear_baraja()` via `obtener_ruta_imagen(f"card_{palo_en}_{valor:02d}")`. There are already hints of alternate skins in `mus_mecanicas.py` (comments `Oros_btc`, `Copas_pirate`).

**Steps:**
1. **Asset organization:** `static/img/decks/<deck_id>/card_<suit>_<NN>.webp` plus `card_back.webp`; keep the current set as `decks/classic/`. A `decks.json` manifest (id, display name, unlocked-by-default flag).
2. **Make skins purely client-side** (recommended — avoids touching the engine): the server keeps sending logical card identity (`valor`, `palo`); the client maps `(palo, valor) → image path` using the player's selected deck instead of using the `img` field. Update `app.js` render functions and the preloader; keep `img` in payloads for backward compat, then remove.
3. **Deck-builder UI:** new modal "My deck": a 40-card grid; for each card (or per-suit / whole-deck for v1) pick among unlocked skins; save selection. **Persistence:** localStorage for guests, plus a `Usuarios.deck_config TEXT` (JSON) column for logged users with `GET/POST /api/deck` endpoints.
4. Each player sees **their own** deck skin for all cards on the table (opponent's choice is irrelevant client-side).
5. Card back selection included.

**Acceptance:** a player picks a mixed custom deck, plays a game seeing their skins, reloads and (if logged in) keeps the config on another device.

---

## 6. Mus for 4 players (online only, no bots) — ✅ DONE (2026-07-24)

**Current state:** implemented and verified end-to-end (2v2, online, no bots). New parallel
engine `PartidaMus4` (`mus_mecanicas_4.py`, seat-keyed, per-team scoring) built on shared
pure functions in `mus_core.py`; server handlers in `server_mus4.py` (separate `salas4`
registry, seat↔sid map, `*_4` events, blind per-seat state, authoritative turn timer,
reconnect grace, ghost sweeper); frontend in `static/app4.js` + `static/table4.js` +
`static/style4.css` (4-seat table relative to the viewer, seat picker, animations, full
ES/EN i18n). Match results (final score, e.g. 2-1) recorded in the new `Partidas4` table
plus per-player 4p tallies on `Usuarios`, separate from 1v1 ELO (explained by a note in the
Leaderboard). 2p mode untouched (regression-tested). See [log.md](../log.md) and
[Implementing-Mus-4-Players](Implementing-Mus-4-Players.md). Bots (#7/#8) remain future work.

**Acceptance:** ✅ four Socket.IO clients play a complete 4p match (best-of-1 and best-of-3)
with correct lance resolution and team scoring; disconnect pauses the room and a token-based
reanudar restores the seat within the grace window; the `Partidas4` row is written; a full 2p
game still fires `rival_desconectado` on drop; table/showdown render verified in-browser (ES/EN).

<details><summary>Original plan (kept for reference)</summary>

**The largest gameplay feature.** The whole engine assumes 2 players; 4-player Mus is the traditional 2v2 partnership game with different rules (speaking order around the table, partners, señas are usually excluded online, all four declare Pares/Juego, discards refill order, "de paso" points, and scoring flows to the team).

**Recommendation: build a new engine class `PartidaMus4` in a new file `mus_mecanicas_4.py`** rather than generalizing `PartidaMus` — the 2-player engine is stable and heavily used by training code; don't destabilize it. Extract genuinely shared pure functions (`crear_baraja`, `get_valores_mus`, `get_pares_info`, `get_suma_juego`, `comparar_cartas` adapted to return orderings, `J_RANK`) into a shared module `mus_core.py` imported by both.

**Engine design (`PartidaMus4`):**
1. State: 4 sids in table order; teams = (seat0, seat2) vs (seat1, seat3); `id_mano` rotates one seat per round; points are **per team**.
2. Mus phase: all four must agree to mus; any single "no mus" cuts.
3. Betting: within each lance, speaking starts at mano and proceeds in order; a bet is answered by the opposing **team** (either member can call/raise/fold per standard 2v2 rules — for v1, simplify: the team member with the turn responds). Comparisons at showdown: best hand of team A vs best of team B per lance, with positional tie-breaking (closer to mano wins ties).
4. Pares/Juego declarations by all four in order; a lance is only bet if both teams have at least one qualifying player.
5. Scoring: bonuses counted for **every qualifying hand of the winning team** (e.g. both partners' pairs score), per traditional rules.
6. Reuse the JSONL logging structure with a `modo: '4p'` field (needed later for the 4p bot, #7).

**Server steps:**
1. Room creation: `crear_sala` gains a `modo: '2p'|'4p'` parameter; 4p rooms wait for 4 sids; seat/team selection UI in the waiting panel (players pick seat 0–3; creator can shuffle).
2. `procesar_accion_interna` and `enviar_estado_a_jugadores` branch on room mode. The 4p payload includes all four names, team scores, partner's discard counts, and whose turn — but **never partner cards** (no señas support in v1).
3. Disconnect handling: destroy the game (as in 2p) for v1.

**Frontend steps:** the game screen needs a 4-seat layout (partner top, opponents left/right), team score display, and declaration indicators. This is a big `app.js` change — consider extracting the table renderer into `static/table4.js`.

**Acceptance:** four browsers play a complete 4p game to 40 with correct lance resolution and team scoring; 2p mode is untouched (regression-test it).

</details>

---

## 7. Bot for 4-player Mus

**Depends on:** #6. **Do not block #6 on this.**

**Steps:**
1. **Heuristic bot first (`SmartBot4` v1):** reuse the EV tables (`mus_data.json` probabilities are per-hand and remain valid approximations), the discard chooser, and simple betting rules (bet with top-X% hands, call by pot odds against hand percentile, órdago near 40). This is enough for a playable experience.
2. **Learned bot (v2):** extend the Deep CFR pipeline: new state encoder (~30+ dims: 4 positions, team points, partner discard counts, declarations, per-lance pots/owners), `MusBettingEnv4` wrapping `PartidaMus4`, new `train_cfr_4.py` generation. Note CFR convergence guarantees weaken for >2 players — accept an approximate strategy; validate via arena vs the heuristic bot.
3. Integration mirrors 2p: fake `BOT_` sids, `obtener_accion(partida4)` per bot seat, same background-task scheduling in `enviar_estado_a_jugadores`.

**Acceptance:** a 4p room with 1–3 heuristic bots completes games without illegal moves.

---

## 8. Mixed online + bots mode (4-player)

**Depends on:** #6 and #7.

**Steps:**
1. In the 4p waiting panel, the creator can toggle each empty seat to "Bot"; a *Start with bots* button becomes enabled when all seats are human-or-bot and ≥1 human.
2. Server: on start, fill empty seats with `SmartBot4` instances (fake sids `BOT_<code>_<seat>`), reusing `crear_partida_bot`'s pattern; the room stores a `bots: {sid: SmartBot4}` map and the bot-turn scheduler iterates all bots.
3. Human disconnect mid-game: v1 destroys the game; v2 (nice-to-have) replaces the leaver with a bot after a grace period — design the room structure so a seat's controller (human sid vs bot instance) is swappable.

**Acceptance:** 2 humans + 2 bots play a full match; bot fills are visible in the UI ("🤖 Bot" name tags).

---

## 9. Turn timer for online play (10-second auto pass/fold)

**Goal:** in **online (human vs human) games only** — not vs bot — a player who takes more than N seconds (default 10; consider 15–20 for beginners, make it a room option) auto-acts: **pass** if no bet is pending, **fold (no ver)** if facing a bet, **no mus** in the mus phase, and auto-discard-nothing… (discard requires ≥1 card: auto-discard a random/worst single card, or auto-ready with the currently selected cards).

**Server implementation (authoritative — never trust client timers):**
1. In `enviar_estado_a_jugadores`, whenever it's a human's turn in an online room, record `sala['turno_deadline'] = time.time() + TURNO_SEGUNDOS` and a monotonically increasing `sala['turno_token']` (increment on every state change).
2. Start a background task: `socketio.sleep(TURNO_SEGUNDOS)`, then if the room still exists, is playing, and `turno_token` is unchanged (the player hasn't acted), inject the default action through `procesar_accion_interna(sid, room, accion_por_defecto)`. The token check makes stale timers harmless — no cancellation machinery needed.
3. Default action chooser: a small function mapping `(fase, subida_pendiente)` → action, honoring the forced-call rule (folding when the fold concedes the game auto-converts anyway in the engine).
4. Discard phase is not turn-based (both act in parallel): give each non-ready player their own deadline.
5. Exempt: bot rooms, transition acknowledgements (`continuar_transicion` — or auto-continue those after 5 s too), and `listo_siguiente_ronda` (use a longer 60 s timeout there so a distracted player doesn't stall the rival forever).

**Frontend:** payload gains `turno_deadline_epoch` (or remaining seconds); render a countdown bar/number near the action buttons; flash under 3 s. Strings in both languages.

**Acceptance:** in an online game, letting the timer expire passes/folds automatically and the game continues; timers never fire for a player who already acted; bot games unaffected.

---

## 10. Android/iOS app

**Recommendation: don't build native yet.** The game is a websocket web app; the cheapest credible path:

1. **Phase 1 — PWA:** the manifest already exists (`static/favicon_io/site.webmanifest`) — flesh it out (name, theme color, icons, `display: standalone`), add a service worker caching the static shell + card images (network-first for `index.html`, cache-first for `/static/img/`), verify installability with Lighthouse. Gives "add to home screen" on both platforms for near-zero cost.
2. **Phase 2 — store presence via wrapper:** use **Capacitor** to wrap the deployed URL (or the static bundle pointing at the production server). Repo layout: a `mobile/` folder with the Capacitor project; the web code needs: viewport-safe-area CSS, touch-target audit (≥44px), disabling pinch-zoom on the table, and handling app-background/websocket-reconnect (Socket.IO auto-reconnect + re-join room by code — this pairs with #18's reconnection work).
3. Account requirements: Apple requires "Sign in with Apple" if Google login is offered — plan for it (Authlib supports it) before iOS submission.
4. **Native (Phase 3, only if warranted):** not recommended; would mean rebuilding the UI in React Native/Flutter against the same Socket.IO protocol.

**Acceptance (Phase 1):** Lighthouse PWA checks pass; the app installs on Android/iOS home screens and plays a full game.

---

## 11. Animations

**Goal:** juice up the table: dealing, discarding/drawing, chip/point movement, órdago drama, card flip at showdown.

**Steps:**
1. Pure CSS/JS in `app.js`/`style.css` — no library needed (or use the tiny FLIP technique). Key animations, in value order:
   - **Deal:** cards fly from a deck position to each hand slot with staggered delays (CSS `transition: transform` from a start position).
   - **Discard/draw:** selected cards slide to the discard pile; replacements fly in.
   - **Showdown flip:** opponent cards 3D-flip (`rotateY`) when revealed at recuento.
   - **Point gain:** floating `+N` text over the score that fades up.
   - **Órdago:** table shake + red flash overlay.
   - **Turn pulse:** already exists (`anim-parpadeo`) — keep.
2. Architectural prerequisite: the client currently **repaints everything** on each `actualizar_mesa`. Animations need diffing: keep the previous payload, compare card arrays/scores, and only animate deltas. Wrap this in a `renderMesa(prev, next)` function — do this refactor first.
3. Respect `prefers-reduced-motion`; add a settings toggle (localStorage) to disable animations.
4. Keep every animation ≤ 600 ms so they never block input; game state must never depend on animation completion.

**Acceptance:** dealing, discarding, showdown, and scoring visibly animate; disabling animations restores instant rendering; no desync (spam-clicking during animations can't break state).

---

## 12. Bot personality settings (aggressive, conservative, musero, …)

**Current hooks:** `SmartBot.update_meta_variables()` already randomizes `musero`, `bluffer`, `aleatorio`, `fish` each hand ([Bot-AI](Bot-AI.md)).

**Steps:**
1. Define presets in `bot_ml.py`:
   ```python
   PERSONALIDADES = {
     'equilibrado':  None,  # current random behavior
     'agresivo':     {'musero': 0.3, 'bluffer': 0.35, 'aleatorio': 0.2, 'fish': 0.1, 'bias_apuesta': +0.15},
     'conservador':  {'musero': 0.8, 'bluffer': 0.05, 'aleatorio': 0.1, 'fish': 0.05, 'bias_apuesta': -0.15},
     'musero':       {'musero': 1.2, 'bluffer': 0.15, 'aleatorio': 0.2, 'fish': 0.1, 'bias_apuesta': 0.0},
     'caotico':      {'musero': None, 'bluffer': 0.5, 'aleatorio': 0.6, 'fish': 0.4, 'bias_apuesta': 0.0},
   }
   ```
   `SmartBot(sid, personalidad='equilibrado')`; fixed values replace the per-hand re-roll (keep re-rolling any field set to `None`).
2. **`bias_apuesta`** — a new post-processing step in `decidir_apuesta_cfr`: after masking/renormalizing, shift probability mass toward aggressive actions (`envidar/subir/ordago`) or passive ones (`pasar/ver/nover`) by the bias factor, then renormalize. This keeps the Nash strategy as the base and tilts it.
3. Wire through: `crear_partida_bot` accepts `personalidad` from the client; lobby UI adds a personality dropdown next to *Play vs bot* (strings in both languages, with short descriptions).
4. Log the personality in the JSONL (`detalles`) for later analysis.

**Acceptance:** selecting "aggressive" produces measurably more bids/órdagos over ~20 hands than "conservative" (eyeball via logs); default behavior unchanged.

---

## 13. Online admin panel — ✅ DONE (2026-07-25)

**Current state:** implemented and verified end-to-end. `/admin` is a server-rendered
panel with seven views (Resumen, Cuentas, Salas, Soporte, Anuncios, Variables y bot,
Datos, Auditoría); players get a **Support & contact** section inside Settings and see
the admin's pinned/one-shot announcements in the lobby. See [log.md](../log.md) for the
change entry.

**Answer to the deployment question below: no extra deployment.** `admin.py` is an
additive module hooked into the **same Flask process, port and session** as the game
(`init_admin(app, socketio, ctx)`, the `social.py` pattern). The only new environment
variable is `ADMIN_USERNAME`, which promotes the **first** admin at startup; after that
the flag is granted from the panel itself and the variable can be left empty.

**What was done:**
1. ✅ **Auth:** `is_admin`, `banned`, `ban_motivo`, `ban_en` added to `Usuarios` by the
   idempotent migration; `admin_requerido` decorator (403, never leaking whether a route
   exists); `ADMIN_USERNAME` bootstrap. A ban bites in three places — `/auth/login`
   (with reason), `/auth/sesion` (clears an already-open cookie) and the single `connect`
   handler in `social.py` (returns `False`, refusing the socket) — and banning also drops
   the account's live sockets and evicts it from its room.
2. ✅ **`admin.py` + `admin.html`** (Spanish-only: it is the owner's internal tool; every
   *player-facing* string added — support and announcements — is in `dict.es`/`dict.en`).
   - **Accounts:** search by name/email/`#code`; ban/unban with reason; edit ELO/wins/
     losses; grant or revoke admin (never leaving zero admins, never banning an admin);
     delete (reuses `anonimizar_usuario`, so rivals' history survives); "send password
     code", which sets **no** password — it emails the same recovery code as the normal
     "forgot password" flow, so an admin never learns anyone's password.
   - **Live ops:** unified snapshot of `salas` (2p) and `salas4` (4p) with state, phase,
     occupants, age and idle time, plus force-close. `/api/debug/salas` stays as-is.
   - **Data download:** `mus.db` via SQLite's backup API (safe with the server running)
     and a date-filterable zip of `logs/`.
   - **Bot settings:** dropdown over `learn/cfr/*.pth`; the choice lives in the new
     `Config` table and `bot_ml.ruta_checkpoint_activa()` reads it, accepting only a
     filename inside `learn/cfr` and falling back to the default if it is gone. The model
     is cached **process-wide** (it used to be re-read from disk per `SmartBot`) and the
     panel calls `invalidar_modelo_cacheado()` so the swap needs no restart.
   - **Global variables:** generic `Config` editor. Wired today: `bot_checkpoint`,
     `bot_delay` (#15), `mantenimiento_activo`, `mantenimiento_texto`. Free keys can be
     created for the future; the table marks which ones actually have a reader — the
     turn-timer (#9) and tournament (#4) keys will land with those features.
   - **Stats overview:** users, signups today, 1v1/2v2 games, live rooms, connections.
3. ✅ **Security:** in-memory rate limits on the player-facing support routes, and every
   admin action written to `AdminAudit` (date, admin, action, target, detail, IP honouring
   `X-Forwarded-For` for the future proxy of #16). HTTPS itself remains #16.
4. ✅ **Support with conversation:** `SupportTickets` + `SupportMessages`; a **Support &
   contact** section in the player's Settings window (visible with and without an account;
   guests are told an account is needed so they can be answered). The thread goes back and
   forth until either side marks it solved, and the state moves itself — `respondido` when
   the admin writes, `abierto` when the player does — so the panel's inbox always shows
   what is still pending. Unread badge on ⚙ and live delivery over the #3 `notificacion`
   channel.
5. ✅ **Announcements:** `Anuncios` + `AnuncioLeido`, two shapes — **notification** (one
   popup, marked read per account, so an offline player still gets it on return) and
   **pinned message** (stays in the lobby until it expires or is unpinned). Audience:
   everyone, one #3 group, or a list of names/`#codes`. The maintenance banner comes from
   the `mantenimiento_*` variables and reaches guests too.

**Found and fixed along the way (both pre-existing, unrelated to the panel):** a repeated
`import base_datos` *inside* `enviar_estado_a_jugadores` made the name local to the whole
function (`UnboundLocalError` → dead greenlet → frozen game), and `mus_mecanicas.py` wrote
`logs/*.jsonl` with `json.dumps` without importing `json` at module level, so **every log
file was empty** — which would have made the panel's log download useless.

**Acceptance:** ✅ an admin logs into `/admin`, bans a user (who is kicked off instantly,
cannot log in and cannot open a socket), swaps the bot checkpoint without restarting,
downloads the DB and the logs, and kills a stuck room; non-admins get 403. Verified with
scripted end-to-end runs plus in-browser checks of the panel, the support window, the
live announcement popup and the maintenance banner; regression: a full game vs the bot
still plays to 40.

<details><summary>Original plan (kept for reference)</summary>

**Goal:** manage accounts, download data, tune the bot, and change global variables from the browser instead of SSH.

**Steps:**
1. **Auth:** add `is_admin INTEGER DEFAULT 0` to `Usuarios` (migration like #1). A `@admin_required` decorator checking `session['username']` → DB `is_admin`. Bootstrap the first admin via env var (`ADMIN_USERNAME` promoted at startup) or a one-off CLI flag.
2. **Blueprint `admin.py`** mounted at `/admin` with a minimal server-rendered page (a separate `admin.html` template is fine — no need to touch the game SPA):
   - **Accounts:** search/list users; reset password (send a code), edit ELO/wins, delete account, ban flag (add `banned INTEGER DEFAULT 0`; check it in `auth_login` and on socket connect).
   - **Live ops:** list active rooms (`salas`) with state, age, players; force-close a room (emit an error to occupants and delete — also the manual fix for ghost games until #21 lands).
   - **Data download:** download `mus.db` (backup) and a zip of `logs/` (`send_file`); date-filtered log export.
   - **Bot settings:** dropdown of available checkpoints in `learn/cfr/` (list `*.pth`), select the active one — store the selection in a new `config` table (`key TEXT PRIMARY KEY, value TEXT`) and make `SmartBot.__init__` read it (cache the loaded model process-wide, reload when changed). Also expose default personality and bot delay (#15).
   - **Global variables:** a generic editor over the `config` table: turn-timer seconds (#9), tournament schedule (#4), maintenance-mode banner text.
   - **Stats overview:** counts of users, games today, active rooms.
1. **Security:** admin routes must also be rate-limited and behind HTTPS (see #16); log every admin action to an `AdminAudit` table.
2. Add a feedback/support/bug report menu, where you see all support-requestig messages by user. For that you need to add to the settings menu of players a button saying support or something like that. And that allows them to report a bug or send a message to the admin. And then from the admin menu, admin can read and answer those messages and keep conversations until admin or user considers the issue fixed.
3. Add a notifications menu where you can send a message to all (or a selected group of) players. You can either send a notification or pin a message in some suitable section in the main menu for a determined period of time (or until choose to unpin)

**Acceptance:** an admin can log into `/admin`, ban a user (who then can't log in), swap the bot checkpoint without restarting, download the DB, and kill a stuck room. Non-admins get 403.

I need to know if this admin mode requires extra deployment in the server, or just runs together with server.py

</details>

---

## 14. "Deck exhausted" notice

**Current behavior:** `PartidaMus.robar()` silently reshuffles the discard pile when the draw pile empties. Players sometimes get confused when repeated mus rounds exhaust the deck.

**Steps:**
1. In `robar()`, when the reshuffle branch triggers, set a flag: `self.baraja_agotada_aviso = True`.
2. In `enviar_estado_a_jugadores`, include it in the payload once and reset it (`aviso_baraja: True`), or reuse the existing `mensaje_transicion` mechanism with a new code: `{'code': 'baraja_agotada'}` — the transition path is preferable because the client already renders those as dismissable notices.
3. Client: add `msg_baraja_agotada` to both dicts — ES: "¡Se ha acabado la baraja! Se barajan los descartes."; EN: "The deck ran out! Reshuffling the discards." Render as a brief toast/transition (auto-dismiss ~2.5 s; don't require a click, it shouldn't interrupt flow).
4. Rare edge: the reshuffle can happen mid-discard for both players; ensure the notice shows to both (room-wide flag, not per-player).

**Acceptance:** playing many consecutive mus rounds triggers the notice exactly when the reshuffle happens, in the player's language, without blocking play.

---

## 15. Speed setting (bot execution speed)

**Current behavior:** the bot's "thinking" delay is hardcoded — `socketio.sleep(1.5)` inside `bot_action_task` in `server.py`.

**Steps:**
1. Store delay per room: `salas[codigo]['bot_delay']`, default 1.5.
2. `crear_partida_bot` accepts `velocidad` from the client: map `'lenta'→2.5, 'normal'→1.5, 'rapida'→0.6, 'instantanea'→0.05` (define server-side; validate input).
3. Lobby UI: a speed selector (radio or dropdown) next to *Play vs bot*; persist choice in localStorage. Strings in both languages.
4. Optional live control: a speed button on the game screen emitting `accion_juego {accion: 'set_velocidad'}` (validated to the allowed set, bot rooms only).
5. Also make the global default admin-editable via the `config` table (#13).

**Acceptance:** "instant" makes full bot rounds resolve in ~a second; "slow" is comfortable for beginners; online games unaffected.

---

## 16. Security hardening (Cloudflare, etc.)

**Steps (roughly in order of value):**
1. **Secrets to env vars** (covered in #1) — the true prerequisite.
2. **Reverse proxy + TLS:** put the eventlet server behind **nginx** (or Caddy) with HTTPS; proxy WebSocket upgrade headers (`proxy_set_header Upgrade/Connection`). Set `SESSION_COOKIE_SECURE=True`, `SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SAMESITE='Lax'`.
3. **Cloudflare in front:** orange-cloud the DNS record (Cloudflare supports WebSockets on all plans). Configure: SSL "Full (strict)", a WAF rate-limiting rule on `/auth/*` (e.g. 10 req/min/IP), bot-fight mode, and restore real client IPs in nginx (`CF-Connecting-IP`) for logging/rate limits.
4. **App-level rate limiting:** Flask-Limiter on `/auth/login`, `/auth/solicitar_codigo`, `/auth/registro` (protects even if Cloudflare is bypassed; bind to the real IP).
5. **Tighten CORS:** `SocketIO(app, cors_allowed_origins=["https://<domain>"])` instead of `"*"`.
6. **Input validation server-side everywhere:** name lengths, room codes `^[A-Z0-9]{4}$`, bet amounts are ints in range (the engine caps them, but validate at the boundary), message/JSON size limits.
7. **Headers:** CSP (self-host the Socket.IO client to allow a strict policy), `X-Content-Type-Options`, `Referrer-Policy`, HSTS (via nginx).
8. **DB:** already parameterized queries throughout — keep it that way; nightly `mus.db` backup cron.
9. Dependency hygiene: pin versions in `requirements.txt` (currently unpinned) and enable GitHub Dependabot.

**Acceptance:** site served over HTTPS behind Cloudflare; login brute-force gets rate-limited; a security-headers scan (e.g. securityheaders.com) scores well; sockets still work through the proxy.

---

## 17. Reddit promotion post

Not a code task — a launch checklist:

1. **Pre-launch gates:** finish #1 (login works), #21 (no ghost games), #16 (HTTPS — Reddit users will bounce off http://), and make sure the server survives a few hundred concurrent visitors (eventlet single-process is fine for ~1k sockets; verify with a quick load test, e.g. `python-socketio` client loop).
2. **Target subreddits:** r/WebGames, r/playmygame, r/IndieGaming, r/cardgames, r/SideProject; Spanish-speaking: r/es, r/spain, r/mus if it exists. Read each sub's self-promo rules first — several require participation history or specific flairs/days.
3. **Post content:** lead with the hook (playable in-browser, no signup needed, AI trained with Deep CFR — the training story from the [readme](../readme.md) §3 is genuinely interesting to r/SideProject and HN-adjacent crowds), a GIF of gameplay (record with the browser, convert to a <10 MB gif/mp4), the link, and a comment from you explaining the tech and asking for feedback.
4. **Ops on launch day:** watch server logs, have the admin panel (#13) ready to kill stuck rooms, and a feedback channel (GitHub issues + the contact email already in the privacy text).
5. Add lightweight analytics first (a privacy-friendly counter like a self-hosted Plausible, or just count socket connects in the DB) so you can measure the spike.

---

## 18. Resume games against the bot (persist progress across disconnects)

**Current behavior:** bot rooms live only in `salas`; a disconnect destroys them (`handle_disconnect` deletes playing rooms).

**Design:** two layers — **reconnect grace** (in-memory) and **persistence** (survives server restarts). Layer 1 delivers most of the value.

**Layer 1 — reconnect grace (in-memory):**
1. In `handle_disconnect`, if the room is a **bot room**, do *not* delete it: mark `sala['estado'] = 'pausada'`, remember the identity of the human (username if logged in; else a random `resume_token` that was sent to the client at room creation and stored in localStorage).
2. Keep paused bot rooms for 24 h (background sweeper task).
3. New event `reanudar_partida {codigo?, token?/session}`: match by username or token, swap the old sid for the new one everywhere (`sala['sids']`, `jugadores`, and inside the engine — add a `PartidaMus.reemplazar_sid(viejo, nuevo)` helper that rewrites `j1/j2`, `estado` keys, `id_mano/id_postre`, `turno_de`, `partidas_ganadas`, `jugadores_listos`, `nombres_ia`, `quien_sube`, `ganadores_fase`, `dejes_fase` values, `quien_corta_mus`). **Alternative that avoids all this rewriting:** key the engine by stable player IDs (`'p1'/'p2'`) instead of sids and keep a `sid → player_id` map in the room. This is the cleaner refactor; do it if touching the engine anyway.
4. Lobby: on load, ask the server (`GET /api/partida_pendiente` using session/token) and show a "Resume game vs bot (you: 23 – bot: 31)" banner with resume/discard buttons.

**Layer 2 — persistence (optional v2):** serialize the engine to JSON (all fields are primitives except card dicts — trivially serializable) into a `SavedGames(user_or_token, codigo, estado_json, updated_at)` table on every recuento (not every action — cheap and consistent); on server boot, don't preload anything; on resume request, if not in memory, rebuild `PartidaMus` from JSON (write `PartidaMus.from_dict/to_dict`) and a fresh `SmartBot`.

**Acceptance:** close the tab mid-bot-game, reopen, click resume, continue from the same round with the same scores; ghost cleanup still removes 24h-old paused rooms.

---

## 19. Game statistics

**Current data:** only aggregate wins/losses/ELO per user; rich per-turn data exists in `logs/*.jsonl` but isn't queryable per user.

**Steps:**
1. **New table written at game end** (in `registrar_partida_completa`, extended signature):
   ```sql
   Partidas(id, fecha TEXT, ganador_id, perdedor_id, puntos_ganador, puntos_perdedor,
            vs_bot INTEGER, ordago INTEGER, num_rondas INTEGER, match_id TEXT)
   ```
   Pass the extra facts from `enviar_estado_a_jugadores`'s persistence block (the engine knows `ronda_n`, órdago usage via `ordago_aceptado_en`, and the match_id).
2. **Per-user stats endpoint** `GET /api/stats/<username>`: totals, winrate, ELO history (add an `EloHistory(user_id, elo, fecha)` row on every update — or derive from `Partidas`), vs-bot vs online split, órdagos won/lost, longest streak, favorite outcome breakdown.
3. **Deeper lance stats (v2):** a nightly job (or on-demand admin action) that parses that user's rows out of `logs/*.jsonl` into aggregates: % mus, % bids by lance, showdown win rate by lance — store in a `UserLanceStats` cache table. Don't parse JSONL per web request.
4. **Frontend:** a "My stats" modal (from the greeting bar) with numbers + a simple ELO sparkline (inline SVG, no chart lib); extend the leaderboard modal with a click-through to public profile stats.
5. Every label in both languages.

**Acceptance:** after a logged game, "My stats" reflects it; ELO chart renders; stats page loads in <100 ms (no log parsing in the request path).

---

## 20. Improve the AI

Concrete, ordered avenues (see [Bot-AI](Bot-AI.md) for pipeline details):

1. **Finish the cfr5 run and select properly:** train to the full 5,000 iterations; use `arena.py` systematically (script a tournament of every 200th checkpoint) instead of eyeballing; ship the arena winner.
2. **Fix train/serve mismatch risks:** the env fast-forwards past mus/discard with the same EV logic the bot uses — verify the distribution of betting states in training matches live play (log `estado_dict` histograms from real games and compare).
3. **Richer information set:** add features the network currently lacks — number of own discards, pedrete availability, best-of match score, and (importantly) **whether the rival declared pares/juego** — retrain as `cfr6` with input_size bumped.
4. **Bet sizing:** amounts are discretized to 2; add 2/5/10 as separate actions (`envidar_2/envidar_5/...`) to let the net learn sizing — output layer grows accordingly.
5. **Exploit human data:** the `logs/` corpus + `gano_ronda` labels can train an opponent model (predict human fold/call rates by state) to tilt the Nash strategy toward exploitation — keep it optional per personality (#12).
6. **Mus/discard strategy noise:** currently near-deterministic (EV threshold); a strategic mus (keeping a deceptive hand) is a known human tactic — add a small learned or rule-based deviation.
7. **Evaluation harness:** track bot winrate vs humans over time from the `Partidas` table (#19, `vs_bot` flag) as the true metric.

---

## 21. Bug fixes (ghost games and friends) — ✅ DONE (2026-07-25)

**Current state:** all six vectors fixed in `server.py` (plus one in `social.py`) and
verified with a scripted soak test driving real Socket.IO clients. See [log.md](../log.md)
for the change entry.

**What was done:**
1. ✅ **Waiting rooms never expire → fixed twice over.** `emitir_lista_publicas` now
   refuses to advertise a waiting room with no *live* seat (`_sid_vivo`: not `None`,
   not a `BOT_` sid, and still present in `jugadores`) — previously such rooms were
   published with `creador_sid: None` and stayed in the lobby forever. The 2-minute
   `limpiar_sala_huerfana` timer also checks liveness instead of `is None`, and a new
   periodic sweeper (`_barredor_2p`, every 5 min, mirroring `server_mus4._barredor`)
   deletes waiting rooms with no live seat after a 2-min grace (`vacia_desde`), waiting
   rooms older than 30 min, playing rooms idle > 2 h, and pauses/replacement windows
   whose one-shot timer never fired.
2. ✅ **Bot `jugadores` leak:** every death path now goes through `_destruir_sala_2p`,
   which sweeps *all* of `jugadores` for entries pointing at the room (not just the
   current seats, so remapped/abandoned sids go too) and calls `close_room`. The
   sweeper additionally purges orphan `jugadores` entries whose room exists in neither
   `salas` nor `salas4`.
3. ✅ **`abandonar_sala_limpiamente`** extracted into `_salir_de_sala_2p(sid)`: it now
   does `leave_room(codigo)`, frees the seat and its token, drops the `jugadores` entry,
   and — if it is called with a live game (old client, duplicate event) — routes to
   `_abrir_hueco_2p` so the rival is told instead of the table silently freezing.
4. ✅ **Seat race in `unirse_sala`:** `sids` is normalised to exactly two slots *before*
   choosing, assignment is `sids[i] = sid` (never `append`), and occupancy is
   re-validated immediately before sitting — two interleaved joins can no longer produce
   a three-seat room; the loser gets `error_sala`.
5. ✅ **`enviar_estado_a_jugadores` crash-proofed:** missing engine state for a seat is
   skipped with a warning instead of raising `KeyError`; the rival's state is read
   through an `estado_rival` fallback dict; `partidas_ganadas` and the debug print use
   `.get()`. The bot's background task is wrapped in `try/except` so a bot error can no
   longer kill the greenlet mid-update (the "frozen game" that reads as a ghost).
6. ✅ **Observability:** rooms carry `creada_en` / `ultima_actividad` (stamped in
   `procesar_accion_interna`, on join, on resume and on substitution), and
   `GET /api/debug/salas?token=…` returns per-room state, age, idle time, seat liveness,
   phase and the orphan count. The endpoint 404s unless `DEBUG_TOKEN` is set in the
   environment (see `.env.example`); it is the natural data source for the #13 panel.
7. ✅ **Friends (`social.py`):** `invitar_amigo` created a room while the host might
   already be sitting in another one, overwriting `jugadores[sid]` and orphaning the old
   room — it now evicts the host first via the `salir_de_sala` context hook. The invite
   room also gets `tokens` / `creada_en` / `ultima_actividad` like every other room, so
   the host can resume it after a refresh and the sweeper can see it.

**Acceptance:** ✅ a soak test (create / join / abandon / hard-disconnect at every phase:
waiting, playing, paused, replacement, after match end, plus simultaneous joins and a
full vs-bot match played to the end) leaves `salas` and `jugadores` empty except for
live games; the public list never shows a dead room; the sweeper was unit-tested against
hand-aged rooms for all five expiry rules and confirmed not to touch 4p players sharing
the same `jugadores` dict.

<details><summary>Original plan (kept for reference)</summary>

**Known ghost-game vectors (all in `server.py`):**

1. **Waiting rooms with one live seat never expire:** `limpiar_sala_huerfana` only deletes when **all** seats are `None`; a room where the creator disconnected but the entry kept a live-looking sid, or where the 2-minute sweep raced a rejoin, lingers forever in the public list. Fix: sweep periodically (every 5 min) deleting waiting rooms older than e.g. 30 min regardless, and validate sids against `jugadores` when building the public list (`emitir_lista_publicas` should skip/queue-for-cleanup rooms whose creator sid is dead).
2. **Bot rooms leak `jugadores` entries:** `handle_disconnect` deletes the room but the fake `BOT_<code>` entry in `jugadores` is never removed (created in `crear_partida_bot`). Fix: clean bot sids whenever their room dies (and in `abandonar_sala_limpiamente`).
3. **`abandonar_sala_limpiamente` doesn't leave the Socket.IO room or clear `jugadores[sid]['sala']`:** the player's record still points at a deleted room; a later `accion_juego` hits `salas[codigo]` KeyError paths (guarded, but messy) and a later disconnect logs against a dead room. Fix: `leave_room(codigo)` + delete/refresh the `jugadores` entry, and notify the remaining player if the room was waiting.
4. **Race: both players emit `unirse_sala` simultaneously** — the seat logic mutates `sids` without locks; eventlet greenlets can interleave on `emit` yields. Audit for yield points between check and append; simplest fix is re-validating seat occupancy just before assignment.
5. **`enviar_estado_a_jugadores` crashes if a rival sid vanished from `jugadores`** mid-render (`jugadores[partida_actual.turno_de]['nombre']` raises KeyError) — one crash in an eventlet task can leave the room half-updated ("frozen" game = perceived ghost). Fix: `.get()` with fallbacks everywhere this function dereferences `jugadores`.
6. **Add observability first:** an admin/debug endpoint (or the #13 panel) listing `salas` with age + last-activity timestamp, and a counter of orphan `jugadores` entries. Add `sala['ultima_actividad'] = time()` updated in `procesar_accion_interna`; the sweeper kills playing rooms idle > 2 h.

**Approach for the agent:** reproduce first (two browser tabs + killing tabs at each phase: waiting, playing, recuento, after match end), then apply fixes 1–5, then add the sweeper + metrics, then re-run the same matrix. Also regression-test the seat-recovery path in `unirse_sala` (creator refresh while waiting) since these fixes touch it.

**Acceptance:** after a soak test of creating/abandoning/disconnecting rooms in every phase, `salas` and `jugadores` return to empty (except live games); the public list never shows dead rooms.

</details>

---

## 22. Settings menu and session-state bug — ✅ DONE (2026-07-25)

**Current state:** the ⚙ button replaced the EN/ES toggle in the lobby corner and opens
a settings window; the login/logout state no longer needs a manual refresh. See
[log.md](../log.md) for the change entry.

**What was done:**

1. ✅ **The session bug ("I log in but I'm still logged out until I refresh", and the
   mirror case after logging out).** Two causes, both fixed:
   - `/auth/sesion` was served with **no cache headers**, so a browser could reuse a
     stale copy of it — that is exactly the observed symptom in both directions. The
     `after_request` hook now sends `no-store, no-cache, must-revalidate` +
     `Pragma`/`Expires` on every `/auth/*` and `/api/*` response, and the client fetches
     it with `cache: 'no-store'`.
   - The client only ever painted the *logged-in* branch: a negative answer left
     whatever was on screen. `comprobarSesion()` now derives the interface from the
     answer in **both** directions (new `actualizarInterfazDeslogueado()`), re-checks on
     `pageshow` when the page comes back from the bfcache, and the logout handler paints
     the logged-out state *before* reloading.
2. ✅ **Settings window** (`static/settings.js`, `#modal-settings`), opened from the ⚙
   button that now sits where EN/ES used to be. It is available with or without an
   account, per the decision below.
   - **Always:** language (the ES/EN toggle button keeps the id `btn-lang`, so the
     listeners in `app.js` and `tutorial.js` keep working unchanged).
   - **Guests:** their table name (synced with the lobby field and `localStorage`) and
     shortcuts to log in / sign up.
   - **With an account:** change username, change email, change password, log out and
     delete account — each in its own `<details>` section.
3. ✅ **Log out moved** out of the top bar into the settings window.
4. ✅ **Authorization for sensitive changes** — new `_autorizar_cambio()` in `server.py`
   accepts *either* the current password *or* a single-use 6-digit code emailed to the
   account. Accounts created with Google have no usable password (new column
   `tiene_password`, set to 0 at creation and by the migration for rows with a
   `google_id`), so their panels default to the code and offer "create a password".
5. ✅ **Email change is two-step:** the code goes to the **new** address (that is what
   proves ownership) and the old address gets a notification that a change was
   requested. The address is only written after the code is confirmed.
6. ✅ **Username changes** are validated with the signup rules and rate-limited to one
   every `DIAS_ESPERA_CAMBIO_USERNAME` (30) days via the new `username_cambiado_en`
   column; the button is disabled and the remaining days are shown. Nothing else stores
   usernames (friends, groups, messages and match history all key on `Usuarios.id`), so
   a rename is safe; the client reloads afterwards because the open socket still carries
   the old name in its session snapshot.
7. ✅ **Account deletion anonymizes rather than deletes the row.** `anonimizar_usuario()`
   drops email, country, birthdate and `google_id`, renames the row, sets an
   unusable password, deletes friendships, direct and group messages, and leaves every
   group via the existing `salir_del_grupo()` (so ownership transfers to the oldest
   member, or the group disappears if empty). The `Usuarios` row survives because
   `Partidas`/`Partidas4` reference its id — deleting it would corrupt the rivals'
   history and ELO. Deleting also requires typing your own username.
   *(Superseded in part by #23: the anonymous name is now `#CODE`, the row is flagged
   with `eliminada_en`, and the original username is released.)*

**Endpoints added** (all session-scoped; the target user is never taken from the client):
`POST /auth/cuenta/codigo`, `/auth/cuenta/username`, `/auth/cuenta/email/solicitar`,
`/auth/cuenta/email/confirmar`, `/auth/cuenta/password`, `/auth/cuenta/eliminar`.
They answer `{exito, codigo, mensaje, …}`, where `codigo` is a dictionary key so the
client renders it in the chosen language (`mensaje` is the Spanish fallback).

**Acceptance:** ✅ verified end-to-end in the browser (guest and logged-in windows,
language switch, rename + cooldown, password change, delete) and with a scripted suite
covering the email round-trip, the Google/code credential (including single-use), the
cooldown, the deletion side effects on the social tables, 401s without a session, and
the cache headers.

**Not done / deliberate:** no settings for sound (there is none), theme, or bot speed —
bot speed belongs to #15.

---

## 23. Permanent player code, name reuse after deletion, and Google sign-in intent — ✅ DONE (2026-07-25)

**Why:** reported after #22 shipped — *"I created an account with Google, deleted it,
pressed log in and I was automatically logged in (without registration)"*, plus two
requests: deleting an account should free the username, and players should have a
unique, non-reusable identifier so that history can tell two players apart when they
have used the same name.

**What was done:**

1. ✅ **Public player code.** New `Usuarios.codigo` column: 6 characters from
   `ABCDEFGHJKMNPQRSTUVWXYZ23456789` (no `0/O`, no `1/I/L` — it is meant to be read
   aloud and typed), ~10⁹ combinations, unique partial index. Assigned at signup and at
   Google account creation, and back-filled for every pre-existing row by
   `_migrar_columnas()`. **It never changes and is never recycled:** a rename keeps it,
   and a deleted account keeps its row *and* its code, so the unique index alone
   guarantees no reuse.
   - Shown in the ⚙ settings window under the username (click to copy), and next to
     every name in the global leaderboard.
   - `/api/friends/request` and `/api/groups/<id>/invite` accept `#A7K2QX` as well as a
     username, via the shared `social._resolver_objetivo()` (case-insensitive, tolerant
     of separators through `base_datos.normalizar_codigo`).
2. ✅ **Deleting an account now frees the username.** `anonimizar_usuario()` renames the
   row to `#CODE` — impossible to register, since the signup regex only allows
   `[A-Za-z0-9_]` — instead of `EliminadoNN`, which squatted a perfectly valid name.
   Someone else can immediately take the old name; they are a different person and the
   codes prove it.
3. ✅ **Deleted rows are flagged, not disguised.** New `eliminada_en` column. A flagged
   row is excluded from the global leaderboard, from `obtener_usuario`,
   `obtener_id_usuario`, `verificar_login`, the Google lookups and the code search — so
   it cannot be logged into, found, befriended or invited. `obtener_jugador_publico(id)`
   returns `{id, codigo, eliminada, username=None}` for any surface that has to show a
   past player (a match-history screen would use this; there isn't one yet, see #19).
   A one-time migration converts old `EliminadoNN` rows (recognised by the name *plus*
   no email, no `google_id` and `tiene_password = 0`) to the new scheme.
4. ✅ **"Log in with Google" no longer creates accounts.** `/auth/google/login` takes
   `?intent=login|signup` (stored in the Flask session, not the redirect URL, so it
   cannot be forced from outside) and `registrar_o_loguear_google(..., crear=)` returns
   `None` instead of inserting when the intent is `login`. The callback then redirects
   to `/?auth_error=google_sin_cuenta`; the client alerts and opens the signup modal.
   Anything without an explicit intent is treated as `login`. This is the reported bug:
   the account looked like it had "come back" because the login button silently signed
   the user up again, and — the old name having been freed — under the same name.
5. ✅ **Stale session cookies are cleared.** `/auth/sesion` now pops `username` from the
   session when the account behind it no longer exists, instead of leaving the cookie
   pointing at nothing.

**Acceptance:** ✅ two scripted suites (`test_codigo.py`, `test_google_intent.py`, 44
checks) covering the migration and its idempotency, code uniqueness/alphabet, code
survival across a rename, the full deletion side effects, name reuse by a different
player, every lookup path rejecting deleted rows, and the four Google intent paths
(including delete → log in → *no account*, and delete → sign up → *new code*). ✅
Verified in the browser: the code in the settings window in ES/EN, the leaderboard, and
adding a friend by lower-case code while a deleted account's code is rejected. ✅ The
#21 and #22 suites still pass.

**Not done / deliberate:** the code is not shown in the friends list or group member
lists (usernames are unique among live accounts, so there is nothing to disambiguate
there); there is no match-history screen yet to flag past players in — `#19` is where
that lands, and `obtener_jugador_publico()` is the hook it should use.

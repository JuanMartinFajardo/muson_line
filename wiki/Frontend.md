# Frontend

The frontend is a **single HTML page with vanilla JavaScript** — no framework, no bundler. Flask serves [index.html](../index.html) at `/` and everything else from `static/`.

## Screens (all in `index.html`, toggled with the `.hidden` class)

1. **Menu / lobby (`#menu-screen`)** — redesigned (see [The menu and the Play window](#the-menu-and-the-play-window)): three fixed icon buttons in the top-right corner (👥 friends when logged in · ⚙ settings · ⛶ fullscreen), identity in the top-left corner (`#txt-user-stats` with a session, `#user-buttons` login/signup without one), logo, pinned announcements, one big **Jugar / Play** button, *How to play*, *My decks* (flagged unavailable), and a footer row with *Leaderboard*, *Ko-fi* and *About CallMus*. Everything about starting a game moved into the Play window.
2. **Game screen (`#game-screen`)** — redesigned with the same visual language as the menu (see [The tables](#the-tables-1v1-and-2v2)): a *plate* per player (`.cm-plate-head`: suit mark, name, score and the won-games "piedras"), the message/log area, the four-lance score board (`.cm-botes`), the action buttons and your own cards (clickable for discard selection). The recuento (results) is written into `#game-log` and ends with *Next round / Next game / Return to menu*. A permanent `✕` exit button (`.btn-salir-mesa`, fixed next to the fullscreen toggle) and a `?` tutorial button (`.cm-mesa-btn`, top-left) are available in every phase.
3. **Modals** — **Play (`#modal-play`)**, login (with "forgot password?" + Google), signup (with email + Google), email verification code, password recovery (request + reset), leaderboard, privacy/about, settings. The Play window, the leaderboard and about carry the class `.cm-win` and are styled by `static/menu.css`; the rest still use the old inline styles (the tutorial, reachable from the table with `?`, is the most visible one left).
4. **Game overlays** (`.overlay-partida`, fixed and shared by both tables, outside `#modal-overlay` so they work over any screen; `game.css` gives them the same plate as the menu's windows — gold hairline crown, serif small-caps title, gold primary / red danger buttons) — `#overlay-salir` (confirm before leaving), `#overlay-abandono` (someone left: *wait for another player* / *leave as well*), `#overlay-espera-reemplazo` (looking for a substitute, with a countdown). The helpers `confirmarSalidaPartida()`, `mostrarAvisoAbandono()`, `mostrarEsperaReemplazo()` and `ocultarOverlaysPartida()` live in `app.js` and are reused verbatim by `app4.js`; both take optional text overrides so the 2v2 can name the vacant seat and how many players are still missing.

## `static/app.js` (~1500 lines) — main client

- **Card preloading:** after 2 s, silently preloads all 40 card `.webp` images plus the card back.
- **i18n engine:** a `dict` object with `es`, `en` and `eu` (Basque) translations (~500 keys each); `t(key)` resolves strings, elements carry `data-i18n` attributes (or `data-i18n-title` for icon-only buttons whose tooltip needs translating), and dynamic server messages arrive as **message codes** (e.g. `{'code': 'fase_apuestas', 'fase': 'Grande', 'jugador': 'X'}`) that the client renders in the active language. Language cycles through `es → en → eu` via the button inside the ⚙ settings window (same `#btn-lang` id, driven by the `LANGS` array in `app.js`; the button always shows the *next* language) and persists (localStorage). Missing keys fall back to Spanish via `_resolver()`, never to the raw key name.
- **Socket.IO client:** `const socket = io({ closeOnBeforeunload: false })`. Emits `crear_sala`, `crear_partida_bot`, `unirse_sala`, `accion_juego`, `pedir_publicas`, `abandonar_sala_limpiamente`, `abandonar_partida`, `esperar_reemplazo`, `reanudar_partida`; listens for `sala_creada`, `iniciar_partida`, `actualizar_mesa`, `actualizar_publicas`, `error_sala`, `rival_desconectado`, `oponente_desconectado`/`oponente_reconectado`, `jugador_abandono`, `esperando_reemplazo`, `reemplazo_encontrado`.
- **Rendering:** every `actualizar_mesa` payload repaints the whole table: cards, whose turn, phase banner, bet info (pending raise, pots, concessions), recuento steps, match score. Card selection for discards is tracked in `cartasSeleccionadas`.
- **Sharing:** the waiting panel offers copy-link / WhatsApp / Web Share API buttons with a join URL containing the room code.
- **Leaderboard:** rank · name · ELO · wins · win-rate, sortable by the last three. The permanent player code is **not** printed under the name any more: the name is a button (`.lb-name`) that swaps to `#CODE` for ~2.6 s when clicked (`mostrarCodigoJugador`). Deleted accounts are not listed.
- **Menu messages:** `menuMensaje(texto, color)` writes to `#menu-msg` *and* `#play-msg`, because the Play window covers the menu while it is open.
- **Escaping:** `escHtml()` guards every player-supplied string that goes into `innerHTML` (room creator in the public lists, leaderboard names, occupied seats, 2v2 seat names). Guests choose their own name, so it is untrusted input.
- **Table helpers shared with the 2v2** (both live in `app.js`, section 4, and are called from `table4.js`): `htmlTanteador(apuestas, faseActual, dejeDe)` builds the four-lance board — the `dejeDe` callback exists because a concession is `gano_yo` in the 1v1 and `gano_mi_equipo` in the 2v2 — and `pintarPiedras(el, ganadas, alMejorDe)` draws one *piedra* (amarrako) per game needed to win the match, filling in gold the ones already won. `alMejorDeActual` keeps the last known best-of because the recuento payload does not always repeat it.

## `static/auth.js`

All client-side auth: session check, login (username or email), 2-step signup (request code
→ verify), password recovery (request code → reset), logout, and the Google button
redirects. Loaded **after** `app.js` and reuses its globals (`t()`, `cerrarModales()`,
`miUsernameLogueado`). All user-facing strings go through `t()` (es + en). See
[Authentication](Authentication.md).

`comprobarSesion()` is the single source of truth for the logged-in UI: it fetches
`/auth/sesion` with `cache: 'no-store'`, stores the profile in the `usuarioActual` global
(read by `settings.js`) and calls **either** `actualizarInterfazLogueado()` **or**
`actualizarInterfazDeslogueado()` — it never leaves the screen as it was, which is half of
the Roadmap #22 fix for "logged in but the page disagrees until I refresh". It runs on load
and again on `pageshow` when the browser restores the page from the bfcache.

## `static/settings.js`

The ⚙ window (`#modal-settings`). Language is always available; the account block only
appears when `usuarioActual` is set, and guests get their table name plus log-in / sign-up
shortcuts instead. Logged-in players also see their permanent player code (`#A7K2QX`)
under their username, click-to-copy — see [Database](Database.md#player-codes-codigo). The ES/EN toggle inside it deliberately keeps the id `btn-lang` because
`app.js` and `tutorial.js` already listen on that element.

Each account section is a `<details>` with a `.credencial` block that `settings.js` builds
once: a current-password field plus an "I signed in with Google" link that swaps it for a
6-digit code requested from `/auth/cuenta/codigo`. `_credencial(panel)` turns whichever is
filled into `{password}` or `{code}` for the request. Server replies are rendered through
`_traducir()`, which looks up the reply's `codigo` in the dictionary (filling `{dias}`,
`{email}`… from the rest of the payload) and falls back to the server's Spanish `mensaje`
if the key is missing. See [Authentication](Authentication.md) for the routes.

## `static/soporte.js`

Loaded after `settings.js`. Two jobs, both from Roadmap #13:

1. **Support inbox** inside the ⚙ window (`#seccion-soporte`): open a ticket (type,
   subject, body), list your threads with their state, and keep the conversation with the
   admin going until either side marks it solved. Message bodies are rendered with
   `textContent` — never `innerHTML` — same rule as `social.js`. An unread counter is
   painted onto the ⚙ button itself (`#settings-badge`).
2. **Admin announcements:** `GET /api/anuncios` on load (it works for guests too) paints
   the pinned messages and the maintenance banner into `#anuncios-fijados`, and queues
   one-shot notifications into `#anuncio-popup`; closing one POSTs `…/leido` so it does
   not come back.

It hooks into the settings window by wrapping the global `refrescarAjustes()` instead of
duplicating the "is anyone logged in?" logic, and it adds a **second** `socket.on(
'notificacion')` listener — Socket.IO listeners stack, and each one ignores the types that
are not its own (`anuncio`, `soporte_respuesta` here; friends and chat in `social.js`).
The link to `/admin` in the settings window only appears when `usuarioActual.is_admin`.

## `static/pantalla.js` — fullscreen and "table mode"

Loaded **last**. It owns everything about how much screen the game gets, and it exists
because of one phone problem: on the table, a swipe is a **game control** (the 2v2 signs
turn your head with it), but the browser reads that same gesture as its own — it scrolls
the page, bounces, or pulls to refresh. Fullscreen used to be the only way around it, and
**Safari on the iPhone has no Fullscreen API at all** (outside `<video>`), so the ⛶ button
could never work there. Both halves are fixed here:

1. **Table mode.** A `MutationObserver` on `#game-screen` / `#game-screen-4` puts
   `.modo-mesa` on `<html>` while a table is on screen. `game.css` then freezes the
   document (`position: fixed` body — the only thing Safari really honours —
   `overflow: hidden`, `overscroll-behavior: none`, `touch-action: manipulation`), and a
   **non-passive** `touchmove` listener cancels any drag that is not inside something that
   can actually scroll (`desplazable()` walks up looking for a real overflow). The 1v1
   recuento, the signs cheat sheet and the tutorial keep scrolling; the table does not.
   **The game plays the same with or without fullscreen** — that was the point.
2. **Fullscreen**, in one place, with the vendor prefixes. The ⛶ button toggles it and
   repaints its own tooltip on `fullscreenchange`; it hides itself when the page is already
   running from the home screen (`enApp()`).
3. **Automatic entry** on the click that starts a game (`#btn-crear`, `#btn-jugar-bot`,
   `#btn-unirse`, `#btn-crear-sala-4`, `#btn-unirse-4` and the join buttons of the public
   lists). It has to be *that* click: the API needs a user gesture and the table only opens
   later, when the server says so. `arranqueValido()` skips it when the name or the code is
   missing, so a click that only produces an error message does not go fullscreen either.
   The admin switch is the `pantalla_completa_auto` `Config` variable (default `1`,
   editable from `/admin` like `bot_delay` or `menu_pintas_ms`), which `server.py` reads in
   `index()` and `index.html` injects as `window.CM_AUTO_FULLSCREEN`; leaving is always
   manual.
4. **The iPhone.** Where there is no API, ⛶ opens a floating `.cm-ayuda` window explaining
   *Share → Add to Home Screen*, which is the only real fullscreen Safari offers, and says
   that the table already works without it. `index.html` carries the
   `apple-mobile-web-app-*` tags and `viewport-fit=cover`, and
   `static/favicon_io/site.webmanifest` was filled in (it had an empty name and icon paths
   that pointed nowhere).

`env(safe-area-inset-*)` is applied in `game.css` to the tables and to the fixed corner
buttons: with `viewport-fit=cover` the table reaches the physical edge of the screen, so
the notch and the gesture bar have to be dodged by the content.

## `static/tutorial.js` (~2200 lines)

An interactive step-by-step tutorial launched by the *How to Play* button: injected styles for card-zoom effects (hover on desktop, tap on mobile), staged explanations of the deck, lances, and betting. **Fully translated (ES/EN/EU)**, bilingual since Roadmap #2 and trilingual with the Basque pass: slide content is keyed by the global `langActual` variable defined in `app.js` (single source of truth, persisted to `localStorage['callmus_lang']`), and a listener on `#btn-lang` re-renders the open tutorial when the language is toggled. The *How to Play* launcher button is translated via `data-i18n="btn_tutorial"` in `app.js`.

**Three tracks and an index (July 2026).** The tutorial no longer is one long carousel: it opens on an **index** (`dictIndice`) with three buttons, each leading to its own slide array.

| Track | Constant | Slides | What it covers |
| :--- | :--- | :--- | :--- |
| `1v1` | `dictTut1v1` | 13 | The rules of Mus from scratch (the original carousel, untouched) |
| `2v2` | `dictTut2v2` | 9 | Only what changes with partners: teams, cutting the Mus with four, public Pares/Juego declarations, team betting (both partners answer), showdown with bonuses that add up, two worked examples |
| `senas` | `dictTutSenas` | 8 | The ten gestures, the "highest sign only" rule, when the button is live, calling out a sign, tips |

- `CONTENIDO` maps the track name to its dictionary; `pistaActual` (null = index) plus `currentSlideIndex` are the whole navigation state. `renderTutorial()` paints whichever applies — used by the language toggle so a track keeps its position across languages.
- Both `es` and `en` arrays of a track keep the same slide count/order, so the practice-slide skip logic (index 8 **of the 1v1 track**, `IDX_PRACTICA_1V1`) stays valid.
- A slide's `content` may be a **function** instead of a string: the sign slides are generated at paint time because they borrow the face SVG from `senas4.js` (`window.Senas4.svgCara()`), which loads after this file. The faces replay each gesture on a loop with the same `sena-<name>` + `en-bucle` classes as the in-game cheat sheet (`.sena-muestra` in `senas.css`).
- Navigation: `#btn-tutorial-indice` (the ☰ in the modal's top-left corner) and *Prev* on the first slide both return to the index; the footer (`#tut-nav`) is hidden on the index. Buttons carrying `data-tut-pista="…"` inside a slide jump between tracks (the 2v2 track links to both 1v1 and señas).
- The in-game `?` opens the track of the mode being played: `#btn-help-game` → `1v1`, `#btn-help-game-4` → `2v2`, both with `openedFromGame = true` so the "start practising" slide is skipped. `window.tutorialAbrirPista(id, index)` is the public entry point (used by the señas help in `menu.js`).

## The menu and the Play window

Rewritten in July 2026 (the "redesign the main menu" entry of [Home](Home.md)). Two new
files own it — `static/menu.css` and `static/menu.js` — and they are loaded **last** so they
can redefine the palette and re-point the 2v2 panels.

**Design language ("midnight ink"):** near-black surfaces (`--cm-ink*`), 1 px hairlines
instead of rounded boxes, serif small-caps for labels (`--cm-serif`), gold (`--cm-gold`) as
the only accent, red only for errors — plus the four Spanish suits (oros, copas, espadas,
bastos) hand-drawn as SVG `<symbol>`s at the top of `index.html` and reused with
`<use href="#pinta-…">`. `menu.css` also **reassigns the old `--menu-*` variables**, so the
windows that have not been redesigned inherit the new palette instead of clashing.

The row of four suits under the logo (`.cm-orn.cm-orn-ciclo`) passes the gold from one to
the next — oros → copas → espadas → bastos and round again — with a CSS animation
(`@keyframes cm-orn-oro`, one shared 4-step cycle plus a negative `animation-delay` per
suit). The step is the `--cm-orn-paso` variable, which `index.html` injects from the
`menu_pintas_ms` `Config` variable (default 1000 ms, 0–10000, editable from `/admin`);
`0` stops the animation and leaves the gold parked on espadas, as it was before. The lone
suit inside `#modal-play` does not carry `.cm-orn-ciclo`, so it stays quiet.

**`#modal-play` — one window for every way of starting a game:**

| Step | 1v1 | 2v2 |
| :--- | :--- | :--- |
| Name | `#nombre-jugador`, guests only (`#play-nombre`); with a session, "you will play as …" | same field |
| 1 · table | `.cm-mode[data-modo="2"]` | `.cm-mode[data-modo="4"]` |
| 2 · opponents | people · **bot** | four people · with bots *(soon)* · mixed *(soon)* |
| 3 · details | best-of `#in-mejor-de`, public `#in-publico` | best-of `#in-mejor-de-4`, public `#in-publico-4`, signs *(soon)*, seat picker `#seat-picker-4` |
| create | `#btn-crear` / `#btn-jugar-bot` | `#btn-crear-sala-4` |
| join | `#in-codigo` + `#btn-unirse` + live list `#lista-partidas-publicas` | `#in-codigo-4` + `#btn-unirse-4` + `#lista-publicas-4` |
| waiting | `#codigo-creado` (code + share + cancel) | `#panel-4-espera` (code + four seats) |

`menu.js` **only decides what is visible** (`pintarPlay()`), keeps the summary line in sync
and polls the list of the mode being looked at; every id was preserved, so `app.js` and
`app4.js` still own creating and joining. Only one create button and one join block are
visible at a time — that is why no event wiring had to move.

**Unavailable features** are marked with `data-soon` plus a *Pronto/Soon* tag; a single
capturing listener in `menu.js` turns any click on them into a floating explanation
(`.cm-toast`, `avisar(clave)`): deck menu, 2v2 bots, mixed tables and signs.

The 2v2 lost its own window: `#modal-4` no longer exists and `app4.js` points `modal4`,
`panelSetup4` and `msg4` at `#modal-play`, `#play-setup` and `#play-msg`.

**The señas help (`#btn-ayuda-senas`).** The *Con señas* switch is wrapped in a
`.cm-switch-fila` together with a round `?` (`.cm-help-dot`) — a `<button>` cannot live
inside the `<label>` without becoming a second labelable control, so the row is the wrapper
and it keeps the id `#set-senas` that `pintarPlay()` shows and hides. The `?` opens a light
floating window (`.cm-ayuda` + `#cm-ayuda-velo`, built by `menu.js`) that explains the
**mechanics**, not the gestures: the four focus regions with their keys, arrows/WASD/swipe,
the gold face that means "they are looking at you", the automatic wandering and the 2.5 s
manual hold, the 1 s focus cut and the 1 s overlap, and when the *Seña* button is live. Its
prose lives in the `AYUDA_SENAS` constant (one HTML block per language, repainted on the
language toggle, since it carries no `data-i18n`), and its *See the ten signs* button calls
`window.tutorialAbrirPista('senas')`. It closes with the veil, the *Got it* button or `Esc`.

## The tables (1v1 and 2v2)

Both tables were redesigned to continue the menu's "midnight ink" language, and the look of
**both** now lives in a single file, [static/game.css](../static/game.css). Two ideas are
specific to the table:

- **The plate** (`.cm-plate-head` in the 1v1, `.team-score` in the 2v2): suit mark, name in
  serif small-caps, the score as a large serif number over a quiet `/40`, and the games won
  as **piedras** — the amarrakos of the real game, one hollow circle per game needed for
  the match, filled in gold as they are won (`pintarPiedras`). Oros marks you, espadas the
  opponent; in the 2v2 team A is gold and team B steel (`--equipo-a` / `--equipo-b`).
- **The lance board** (`.cm-botes`): Grande · Chica · Pares · Juego in four columns split by
  hairlines, the lance in play in gold with a gold rule under it, and a concession shown as
  `3⁺` / `3⁻`. It is built by `htmlTanteador()` and shared by the two tables. Above it,
  `.cm-aire` shows the bet in the air and collapses to nothing when there is none (it used
  to reserve 65 px of empty space).

Whose turn it is is marked on the plate, not only in the banner: in the 1v1 the CSS reads
`#mi-turno:not(.hidden) + #my-area` (the banners sit right before their plate in the HTML,
so no JavaScript was needed); in the 2v2 the active seat's name turns gold with a hairline
under it. Buttons follow one rule: the action that moves the game on (deal, discard, see,
next round) is solid gold, everything else is a hairline, **órdago** is the only red thing
on the table, and *back to menu* is a quiet outline. The bet amount is glued to its button
(`2 | ENVIDAR`) so the number reads as part of the action.

In the 2v2, each seat's name, chips and cards live inside a `.seat-cuerpo`: the
seat itself fills its whole grid cell — the side columns are as tall as the table —
so the label of what a player just called (`.accion-burbuja`, `mostrarAccion4`) is
anchored to the *cuerpo* and lands right above that player's name instead of high
up in the column. It sits just clear of the name (the plate is opaque), and only
under 640 px does it anchor to the outer edge of the side columns and grow towards
the centre, because a 60 px column cannot hold it centred.

The betting buttons of the 2v2 are not decided by the client: the payload's
`acciones_legales` (built by the engine, the same list the bots use) says which of
*envidar/pasar/órdago/ver/subir/no ver* to show, which is how the table stops
offering a Pares or Juego bet to a player who does not have the combination — see
[Implementing Mus 4 Players](Implementing-Mus-4-Players.md) §4.3 ter.

Two layout traps worth remembering: `#center-table` is a flex column with its own scroll,
so its children need `flex: 0 0 auto` (otherwise the growing recuento text overlaps the
board), and `mostrarBotones()` calls `scrollIntoView({block:'nearest'})` so the buttons
cannot end up below the fold on short windows. The top band for the corner buttons is only
reserved under 830 px wide, where the plate would actually reach them.

## `static/sorteo.js` — the draw for the Mano

Before the first hand of a match, the table is covered by an opaque curtain while the
four suits are drawn in the centre: the gold runs through them fast (oros → copas →
espadas → bastos, the same cycle as the menu ornament in `menu.css`) and slows down
until it stops on one. **Where it stops is the Mano.** The spin always takes exactly
2 s — the per-step durations are generated with a cubic ease-out and then rescaled to
2000 ms, so the number of steps does not change the duration — then the result is held
for 1.1 s and the curtain fades. With `prefers-reduced-motion` it goes straight to the
result.

Each player only has their suit(s) and their name in their area, placed as they sit
(yourself always at the bottom, the other seats via the same mapping as
`slotDeAsiento4`). In the 1v1 each player gets **two** suits; in the 2v2, one each,
handed out **anticlockwise as seen on screen** (`seat + 1` is drawn to the left, i.e.
clockwise, so the server subtracts) starting from a random seat.

The draw is decided by the **server** and travels inside the `sorteo` of
`iniciar_partida` / `iniciar_partida_4`, so every client sees the same one. The Mano
itself was already drawn by the engine (`random.shuffle` in `PartidaMus.__init__`,
`random.randint` in `PartidaMus4.__init__`): the server only invents a suit deal
*compatible* with that decision, which is why the wheel always stops on a suit of the
Mano. It is sent **only when a match starts** — someone joining a game already in play
gets no `sorteo` and no curtain. Since both engines start in `espera_reparto`, nothing
is dealt behind the curtain: it is blocking in practice.

## `static/style.css`

Shared skeleton: the responsive layout of both screens, the card fan, the `parpadeo`
keyframes and the old windows' theme. It no longer styles the tables — that block moved to
`game.css`, and `style4.css` was reduced to the 2v2 grid, sizes and animations. Its "TAPETE
PREMIUM" block only reaches the **old** windows now: it used to target `div[id^="modal-"]`,
which also matches `#modal-overlay` and therefore leaked `!important` colours into
everything inside it, so the affected windows are listed explicitly. A lot of styling is
still inline in `index.html` (candidate for cleanup).

## Assets

- `static/img/card_<suit>_<NN>.webp` — suits `coins, cups, swords, clubs`, values `01–07, 10, 11, 12` (from the [spanish-playing-cards-svg](https://github.com/gjenkins20/spanish-playing-cards-svg) repo).
- `static/img/card_back.webp`, `callmus2logo_193.jpg`, `static/favicon_io/*`.
- Socket.IO client (v4.7.5) is **self-hosted** at `static/vendor/socket.io-4.7.5.min.js`. It used to come from cdnjs; it was moved so the CSP can forbid third-party scripts ([Security](Security.md#4-the-content-security-policy)). The page now loads **nothing** from outside the origin. When bumping the version, replace the file and the `<script src>` together.
- Inline `<script>`/`<style>` need `nonce="{{ csp_nonce() }}"` and inline `on*=` handlers are blocked outright — attach listeners from a file in `/static` instead.

## Conventions for new frontend work

- Add every user-visible string to **all three** of `dict.es`, `dict.en` and `dict.eu`, and reference it with `t()` / `data-i18n`.
- Server → client messages that need localization must be sent as `{code, ...params}` objects, never pre-rendered text.
- New screens follow the `.screen` + `.hidden` toggle pattern; new modals follow the existing `modal-*` pattern with `cerrarModales()` (add the new id there and to the hide lists in `social.js` / `tutorial.js`).
- Menu-side work goes in `menu.css` / `menu.js` with the `.cm-` prefix and the tokens of the "midnight ink" palette — no new hard-coded hex values, no inline `style=""`. Table-side work goes in `game.css` under the same rules; keep `style.css` / `style4.css` for layout only, so there is one place per screen that decides how it looks.
- Anything the two tables show the same way (the lance board, the piedras) belongs in a helper in `app.js` that `table4.js` calls, not copied into both.
- A feature that is not ready yet gets a visible `data-soon` marker and a reason in `MOTIVOS` (`menu.js`), never a hidden or dead button.
- Bump the `?=vN` query string of any `static/` file you change in `index.html`: browsers cache them and stale JS is very confusing to debug.

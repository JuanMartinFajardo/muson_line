# Frontend

The frontend is a **single HTML page with vanilla JavaScript** — no framework, no bundler. Flask serves [index.html](../index.html) at `/` and everything else from `static/`.

## Screens (all in `index.html`, toggled with the `.hidden` class)

1. **Menu / lobby (`#menu-screen`)** — user bar (login/signup, or greeting + friends), a ⚙ settings button fixed in the top-right corner where the EN/ES toggle used to be, logo, name input, "best of N" selector, public checkbox, buttons: *Create new game*, *Play vs bot*, *How to Play (Tutorial)*; join-by-code input; live **public games table**; leaderboard button; "About CallMus" (privacy) modal.
2. **Game screen (`#game-screen`)** — opponent info + hidden cards, message/log area, own cards (clickable for discard selection), action buttons (deal / mus / cut / discard / pass / bid / raise / call / fold / órdago / pedrete), scores and match counters, recuento (results) panel with *Next round / Next game / Return to menu*. A permanent `✕` exit button (`.btn-salir-mesa`, fixed next to the fullscreen toggle) is available in every phase.
3. **Modals** — login (with "forgot password?" + Google), signup (with email + Google), email verification code, password recovery (request + reset), leaderboard, privacy/about, settings.
4. **Game overlays** (`.overlay-partida`, fixed and shared by both tables, outside `#modal-overlay` so they work over any screen) — `#overlay-salir` (confirm before leaving), `#overlay-abandono` (someone left: *wait for another player* / *leave as well*), `#overlay-espera-reemplazo` (looking for a substitute, with a countdown). The helpers `confirmarSalidaPartida()`, `mostrarAvisoAbandono()`, `mostrarEsperaReemplazo()` and `ocultarOverlaysPartida()` live in `app.js` and are reused verbatim by `app4.js`; both take optional text overrides so the 2v2 can name the vacant seat and how many players are still missing.

## `static/app.js` (~1500 lines) — main client

- **Card preloading:** after 2 s, silently preloads all 40 card `.webp` images plus the card back.
- **i18n engine:** a `dict` object with `es` and `en` translations (~150 keys each); `t(key)` resolves strings, elements carry `data-i18n` attributes (or `data-i18n-title` for icon-only buttons whose tooltip needs translating), and dynamic server messages arrive as **message codes** (e.g. `{'code': 'fase_apuestas', 'fase': 'Grande', 'jugador': 'X'}`) that the client renders in the active language. Language toggles via the `EN`/`ES` button (now inside the ⚙ settings window, same id) and persists (localStorage).
- **Socket.IO client:** `const socket = io({ closeOnBeforeunload: false })`. Emits `crear_sala`, `crear_partida_bot`, `unirse_sala`, `accion_juego`, `pedir_publicas`, `abandonar_sala_limpiamente`, `abandonar_partida`, `esperar_reemplazo`, `reanudar_partida`; listens for `sala_creada`, `iniciar_partida`, `actualizar_mesa`, `actualizar_publicas`, `error_sala`, `rival_desconectado`, `oponente_desconectado`/`oponente_reconectado`, `jugador_abandono`, `esperando_reemplazo`, `reemplazo_encontrado`.
- **Rendering:** every `actualizar_mesa` payload repaints the whole table: cards, whose turn, phase banner, bet info (pending raise, pots, concessions), recuento steps, match score. Card selection for discards is tracked in `cartasSeleccionadas`.
- **Sharing:** the waiting panel offers copy-link / WhatsApp / Web Share API buttons with a join URL containing the room code.
- **Leaderboard:** each row shows the player's permanent code under the name; deleted accounts are not listed.

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

## `static/tutorial.js` (~700 lines)

An interactive step-by-step tutorial launched by the *How to Play* button: injected styles for card-zoom effects (hover on desktop, tap on mobile), staged explanations of the deck, lances, and betting. **Fully bilingual (ES/EN)** since Roadmap #2: slide content lives in a `dictTutorial` object keyed by the global `langActual` variable defined in `app.js` (single source of truth, persisted to `localStorage['callmus_lang']`); `getSlides()` / `getTutBtns()` return the active-language content, and a listener on `#btn-lang` re-renders the open tutorial when the language is toggled. Both `es` and `en` arrays keep the same slide count/order so the practice-slide skip logic (index 8) stays valid. The *How to Play* launcher button is translated via `data-i18n="btn_tutorial"` in `app.js`.

## `static/style.css`

Nord color palette (`#2e3440` background, `#88c0d0`/`#a3be8c`/`#bf616a` accents), responsive layout, card fan styles, blinking-turn animation (`anim-parpadeo`). A lot of styling is also inline in `index.html` (candidate for cleanup).

## Assets

- `static/img/card_<suit>_<NN>.webp` — suits `coins, cups, swords, clubs`, values `01–07, 10, 11, 12` (from the [spanish-playing-cards-svg](https://github.com/gjenkins20/spanish-playing-cards-svg) repo).
- `static/img/card_back.webp`, `callmus2logo_193.jpg`, `static/favicon_io/*`.
- Socket.IO client is loaded from the **cdnjs CDN** (v4.7.5) — the only external dependency.

## Conventions for new frontend work

- Add every user-visible string to **both** `dict.es` and `dict.en` and reference it with `t()` / `data-i18n`.
- Server → client messages that need localization must be sent as `{code, ...params}` objects, never pre-rendered text.
- New screens follow the `.screen` + `.hidden` toggle pattern; new modals follow the existing `modal-*` pattern with `cerrarModales()`.

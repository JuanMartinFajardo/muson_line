# Frontend

The frontend is a **single HTML page with vanilla JavaScript** — no framework, no bundler. Flask serves [index.html](../index.html) at `/` and everything else from `static/`.

## Screens (all in `index.html`, toggled with the `.hidden` class)

1. **Menu / lobby (`#menu-screen`)** — user bar (login/signup or greeting+logout), logo, name input, "best of N" selector, public checkbox, buttons: *Create new game*, *Play vs bot*, *How to Play (Tutorial)*; join-by-code input; live **public games table**; leaderboard button; "About CallMus" (privacy) modal.
2. **Game screen (`#game-screen`)** — opponent info + hidden cards, message/log area, own cards (clickable for discard selection), action buttons (deal / mus / cut / discard / pass / bid / raise / call / fold / órdago / pedrete), scores and match counters, recuento (results) panel with *Next round / Next game / Return to menu*.
3. **Modals** — login (with "forgot password?" + Google), signup (with email + Google), email verification code, password recovery (request + reset), leaderboard, privacy/about.

## `static/app.js` (~1500 lines) — main client

- **Card preloading:** after 2 s, silently preloads all 40 card `.webp` images plus the card back.
- **i18n engine:** a `dict` object with `es` and `en` translations (~150 keys each); `t(key)` resolves strings, elements carry `data-i18n` attributes, and dynamic server messages arrive as **message codes** (e.g. `{'code': 'fase_apuestas', 'fase': 'Grande', 'jugador': 'X'}`) that the client renders in the active language. Language toggles via the `EN`/`ES` button and persists (localStorage).
- **Socket.IO client:** `const socket = io({ closeOnBeforeunload: false })`. Emits `crear_sala`, `crear_partida_bot`, `unirse_sala`, `accion_juego`, `pedir_publicas`, `abandonar_sala_limpiamente`; listens for `sala_creada`, `iniciar_partida`, `actualizar_mesa`, `actualizar_publicas`, `error_sala`, `rival_desconectado`.
- **Rendering:** every `actualizar_mesa` payload repaints the whole table: cards, whose turn, phase banner, bet info (pending raise, pots, concessions), recuento steps, match score. Card selection for discards is tracked in `cartasSeleccionadas`.
- **Sharing:** the waiting panel offers copy-link / WhatsApp / Web Share API buttons with a join URL containing the room code.

## `static/auth.js`

All client-side auth: session check, login (username or email), 2-step signup (request code
→ verify), password recovery (request code → reset), logout, and the Google button
redirects. Loaded **after** `app.js` and reuses its globals (`t()`, `cerrarModales()`,
`miUsernameLogueado`). All user-facing strings go through `t()` (es + en). See
[Authentication](Authentication.md).

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

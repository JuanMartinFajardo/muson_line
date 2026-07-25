# Authentication

The account system is **fully implemented** (Roadmap #1, done 2026-07-24). This page
documents the current flows. Secrets come from environment variables / a `.env` file —
see [Setup-and-Deployment](Setup-and-Deployment.md) and `.env.example`.

Frontend auth logic lives in [static/auth.js](../static/auth.js) (loaded after `app.js`,
which still owns the shared helpers `t()`, `cerrarModales()` and the `miUsernameLogueado`
global). Backend routes are in [server.py](../server.py); DB access in
[base_datos.py](../base_datos.py).

## Data model

`Usuarios` gained four columns over the original schema:

- `email TEXT` — unique (case-insensitive) via a partial index; **required for new
  username/password signups**, used for verification and password recovery.
- `google_id TEXT` — unique; set when an account is created or linked via Google.
- `tiene_password INTEGER DEFAULT 1` — 0 for accounts *created* through Google, whose
  password hash is random and unusable. It only decides which form the settings window
  shows; authorization accepts a valid password either way. Set back to 1 by
  `actualizar_password` and `cambiar_password_usuario`.
- `username_cambiado_en TEXT` — date of the last rename, for the 30-day cooldown
  (`DIAS_ESPERA_CAMBIO_USERNAME`).
- `codigo TEXT` — the permanent public player code (`#A7K2QX`), unique and never reused.
  See [Database](Database.md#player-codes-codigo).
- `eliminada_en TEXT` — set when the account is deleted. A flagged row can no longer be
  logged into, found or added.

A startup migration (`base_datos._migrar_columnas`) adds these columns and indexes to
older `mus.db` files without data loss (it also back-fills `tiene_password = 0` for rows
that already have a `google_id`).

## Flows

### 1. Email + password signup (2-step verification)

1. **Signup modal** collects username, email, password, country, birthdate. Client-side
   validation (username 3–20 chars, email regex, password ≥ 6) then POST
   `/auth/solicitar_codigo` with `{username, email, password}`; the full form is kept in
   `temporalRegistrationData`.
2. **`auth_solicitar_codigo`**: re-validates, calls `base_datos.existe_usuario` to reject
   duplicate username/email *before* sending anything, enforces the rate limit, generates a
   6-digit code, stores `{code, ts, tipo:'registro'}` in `codigos_pendientes[email]`, and
   emails it via `enviar_correo()` (Gmail SMTP SSL, port 465).
3. **Verify modal** collects the code → POST `/auth/registro` with all data + code.
   `auth_registro` checks the code exists, is < 15 min old and matches, calls
   `registrar_usuario(..., email)`, clears the pending entry, and auto-logs-in
   (`session['username']`, permanent).

> **Dev mode without SMTP:** if `SMTP_USER/SMTP_PASS` are unset, the code is printed to the
> server console instead of emailed and signup still proceeds, so the flow is testable
> locally without credentials.

### 2. Login / session / logout

- POST `/auth/login` `{username, password, remember}` where `username` may be a **username
  or an email** → `verificar_login` returns the canonical username; `remember` makes the
  session permanent (30-day lifetime).
- GET `/auth/sesion` on every page load (`auth.js` → `comprobarSesion()`) drives the UI in
  **both** directions: `actualizarInterfazLogueado` or `actualizarInterfazDeslogueado`,
  never "leave it as it was". It is fetched with `cache: 'no-store'` and the server sends
  `no-store` on all `/auth/*`; both halves are what fixed the "logged in but the page says
  otherwise until I refresh" bug (Roadmap #22). It is re-run on `pageshow` when the browser
  restores the page from the bfcache.
- POST `/auth/logout` clears the session; the client paints the logged-out state *before*
  reloading, and drops the saved room/token from `localStorage`.
- If the session names an account that no longer exists (deleted), `/auth/sesion` pops it
  from the session instead of leaving the cookie pointing at nothing.

### 2b. Account settings (`/auth/cuenta/*`)

Change username, email or password, and delete the account — all from the ⚙ settings
window ([Frontend](Frontend.md)). Each route reads the user from the session and authorizes
through `_autorizar_cambio()`: **current password, or** a single-use 6-digit code emailed
to the account (`tipo: 'cuenta'`), which is the only option for Google accounts with
`tiene_password = 0`. Notes:

- **Email change is two-step:** the code goes to the *new* address and the old one gets a
  heads-up; nothing is written until the code is confirmed (`tipo: 'cambio_email'`, keyed
  by the new address so it cannot collide with an account code).
- **Rename** re-uses the signup regex and is limited to one every 30 days. Nothing else
  stores usernames — friends, groups, messages and match history all key on `Usuarios.id` —
  so a rename is safe; the client reloads because the open socket still holds the old name
  in its session snapshot.
- **Deletion anonymizes** (`base_datos.anonimizar_usuario`): email, country, birthdate and
  `google_id` are wiped, `eliminada_en` is set, the row is renamed `#CODE` with an unusable
  password, friendships and messages are deleted, and every group membership goes through
  the existing `salir_del_grupo()` so ownership transfers (or the group is removed if empty).
  The `Usuarios` row itself is kept on purpose: `Partidas`/`Partidas4` reference its id, and
  deleting it would corrupt the opponents' history and ELO. Deleting also requires typing
  your own username. The **original username is released** — `#CODE` is not a registrable
  name — so someone else can take it; the two are still distinguishable because each keeps
  its own permanent `codigo`.

### 3. Password recovery (2-step)

1. "¿Olvidaste tu contraseña?" link → forgot modal collects the email → POST
   `/auth/solicitar_reset`. The response is identical whether or not the email exists (no
   account enumeration); if it exists, a `tipo:'reset'` code is emailed.
2. Reset modal collects code + new password → POST `/auth/reset`. On a valid, unexpired
   code, `base_datos.actualizar_password` updates the hash.

### 4. Google OAuth

Authlib is registered **only when** `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` are present.
`/auth/google/login` redirects to Google; `/auth/google/callback` reads the OpenID
userinfo and calls `base_datos.registrar_o_loguear_google(google_id, email, nombre, crear)`,
which finds the account by `google_id`, else links an existing account with the same email,
else — only when `crear` — creates a new one (username derived uniquely from the Google
name, random unusable password). If credentials are absent the route returns 503 and the
flow is inert.

**Log in ≠ sign up.** `/auth/google/login` takes `?intent=login|signup` and stores it in
the Flask session (not in the redirect URL, so it cannot be forced from outside). Only
`btn-google-signup` sends `intent=signup`; `btn-google-login` sends `intent=login` and gets
`crear=False`, so when no account matches the callback redirects to
`/?auth_error=google_sin_cuenta` and the client opens the signup modal instead of silently
creating an account. Anything without an explicit intent is treated as `login`. Before this
(Roadmap #23) both buttons created accounts, which made a *deleted* Google account look
like it had come back to life on the next "log in" — under its old name, since deletion
frees it.

## Security notes / limitations

- `codigos_pendientes` and the rate-limit counters are **in-memory**: lost on restart and
  not shared across processes (fine for the single eventlet worker; would need Redis if
  scaled out).
- Rate limiting is per-email only (3/hour). App-level per-IP limiting (Flask-Limiter) is
  still a Roadmap #16 item.
- Google-only accounts get a random password hash; such a user can set a real password
  from the settings window (an emailed code authorizes it) or via the recovery flow.
- Deleting an account **does** free its username. Anything that has to name a past player
  should use its `codigo`, not its name — see `obtener_jugador_publico()`.
- **Bans** (Roadmap #13, `Usuarios.banned`) are checked in three places, and all three are
  needed: `/auth/login` refuses to open a session (returning the reason), `/auth/sesion`
  clears a cookie that was already issued, and the `connect` handler in `social.py`
  returns `False` so no socket is created. Banning from `/admin` additionally disconnects
  the account's live sockets and evicts it from its room, so it takes effect immediately
  rather than at the next reload.

## How sessions tie into gameplay

Socket.IO handlers read `session.get('username')` (the Flask session cookie is shared with
the WebSocket handshake). The username is stored in `jugadores[sid]['username']` and in the
room, and is used to: prevent playing yourself with the same account, let a room creator
reclaim their seat after a refresh, and record ELO when both players are registered. Guests
can always play by just typing a display name.

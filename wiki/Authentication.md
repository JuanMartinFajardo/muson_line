# Authentication

The account system is **fully implemented** (Roadmap #1, done 2026-07-24). This page
documents the current flows. Secrets come from environment variables / a `.env` file —
see [Setup-and-Deployment](Setup-and-Deployment.md) and `.env.example`.

Frontend auth logic lives in [static/auth.js](../static/auth.js) (loaded after `app.js`,
which still owns the shared helpers `t()`, `cerrarModales()` and the `miUsernameLogueado`
global). Backend routes are in [server.py](../server.py); DB access in
[base_datos.py](../base_datos.py).

## Data model

`Usuarios` gained two columns over the original schema:

- `email TEXT` — unique (case-insensitive) via a partial index; **required for new
  username/password signups**, used for verification and password recovery.
- `google_id TEXT` — unique; set when an account is created or linked via Google.

A startup migration (`base_datos._migrar_columnas`) adds these columns and indexes to
older `mus.db` files without data loss.

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
- GET `/auth/sesion` on every page load (`auth.js` top-level fetch) → if logged in, the UI
  switches to the logged state (`actualizarInterfazLogueado`).
- POST `/auth/logout` clears the session; the page reloads.

### 3. Password recovery (2-step)

1. "¿Olvidaste tu contraseña?" link → forgot modal collects the email → POST
   `/auth/solicitar_reset`. The response is identical whether or not the email exists (no
   account enumeration); if it exists, a `tipo:'reset'` code is emailed.
2. Reset modal collects code + new password → POST `/auth/reset`. On a valid, unexpired
   code, `base_datos.actualizar_password` updates the hash.

### 4. Google OAuth

Authlib is registered **only when** `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` are present.
`/auth/google/login` redirects to Google; `/auth/google/callback` reads the OpenID
userinfo and calls `base_datos.registrar_o_loguear_google(google_id, email, nombre)`, which
finds the account by `google_id`, else links an existing account with the same email, else
creates a new one (username derived uniquely from the Google name, random unusable
password). The `btn-google-signup`/`btn-google-login` buttons redirect to the login route.
If credentials are absent the route returns 503 and the flow is inert.

## Security notes / limitations

- `codigos_pendientes` and the rate-limit counters are **in-memory**: lost on restart and
  not shared across processes (fine for the single eventlet worker; would need Redis if
  scaled out).
- Rate limiting is per-email only (3/hour). App-level per-IP limiting (Flask-Limiter) is
  still a Roadmap #16 item.
- Google-only accounts get a random password hash; such a user can set a real password
  later via the recovery flow (their Google email is on the account).

## How sessions tie into gameplay

Socket.IO handlers read `session.get('username')` (the Flask session cookie is shared with
the WebSocket handshake). The username is stored in `jugadores[sid]['username']` and in the
room, and is used to: prevent playing yourself with the same account, let a room creator
reclaim their seat after a refresh, and record ELO when both players are registered. Guests
can always play by just typing a display name.

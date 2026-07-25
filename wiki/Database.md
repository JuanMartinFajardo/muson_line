# Database — `base_datos.py`

SQLite database `mus.db` in the project root. `init_db()` runs on import, so simply importing `base_datos` creates the table (and runs the migration) if missing.

## Schema

```sql
CREATE TABLE IF NOT EXISTS Usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,      -- werkzeug hash; a random unusable hash for Google-only accounts
    email TEXT,                       -- required for new signups; unique (case-insensitive) via partial index
    google_id TEXT,                   -- set for Google accounts; unique via partial index
    country TEXT,
    birthdate TEXT,
    victorias INTEGER DEFAULT 0,
    derrotas INTEGER DEFAULT 0,
    elo REAL DEFAULT 1200.0,
    fecha_registro TEXT,
    tiene_password INTEGER DEFAULT 1,  -- 0 = created via Google, hash is unusable
    username_cambiado_en TEXT,         -- date of the last rename (30-day cooldown)
    codigo TEXT,                       -- permanent public player code (#A7K2QX); unique, never reused
    eliminada_en TEXT                  -- date of deletion; NULL = live account
);
```

(Plus the 4-player columns `victorias_4p` / `derrotas_4p` / `juegos_4p`, the admin columns
`is_admin` / `banned` / `ban_motivo` / `ban_en`, and the social tables `Friendships`,
`Messages`, `Groups`, `GroupMembers`, `Partidas`, `Partidas4` — all created in `init_db()`
and all keyed on `Usuarios.id`, never on the username.)

### Admin panel tables (Roadmap #13)

```sql
Config(key TEXT PRIMARY KEY, value TEXT, updated_at, updated_by)
AdminAudit(id, fecha, admin, accion, objetivo, detalle, ip)
SupportTickets(id, user_id, asunto, tipo, estado, created_at, updated_at,
               leido_admin, leido_user)
SupportMessages(id, ticket_id, autor('user'|'admin'), autor_nombre, body, created_at)
Anuncios(id, tipo('notificacion'|'pin'), titulo, cuerpo,
         audiencia('todos'|'grupo'|'usuarios'), group_id, destinatarios,
         creado_por, created_at, expira_en, activo)
AnuncioLeido(anuncio_id, user_id, leido_en, UNIQUE(anuncio_id, user_id))
```

`Config` is a plain key→value store read live by whoever cares (`bot_ml` for
`bot_checkpoint`, `server.py` for `bot_delay`, `/api/anuncios` for `mantenimiento_*`), so
new settings need no schema change. `Anuncios.destinatarios` is a CSV of `Usuarios.id`,
only used when `audiencia = 'usuarios'` — short lists that are always read whole.

**Migration:** `_migrar_columnas()` (called by `init_db`) runs `PRAGMA table_info` and
`ALTER TABLE ... ADD COLUMN` for the columns missing on older databases, then creates the
partial unique indexes `idx_usuarios_email` (COLLATE NOCASE), `idx_usuarios_google` and
`idx_usuarios_codigo`. This keeps pre-existing `mus.db` files working with no manual steps.
When `tiene_password` is added it is back-filled to 0 for every row that already has a
`google_id`; `codigo` is back-filled for every row that lacks one (the loop looks for
missing codes rather than for a schema version, so a half-applied migration heals itself
on the next start), and old-style `EliminadoNN` rows are converted to the `#CODE` +
`eliminada_en` scheme.

### Player codes (`codigo`)

Six characters from `ABCDEFGHJKMNPQRSTUVWXYZ23456789` — no `0`/`O`, no `1`/`I`/`L`, since
the code is meant to be read aloud and typed. Displayed as `#A7K2QX`. It is the **only
stable identity a player has in public**: usernames can be changed and, once an account
is deleted, reused by somebody else. A code never changes and is never recycled, because
the row it belongs to is never deleted and the unique index does the rest. Helpers:
`_generar_codigo_libre(cursor)`, `normalizar_codigo(texto)` (`'#a7k-2qx'` → `'A7K2QX'`,
`None` if it isn't one), `obtener_usuario_por_codigo(codigo)`.

### Deleted accounts (`eliminada_en`)

Deletion keeps the row (match history and opponents' ELO depend on its id) but flags it.
A flagged row is skipped by `obtener_usuario`, `obtener_id_usuario`, `verificar_login`,
`obtener_leaderboard`, `obtener_usuario_por_codigo` and both Google lookups, and its
username becomes `#CODE`, which the signup regex can never produce — so the original name
is released without ever colliding.

## Functions

| Function | Purpose |
| :--- | :--- |
| `init_db()` | Creates the `Usuarios` table and runs `_migrar_columnas()` |
| `existe_usuario(username, email)` | Pre-signup duplicate check; returns `(exists, message)` |
| `registrar_usuario(username, password, country, birthdate, email=None)` | Hashes the password (werkzeug) and inserts; returns `(ok, message)`; distinguishes username vs email `IntegrityError` |
| `verificar_login(identificador, password)` | Accepts a username **or** email; returns the canonical username on success, else `None` |
| `email_registrado(email)` | Returns the username for an email, or `None` (used by password reset) |
| `actualizar_password(email, nueva)` | Updates the password hash for the account with that email |
| `registrar_o_loguear_google(google_id, email, nombre, crear=True)` | Finds by `google_id`, else links an account with the same email, else — **only when `crear`** — creates a new one (unique username from the Google name, random unusable password). Returns the username, or `None` when nothing matched and `crear=False` (the *log in* button) |
| `normalizar_codigo(texto)` / `obtener_usuario_por_codigo(codigo)` | Parse a `#A7K2QX` player code / look up the live account that owns it |
| `obtener_jugador_publico(user_id)` | `{id, codigo, eliminada, username}` for showing a player to third parties; a deleted account comes back with `eliminada=True` and no name |
| `obtener_usuario(username)` | Profile dict + computed `winrate`, plus the account fields the settings window needs (`email`, `tiene_password`, `google`, `dias_para_cambiar_username`) — only ever sent to its owner |
| `verificar_password_usuario(username, password)` | `True` if that is the account's current password (used to authorize account changes) |
| `cambiar_username(actual, nuevo)` | Renames the account if free and outside the 30-day cooldown; returns `(ok, codigo)` |
| `cambiar_email(username, nuevo)` | Writes an already-verified email address; returns `(ok, codigo)` |
| `cambiar_password_usuario(username, nueva)` | Sets a new hash and marks `tiene_password` |
| `anonimizar_usuario(username)` | Account deletion: wipes personal data and the social trail, flags `eliminada_en` and renames the row to `#CODE` so match history stays valid and the old username is released; returns `(ok, codigo_msg, nombre_anonimo)` |
| `obtener_email(username)` | Email for a username, or `None` |
| `obtener_leaderboard()` | All users with `username`, `elo`, `victorias`, `winrate` (no ordering/pagination — client sorts) |
| `registrar_partida_completa(ganador, perdedor)` | Increments win/loss counters and updates ELO — **only when both players are registered** |

### Admin panel functions (Roadmap #13)

| Function | Purpose |
| :--- | :--- |
| `es_admin(username)` / `marcar_admin(username, valor)` / `contar_admins()` | The `is_admin` flag; `contar_admins` is what stops the last admin from demoting themselves |
| `esta_baneado(username)` | `(banned, motivo)`; checked by `/auth/login`, `/auth/sesion` and the socket `connect` |
| `buscar_usuarios(texto, limite, incluir_eliminadas)` / `obtener_usuario_admin(id)` | Account search by name, email or `#code`, and the full admin-side record |
| `admin_banear(id, banear, motivo)` / `admin_editar_estadisticas(id, elo, victorias, derrotas)` | Ban/unban and manual stat correction |
| `config_get/config_get_float/config_set/config_delete/config_all` | The `Config` key→value store |
| `registrar_auditoria(...)` / `listar_auditoria(limite)` | `AdminAudit` writes and reads |
| `crear_ticket / responder_ticket / cambiar_estado_ticket / listar_tickets / listar_tickets_de / obtener_ticket / mensajes_ticket / marcar_ticket_leido / contar_tickets_pendientes / contar_soporte_no_leido` | Support threads |
| `crear_anuncio / desactivar_anuncio / listar_anuncios / destinatarios_de / anuncios_para / marcar_anuncio_leido` | Announcements; `anuncios_para(None)` returns the public pinned ones for guests |
| `estadisticas_globales()` | The counters on the panel's front page |

## ELO system

Standard Elo with **K = 16**, starting rating **1200**:

```
P(A beats B) = 1 / (1 + 10^((elo_B − elo_A)/400))
elo_A' = elo_A + K · (S_A − P_A)      # S = 1 win / 0 loss / 0.5 draw
```

Implemented in `calcular_probabilidad()` and `procesar_partida_mus()`. Ratings are rounded to 1 decimal.

## Notes and conventions

- Connections are opened/closed per call (no pool); mostly fine for SQLite at this scale, but heavier features (friends, messaging, tournaments) should introduce a helper (`get_conn()` context manager) and enable WAL mode.
- `DB_NAME = 'mus.db'` is defined but two functions hardcode `'mus.db'` directly — keep consistent when refactoring.
- Guest (non-registered) games are played normally but never touch the database.

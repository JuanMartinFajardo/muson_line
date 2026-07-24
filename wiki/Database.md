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
    fecha_registro TEXT
);
```

**Migration:** `_migrar_columnas()` (called by `init_db`) runs `PRAGMA table_info` and
`ALTER TABLE ... ADD COLUMN` for `email`/`google_id` on older databases, then creates the
partial unique indexes `idx_usuarios_email` (COLLATE NOCASE) and `idx_usuarios_google`. This
keeps pre-existing `mus.db` files working with no manual steps.

## Functions

| Function | Purpose |
| :--- | :--- |
| `init_db()` | Creates the `Usuarios` table and runs `_migrar_columnas()` |
| `existe_usuario(username, email)` | Pre-signup duplicate check; returns `(exists, message)` |
| `registrar_usuario(username, password, country, birthdate, email=None)` | Hashes the password (werkzeug) and inserts; returns `(ok, message)`; distinguishes username vs email `IntegrityError` |
| `verificar_login(identificador, password)` | Accepts a username **or** email; returns the canonical username on success, else `None` |
| `email_registrado(email)` | Returns the username for an email, or `None` (used by password reset) |
| `actualizar_password(email, nueva)` | Updates the password hash for the account with that email |
| `registrar_o_loguear_google(google_id, email, nombre)` | Finds by `google_id`, else links an account with the same email, else creates a new one (unique username from the Google name, random unusable password); returns the username |
| `obtener_usuario(username)` | Profile dict + computed `winrate` |
| `obtener_email(username)` | Email for a username, or `None` |
| `obtener_leaderboard()` | All users with `username`, `elo`, `victorias`, `winrate` (no ordering/pagination — client sorts) |
| `registrar_partida_completa(ganador, perdedor)` | Increments win/loss counters and updates ELO — **only when both players are registered** |

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

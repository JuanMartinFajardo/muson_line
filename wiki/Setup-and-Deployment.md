# Setup and Deployment

## Requirements

- Python 3.12 (`runtime.txt` pins the version for PaaS deploys)
- **Runtime** ([requirements.txt](../requirements.txt)): Flask, Flask-SocketIO, eventlet, gunicorn, **Authlib**, **requests**, plus **torch (CPU wheels)**, installed separately.
- **Training only** ([requirements-train.txt](../requirements-train.txt)): pandas, scikit-learn, joblib, matplotlib, tensorboard. **The server imports none of these** — a production box that does not train models should not install them.

> Torch is required at server startup because `SmartBot` loads the CFR checkpoint on room creation. Install it from the CPU index or `pip` will pull multi-gigabyte CUDA wheels that are never used:
> `pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu`
>
> `torchvision` and `torchaudio` are **not** used anywhere in the project; they used to be in the install line and were pure waste. The CPU index URL is deliberately *not* inside `requirements.txt`: as a requirements-file option it replaces PyPI for the whole file, and Flask and friends are not published on the torch index.

## Local development

```bash
git clone <repo>
cd muson_line
virtualenv .musenv
source .musenv/bin/activate
pip install -r requirements.txt
pip install -r requirements-train.txt   # only if you train models here
cp .env.example .env         # then fill in the secrets (see below)
python3 server.py            # → http://localhost:5001
```

`server.py` runs SocketIO with `debug=True` on `0.0.0.0:5001`. The SQLite DB (`mus.db`) and the `logs/` folder are created automatically; the DB self-migrates new auth columns on startup.

Without a `.env` the server still boots (it prints warnings): email sending and Google login are simply disabled, and signup verification codes are printed to the console so the flow is testable locally.

To test online play locally, open two browser windows (one normal, one private) — the server blocks two seats with the *same logged account*, but two guests or guest+account work.

## Production notes

- `gunicorn` is in requirements; with Flask-SocketIO + eventlet use a single eventlet worker:
  `gunicorn --worker-class eventlet -w 1 server:app -b 0.0.0.0:5001`
  (More than one worker breaks Socket.IO rooms unless a message queue like Redis is added.)
- Static card images get 1-year immutable cache headers from the `after_request` hook.
- The Socket.IO **client** library is loaded from the cdnjs CDN in `index.html`; production behind a strict CSP would need it self-hosted.

## Configuration (environment variables / `.env`)

`server.py` reads these from the environment, falling back to a `.env` file in the project
root (loaded by a tiny built-in parser — python-dotenv is **not** required). Copy
`.env.example` to `.env` and fill it in. Never commit `.env` (it is gitignored).

| Variable | Purpose | How to obtain |
| :--- | :--- | :--- |
| `SECRET_KEY` | Signs Flask session cookies | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `SMTP_USER` | Gmail sender address | e.g. `callmus.contact@gmail.com` |
| `SMTP_PASS` | Gmail **app password** (16 letters) | Google Account → Security → 2-Step Verification → App passwords |
| `SMTP_HOST` / `SMTP_PORT` | SMTP server (optional) | default `smtp.gmail.com` / `465` |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google OAuth | Google Cloud Console → APIs & Services → Credentials → OAuth 2.0 Client ID |
| `ADMIN_USERNAME` | Account promoted to admin at startup — the only way to create the **first** admin. Afterwards the flag is granted from `/admin` and this can be left empty | an existing username |
| `DEBUG_TOKEN` | Optional: enables `GET /api/debug/salas?token=…` (404 without it). `/admin` → *Salas* shows the same thing with a real login | any random string |
| `ANALYTICS_DB` | Optional: path of the analytics database ([Analytics](Analytics.md)). Created on first start; needs no setup | `analitica.db` |
| `ANALYTICS_RETENCION_DIAS` | Optional: days of **raw** analytics rows kept before pruning. Daily aggregates never expire, so long-range charts survive | `90` |
| `SISTEMA_RETENCION_DIAS` | Optional: days of hourly server-health history kept (`SistemaHora`, stored in the analytics DB). Nothing to set up; see [Backend-Server](Backend-Server.md#server-health-sistemapy) | `180` |

The CFR checkpoint the bot uses is **no longer hardcoded**: it is the `bot_checkpoint` row
of the `Config` table, chosen from `/admin` → *Variables y bot*, with the value in
`bot_ml.CHECKPOINT_POR_DEFECTO` as the fallback.

### Admin panel

There is **nothing extra to deploy**: `/admin` runs inside the same Flask process, port
and session as the game. Set `ADMIN_USERNAME` to your account, restart once, and the ⚙
settings window will show a link to the panel.

### Gmail app password (for verification & recovery emails)

1. On the `callmus.contact@gmail.com` account, enable **2-Step Verification** (required).
2. Go to Google Account → Security → **App passwords**, create one for "Mail", and copy the
   16-character value into `SMTP_PASS` (spaces can be omitted). Set `SMTP_USER` to the Gmail
   address. No other Gmail configuration is needed — regular SMTP over SSL (port 465) works.

### Google OAuth credentials

1. In [Google Cloud Console](https://console.cloud.google.com/), create/select a project.
2. Configure the **OAuth consent screen** (External, add the app name and the contact email).
3. Create an **OAuth 2.0 Client ID** of type *Web application* with **Authorized redirect
   URIs**: `https://<your-domain>/auth/google/callback` and, for local testing,
   `http://localhost:5001/auth/google/callback`.
4. Put the resulting client ID and secret into `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`.

> Note: Apple requires "Sign in with Apple" if Google login is offered, before an iOS App
> Store submission (Roadmap item). Not needed for the web launch.

## Training workflow (offline)

1. Play games → `logs/*.jsonl` accumulate.
2. `python3 train_cfr.py` — trains the Deep CFR betting networks (long-running; checkpoints in `learn/cfr/`, TensorBoard logs available).
3. `python3 arena.py` — compare two checkpoints head-to-head (edit the model names at the top).
4. Update the checkpoint name in `bot_ml.py` (`name_model = ...`) and restart the server.

Legacy random-forest pipeline: `python3 global_trainer.py` (compiles `logs/` → `learn/datasets/compiled_dataset.csv` and trains the old models). Not used by the live bot.

# Implementing Friends, Messaging, Groups & Group Leaderboards

Full build guide for the social layer of CallMus ([Roadmap](Roadmap.md) #3). This turns CallMus from a pair of strangers-by-code into a small social platform: add friends, chat (online and offline), form groups, chat in groups, and see group-only ELO leaderboards, plus invite friends straight into a game.

> **Prerequisites:** login must actually work end-to-end first ([Authentication](Authentication.md) / Roadmap #1) — this feature is **for registered users only**; guests are excluded. It also assumes the `Usuarios.email`/`id` columns exist and are stable.

---

## 0. Design overview

Two distinct layers:

1. **Persistence + REST (HTTP):** friendships, messages, groups, memberships — all stored in SQLite and served through session-gated `/api/...` endpoints. This is the source of truth. Everything works even if the recipient is offline.
2. **Presence + real-time (Socket.IO):** a `usuarios_conectados` map so we can show online dots and **push** new messages / friend requests / game invites to connected users instantly. Real-time is a delivery optimization layered on top of persistence — **never the source of truth**.

Golden rule for every action: **persist first, then notify if the peer is online.** Offline peers pick everything up on next login via unread counts.

**Files:**

| File | Change |
| :--- | :--- |
| [base_datos.py](../base_datos.py) | New tables in `init_db()` + a set of new data functions (§1, §2). |
| [server.py](../server.py) | New `/api/friends`, `/api/messages`, `/api/groups` routes; presence tracking in `connect`/`disconnect`; a `notificacion` emit helper. (Additive — don't disturb game handlers.) Consider extracting into a Flask **Blueprint** `social.py` registered on the app to keep `server.py` from growing further. |
| [index.html](../index.html) | A "Friends" button + a social side-panel/modal (friends list, requests, chat, groups). |
| [static/app.js](../static/app.js) | Social UI logic + new i18n keys, reusing the existing modal and leaderboard-render patterns. Optionally split into `static/social.js` (loaded after `app.js`) to keep `app.js` focused. |

Recommendation: put frontend social code in a **new `static/social.js`** and backend in a **new `social.py` Blueprint**, both additive, mirroring the parallel-file approach used elsewhere in this wiki.

---

## 1. Database schema

Add to `base_datos.init_db()` (all `CREATE TABLE IF NOT EXISTS`). Store **user IDs** (`Usuarios.id`), never usernames, as foreign keys.

```sql
CREATE TABLE IF NOT EXISTS Friendships (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_low      INTEGER NOT NULL,          -- always MIN(a,b): canonical ordering
    user_high     INTEGER NOT NULL,          -- always MAX(a,b)
    status        TEXT NOT NULL DEFAULT 'pending',  -- 'pending' | 'accepted' | 'blocked'
    requested_by  INTEGER NOT NULL,          -- who sent the request
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    UNIQUE(user_low, user_high)
);

CREATE TABLE IF NOT EXISTS Messages (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id     INTEGER NOT NULL,
    recipient_id  INTEGER,                   -- for 1:1 DMs (NULL for group messages)
    group_id      INTEGER,                   -- for group messages (NULL for DMs)
    body          TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    read_at       TEXT                       -- NULL = unread (DMs only; groups use a per-user cursor)
);
CREATE INDEX IF NOT EXISTS idx_msg_dm    ON Messages(recipient_id, sender_id, id);
CREATE INDEX IF NOT EXISTS idx_msg_group ON Messages(group_id, id);

CREATE TABLE IF NOT EXISTS Groups (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    owner_id    INTEGER NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS GroupMembers (
    group_id    INTEGER NOT NULL,
    user_id     INTEGER NOT NULL,
    role        TEXT NOT NULL DEFAULT 'member',  -- 'owner' | 'admin' | 'member'
    joined_at   TEXT NOT NULL,
    last_read_id INTEGER DEFAULT 0,          -- highest Messages.id this user has read in the group
    UNIQUE(group_id, user_id)
);
```

**Why `user_low`/`user_high`:** a friendship between users 7 and 3 must be a single row regardless of who asked. Always insert/lookup with `low = min(a,b)`, `high = max(a,b)`. This makes the `UNIQUE` constraint prevent duplicate/mirror requests for free.

**Migration:** since existing `mus.db` files already have data, run an idempotent migration on startup (the `CREATE TABLE IF NOT EXISTS` above is enough for new tables; only `Usuarios` needs `ALTER` handling per Roadmap #1). Add a small `Usuarios.id` lookup helper if not already present.

---

## 2. Backend data functions (`base_datos.py`)

Follow the existing idioms: `sqlite3.connect(DB_NAME)`, parameterized queries, `row_factory = sqlite3.Row` for dict results, connection closed per call. Add a tiny helper to avoid repetition:

```python
def _conn():
    c = sqlite3.connect(DB_NAME)
    c.row_factory = sqlite3.Row
    return c

def obtener_id_usuario(username):
    with _conn() as c:
        r = c.execute("SELECT id FROM Usuarios WHERE username = ?", (username,)).fetchone()
        return r['id'] if r else None
```

### 2.1 Friendships

```python
def enviar_solicitud_amistad(from_id, to_id):
    """Create/refresh a pending friendship. Returns (ok, msg)."""
    if from_id == to_id: return (False, 'self')
    low, high = min(from_id, to_id), max(from_id, to_id)
    now = datetime.now().isoformat()
    with _conn() as c:
        existing = c.execute(
            "SELECT status, requested_by FROM Friendships WHERE user_low=? AND user_high=?",
            (low, high)).fetchone()
        if existing:
            if existing['status'] == 'accepted': return (False, 'already_friends')
            if existing['status'] == 'blocked':  return (False, 'blocked')
            return (False, 'already_pending')
        c.execute("""INSERT INTO Friendships(user_low,user_high,status,requested_by,created_at,updated_at)
                     VALUES(?,?,'pending',?,?,?)""", (low, high, from_id, now, now))
    return (True, 'sent')

def responder_solicitud(user_id, other_id, aceptar):
    """The *recipient* accepts or declines. Only the non-requester may respond."""
    low, high = min(user_id, other_id), max(user_id, other_id)
    now = datetime.now().isoformat()
    with _conn() as c:
        row = c.execute("SELECT requested_by,status FROM Friendships WHERE user_low=? AND user_high=?",
                        (low, high)).fetchone()
        if not row or row['status'] != 'pending' or row['requested_by'] == user_id:
            return False
        if aceptar:
            c.execute("UPDATE Friendships SET status='accepted', updated_at=? WHERE user_low=? AND user_high=?",
                      (now, low, high))
        else:
            c.execute("DELETE FROM Friendships WHERE user_low=? AND user_high=?", (low, high))
    return True

def eliminar_amistad(user_id, other_id): ...   # DELETE the row
def bloquear_usuario(user_id, other_id): ...   # status='blocked', requested_by=user_id

def listar_amigos(user_id):
    """Accepted friends with their public stats. Presence dot is added in the route (§3)."""
    with _conn() as c:
        rows = c.execute("""
            SELECT u.id, u.username, u.elo, u.victorias, u.derrotas
            FROM Friendships f
            JOIN Usuarios u ON u.id = CASE WHEN f.user_low=? THEN f.user_high ELSE f.user_low END
            WHERE (f.user_low=? OR f.user_high=?) AND f.status='accepted'
            ORDER BY u.username COLLATE NOCASE
        """, (user_id, user_id, user_id)).fetchall()
        return [dict(r) for r in rows]

def listar_solicitudes_pendientes(user_id):
    """Incoming requests (someone else asked me)."""
    with _conn() as c:
        rows = c.execute("""
            SELECT u.id, u.username FROM Friendships f
            JOIN Usuarios u ON u.id = f.requested_by
            WHERE ((f.user_low=? OR f.user_high=?)) AND f.status='pending' AND f.requested_by != ?
        """, (user_id, user_id, user_id)).fetchall()
        return [dict(r) for r in rows]

def son_amigos(a_id, b_id) -> bool: ...        # used to gate DMs
```

### 2.2 Messages (DMs)

```python
MAX_MSG_LEN = 500

def enviar_mensaje_dm(sender_id, recipient_id, body):
    body = (body or '').strip()
    if not body or len(body) > MAX_MSG_LEN: return (False, None)
    if not son_amigos(sender_id, recipient_id): return (False, None)  # only friends DM
    now = datetime.now().isoformat()
    with _conn() as c:
        cur = c.execute("""INSERT INTO Messages(sender_id,recipient_id,body,created_at)
                           VALUES(?,?,?,?)""", (sender_id, recipient_id, body, now))
        msg_id = cur.lastrowid
    return (True, {'id': msg_id, 'sender_id': sender_id, 'recipient_id': recipient_id,
                   'body': body, 'created_at': now})

def obtener_conversacion(user_id, friend_id, before_id=None, limit=50):
    """Paginated DM history (newest first, or older than before_id). Marks them read."""
    with _conn() as c:
        params = [user_id, friend_id, friend_id, user_id]
        clause = ""
        if before_id:
            clause = "AND id < ?"; params.append(before_id)
        rows = c.execute(f"""
            SELECT * FROM Messages
            WHERE recipient_id IS NOT NULL
              AND ((sender_id=? AND recipient_id=?) OR (sender_id=? AND recipient_id=?)) {clause}
            ORDER BY id DESC LIMIT ?""", (*params, limit)).fetchall()
        # mark inbound-to-me as read
        c.execute("UPDATE Messages SET read_at=? WHERE recipient_id=? AND sender_id=? AND read_at IS NULL",
                  (datetime.now().isoformat(), user_id, friend_id))
        return [dict(r) for r in rows][::-1]   # return chronological

def contar_no_leidos(user_id):
    """Total unread DMs, and a per-friend breakdown, for badges."""
    with _conn() as c:
        rows = c.execute("""SELECT sender_id, COUNT(*) n FROM Messages
                            WHERE recipient_id=? AND read_at IS NULL GROUP BY sender_id""",
                         (user_id,)).fetchall()
        return {r['sender_id']: r['n'] for r in rows}
```

### 2.3 Groups

```python
def crear_grupo(owner_id, name):
    name = (name or '').strip()
    if not (3 <= len(name) <= 40): return (False, None)
    now = datetime.now().isoformat()
    with _conn() as c:
        gid = c.execute("INSERT INTO Groups(name,owner_id,created_at) VALUES(?,?,?)",
                        (name, owner_id, now)).lastrowid
        c.execute("INSERT INTO GroupMembers(group_id,user_id,role,joined_at) VALUES(?,?, 'owner', ?)",
                  (gid, owner_id, now))
    return (True, gid)

def es_miembro(group_id, user_id) -> bool: ...
def añadir_miembro(group_id, user_id, by_id): ...     # owner/admin only; UNIQUE prevents dupes
def salir_del_grupo(group_id, user_id): ...           # owner leaving → transfer or delete group
def listar_grupos_de(user_id): ...                    # groups I belong to (+ my unread count)
def listar_miembros(group_id): ...                    # members + roles

def enviar_mensaje_grupo(sender_id, group_id, body):
    if not es_miembro(group_id, sender_id): return (False, None)
    # same length checks; INSERT with group_id set, recipient_id NULL
    ...

def obtener_mensajes_grupo(group_id, user_id, before_id=None, limit=50):
    # verify membership; page like DMs; then bump GroupMembers.last_read_id to newest id
    ...

def leaderboard_grupo(group_id):
    """Group-only ELO table — the existing global query filtered by membership."""
    with _conn() as c:
        rows = c.execute("""
            SELECT u.username, u.elo, u.victorias, u.derrotas
            FROM GroupMembers gm JOIN Usuarios u ON u.id = gm.user_id
            WHERE gm.group_id = ? ORDER BY u.elo DESC""", (group_id,)).fetchall()
        out = []
        for r in rows:
            total = r['victorias'] + r['derrotas']
            out.append({'username': r['username'], 'elo': r['elo'],
                        'victorias': r['victorias'],
                        'winrate': round(r['victorias']/total*100, 1) if total else 0.0})
        return out
```

> Note `leaderboard_grupo` reproduces the exact shape returned by the existing `obtener_leaderboard()` so the **frontend leaderboard renderer can be reused unchanged** (§5.4).

---

## 3. HTTP API (session-gated)

Add a small decorator and the routes. Every route requires a logged-in session; return 401 otherwise. All IDs resolved from `session['username']` server-side — **never trust a client-supplied user id for the "me" side.**

```python
from functools import wraps
def login_requerido(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if 'username' not in session:
            return jsonify({'exito': False, 'mensaje': 'no_auth'}), 401
        return f(*a, **kw)
    return wrapper

def _mi_id():
    return base_datos.obtener_id_usuario(session['username'])
```

| Method & path | Body | Action |
| :--- | :--- | :--- |
| `GET  /api/friends` | — | `listar_amigos(me)` + online flag per friend (from `usuarios_conectados`, §4) + unread counts (`contar_no_leidos`). |
| `GET  /api/friends/requests` | — | `listar_solicitudes_pendientes(me)`. |
| `POST /api/friends/request` | `{username}` | resolve target id, `enviar_solicitud_amistad`; if target online → push `notificacion`. |
| `POST /api/friends/respond` | `{user_id, accept}` | `responder_solicitud`; notify requester if online. |
| `DELETE /api/friends/<user_id>` | — | `eliminar_amistad`. |
| `POST /api/friends/<user_id>/block` | — | `bloquear_usuario`. |
| `GET  /api/messages/<friend_id>?before=<id>` | — | `obtener_conversacion` (marks read). |
| `POST /api/messages/<friend_id>` | `{body}` | `enviar_mensaje_dm`; if friend online → push `notificacion` with the message. |
| `POST /api/friends/<friend_id>/invite` | `{al_mejor_de}` | create a **private** game room (reuse `crear_sala` internals) and push the room code to the friend as a `notificacion` (§6). |
| `POST /api/groups` | `{name}` | `crear_grupo`. |
| `GET  /api/groups` | — | `listar_grupos_de(me)` (+ unread). |
| `GET  /api/groups/<id>` | — | metadata + `listar_miembros`. |
| `POST /api/groups/<id>/invite` | `{username}` | owner/admin only → `añadir_miembro`; notify invitee. |
| `POST /api/groups/<id>/leave` | — | `salir_del_grupo`. |
| `GET  /api/groups/<id>/messages?before=<id>` | — | `obtener_mensajes_grupo`. |
| `POST /api/groups/<id>/messages` | `{body}` | `enviar_mensaje_grupo`; push to online members. |
| `GET  /api/groups/<id>/leaderboard` | — | `leaderboard_grupo`. |

**Validation / abuse limits (server-side, always):** message length ≤ 500; max 200 friends; max 50 group memberships; group name 3–40 chars; a simple in-memory rate limit on `POST /api/messages/*` and `/api/friends/request` (e.g. token bucket per user id — reuse for Roadmap #16). Membership/ownership checks on every group route.

---

## 4. Presence & real-time (Socket.IO)

The game already uses Flask sessions on the socket handshake (handlers read `session.get('username')`). Reuse that.

```python
# in server.py (module scope, next to jugadores/salas)
usuarios_conectados = {}   # username -> set of sids (a user may have multiple tabs)

@socketio.on('connect')
def social_on_connect():
    u = session.get('username')
    if u:
        usuarios_conectados.setdefault(u, set()).add(request.sid)
        _broadcast_presencia(u, True)          # tell this user's friends he's online

@socketio.on('disconnect')
def social_on_disconnect():
    u = session.get('username')
    if u and u in usuarios_conectados:
        usuarios_conectados[u].discard(request.sid)
        if not usuarios_conectados[u]:
            del usuarios_conectados[u]
            _broadcast_presencia(u, False)
```

> **Important:** `server.py` already defines a `@socketio.on('disconnect')` for game cleanup. Flask-SocketIO allows **multiple handlers for the same event**, so add these as *separate* handlers (ideally in `social.py`) rather than editing the game one — keeps concerns isolated per the wiki's non-interference principle.

Helpers:

```python
def _sids_de(username):
    return list(usuarios_conectados.get(username, []))

def notificar(username, tipo, payload):
    """Push a real-time notification to all of a user's connected tabs."""
    for sid in _sids_de(username):
        socketio.emit('notificacion', {'tipo': tipo, **payload}, room=sid)

def _broadcast_presencia(username, online):
    """Notify this user's *accepted friends* that his status changed."""
    uid = base_datos.obtener_id_usuario(username)
    for amigo in base_datos.listar_amigos(uid):
        notificar(amigo['username'], 'presencia', {'username': username, 'online': online})
```

**`notificacion` types** (client switches on `tipo`): `mensaje` (new DM), `mensaje_grupo`, `solicitud_amistad`, `amistad_aceptada`, `presencia`, `invitacion_partida`, `invitacion_grupo`.

Everything is **persisted by the REST layer first**; `notificar` is best-effort delivery. Offline users get nothing pushed but see unread badges + pending requests on next `GET /api/friends`.

---

## 5. Frontend UI

Reuse the existing patterns from [index.html](../index.html) / [static/app.js](../static/app.js): the `modal-overlay` + `modal-*` + `.btn-cerrar-modal` + `cerrarModales()` machinery, and the leaderboard table renderer.

### 5.1 Entry point

Add a **Friends** button to the logged-in user bar (`#user-info-logged`, index.html ~line 51), next to the logout button, with an unread badge:

```html
<button id="btn-amigos" data-i18n="btn_amigos" class="hidden">
  👥 Amigos <span id="amigos-badge" class="hidden badge">0</span>
</button>
```

Show it only when logged in (unhide it inside `actualizarInterfazLogueado()` in [static/auth.js](../static/auth.js)). Guests never see social UI.

### 5.2 Social panel (a new modal `#modal-social`)

A modal with a left tab strip and a content area — three tabs:

- **Amigos (Friends):** list of friends, each row = online dot (green/grey) · username · ELO · buttons **💬 Chat**, **🎮 Invite**, **✕ Remove**. A "＋ Add friend" input (username → `POST /api/friends/request`). A **Requests** sub-section with Accept/Decline per pending request (badge shows count).
- **Grupos (Groups):** list of my groups (name + unread badge → opens group chat), a "＋ Create group" input, and inside a group: member list, **Group chat**, **🏆 Group leaderboard**, invite input (owner/admin), leave button.
- **Chat view:** a scrollable message list + text input + send button; used for both DM and group chat (same component, different endpoint).

Keep every string in `data-i18n` / `t()` (§7).

### 5.3 Client logic (`static/social.js`)

```js
// Poll-free: rely on 'notificacion' socket events for live updates,
// and fetch full lists when the panel opens.
async function cargarAmigos() {
  const r = await fetch('/api/friends').then(x => x.json());
  renderListaAmigos(r.amigos);       // online dot from r.amigos[i].online
  actualizarBadge(r.total_no_leidos);
}

async function abrirChat(friendId, friendName) {
  const r = await fetch(`/api/messages/${friendId}`).then(x => x.json());
  renderMensajes(r.mensajes, /* soyYo por sender_id */);
  // send:
  btnEnviar.onclick = async () => {
    const body = inputChat.value.trim(); if (!body) return;
    inputChat.value = '';
    const res = await fetch(`/api/messages/${friendId}`, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({body})
    }).then(x=>x.json());
    if (res.exito) appendMensaje(res.mensaje, true);   // optimistic echo
  };
}

// Live updates:
socket.on('notificacion', (n) => {
  switch (n.tipo) {
    case 'mensaje':
      if (chatAbiertoCon === n.sender_id) appendMensaje(n, false);
      else incrementarBadge(n.sender_id);
      break;
    case 'presencia':      setDotOnline(n.username, n.online); break;
    case 'solicitud_amistad': mostrarToast(t('toast_nueva_solicitud')); refrescarRequests(); break;
    case 'invitacion_partida': mostrarInvitacionPartida(n); break;  // §6
    // ...
  }
});
```

Reuse the same `socket` global from `app.js` (loaded first). Don't duplicate the i18n dict — extend it (§7).

### 5.4 Group leaderboard — reuse the existing renderer

The global leaderboard already has a table renderer in `app.js` (the `#modal-leaderboard` / `lista-leaderboard-body` logic). Because `leaderboard_grupo` returns the **same object shape** as `obtener_leaderboard`, refactor that renderer into a reusable `renderLeaderboard(rows, tbodyEl)` and call it with the group rows in the group leaderboard sub-view. No new table markup needed — just a second `<tbody>` target.

---

## 6. Friend game invites (tie-in with the lobby)

The payoff feature: invite a friend directly into a game instead of copy-pasting codes.

1. `POST /api/friends/<id>/invite` (or a `socket.emit('invitar_amigo', {friend_id, al_mejor_de})`) → server creates a **private** room using the *existing* `crear_sala` internals (reuse `generar_codigo`, populate `salas[codigo]` with `estado='esperando'`, `publico=False`, seat 0 = inviter's sid). Return the code to the inviter (who is placed in the waiting panel exactly as today) and `notificar(friend, 'invitacion_partida', {codigo, de: inviter_name, al_mejor_de})`.
2. The invitee's client shows an accept/decline toast; **Accept** runs the normal existing flow: `socket.emit('unirse_sala', {codigo, nombre})` — which already handles seating and starting the game. **No changes to the game engine or the join handler needed.**
3. Decline → optional `notificar(inviter, 'invitacion_rechazada', ...)`.

This reuses the entire existing room/seat/start machinery; the social layer only introduces the room and delivers the code.

---

## 7. i18n keys

Add to **both** `dict.es` and `dict.en` in `app.js`. Sample:

| Key | ES | EN |
| :--- | :--- | :--- |
| `btn_amigos` | "Amigos" | "Friends" |
| `tab_amigos` / `tab_grupos` | "Amigos" / "Grupos" | "Friends" / "Groups" |
| `add_friend_ph` | "Añadir amigo por usuario…" | "Add friend by username…" |
| `friend_requests` | "Solicitudes" | "Requests" |
| `btn_aceptar` / `btn_rechazar` | "Aceptar" / "Rechazar" | "Accept" / "Decline" |
| `btn_chat` / `btn_invitar_juego` / `btn_eliminar_amigo` | "Chat" / "Invitar" / "Eliminar" | "Chat" / "Invite" / "Remove" |
| `crear_grupo_ph` | "Nombre del grupo…" | "Group name…" |
| `btn_crear_grupo` | "Crear grupo" | "Create group" |
| `group_leaderboard` | "Clasificación del grupo" | "Group leaderboard" |
| `chat_ph` | "Escribe un mensaje…" | "Type a message…" |
| `estado_online` / `estado_offline` | "En línea" / "Desconectado" | "Online" / "Offline" |
| `toast_nueva_solicitud` | "Nueva solicitud de amistad" | "New friend request" |
| `invitacion_de` | "{nombre} te invita a jugar" | "{nombre} invites you to play" |
| `sin_amigos` | "Aún no tienes amigos. ¡Añade a alguien!" | "No friends yet. Add someone!" |
| `sin_grupos` | "No perteneces a ningún grupo." | "You're not in any group." |
| `err_ya_amigos` / `err_pendiente` / `err_bloqueado` | "Ya sois amigos." / "Solicitud ya enviada." / "Usuario no disponible." | "Already friends." / "Request already sent." / "User unavailable." |

Server → client text that needs localization travels as codes (e.g. the invite `notificacion` sends `de` as a raw name plus a `tipo`, and the client formats with `t_dinamico('invitacion_de', {nombre})`), matching the existing `mensaje`/`t_dinamico` pattern.

---

## 8. Security & privacy notes

- **DMs only between accepted friends** (`son_amigos` gate in `enviar_mensaje_dm`) — prevents spam from strangers.
- **Never expose** email, birthdate, password hash, or country through any social endpoint — only username, ELO, wins, winrate (the public leaderboard fields).
- All group/message routes verify membership/ownership server-side; a client can't read a group it isn't in by guessing the id.
- Resolve the "me" identity from the session, not the request body.
- Rate-limit friend requests and messages (ties into Roadmap #16). Escape/````textContent```` message bodies on render — **never `innerHTML`** user text (XSS). This is the one place the app renders untrusted user input, so be strict.
- `blocked` status hides the blocker from search and silently drops requests/messages.

---

## 9. Build order & testing

**Suggested order:** schema + data functions → REST endpoints (test with curl/Postman) → presence + `notificacion` → friends UI → DM chat → groups → group leaderboard → game invites.

**Test with two+ registered accounts (two browser contexts):**

1. A sends B a friend request → B sees it (live if online, on next load if offline) → B accepts → both see each other with correct online dots.
2. A messages B while B is offline → B logs in → sees unread badge → opens chat → history loads → messages marked read → badge clears.
3. Presence: A opens/closes a tab → B's dot updates live; A with two tabs stays "online" until both close.
4. Group: A creates a group, invites B and C → all three chat → group leaderboard shows the three members' ELO sorted, and reuses the global leaderboard renderer.
5. Invite: A invites B to a game from the friends list → B accepts the toast → they land in a normal 2p game via the untouched `unirse_sala` flow → result records ELO as usual.
6. Abuse: sending a 600-char message, adding yourself, double friend request, reading a group you're not in, DM to a non-friend — all rejected server-side.
7. **Regression:** guests can still play by code; the game screen, leaderboard, and auth flows are unchanged (social code is additive and gated on login).

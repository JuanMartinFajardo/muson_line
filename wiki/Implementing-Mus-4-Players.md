# Implementing 4-Player Mus (2v2, online only, no bots)

Exact, step-by-step build guide for the 4-player variant of CallMus: mechanics, interface, animations, information messages, connection handling, and menu integration. Scope of this document: **4 human players online, in a single room, no bots** (bots come later — see [Roadmap](Roadmap.md) #7/#8).

> **Guiding principle — do not destabilize the 2-player game.**
> The 2p engine ([mus_mecanicas.py](../mus_mecanicas.py)) is used both live and by the training pipeline (`mus_env.py`, `train_cfr.py`, `arena.py`). We will **not edit `PartidaMus`, `bot_ml.py`, or the CFR code**. We add a **parallel** engine, parallel server handlers, and a parallel frontend screen. The only edits to existing files are additive: a menu button + a `modo` switch in a few `server.py` handlers, and a screen-switch hook in `app.js`. Everything else is new files.

---

## 0. File plan

**New files (all additive):**

| File | Purpose |
| :--- | :--- |
| `mus_core.py` | Shared **pure** functions, imported by both engines. See §2 — we *import* from `mus_mecanicas.py`, we don't move code, to avoid touching the 2p file. |
| `mus_mecanicas_4.py` | New `PartidaMus4` engine (2v2 state machine). |
| `server_mus4.py` | All Socket.IO handlers for 4p, registered onto the existing `socketio` instance. |
| `static/app4.js` | 4p client: socket events, state, and the render loop. |
| `static/table4.js` | 4p table renderer (4-seat layout) — kept separate so `app.js` stays 2p-only. |
| `static/style4.css` | 4p-specific layout/animation CSS (imported after `style.css`). |

**Minimal edits to existing files:**

| File | Edit |
| :--- | :--- |
| [index.html](../index.html) | Add a **"Mus 4 jugadores"** button in the lobby panel; add a hidden `#game-screen-4` container; add `<script src="/static/app4.js">` and `<script src="/static/table4.js">`; `<link>` `style4.css`. |
| [server.py](../server.py) | One line: `import server_mus4` (after `socketio` is defined) so its `@socketio.on(...)` handlers register. Optionally add a `modo` field when listing public games so 4p rooms show a "4p" tag. |
| [static/app.js](../static/app.js) | Nothing functional required — 4p lives in its own screen/socket-event namespace. (If you want a shared language toggle, expose `langActual`/`t()` on `window` and reuse them in `app4.js` instead of duplicating the dictionary.) |

Keeping 4p on **distinct Socket.IO event names** (`crear_sala_4`, `accion_juego_4`, `actualizar_mesa_4`, …) means the two games never collide and you can develop 4p without breaking 2p.

---

## 1. Rules to implement (2v2 Mus)

Differences from the 2p rules already documented in [Game-Rules](Game-Rules.md):

- **4 players, 2 teams.** Seats 0-1-2-3 around the table; **partners sit across**: team A = seats {0, 2}, team B = seats {1, 3}. Points are **per team** (both partners share the score).
- **Mano** is one seat; roles rotate **one seat per round** (mano → next seat). Turn order is fixed table order starting at mano.
- **Mus phase:** going around the table from mano, each player says mus / no-mus. **Mus only continues if all four want it**; a single "no mus" (cut) ends the mus phase and betting begins with the cutter... — actually, standard rule: the player who cut speaks first in Grande. Keep that (`quien_corta_mus`).
- **Discards:** every player who wants cards discards 1–4 and draws; deck reshuffles from discards when empty (same `robar` logic — trigger the deck-exhausted notice, Roadmap #14).
- **Declarations:** for **Pares** and **Juego**, all four players declare (have / don't have). A lance is only bet if **both teams** have at least one qualifying player; otherwise it's skipped or auto-won by the qualifying team (bonuses still counted at showdown for each qualifying hand).
- **Betting is team-vs-team** (see §3.4 for the concrete v1 model). Actions: pasar, envidar, subir, ver, no ver, órdago — same vocabulary as 2p.
- **Showdown / recuento:** for each lance, compare the **best hand of team A** against the **best hand of team B**; the winning team scores. **Bonuses (Pares/Juego) count for _every_ qualifying hand on the winning team** (e.g. if both partners have pairs, both pairs' premios add up). Ties resolved by proximity to mano (the hand belonging to the player closest to mano in turn order wins the tie).
- **Señas (partner signals)** were excluded from v1 and **shipped later as an optional table setting** — see [Señas (2v2)](Senas-2v2.md). Partners still **never see each other's cards**: a sign transmits a *gesture*, and only to whoever happens to be looking at that moment.

---

## 2. Shared pure functions (`mus_core.py`)

`mus_mecanicas.py` already exposes these as module-level pure functions:
`crear_baraja`, `get_valores_mus`, `tiene_pares`, `get_pares_info`, `get_suma_juego`, `tiene_juego`, `es_la_real`, `comparar_cartas`, `comp_pares_info`, `comp_juego`, `comp_punto`, `obtener_ruta_imagen`, `J_RANK`.

**Do not move them** (that would touch the 2p file and its imports). Instead, `mus_core.py` re-exports them:

```python
# mus_core.py — thin shared layer, zero logic duplication
from mus_mecanicas import (
    crear_baraja, get_valores_mus, tiene_pares, get_pares_info,
    get_suma_juego, tiene_juego, es_la_real, comparar_cartas,
    comp_pares_info, comp_juego, comp_punto, J_RANK,
)

def mejor_hand_equipo(cartas_por_jugador, comparador, is_grande=None):
    """Return the seat index whose hand is best for a lance, within one team.
    cartas_por_jugador: {seat: cards}. comparador: one of the comp_* funcs.
    Reuses the 2p pairwise comparators to reduce a team to its representative hand."""
    seats = list(cartas_por_jugador)
    best = seats[0]
    for s in seats[1:]:
        if is_grande is None:
            gan = comparador(cartas_por_jugador[best], cartas_por_jugador[s])
        else:
            gan = comparador(cartas_por_jugador[best], cartas_por_jugador[s], is_grande)
        if gan == 'postre':   # the 2p comparators return 'mano'/'postre'; 'postre' = second arg won
            best = s
    return best
```

`PartidaMus4` imports only from `mus_core`, so the 2p engine file is never touched.

---

## 3. The engine — `mus_mecanicas_4.py`

Model `PartidaMus4` closely on `PartidaMus` so the two are familiar, but generalize the 2-player assumptions (roles, `estado` keyed by 2 sids, pairwise comparators, per-player points) to **4 seats / 2 teams**.

### 3.1 Construction & state

```python
class PartidaMus4:
    FASES_APUESTA = ['Grande', 'Chica', 'Pares', 'Juego']

    def __init__(self, sids):            # sids: list of 4, already in seat order 0..3
        self.seats = list(sids)          # index = seat number
        self.equipos = {'A': [0, 2], 'B': [1, 3]}
        self.equipo_de = {0: 'A', 1: 'B', 2: 'A', 3: 'B'}

        self.mano = random.randint(0, 3) # seat index of Mano this round
        self.baraja = []; self.descartes = []

        self.estado = {                  # keyed by SEAT, not sid
            s: {'cartas': [], 'quiere_mus': None,
                'descartes_listos': False, 'descartes_hechos': 0,
                'tiene_pares_dec': None, 'tiene_juego_dec': None}
            for s in range(4)
        }
        self.puntos = {'A': 0, 'B': 0}   # team scores
        self.partidas_ganadas = {'A': 0, 'B': 0}
        self.al_mejor_de = 3
        self.match_finalizado = False

        self.fase = 'espera_reparto'     # same phase names as 2p
        self.indice_fase = 0
        self.turno_de = None             # SEAT whose turn it is
        self.botes   = {f: 0 for f in self.FASES_APUESTA}
        self.dejes_fase = {f: None for f in self.FASES_APUESTA}
        self.ganadores_fase = {f: None for f in self.FASES_APUESTA}  # stores 'A'/'B'
        self.apuesta_vista = 0
        self.subida_pendiente = 0
        self.quien_sube = None           # team 'A'/'B' that has the live bet
        self.ronda_n = 0
        self.mensaje_transicion = None
        self.jugadores_listos = []       # seats ready for next round
        # logging (reuse the 2p JSONL shape, add modo='4p')
        self.match_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        self.nombres = {}                # {seat: display name}
        self.historial_ia = []; self.generate_log = True
```

Key structural change vs 2p: **`estado` is keyed by seat index**, not by sid, and **points/bets are per team**. The server keeps the `seat ↔ sid` mapping (§4), so the engine never deals with socket ids — this is the clean design the [Roadmap](Roadmap.md) recommends and it makes reconnection trivial later.

### 3.2 Turn order helpers

```python
def orden_desde(self, seat):
    """Table order starting at `seat`: [seat, seat+1, seat+2, seat+3] mod 4."""
    return [(seat + i) % 4 for i in range(4)]

def siguiente_seat(self, seat):
    return (seat + 1) % 4

def siguiente_rival(self, seat):
    """Next seat belonging to the opposing team, in table order."""
    eq = self.equipo_de[seat]
    for s in self.orden_desde(self.siguiente_seat(seat)):
        if self.equipo_de[s] != eq:
            return s
```

### 3.3 Round flow (mirror the 2p method names)

- `iniciar_ronda()` — reset per-round state, `ronda_n += 1`, `fase='espera_reparto'`, `turno_de = self.mano` (Mano triggers the deal, like 2p Postre does — pick one and stay consistent), clear declarations.
- `repartir_inicial()` — `crear_baraja()`, shuffle, deal 4 to each seat, `fase='mus'`, `turno_de = self.mano`.
- `cantar_mus(seat, quiere)`:
  - record decision; if `quiere is False`, `quien_corta_mus = seat`, go to `iniciar_fase_apuestas()`.
  - otherwise advance `turno_de` to the next seat in `orden_desde(mano)` that hasn't spoken; when **all four** said mus → `fase='descarte'`, reset `descartes_listos`, `rondas_mus += 1`.
- `procesar_descarte(seat, indices)` — identical logic to 2p but per seat; when **all four** `descartes_listos`, return to `fase='mus'`, clear `quiere_mus`, `turno_de=self.mano`.
- Pedrete: keep it (4-5-6-7 hand) exactly as 2p (`procesar_pedrete(seat)`) — awards the point to that seat's **team**.

### 3.4 Betting model (v1 — simple, unambiguous, team-based)

The trickiest generalization. Use this concrete, well-defined model (a faithful-enough 2v2; note the simplification in code comments):

- Within a lance, players act in **table order from mano**. State tracks `turno_de` (seat) and `equipo_apostador` (the team with a live bet, or `None`).
- **No live bet (`subida_pendiente == 0`):** the seat on turn may `pasar`, `envidar`, or `ordago`.
  - `pasar` → advance `turno_de` to next seat. If all four pass consecutively, the lance closes "en paso" (1 "de paso" point to the eventual Grande/Chica winner, resolved at recuento; nothing for Pares/Juego). Reuse a `pases_consecutivos` counter that resets on any bet, but count **4** for a full pass-around.
  - `envidar(cantidad)` / `ordago` → set `subida_pendiente`, `quien_sube = equipo_de[seat]`, and pass control to **`siguiente_rival(seat)`** (the responding team).
- **Live bet pending:** the responder (a member of the opposing team) may `ver`, `subir`, `nover`, or `ordago`.
  - `ver` → pot resolved; add `apuesta_vista + subida` to the lance's bote; advance to next lance.
  - `subir` → increase the bet; control passes back to `siguiente_rival(responder)`.
  - `nover` (fold) → the betting team wins the lance concession (`dejes_fase`, `ganadores_fase[lance]=quien_sube`); advance to next lance.
  - `ordago` → mark `subida_pendiente='ÓRDAGO'`, pass to `siguiente_rival`.
- **Simplification to document in code:** only the single "responder" seat answers on behalf of its team (real mus lets either partner respond / accept an órdago). This is acceptable for v1 and keeps the state machine deterministic. A v2 can add "either partner may respond" by broadening the turn check to "any seat of the responding team."
- Keep the **two 2p safety rules** verbatim (they generalize cleanly): raises capped at `40 − max(team points) − apuesta_vista` (excess → auto-órdago), and a fold that would hand the opposing **team** the game (their points + concession ≥ 40) auto-converts to `ver`.

`accion_apuesta(seat, accion, cantidad)` is a direct adaptation of the 2p method — copy its structure, replace `jugador/rival` (sids) with `seat` / `siguiente_rival(seat)`, and replace per-player point reads/writes with **team** reads/writes (`self.puntos[self.equipo_de[seat]]`).

### 3.5 Lance setup & skipping (Pares / Juego)

`preparar_subfase()` mirrors 2p but checks **teams**:

- **Pares:** a team "has pares" if **any** of its two players has pares. If only one team has pares → skip the lance, auto-assign `ganadores_fase['Pares']` to that team (bonuses still added at recuento). If neither team → skip with the `nadie_pares` transition message. Turn starts at the first seat (from mano) whose team is eligible.
- **Juego:** a team "has juego" if any member reaches 31. If neither team has juego → **Punto** (`juego_es_punto=True`, `juego_a_punto` message), still bet. If exactly one team has juego → skip, auto-assign.
- Declarations (`tiene_pares_dec`, `tiene_juego_dec`) are collected from all four during a short **declaration sub-step** before Pares/Juego betting; expose them in the payload so the UI can show "Pares sí/no" chips per seat (without revealing cards).

### 3.6 Recuento (`calcular_recuento`)

Adapt the 2p method:

- For each lance (or only `ordago_aceptado_en`): determine the winning **team**.
  - If a team already won by fold/skip (`ganadores_fase[lance]`), use it.
  - Otherwise compute each team's **representative (best) hand** with `mejor_hand_equipo` (§2) and compare the two representatives with the matching `comp_*`. Ties → team of the seat closest to mano.
- Points: `bote + bonus`. **Bonus counts every qualifying hand of the winning team** (sum both partners' `get_pares_info(...)['premio']`, or both juego premios). Cap team score at 40 (`min(40, ...)`).
- Mark game/match winners on team scores; `match_finalizado` when a team reaches `ceil(al_mejor_de/2)`.
- **Logging:** append per-turn records to `logs/<match_id>.jsonl` with an added `"modo": "4p"` field and seat/team context, reusing the 2p JSONL shape so the corpus stays uniform (feeds Roadmap #7 later). Guard with `self.generate_log`.

### 3.7 Round advance

- `listo_siguiente_ronda`: when all four seats are ready, either reset the game (a team hit 40 and the match isn't over → rotate mano, zero team points) or advance to the next round (`mano = siguiente_seat(mano)`, `iniciar_ronda`, `fase='espera_reparto'`). Same shape as the 2p handler in `server.py`.

---

## 4. Server — `server_mus4.py`

Register handlers on the existing `socketio` (imported from `server`). Reuse `server.py`'s `jugadores` dict for name/room lookup but keep a **separate room registry** for 4p to avoid entangling the 2p logic.

### 4.1 Room registry

```python
from server import socketio, jugadores, generar_codigo   # reuse helpers
from flask import request, session
from flask_socketio import emit, join_room, leave_room
from mus_mecanicas_4 import PartidaMus4

salas4 = {}   # code -> room dict (separate from server.salas)
# room dict:
# { 'estado': 'esperando'|'jugando',
#   'asientos': [sid|None, sid|None, sid|None, sid|None],  # index = seat
#   'motor': PartidaMus4, 'al_mejor_de': int, 'publico': bool,
#   'creador_username': str|None, 'ultima_actividad': float }
```

**seat ↔ sid mapping lives here** (`asientos`); the engine only knows seats. To translate an incoming action: `seat = room['asientos'].index(request.sid)`.

### 4.2 Events (client → server)

| Event | Handler | Behavior |
| :--- | :--- | :--- |
| `crear_sala_4` | create a room; put the creator in a seat they pick (default 0); `estado='esperando'`; emit `sala_creada_4 {codigo, asiento}`; broadcast public list if public. |
| `unirse_sala_4 {codigo, asiento?}` | seat the joiner in the requested free seat (or first free); block same-account duplicates (compare `session['username']`); when **all 4 seats filled**, build `PartidaMus4([...sids in seat order])`, set `nombres`, `al_mejor_de`, `iniciar_ronda()`, `estado='jugando'`, emit `iniciar_partida_4`, then `enviar_estado_4(codigo)`. |
| `accion_juego_4 {accion, ...}` | resolve `seat` from sid, then `procesar_accion_4(seat, codigo, datos)` — the 4p analogue of `procesar_accion_interna` (dispatch to `cantar_mus`, `procesar_descarte`, `accion_apuesta`, `continuar_transicion`, `listo_siguiente_ronda`, `pedrete`). Turn-gate the same way (`seat == motor.turno_de`), and allow non-turn actions (`descartar`, `pedrete`) as in 2p. |
| `pedir_publicas_4` | broadcast the 4p public list (rooms in `esperando` with a seat count, e.g. "2/4"). |
| `abandonar_sala_4` | leave cleanly (see §4.4). |

### 4.3 Per-player payload — `enviar_estado_4(codigo)`

Mirror `enviar_estado_a_jugadores`, but loop over the four seats and emit `actualizar_mesa_4` with a `para_sid` filter (same pattern the 2p client already relies on). Payload per seat:

```python
payload = {
  'para_sid': sid,
  'mi_asiento': seat,
  'mano': motor.mano,
  'turno_de': motor.turno_de,
  'es_mi_turno': (seat == motor.turno_de),
  'mi_equipo': motor.equipo_de[seat],
  'fase': motor.fase,
  'mis_cartas': motor.estado[seat]['cartas'],       # only your own cards
  'seats': [                                          # public, card-free info per seat
     {'asiento': s,
      'nombre': motor.nombres.get(s, f'J{s}'),
      'equipo': motor.equipo_de[s],
      'es_mano': (s == motor.mano),
      'descartes_hechos': motor.estado[s]['descartes_hechos'],
      'pares_dec': motor.estado[s]['tiene_pares_dec'],   # for the "Pares sí/no" chip
      'juego_dec': motor.estado[s]['tiene_juego_dec'],
      # NEVER include 'cartas' here except at recuento
     } for s in range(4)],
  'puntos': motor.puntos,                             # {'A':.., 'B':..}
  'partidas': motor.partidas_ganadas,
  'al_mejor_de': motor.al_mejor_de,
  'apuestas': {  # same fields the 2p client reads: fase_actual, subida,
                 # botes, dejes, apuesta_vista, juego_es_punto,
                 # plus 'equipo_apostador' so the UI can highlight the betting team
  },
  'mensaje': {...},                # localizable message codes (see §6)
  'mensaje_transicion': motor.mensaje_transicion,
  'recuento': datos_recuento,      # only at recuento; include all four hands + team results
  'match_finalizado': motor.match_finalizado,
}
```

At **recuento only**, add every seat's `cartas` to the `seats` entries (so the client can reveal all four hands with a flip animation, §7).

**Result persistence:** when the match/game ends, record it like 2p. ELO is currently a 1v1 function ([base_datos.py](../base_datos.py)); for 4p either (a) skip ELO in v1 and only store a `Partidas` row per team (recommended — see Roadmap #19 stats table), or (b) apply the pairwise ELO update to each winner–loser cross pair. Do **not** modify `registrar_partida_completa`'s 2p behavior; add a new `registrar_partida_4(equipo_ganador_usernames, equipo_perdedor_usernames)`.

### 4.4 Connection handling (critical section)

4p is far more sensitive to disconnects than 2p (four fragile sockets). Handle it explicitly:

1. **Waiting room, a seat leaves:** set that `asientos[seat] = None`, keep the room, broadcast the updated public list ("2/4"). Reuse the 2p orphan-cleaner pattern: if all seats `None` for 2 min, delete the room.
2. **Playing, a seat drops (v1 policy = end the game):** to avoid ghost games, on any in-game disconnect emit `rival_desconectado_4 {asiento}` to the room and **delete the room** (`salas4`), matching current 2p behavior. Simpler and safe for v1.
3. **Reconnect grace (recommended even in v1, cheap because the engine is seat-keyed):** instead of instant deletion, mark `estado='pausada'`, remember `username`/token per seat, and accept a `reanudar_partida_4` event that **only swaps `asientos[seat]` to the new sid** — the engine needs no changes because it's keyed by seat. Give a 60–120 s grace; if unmet, delete and notify. This is the payoff of the seat-keyed design and directly reuses the mechanism in Roadmap #18.
4. **Hook into the global `disconnect`:** `server.py`'s `@socketio.on('disconnect')` won't know about `salas4`. Add a **separate** `@socketio.on('disconnect')` in `server_mus4.py` (Socket.IO supports multiple handlers for the same event) that scans `salas4` for the sid — this keeps the 2p disconnect handler untouched.
5. **`abandonar_sala_4`:** `leave_room(codigo)`, free the seat (or delete the room if playing), clear the sid from `jugadores`, broadcast the public list. Fix the 2p bug proactively here: always `leave_room` and always clean the `jugadores` entry (Roadmap #21).
6. **Turn timer** (Roadmap #9) matters more with four players — wire the same authoritative deadline/token mechanism into `enviar_estado_4` so one AFK player can't freeze three others. Recommended to include from the start: auto-pass/fold/no-mus on timeout.
7. **Activity stamp:** set `room['ultima_actividad'] = time.time()` in `procesar_accion_4`; a periodic sweeper deletes playing rooms idle > 2 h and waiting rooms > 30 min.

---

## 5. Frontend — menu integration & screens

### 5.1 Menu button (`index.html`)

In the lobby panel (near `#btn-jugar-bot`, [index.html](../index.html) ~line 79), add:

```html
<button id="btn-crear-4" data-i18n="btn_crear_4"
        style="margin-top:10px; width:100%; background-color:#5e81ac; color:#eceff4;
               font-weight:bold; padding:12px; border-radius:8px; border:none; cursor:pointer;">
  👥 Mus 4 jugadores
</button>
```

Add a **4p waiting/lobby sub-panel** (seat picker: four seat buttons showing occupant name or "Libre/Free", team colors A/B, a public checkbox, and the room code + share buttons reusing the existing copy/WhatsApp/share widgets). This can be a new modal or an inline `#panel-4` block hidden by default.

### 5.2 New game screen (`#game-screen-4`)

Add a second game container alongside `#game-screen`, hidden by default. Layout for four seats:

```
                ┌─────────────────┐
                │  Partner (seat+2)│   ← top: your partner (team color)
                │  [back][back][back][back]
   ┌──────────┐ ┌─────────────────┐ ┌──────────┐
   │ Left      │ │   CENTER TABLE  │ │ Right     │
   │ opponent  │ │  bet log / botes│ │ opponent  │
   │ (seat+1)  │ │  action buttons │ │ (seat+3)  │
   │ [backs]   │ │  transition msg │ │ [backs]   │
   └──────────┘ └─────────────────┘ └──────────┘
                ┌─────────────────┐
                │  YOU (mi_asiento)│   ← bottom: your hand (clickable)
                │  [card][card][card][card]
                └─────────────────┘
```

Render **relative to the viewer**: bottom = `mi_asiento`, top = partner (`+2`), left = `+1`, right = `+3` (mod 4). Reuse the center-table markup from `#game-screen` almost verbatim (`#action-buttons`, `#apuesta-iniciar`, `#apuesta-responder`, `#betting-log`) — give them `-4` id suffixes and reuse the same `data-i18n` keys and CSS classes so styling and translations come for free.

### 5.3 `static/app4.js` — client logic

Structure it on [static/app.js](../static/app.js) (the 2p client) but scoped to 4p events. Reuse, don't duplicate:

- **Language:** reuse `app.js`'s `langActual`, `dict`, and `t()` by referencing them (they are globals in `app.js`, which loads first). Only add the **new** keys (§6) to `dict.es`/`dict.en` — extend the existing object, don't fork it.
- **Socket:** reuse the same `socket` object (also a global from `app.js`) — just bind new event names: `socket.on('actualizar_mesa_4', ...)`, `socket.on('iniciar_partida_4', ...)`, `socket.on('sala_creada_4', ...)`, `socket.on('rival_desconectado_4', ...)`.
- **Menu wiring:** `btn-crear-4` → `socket.emit('crear_sala_4', {nombre, al_mejor_de, publico, asiento})`; seat buttons → `unirse_sala_4`.
- **Screen switch:** on `iniciar_partida_4`, hide `#menu-screen`, show `#game-screen-4`, set a module flag `enPartida4 = true`. Keep this independent of `app.js`'s `enPartida` so the two games never interfere.
- **Action buttons:** identical handlers to 2p but emit `accion_juego_4`. The response/initiate panel show/hide logic (2p lines ~846–908) copies over directly; the only new bits are reading `payload.seats` and `payload.puntos[team]`.

### 5.4 `static/table4.js` — renderer

The `actualizar_mesa_4` handler delegates to `renderMesa4(prev, next)`:

- Paint the four seats: your hand (clickable during discard, same selection logic as 2p lines ~760–790), partner + two opponents as `card_back.webp` fans (count = 4 unless recuento).
- Team scores: two badges (Team A / Team B) with your team highlighted; per-seat name tags colored by team; a crown/marker on the Mano seat; a subtle glow on `turno_de`'s seat.
- Bet log / botes grid: reuse the 2p `htmlBotes` block (Grande/Chica/Pares/Juego columns with active-column highlight and `getBoteTexto`) unchanged — it's already team-agnostic.
- Declaration chips: show "Pares ✓/✗" and "Juego ✓/✗" over each seat when `pares_dec`/`juego_dec` are set (never the cards).
- Recuento: reveal all four hands (from `payload.seats[*].cartas`) and render the per-lance results list (reuse `mostrarRecuentoEstatico` shape, but keyed by team).

Keep a `prevPayload4` and diff it so §7 animations only fire on real deltas.

---

## 6. Information messages (i18n)

Add these keys to **both** `dict.es` and `dict.en` in `app.js` (extend the existing object). Reuse every existing key that already fits (`fase_grande/chica/pares/juego/punto`, `msg_recuento_*`, `eres_mano`, betting button labels, etc.). New 4p-specific keys:

| Key | ES | EN |
| :--- | :--- | :--- |
| `btn_crear_4` | "Mus 4 jugadores" | "4-Player Mus" |
| `seat_libre` | "Libre" | "Free" |
| `equipo_a` / `equipo_b` | "Equipo A" / "Equipo B" | "Team A" / "Team B" |
| `tu_equipo` | "Tu equipo" | "Your team" |
| `tu_pareja` | "Tu pareja" | "Your partner" |
| `esperando_jugadores_4` | "Esperando jugadores ({n}/4)…" | "Waiting for players ({n}/4)…" |
| `elige_asiento` | "Elige un asiento" | "Pick a seat" |
| `pares_si` / `pares_no` | "Pares sí" / "Pares no" | "Pairs" / "No pairs" |
| `juego_si` / `juego_no` | "Juego sí" / "Juego no" | "Game" / "No game" |
| `turno_jugador_4` | "Habla {nombre}" | "{nombre}'s turn" |
| `gano_equipo` | "¡Gana el {equipo}!" | "{equipo} wins!" |
| `rival_desconectado_4` | "Un jugador se ha desconectado. La partida termina." | "A player disconnected. The game is over." |
| `msg_baraja_agotada` | (shared with Roadmap #14) | (shared) |
| `reanudar_4` | "Reanudar partida de 4" | "Resume 4-player game" |

Server → client messages that need localization are sent as `{code, ...params}` objects (never pre-rendered text), exactly like the 2p `mensaje`/`mensaje_transicion` mechanism. Reuse the existing transition codes (`nadie_pares`, `no_pares`, `juego_a_punto`, `no_juego`) — they already exist and the client already renders them; just make sure the 4p engine emits them with a `rol`/`equipo` param where relevant.

---

## 7. Animations

Do these in `style4.css` + `table4.js` only (don't touch `style.css`). Prerequisite: the **diffing renderer** (`renderMesa4(prev, next)`) so animations fire on deltas, not every repaint.

| Moment | Animation | How |
| :--- | :--- | :--- |
| **Deal** | Four cards fly from the center "deck" to each of the four hands, staggered per seat. | Absolute-position a deck stack at center; on the `espera_reparto → mus` transition, animate `transform: translate()` from center to each seat slot with `transition-delay` per seat (0/80/160/240 ms). |
| **Discard / draw** | Selected cards slide toward the center discard pile; replacements fly back to the hand. | FLIP: record the card rects before/after, animate the delta. |
| **Turn indicator** | Soft pulse on the active seat's frame. | Reuse the existing `anim-parpadeo` keyframe (already in the app) applied to the seat container. |
| **Bet placed** | A chip/points token slides from the betting **team's** side toward the center pot; the botes grid cell bumps. | CSS keyframe on the pot cell (`scale` bump) + a token element animating to center. |
| **Órdago** | Table shake + red flash overlay. | Full-screen `#game-screen-4::after` overlay with a 400 ms red-fade keyframe; `animation: shake 0.4s` on the table. |
| **Showdown flip** | All four opponent/partner hands 3D-flip from back to face at recuento. | `transform: rotateY(180deg)` with `transform-style: preserve-3d`; stagger by seat. |
| **Points gain** | Floating `+N` over the winning team's badge, fading upward. | Spawn a temporary absolutely-positioned element, `@keyframes floatUp`. |
| **Deck exhausted** | Brief toast (Roadmap #14). | Reuse the transition-message channel with `msg_baraja_agotada`. |

Rules: every animation ≤ 600 ms; **game state must never depend on animation completion** (the authoritative state is the payload); respect `prefers-reduced-motion` and a settings toggle to disable.

---

## 8. Testing checklist

Do this with **four browser contexts** (e.g. one normal + three private windows, or two machines):

1. **Happy path:** create a 4p room, four players seat themselves (2 per team), play a full game to 40, correct team scoring across all four lances, match ends at best-of-N.
2. **Lance edge cases:** Pares where only one team qualifies (auto-win + bonus for both qualifying partners); Juego → Punto when no team has 31; órdago accepted (immediate showdown, only that lance scores); forced-call when a fold would give a team the game; raise cap → auto-órdago near 40.
3. **Mus:** all-mus multiple rounds until the deck reshuffles (deck-exhausted notice fires once, to all four); a single cut ends mus and the cutter opens Grande.
4. **Turn order:** verify betting passes to the correct opposing-team responder and back; a full pass-around resolves the lance "en paso".
5. **Connection:** drop each seat at each phase (waiting, mus, discard, betting, recuento, between games) — room must not ghost; public list shows accurate seat counts; reconnect grace (if implemented) restores the same seat mid-round.
6. **Turn timer:** an AFK player auto-acts; the other three continue.
7. **i18n:** toggle EN/ES mid-game; all seat labels, chips, and messages switch.
8. **Regression — 2p is untouched:** run a full 2p game and a bot game; confirm nothing changed (this is the whole point of the parallel-file approach).

---

## 9. Summary of what NOT to touch

- `mus_mecanicas.py` (`PartidaMus` and pure functions) — only *import* from it.
- `bot_ml.py`, `mus_env.py`, `train_cfr.py`, `arena.py`, `redes_mus.py`, `mus_discard_chooser.py` — untouched.
- `server.py`'s existing handlers and `salas`/2p flow — only add `import server_mus4` and (optionally) a `modo` tag in the public list.
- `static/app.js`'s 2p render loop — only extend the shared `dict`/globals; the 4p screen and events live in `app4.js`/`table4.js`.
- `static/style.css` — 4p styling goes in `style4.css`.

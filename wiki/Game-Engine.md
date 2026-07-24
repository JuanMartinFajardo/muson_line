# Game Engine — `mus_mecanicas.py`

The engine is a self-contained module with **pure evaluation functions** plus the **`PartidaMus`** class, a per-room state machine. It has no Flask/Socket.IO dependencies, which is why the training scripts (`mus_env.py`, `train_cfr.py`) reuse it directly.

## Pure functions

| Function | Purpose |
| :--- | :--- |
| `crear_baraja()` | Builds the 40-card deck; each card is `{'valor', 'palo', 'img', 'texto'}`. Card image paths are resolved via `obtener_ruta_imagen()` (tries `.webp/.svg/.jpg/.png/.jpeg` under `static/img/`) |
| `get_valores_mus(cartas)` | Applies the Mus mapping: 3→12 (King), 2→1 (Ace) |
| `tiene_pares` / `get_pares_info` | Pair detection; returns `{'tipo': 0–3, 'v1', 'v2', 'premio'}` (tipo 1=Par, 2=Medias, 3=Duples) |
| `get_suma_juego` / `tiene_juego` | Juego sum (face cards & 3s = 10, aces & 2s = 1) and ≥31 check |
| `es_la_real` | Detects the special 7-7-7-Sota hand |
| `comparar_cartas(m, p, is_grande)` | Grande/Chica comparator; sorts and compares card-by-card; **Mano wins ties** |
| `comp_pares_info`, `comp_juego`, `comp_punto` | Comparators for Pares, Juego (uses `J_RANK = {31:8, 32:7, 40:6, 37:5, ...}`), and Punto |

All comparators return `'mano'` or `'postre'`.

## `PartidaMus` — state machine

One instance per room; constructed with the two player SIDs (`PartidaMus(sid1, sid2)`). Mano/Postre are assigned randomly at creation.

### Core state

```python
self.estado = { sid: {'cartas': [], 'puntos': 0, 'quiere_mus': None,
                      'descartes_listos': False, 'descartes_hechos': 0} }
self.fase             # 'espera_reparto' | 'mus' | 'descarte' | 'apuestas' | 'recuento'
self.turno_de         # sid whose turn it is
self.fases_apuesta    # ['Grande', 'Chica', 'Pares', 'Juego']
self.indice_fase      # index into fases_apuesta during betting
self.botes            # accepted-bet pots per lance
self.dejes_fase       # per-lance fold concessions {'ganador', 'valor'}
self.ganadores_fase   # lance winners fixed early by folds
self.apuesta_vista    # amount already seen/on the table
self.subida_pendiente # pending raise (int) or 'ÓRDAGO'
self.quien_sube       # sid of the last raiser
self.partidas_ganadas # games won per sid (match score)
self.al_mejor_de      # best-of-N
self.match_finalizado # True when someone wins ceil(N/2) games
```

### Phase transitions

```
espera_reparto ──repartir_inicial()──► mus
mus ──both say mus──► descarte ──both discarded──► mus (again)
mus ──someone cuts──► apuestas (Grande → Chica → Pares → Juego) ──► recuento
recuento ──both 'listo_siguiente_ronda'──► next round (roles swapped)
                └─ if 40 pts reached: game counted; if match not over, reiniciar_partida()
```

### Notable methods

- **`cantar_mus(jugador, quiere_mus)`** — mus/no-mus logic; sets `quien_corta_mus` (that player opens Grande betting).
- **`procesar_descarte(jugador, indices)`** — removes cards by index, appends to discard pile, draws replacements; when both are done, returns to the mus question.
- **`robar(n)`** — draws n cards, **reshuffling the discard pile** when the deck empties (silent — the Roadmap adds a UI notice for this).
- **`procesar_pedrete(jugador)`** — validates the 4-5-6-7 hand, awards 1 pt, replaces the hand.
- **`preparar_subfase()`** — sets up each lance: skips Pares/Juego with transition messages when a player lacks them; converts Juego into **Punto** when neither has 31+ (`juego_es_punto`).
- **`accion_apuesta(jugador, accion, cantidad)`** — full betting engine: pass/bid/raise/call/fold/órdago, with two safety rules: raises are capped at the legal maximum (excess → Órdago), and folds that would lose the game are converted into calls.
- **`calcular_recuento()`** — resolves all lances (or only the órdago lance), applies pots + category bonuses, caps points at 40, marks game/match winners, and **flushes the AI training log** to `logs/<match_id>.jsonl`.

### Training log

Every decision is recorded via `registrar_movimiento_ia()`: timestamp, match ID, round number, phase, both players' names/cards/points, action, amount, and details (e.g. discarded cards). After a game ends, each record is enriched with final points and a `gano_ronda` flag, then appended to `logs/<match_id>.jsonl` (controlled by `self.generate_log`). This is the raw material for the `learn/` pipeline.

## Quirks worth knowing

- `iniciar_ronda()` does **not** deal cards; dealing happens on the explicit `repartir` action (phase `espera_reparto`, triggered by Postre).
- Point totals are clamped to 40 (`min(40, ...)`) during recuento.
- `dejes_fase` was added later; `accion_apuesta` defensively creates it if missing.
- The engine assumes **exactly 2 players** throughout (comparators, roles, recuento) — Mus for 4 players (Roadmap) needs a parallel engine or a significant generalization.

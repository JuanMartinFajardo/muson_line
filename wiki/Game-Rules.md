# Game Rules (2-Player Mus, as implemented)

Mus is a classic Spanish card game, traditionally played 2v2. CallMus implements the fast, bluff-heavy **two-player variant**. This page describes the rules exactly as the engine ([mus_mecanicas.py](../mus_mecanicas.py)) enforces them.

## Basics

- **Deck:** 40-card Spanish deck — values 1 (Ace), 2, 3, 4, 5, 6, 7, 10 (Sota/Jack), 11 (Caballo/Knight), 12 (Rey/King) in four suits (Oros/coins, Copas/cups, Espadas/swords, Bastos/clubs).
- **Special values:** **3s count as Kings (12)** and **2s count as Aces (1)** — so the deck effectively has 8 Kings and 8 Aces. See `get_valores_mus()`.
- **Roles:** One player is **Mano** (hand, speaks first, wins ties), the other **Postre** (dealer). Roles swap every round (`cambiar_roles`).
- **Winning a game:** first to **40 points**. Matches are played "best of N" (`al_mejor_de`, default 3, configurable 1–21 in the lobby).

## Round flow

1. Each player receives **4 cards** (`repartir_inicial`).
2. **Mus phase:** starting with Mano, each player says **Mus** (wants to discard) or **No Mus / Corto** (cut, go straight to betting).
   - If both say Mus → **discard phase**: each player throws 1–4 cards and draws replacements. Then Mus is asked again. This repeats until someone cuts.
   - If either says No Mus → betting begins. The cutter speaks first in Grande (`quien_corta_mus`).
   - If the draw pile runs out, the discard pile is reshuffled (`robar`).
3. **Betting phases (lances)**, in order: **Grande, Chica, Pares, Juego**.
4. **Recuento (showdown/scoring):** accepted bets and category bonuses are resolved (`calcular_recuento`).

## The four lances

| Lance | Goal | Notes |
| :--- | :--- | :--- |
| **Grande** | Highest cards | Hierarchy: King/3 > Knight > Jack > 7 > 6 > 5 > 4 > Ace/2 |
| **Chica** | Lowest cards | Reverse hierarchy; four Aces is best |
| **Pares** | Pairs | Par (pair, 1 pt) < Medias (three of a kind, 2 pts) < Duples (two pairs / four of a kind, 3 pts). If a player has no pairs the phase is skipped or auto-won by the other |
| **Juego** | Card sum ≥ 31 | Kings/3s/Knights/Jacks = 10, Aces/2s = 1, rest face value. Ranking: 31 > 32 > 40 > 37 > 36 > 35 > 34 > 33. If **neither** player reaches 31, the phase becomes **Punto** (closest to 31 wins, 1 pt) |

Special hand: **La Real** (three 7s + one Sota) beats any other Juego (`es_la_real`).

## Betting actions

Within each lance a player may:

- **Pasar (Pass)** — two consecutive passes end the lance; in Grande/Chica the eventual category winner gets 1 "de paso" point.
- **Envidar (Bid)** — open a bet (minimum 2).
- **Subir (Raise)** — raise a pending bet. The engine caps raises at `40 − max(points) − seen bet`; if no margin remains the raise auto-converts to Órdago.
- **Ver (Call)** — accept; the pot is resolved at showdown.
- **No ver (Fold)** — the bettor immediately gets the seen amount (or 1 if nothing was seen). **Forced-call rule:** if folding would hand the opponent the game (their points + concession ≥ 40), the fold auto-converts to a call.
- **Órdago** — all-in for the whole game (40 pts). If called, cards are shown immediately and only that lance decides the game.

## Scoring at showdown

| Category | Points |
| :--- | :--- |
| Grande / Chica (all passed) | 1 |
| Par | 1 |
| Medias | 2 |
| Duples | 3 |
| Juego of 31 | 3 |
| Juego of 32–40 | 2 |
| Punto | 1 |
| Accepted bets | Pot value added to the category |

Mano wins all ties.

## House extra: Pedrete

If a player holds exactly **4-5-6-7** (raw values) during the mus/discard phase, they may call **Pedrete**: they score 1 point immediately and their whole hand is replaced with 4 new cards (`procesar_pedrete`). The client shows the button only when the hand qualifies.

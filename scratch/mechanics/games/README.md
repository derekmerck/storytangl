Scratch: games
==============

**Status as of the ladder/retrofit pass (PRs #412, #413).**

This tree is prior-version source material, not a package. It does not import,
it is excluded from test collection (`pyproject.toml` `norecursedirs`), and its
modules still reference the old `tangl.mechanics.game` (singular) layout. Treat
it as notes with syntax highlighting.

Most of it has been harvested. What remains below is kept because the *idea* is
not yet expressed anywhere in the engine or its design docs — not because the
code is worth reviving. When one of these lands, delete the file rather than
leaving a stale second copy.

Harvested and deleted
---------------------

The framework spine, the RPS/nim/picking/blackjack kernels, the fungible token
substrate, and the taxonomy notes all landed in `tangl.mechanics.games` in
better form. See `GAME_MECHANICS_DESIGN.md` for the accessory-complexity ladder
that replaced the old genre list, and git history for the deleted sources.

Two worth calling out because the mapping is not obvious:

- `token_games/game_token.py` became `game_token.py`. Its `Token(Fungible)` plus
  affiliation is `FungibleGameToken`, and its `TokenHandler` aggregation is
  `value_by_affiliation()` / `dominant_affiliation()` — now taking an explicit
  definition mapping rather than consulting the global registry (#404).
- `token_games/resources/tokens.yaml` (red/blue pawn/rook/knight at weights
  1/2/3) is exactly what `GameTokenSpec` expresses inline. Several labels
  sharing one affiliation at different weights is the case the retrofit was
  built around.

Still on the table
------------------

| Source | Idea not yet expressed | Where it would go |
|---|---|---|
| `token_games/2p_strategy.py` | Per-owner heaps with an *either-empties* terminal — the exhausted heap's owner loses. Landed nim is multi-heap but shared, terminating only when every heap empties. Also sketches a separate attack/defend prize auction. | nim terminal rules |
| `token_games/winding_rps/` | Geometric dominance: compare normalized power distributions under cyclic rotation instead of a matchup matrix, plus `ADAPTIVE` joker units that pick their affiliation to suit the matchup. Reported degeneracies (balanced forces becoming undominatable) are recorded in `docs/src/notes/migration/engine-architecture-archaeology.md`. | aggregate-force dominance |
| `card_games/twentytwo*.py` | `MndCard`: cards carrying an m-vector of values across n type axes, so one draw pushes several accumulators at once. Landed corridor is deliberately scalar; this is the multi-axis lift. | `CORRIDOR_CONTEST_DESIGN.md` deferral |
| `card_games/card_game.py` | A card-rung shell with **field and discard zones**, which blackjack does not have (deck plus two hands only). Thin, but it is the concrete gap between blackjack and a playable card game. | a Gwent-style demo |
| `incremental/incremental.py` | Per-player **discount / productivity / efficiency** multipliers, and prestige-style reset-with-carryover. Cost escalation and ephemeral resources landed; the upgrade layer that bends the curve back down did not. | `IncrementalGame` upgrades |

Deliberately not kept
---------------------

`simple_games/complex_rps.py` (competing defiance/heat meters filled at rates
set by an RPS matchup) is gone because the reusable claim is already recorded:
it is a corridor/two-heap contest over shared scalars, a strategy-rung variant
with two thresholds rather than a new kernel. See the ladder section of
`GAME_MECHANICS_DESIGN.md`.

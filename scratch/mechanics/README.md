Scratch: mechanics
==================

Prior-version source material. Nothing here imports, nothing is collected by
pytest (`pyproject.toml` `norecursedirs`), and most modules reference layouts
that no longer exist. Treat it as notes with syntax highlighting.

Audit status by area, so nobody has to re-derive it:

| Area | Status |
|---|---|
| `games/` | **Audited.** Harvested sources deleted; five unexpressed ideas kept with a README naming each. See that file. |
| `credentials/` | Superseded by `mechanics/credentials` plus six design docs. Extension laboratory is #246. |
| `sandbox/` | Superseded by `mechanics/sandbox`. Extension laboratory is #236. |
| `progression/` | **Not audited — the real tangle.** Carries three generations at once (`legacy/progression-pre25/`, `legacy/`, `stats/`, `challenge_block/`) with literal duplicates (`task.py` and `task-2.py`). Promotion is genuinely mixed: `LogInt` landed, `SituationalEffect` and `Quality` appear in design docs, while `StatCurrency`, `StatDomain`, and the opinionated/psychosomatic stat domains are absent entirely. Wants the games-style ledger before anything is promoted. Umbrella #112. |
| `presence/` | Mostly superseded by `mechanics/presence` (look, outfit, wearable, ornaments, presentation). `vocals.py` is the one unexpressed idea, now tracked as its own issue. |
| `badge/` | Kept for one problem statement: dynamic badge assignment produces a dependency graph that can cycle, which is why it reaches for `topological_sort`. Vocabulary and shape are being realigned in its own issue; the code itself is not a porting target. |
| `collection/` | Kept. Its question — is this an abstract core feature combining association with wallets for countables — is largely answered by `SlottedContainer` / `ComponentManager` plus `AssetWallet`, and all four of its examples are built. Retained pending a closer read of the coverage mechanics rather than deleted on the strength of the shape alone. |
| `calvin_cards/` | Kept as a **promotion candidate**, not legacy. `MECHANICS_FAMILIES.md` names it the clearest local example of one kernel rebound to multiple semantic catalogs, and its YAML catalogs are the declarative card-list shape a card-game demo wants. |
| `has_demographic.py` | Deleted. Fully superseded by `HasDemographics` / `DemographicData`. The pending demographics work is a modernization of the realized package (#285), not a promotion from here. |

When one of the kept ideas lands, delete the file rather than leaving a stale
second copy of code the engine now implements better.

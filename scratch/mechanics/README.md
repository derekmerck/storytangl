Scratch: mechanics
==================

Prior-version source material. Nothing here imports, nothing is collected by
pytest (`pyproject.toml` `norecursedirs`), and most modules reference layouts
that no longer exist. Treat it as notes with syntax highlighting.

Audit status by area, so nobody has to re-derive it. **Audited** means the ledger exists and is trusted; where a
superseded tree is still present, that is pending mechanical removal rather than an open question.

| Area | Status |
|---|---|
| `games/` | **Audited.** Harvested sources deleted; five unexpressed ideas kept with a README naming each. See that file. |
| `credentials/` | **Audited, awaiting mechanical removal.** Superseded by `mechanics/credentials` plus six design docs; the scratch tree is still present and should be deleted in its own pass. Extension laboratory is #246. |
| `sandbox/` | **Audited, awaiting mechanical removal.** Superseded by `mechanics/sandbox`; the scratch tree is still present and should be deleted in its own pass. Extension laboratory is #236. |
| `progression/` | **Audited** — see `progression/AUDIT.md`. Three generations with literal duplicates (`task.py` and `task-2.py`), but promotion is far more complete than the file count suggests: the realized package is a rewrite, not a thin promotion. `Quality`, `SituationalEffect`, and the LogInt/probit handlers are implemented, exported, tested, and consumed by the `coronate_the_regent` world. `StatCurrency` and the hardcoded stat domains are superseded by `StatDef.currency_name` and `StatSystemDefinition` + `presets/`. Harvested and retired per the five-step Bounded Retirement Sequence in `STAT_CHALLENGE_DESIGN.rst`; semantics that did not survive are in `progression/HARVEST.md`, which `devref` does not index — consult it before designing stats, challenges, or effect vocabulary. Four badge-related sources retained for #421. Umbrella #112. |
| `presence/` | Mostly superseded by `mechanics/presence` (look, outfit, wearable, ornaments, presentation). `vocals.py` is the one unexpressed idea, now tracked as its own issue. |
| `badge/` | Kept for one problem statement: dynamic badge assignment produces a dependency graph that can cycle, which is why it reaches for `topological_sort`. Vocabulary and shape are being realigned in its own issue; the code itself is not a porting target. |
| `collection/` | Kept. Its question — is this an abstract core feature combining association with wallets for countables — is largely answered by `SlottedContainer` / `ComponentManager` plus `AssetWallet`, and all four of its examples are built. Retained pending a closer read of the coverage mechanics rather than deleted on the strength of the shape alone. |
| `calvin_cards/` | Kept as a **promotion candidate**, not legacy. `MECHANICS_FAMILIES.md` names it the clearest local example of one kernel rebound to multiple semantic catalogs, and its YAML catalogs are the declarative card-list shape a card-game demo wants. |
| `has_demographic.py` | Deleted. Its naming and profile capabilities are superseded by `HasDemographics` / `DemographicData`, which model identity more richly through subtype, country, and region. Not a literal superset: the free-form `background` string has no direct counterpart, and name parsing and title handling differ — those were intentionally dropped or absorbed into the structured vocabulary. The pending demographics work is a modernization of the realized package (#285), not a promotion from here. |

When one of the kept ideas lands, delete the file rather than leaving a stale
second copy of code the engine now implements better.

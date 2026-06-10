# Composed Beat Demo

Reference walkthrough of journal **beat composition**: one five-block scene
that exercises every contribution channel of the gather → enrich → compose
pipeline. Use it as the template for story beats with deliberate syuzhet
assembly.

See `docs/src/design/story/BEAT_COMPOSITION.md` for the pattern this world
demonstrates, and `engine/tests/loaders/test_composed_beat_demo_world.py`
for the conformance assertions.

## What each piece shows

| Piece | Channel |
| --- | --- |
| `dock_mood` in story `locals:` vs the `declare` block's `locals:` | data-scope chunk override — no code |
| `porter_greeting` handlers in `domain.py` | handler-scope override — AUTHOR layer beats APPLICATION |
| `render_porter_reaction` | conditional render-time enrichment, gated on the gathered namespace |
| `apply_beat_consequences` | UPDATE-phase mutation plus cross-phase enrichment via `ctx.injected_journal_fragments` |
| `compose_beat` | post-merge composition: slot ordering, fog substitution, beat overlay |
| the `> [!pov]` dialog lines in `arrival` | interplay with the story-layer dialog transform earlier in the compose fold |

## Walkthrough

From `arrival`, the muddy gangway drops `reputation` on the story graph;
declaring cargo then assembles the full beat — setting, the injected
manifest incident, and Maro's reaction in slot order, bound by a
`GroupFragment` beat overlay. Pressing on to `fogbound` swaps the setting
fragment for the fog line via `replace_first`.

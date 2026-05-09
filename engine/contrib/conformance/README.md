# StoryTangl Conformance Fixtures

This directory contains portable JSON fixtures for client/port conformance.

The first fixture suite follows
`docs/src/design/story/WIDGET_CONTRACT_RECONCILIATION.md`, not every future
target in `STORYTANGL_WIDGET_VOCAB.md`. In particular:

- `token` / `zone` fixtures are current web pressure fixtures and decision-
  legibility examples. They are not final `piece` contract fixtures yet.
- `kv` fragments use the current web tuple-like row shape. Record-shaped
  `KvRow` remains a migration target.
- `interpretation` currently tests fallback behavior. A typed engine
  `InterpretationFragment` will get stricter fixtures later.

Every future port should be able to load these JSON files and assert observable
output in its own medium.

`reference_port.py` is the smallest current proof of that portability. It
renders the fixtures into a UI-neutral `RenderDocument` from JSON only, without
importing engine models or calling the service layer. `cli_reference_port.py`
then formats that document as plain terminal text. A Tkinter or curses port can
use the same document roles and `ChoiceControl` records while choosing its own
widgets.

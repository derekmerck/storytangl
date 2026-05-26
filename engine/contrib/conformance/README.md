# StoryTangl Conformance Fixtures

This directory contains portable JSON fixtures for client/port conformance.

The first fixture suite follows
`docs/src/design/story/WIDGET_CONTRACT_RECONCILIATION.md`, not every future
target in `STORYTANGL_WIDGET_VOCAB.md`. In particular:

- `piece` / `zone` fixtures are current web pressure fixtures and decision-
  legibility examples while engine-side typed fragment support catches up.
- `kv` fragments use the unified record-shaped `KvRow` contract.
- `interpretation` uses the v1.5 `result` / `text` / `message` shape while the
  reference renderers still accept the older fallback field names.

Every future port should be able to load these JSON files and assert observable
output in its own medium.

`proposals/` contains non-gating fixtures for target surfaces such as
record-shaped `KvRow`, `piece.realized`, `place` accepts, `roll` fragments,
wireframe-derived v1.5 examples, and the compact CarWars garage turn. Proposal
fixtures should stay JSON-loadable
and reference-port-renderable, but they are not conformance requirements until
`docs/src/design/story/WIDGET_CONTRACT_RECONCILIATION.md` promotes them.

`sequences/` contains multi-envelope fixtures. These exercise the client-side
fragment registry: media placeholders update in place, pieces move between
zones, stale offers or fallback fragments can be deleted, and open choices keep
their referenced state renderable after each envelope.

`legibility.py` contains the first promoted conformance harness. It is a
JSON-only decision-legibility check: after applying update/delete controls, each
available choice must be renderable in the current scene shell and any
piece/zone/state references in its decision surfaces must also be renderable.
`parity.py` is the sibling input-parity harness: available choices must expose
enough `accepts` shape for a low-capability client to submit a portable payload
for `pick`, `text`, `quantity`, `raw_command`, `pieces`, `place`, and recursive
`compose` controls.
`time_parity.py` covers the JSON-visible part of timed presentation parity:
pending media and roll/ritual fragments need immediate readable fallbacks, and
advisory timing hints cannot require waiting for presentation time.

`reference_port.py` is the smallest current proof of that portability. It
renders the fixtures into a UI-neutral `RenderDocument` from JSON only, without
importing engine models or calling the service layer. `cli_reference_port.py`
then formats that document as plain terminal text, including choice blockers,
cost previews, typed accepts prompts, command interpretation feedback, and
unknown-fragment fallbacks.

`tk_reference_port.py` is a tiny desktop-toolkit proof over the same view model.
Its `--inspect` mode prints the planned widgets and sample submission payloads
without importing Tkinter; running without `--inspect` opens a minimal Tkinter
window and prints submissions instead of calling a backend.

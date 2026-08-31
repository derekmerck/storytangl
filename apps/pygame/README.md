# StoryTangl Pygame Client

A second non-web reference port, alongside `apps/renpy`. StoryTangl keeps
ownership of session lifecycle, traversal, and fragment production; this app
adapts typed `RuntimeEnvelope` output into a small turn model and draws it.

## Status

Adapter proof of concept. The bridge and turn model are covered by ordinary
`pytest`; the renderer is deliberately thin.

## What Is Included

- `src/tangl/pygame_client/models.py` — `Turn`, `Line`, `Choice`, `StageImage`.
- `src/tangl/pygame_client/bridge.py` — `ServiceManager` → turn model. Imports
  no pygame, so the whole adaptation layer is testable headlessly.
- `src/tangl/pygame_client/stage.py` — renders one turn to a 320×200 logical
  surface, scaled nearest-neighbour, so output sits on a real pixel grid.
- `src/tangl/pygame_client/__main__.py` — event loop.
- `tests/` — adapter and live-session tests.

## Design Commitments

**The client holds no world knowledge.** Backgrounds and portraits are selected
by `media_role` (`narrative_im_landscape`, `cover_im` → background;
`dialog_im`, `avatar_im` → portrait), never by block label. A world with no art
still plays, rendering flat colour plus text. Art is purely additive.

**Every click resolves to an `edge_id`.** The input layer never commits a
bespoke action, so a later map hotspot produces the same payload as selecting
the numbered choice (widget vocabulary §5.3, Input Parity).

**Unavailable choices render dimmed with their `unavailable_reason`** rather
than being hidden (§5.1, Decision Legibility).

**Attribution decides presentation.** An `AttributedFragment` renders as a
speaker bubble; a plain `ContentFragment` renders as narration. The client does
not parse prose prefixes.

## Running

pygame is not a Poetry dependency, matching the Ren'Py app's convention of not
vendoring a client runtime:

```bash
pip install pygame-ce
```

```bash
PYTHONPATH=engine/src:apps/pygame/src:worlds/repartee_loop \
  python -m tangl.pygame_client --world repartee_loop
```

`--assets DIR` resolves relative media sources. `--screenshot PATH` renders one
frame and exits, which works headless under `SDL_VIDEODRIVER=dummy`.

```bash
PYTHONPATH=engine/src:apps/pygame/src poetry run pytest apps/pygame/tests
```

## Test Isolation

`tests/conftest.py` carries world-singleton isolation that engine tests get from
`engine/tests/conftest.py`. The `repartee_world` fixture additionally repairs a
real cross-suite interaction: `PhraseType` definitions register when the world's
domain module is imported, and a full-suite run can clear those registries while
the module is still in `sys.modules`, so a later compile finds no definitions and
badge construction fails validation. The fixture reloads only when the singletons
are actually missing — an unconditional reload rebinds classes that live
instances still reference.

This is a property of singleton-registering worlds, not of this client. Any
second consumer loading such a world through `ServiceManager` after the engine
suite runs would hit it.

## Divergence From The Ren'Py Adapter

Two ports now build near-identical turn models. Rather than pre-extracting a
shared adapter layer, this file records where they actually differ, so the
decision to share is made on evidence.

**Same in both, and non-obvious enough to be worth sharing eventually:**

- Session bootstrap. `create_user()` must be called for a real user id; an
  invented `uuid4()` is rejected by `ServiceManager.open_user`.
- `ledger_id` travels in `RuntimeEnvelope.metadata`, not as an attribute.
- Group fragments must be flattened before per-step grouping.
- Media that cannot be dereferenced degrades to its text floor.

Both of the first two were rediscovered the hard way while writing this port.
That is the strongest argument so far for a shared session-bootstrap helper.

**Genuinely different, and reasons not to unify the turn model yet:**

| | Ren'Py | pygame |
|---|---|---|
| media | ordered `scene`/`show` ops, stateful | flat per-turn image list, stateless |
| speaker | `portrait_tag` for a defined character image | `speaker` string, looked up by role |
| choices | menu built by the runtime | hitboxes owned by the renderer |
| turns | one per step, played in sequence | merged into one actionable frame |

The media model is the real divergence: Ren'Py has a persistent stage that
`scene` clears and `show` mutates, while this client redraws from scratch each
turn. A shared model would have to pick one or carry both.

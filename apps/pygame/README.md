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
by `media_role` (`narrative_im`, `cover_im` → background;
`dialog_im`, `avatar_im` → portrait), never by block label. A world with no art
still plays, rendering flat colour plus text. Art is purely additive.
Image geometry remains an orthogonal staging hint: Repartee's backgrounds use
`media_shape: landscape`, while this stage is free to promote the current
`narrative_im` to its full-frame background.

**Every click resolves to an `edge_id`.** The input layer never commits a
bespoke action, so a map hotspot produces the same payload as selecting the
numbered choice (widget vocabulary §5.3, Input Parity). That is now exercised
rather than merely intended — see the map view below.

**Unavailable choices render dimmed with their `unavailable_reason`** rather
than being hidden (§5.1, Decision Legibility).

**Attribution decides presentation.** An `AttributedFragment` renders as a
speaker bubble; a plain `ContentFragment` renders as narration. The client does
not parse prose prefixes.

## The Map View

When the cursor publishes a plate, the client draws it instead of the ordinary
scene layout: the plate full-frame, an outlined box per region, and the choice
number pinned inside each box.

The two halves arrive by different routes and are joined in the client, which
is the point of the design:

- **Geometry** comes from story-info, requested by name as `map_plate` and
  `map_regions`. It is reference state — it changes when the art changes, not
  when the reader moves — so a client that cannot draw maps never asks for it.
- **Liveness** comes from the ordinary choice list. A travel choice carries a
  `ui:plate:<plate>:<region>` tag, and the renderer boxes the region whose name
  a live choice claims.

Everything else falls out of that intersection rather than needing a rule. A
region no choice claims is drawn nowhere and clicks nowhere, which is how "not
currently on offer" differs from "offered and refused" — the latter is a real
choice with `available: false`, so it gets a dimmed box and its
`unavailable_reason` in the legend.

The pin carries only the number. A 70px box cannot hold "Go to The Practice
Yard", and shortening it would mean parsing prose the client does not own, so
the names stay in the legend below and the number ties the two together. Every
choice appears there, boxed or not, which keeps the CLI floor literally on
screen: same number, same edge, whichever the reader clicks.

`map_im` is deliberately outside `BACKGROUND_ROLES`. A plate is full-frame but
is not scenery, and a client with no map view must not stage it as a backdrop —
it renders the numbered list instead, which is exactly what this client did
before this feature existed.

## Running

pygame-ce is a **dev/test** dependency, not a runtime one — `poetry install`
brings it in so the renderer tests run in CI, while the engine and service never
import it. That is a different question from the Ren'Py app's convention of not
vendoring an SDK: pygame-ce is an ordinary wheel, so there is no reason it
cannot be a test requirement.

The bridge and session tests import no pygame at all and run regardless; only
the renderer tests need it, and they skip cleanly when it is absent.

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
- Media payloads name their source by `path`/`url` depending on
  `content_format`, never `content` or `source`. Both bridges therefore carry
  the same `("path", "url", "src", "ref")` probe.
- `ChoiceFragment` stores its activation override in `activation_payload`
  (wire alias `payload`), not `choice_payload`.
- Group fragments must be flattened before per-step grouping.
- Media that cannot be dereferenced degrades to its text floor, and the service
  may supply that text itself in a content-shaped payload.

The first four were each rediscovered the hard way while writing this port —
three of them by shipping the bug first. That is the strongest argument so far
for extracting a shared envelope-adaptation helper: none of these is guessable
from the type signatures, and a third port would pay the same tax again.

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

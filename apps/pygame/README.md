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

## Typed Choices

Most choices are answered by their `edge_id` alone. Some want a value first, and
`accepts.kind` says which (§6.1). This port collects `pieces`; the rest render
inert with a reason rather than committing a guessed payload.

A `pieces` choice opens a second numbered list of the pieces it will take, and
the payload is built only once that list has been answered:

```
1. Inspect a document          ->     1. passport
2. Choose pass                        2. work permit
3. Choose deny                        0. Cancel
```

Three things about that are load-bearing.

**The two lists are numbered independently, both from 1.** The CLI takes the
same selection as positional values after the choice number (`do 1 0:passport`),
so the same key names the same piece in both ports. Escape or `0` leaves the
selection without committing — a mode a mouse can enter but only a keyboard can
leave is not a usable surface, so Cancel is a clickable row too.

**Only a full selection commits itself.** At `max` there is nothing left to
decide. Anywhere between `min` and `max` there is no moment the client can infer,
so `8. Confirm` appears once the minimum is met — which is also the only way a
`min=0` choice can be submitted empty. Below the minimum the row reads
`Pick N more` and does nothing.

**Long lists page.** Eight candidates at a time, `9. More (2/3)` to advance.
Numbering restarts per page, so the number a player reads is the key they press
wherever they are in the list. Twenty documents laid out at once put their first
rows above the top of the surface, where they were neither readable nor
clickable.

**Which pieces are offered comes from the choice, not the renderer.** A
`pieces` choice constrained to `target_zone_ref` is satisfiable only by pieces in
that zone, so `selectable_pieces` reads the constraint and the candidate — a
piece too, but outside the packet — never appears. That is §5.1 again: the
player is only offered what the backend will actually accept.

**The finished payload is byte-identical to the CLI's.** `commit_payload` mirrors
the CLI's `_choice_payload` case for case. Its validation is advisory — the
backend re-checks and is authoritative (§6.1.2) — and refusing early only keeps a
doomed commit off the wire.

Every click and key still resolves to `(edge_id, payload)`; `BeginSelection`,
`PickPiece` and `CancelSelection` are client-local steps that never reach the
service. That is what keeps Input Parity true for a choice that takes two
actions to answer.

**Attribution decides presentation.** An `AttributedFragment` renders as a
speaker bubble; a plain `ContentFragment` renders as narration. The client does
not parse prose prefixes.

## The State Panel

A turn carrying pieces, zones or findings reserves the right-hand column for
them. The space is taken from the prose rather than shared with it, because a
document that scrolled away is a document the player cannot evaluate — and §5.1
makes rendering it a requirement, not a flourish.

```
                          Edda Marrow
  You inspect the         CREDENTIALS PACKET
  work permit.             passport - already
  The work permit          inspected
  was never sealed         work permit - already
  by the issuer.           inspected
                           baggage
  1. Inspect a document    FINDINGS
  2. Review packet ...      work permit: The work
```

**A zone renders even when empty.** A targetable container with nothing in it is
information, not an absence.

**Findings keep the engine's `emphasis` word** — `ok`/`warn`/`danger`/`subtle`
choose a colour. The client never re-derives severity from the prose.

**A spent piece is dimmed with its reason and cannot be selected.** That is the
generic `available` / `unavailable_reason` pair, read exactly as it is on a
choice. `credential_gate` sets it on documents already inspected; before that
existed, the only way to learn a document was spent was the backend error raised
after committing it.

**An over-full panel pages.** At 320x200 a nine-choice turn leaves the panel
about eight rows, and a full packet plus findings exceeds that. It paginates and
shows `page 1/2`, clickable as well as keyed. An earlier draft drew an overflow
notice instead: that told the player state was hidden without giving them any way
to read it, which is not what §5.1 asks for.

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

**At most one choice may claim a region.** The engine refuses to project an
ambiguous one — whether two locations claim the same region, or one location is
reachable by two authored routes — and this renderer skips it rather than
picking a winner. Choosing between claimants would hide a dropped choice behind
a hitbox that looks perfectly correct. The routes stay offered in the legend;
only the hitbox is withheld.

The plate drawn is the one the geometry *names*, not merely the first `map_im`
staged. Picture and rectangles arrive by different routes, so a batch that
crosses between two maps could otherwise pair one map's image with the other's
hitboxes.

The footer is capped and pages. It is drawn over the plate, so hit-testing runs
in reverse draw order and a legend row wins the pixels it visibly covers.

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
| typed input | not attempted | two-step numbered selection for `pieces`, paged |
| turns | one per step, played in sequence | merged into one actionable frame |

The media model is the real divergence: Ren'Py has a persistent stage that
`scene` clears and `show` mutates, while this client redraws from scratch each
turn. A shared model would have to pick one or carry both.

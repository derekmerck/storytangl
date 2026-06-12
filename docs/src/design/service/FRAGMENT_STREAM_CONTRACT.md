# Fragment Stream Contract

> Status: Current contract with near-term extension points
> Authority: `tangl.service.response.RuntimeEnvelope`,
> `tangl.journal.fragments`, `ServiceManager`, and the web fixtures under
> `apps/web/tests/fixtures/`.
> Renderer vocabulary: `../story/STORYTANGL_WIDGET_VOCAB.md`; repo-current
> implementation status: `../story/WIDGET_CONTRACT_RECONCILIATION.md`.

Story session methods return `RuntimeEnvelope`. The envelope carries ordered
journal fragments plus cursor metadata. Clients render those fragments directly;
they do not receive, infer, or rebuild a second block-shaped story model.

## Layer Placement

The fragment stream sits at the boundary between story/runtime output and
client presentation.

- Story owns fragment meaning and journal composition.
- Service owns session lifecycle, envelope metadata, and transport-safe
  dereferencing such as media payload shaping.
- Clients own layout, widgets, accessibility mapping, and graceful fallback.

The service layer must not invent a parallel fragment hierarchy. Unknown
fragments remain `BaseFragment` values with their original payload preserved so
clients and remote managers can degrade safely.

## RuntimeEnvelope

`RuntimeEnvelope` is the canonical story-session response:

```text
RuntimeEnvelope
  cursor_id: UUID | null
  step: int | null
  fragments: list[BaseFragment]  # serialized as concrete fragment payloads
  last_redirect: dict | null
  redirect_trace: list[dict]
  metadata: dict
```

`create_story`, `resolve_choice`, and `get_story_update` return this envelope
directly. Acknowledgement-only operations such as `drop_story` return
`RuntimeInfo`.

`fragments` are ordered for reading and replay. The Python type is rooted at
`BaseFragment`, while `RuntimeEnvelope.to_dto()` projects each fragment through
the journal fragment DTO pathway. That pathway uses `fragment_type` as the
transport discriminator, preserves concrete fields such as
`ChoiceFragment.edge_id`, `accepts`, and `ui_hints`, and omits stream
bookkeeping selected by `dto_exclude` field metadata. A fragment's `uid` is also
a stable reference target within the envelope and across later update/delete
control fragments.

## Fragment Registry Model

Clients should treat each envelope as a fragment event batch:

1. Normalize each fragment into a record with `uid` and `fragment_type`.
2. Apply `update` and `delete` control fragments to the local registry.
3. Store all other fragments by `uid`.
4. Build presentation shells from `group` fragments, especially
   `group_type="scene"`.
5. Render known fragment types with widgets and unknown types with visible
   fallback.

This registry model is what lets independent fragments update, disappear, or be
grouped without collapsing the turn back into one display block.

## Current Fragment Vocabulary

Core reusable fragment types live in `tangl.journal.fragments`; active
extension types preserve the same `BaseFragment` shape.

| Fragment | Purpose |
| --- | --- |
| `content` | Prose, status text, or fallback text. |
| `attributed` | Speaker-attributed content such as dialog lines. |
| `media` | Media reference or placeholder; service may dereference RITs. |
| `choice` | Player-facing interaction offer backed by an `Action` edge. |
| `group` | Relational overlay tying peer fragments together by id. |
| `piece` | Targetable piece or object rendered inside a zone. |
| `kv` | Ordered key-value content for compact state/status surfaces. |
| `update` / `delete` | Control fragments mutating an earlier registry entry. |

Unknown fragment types are valid extension points. A client that cannot render a
fragment type must keep the stream alive and show or stash a diagnostic fallback
rather than failing the whole turn.

Transient guidance is not a journal fragment. `RuntimeEnvelope.ux_events`
carries typed inline or interrupt events beside the replayable fragment stream.

## Choice Fragments

Choices are interaction offers, not generic display buttons.

`ChoiceFragment` carries:

- `edge_id`: required UUID of the action to send back to `resolve_choice`
- `text`: user-facing label
- `available`: whether the action can currently be committed
- `unavailable_reason`: short human-readable or code-like reason
- `blockers`: structured diagnostics explaining unavailable state
- `accepts`: optional payload/input contract
- `ui_hints`: optional rendering hints such as hotkey, icon, or widget family

Clients post:

```text
choice_id = choice.edge_id
payload = renderer-collected payload, if any
```

`accepts` is intentionally generic. It describes the payload shape a renderer
should collect, not the widget class a particular client must use. The handler
remains the authority for validation and state change.

Canonical near-term variants:

| `accepts.kind` | Payload | Meaning |
| --- | --- | --- |
| absent or `pick` | `{}` or omitted | The edge id is the whole answer. |
| `text` | `{text: string}` | Freeform line such as a name, password, or note. |
| `quantity` | `{quantity: int}` | Integer amount with optional min/max/unit/cost hints. |
| `pieces` | `{piece_ids: string[]}` | Selection from a visible target zone. |

`compose` may combine these later using role-keyed subpayloads. It should not be
the first implementation target.

A rich client may render sliders, steppers, piece chips, autocomplete, or form
groups. A CLI should be able to ask the same values as sequential prompts and
submit the same payload.

## Media Fragments

`MediaFragment` preserves media indirection until service/client boundaries.

- `content_format="url"`: `content` is directly renderable or remappable.
- `content_format="data"` / `"xml"` / `"json"`: `content` is inline payload.
- `content_format="rit"`: `content` refers to a `MediaRIT` or unresolved
  placeholder.

Pending or unresolved media is still renderable state. Service may turn a
pending RIT into static fallback media, fallback text, or a structured media
placeholder. Clients should show that placeholder when no final URL/data exists.

## Groups And Scene Shells

`GroupFragment` is a relational overlay, not a nested object model.

- `member_ids` references peer fragments in the registry.
- `group_type="scene"` creates a presentation shell for the current turn.
- `group_type="dialog"` associates attributed lines and peer media.
- Other group types such as `zone`, `hand`, `board`, or `status_sidecar` are
  valid extension points.

Groups may reference other groups. Clients may flatten those references for
presentation, but the registry remains id-based.

`group_type="zone"` is the current generic container for targetable piece
surfaces such as a hand, room contents, inventory, field, packet, or map. If a
choice references `constraints.target_zone_ref`, that zone must be rendered or
reachable in the current shell.

## Command Resolution

Natural-language command input is backend-authoritative. The client may offer
affordances, but the backend resolves and validates.

Clients submit one of two typed request shapes:

```text
direct:
  edge_id: <UUID>
  payload: <optional choice payload>

command:
  find_edge:
    kind: command
    command: "take lamp"
  payload: <optional payload>
```

Direct requests execute the selected `ChoiceFragment.edge_id`. Find requests
ask story policy to match a current action and resolve it atomically in the
same service session.

An unmatched, ambiguous, or rejected command returns the current cursor and
step, no new journal fragments, and a typed event:

```text
ux_events:
  - event_type: edge_not_found
    message: "I couldn't match that command."
    presentation: inline
    replay: false
    severity: warning
```

Advisory grammar hints may help capable clients preview a command, highlight
pieces, or show completions. Until there is a dedicated envelope field, such
hints should travel under `metadata.grammar`. If promoted to a top-level
`RuntimeEnvelope.grammar` field later, the semantics should stay the same:
grammar is a visible-surface projection and never a security boundary.

The first supported hint shape is intentionally small:

```text
metadata:
  grammar:
    examples: ["take lamp", "open door"]
    verbs: ["take", "open"]
    nouns: ["lamp", "door"]
```

Clients may ignore these hints and still submit a typed `find_edge` request.

## UX Events

`RuntimeEnvelope.ux_events` is a typed, non-journal side channel:

- `event_id`: stable UUID within the response stream
- `event_type`: machine-readable event name
- `message`: required human-readable fallback
- `presentation`: `inline` or `interrupt`
- `replay`: whether a client may retain the event during envelope playback
- `severity`: `info`, `success`, `warning`, or `error`
- `details`: optional JSON-safe structured context

UX events never participate in the fragment registry and never become journal
entries. Unknown event types still render through `message`.

## Decision Legibility

If an open choice references a piece, zone, blocker, state fragment, or other
renderable object, the referenced state must be visible in the current shell or
otherwise reachable through a supported client affordance.

This rule prevents choices like "Play a card from your hand" from appearing when
the hand or card state is hidden from the renderer. It is a conformance rule for
fixtures and future richer interaction widgets.

## Compatibility Policy

Clients consume `RuntimeEnvelope` directly. Legacy `JournalStoryUpdate[]`
conversion is retired; unknown fragment types remain forward-compatible through
visible fallback rendering.

## Test Contract

Canonical fixtures should live under `apps/web/tests/fixtures/` and act as
executable examples of the service contract.

Required fixture behaviors:

- a realistic whole-turn `RuntimeEnvelope`
- a realistic `ProjectedState`
- locked choices with blockers
- freeform, quantity, and piece payload contracts
- typed direct-edge and find-edge request contracts
- group flattening and dialog grouping
- unknown fragment fallback
- pending media placeholders
- control update/delete
- inline and interrupt UX events with replay policy
- decision legibility checks for references from open choices
- CLI-equivalent payload collection examples for every `accepts.kind`

Browser E2E should be added only after payload widgets and command feedback are
stable enough that E2E coverage will not cement an interim UI shape.

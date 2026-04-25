# Fragment Stream Contract

> Status: Current contract with near-term extension points
> Authority: `tangl.service.response.RuntimeEnvelope`,
> `tangl.journal.fragments`, `ServiceManager`, and the web fixtures under
> `apps/web/tests/fixtures/`.

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
  fragments: list[BaseFragment]
  last_redirect: dict | null
  redirect_trace: list[dict]
  metadata: dict
```

`create_story`, `resolve_choice`, and `get_story_update` return this envelope
directly. Acknowledgement-only operations such as `drop_story` return
`RuntimeInfo`.

`fragments` are ordered for reading and replay. A fragment's `uid` is also a
stable reference target within the envelope and across later update/delete
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

Core reusable fragment types live in `tangl.journal.fragments`.

| Fragment | Purpose |
| --- | --- |
| `content` | Prose, status text, or fallback text. |
| `attributed` | Speaker-attributed content such as dialog lines. |
| `media` | Media reference or placeholder; service may dereference RITs. |
| `choice` | Player-facing interaction offer backed by an `Action` edge. |
| `group` | Relational overlay tying peer fragments together by id. |
| `kv` | Ordered key-value content for compact state/status surfaces. |
| `update` / `delete` | Control fragments mutating an earlier registry entry. |
| `user_event` | User-facing notification or client hint. |

Unknown fragment types are valid extension points. A client that cannot render a
fragment type must keep the stream alive and show or stash a diagnostic fallback
rather than failing the whole turn.

## Choice Fragments

Choices are interaction offers, not generic display buttons.

`ChoiceFragment` carries:

- `edge_id`: the action id to send back to `resolve_choice`
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

`accepts` is intentionally generic. It may describe a freeform value, a quantity
range, a token selection, a target zone, or a future richer interaction shape.
The handler remains the authority for validation and state change.

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

## Decision Legibility

If an open choice references a token, zone, blocker, state fragment, or other
renderable object, the referenced state must be visible in the current shell or
otherwise reachable through a supported client affordance.

This rule prevents choices like "Play a card from your hand" from appearing when
the hand or card state is hidden from the renderer. It is a conformance rule for
fixtures and future richer interaction widgets.

## Compatibility Policy

Legacy `JournalStoryUpdate[]` payloads may be adapted at application boundaries
while old mocks or transports are retired. New tests, fixtures, and widgets must
target `RuntimeEnvelope.fragments` directly.

A compatibility adapter should be narrow, local, and removable. It should never
convert canonical fragments back into a unified legacy block shape.

## Test Contract

Canonical fixtures should live under `apps/web/tests/fixtures/` and act as
executable examples of the service contract.

Required fixture behaviors:

- a realistic whole-turn `RuntimeEnvelope`
- a realistic `ProjectedState`
- locked choices with blockers
- freeform or structured choice payloads
- group flattening and dialog grouping
- unknown fragment fallback
- pending media placeholders
- control update/delete
- user events
- decision legibility checks for references from open choices

Browser E2E should be added only after the direct fragment renderer is stable
enough that E2E coverage will not cement the retired block shape.

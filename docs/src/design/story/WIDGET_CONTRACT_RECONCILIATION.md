# Widget Contract Reconciliation

**Status:** working reconciliation pass for
`STORYTANGL_WIDGET_VOCAB.md` v1.1 against this branch.

The unified vocabulary is the preferred design target. This note keeps fixture
work honest by separating four things that otherwise get blurred:

- what the engine currently models or decodes
- what the web client currently renders
- what the unified vocabulary wants to call the surface
- what should enter the first conformance fixture suite

Conformance fixtures should be generated from the "fixture status" column, not
from the vocabulary tier labels alone. Proposal fixtures live separately under
`engine/contrib/conformance/proposals/` and are not gating until this document
promotes them.

## Naming Decisions

| Surface | Current branch | v1.1 target | Decision |
| --- | --- | --- | --- |
| UI piece / selectable item | Web fixtures and conformance fixtures use `piece`, `piece_id`, `piece_ids`. Engine typed decode support is still pending. | `piece`, `piece_id`, `piece_ids`. | `piece` is now the only UI target terminology. Do not add new `token` UI fixtures or payloads. |
| Engine singleton token | `tangl.core.token.Token` names a local instance of a reference singleton. | Unchanged. | This is the reason to avoid `token` for UI pieces. |
| Ordered kv rows | Engine `KvFragment.content` is still `OrderedTupleDict`; web fixtures use tuple-like arrays. | Record-shaped `KvRow` with optional semantic fields. | Treat record-shaped `KvRow` as a migration target, not current Tier S. |
| Choice HTTP id | Web posts `choice_id` containing `ChoiceFragment.edge_id`; docs increasingly say `edge_id`. | `edge_id` in contract language. | Keep transport compatibility for now; prefer `edge_id` in new docs and fixtures where possible. |
| Command feedback | Current fixture uses unknown `interpretation` fallback fields `outcome` and `command_text`. | Typed `interpretation` with `result` and `text`. | Do not make typed interpretation a Tier-S conformance requirement yet. |
| `place` payloads | Not current in engine; web/Tk/reference clients can inspect proposal fixtures. | `accepts.kind="place"` with source and target zone refs. | Proposal fixture only until the engine emits a worked turn and a CLI commit path exists. |
| Piece lifecycle | Current fixtures render `piece`; web/Tk/reference clients surface `realized=false` as an offer hint. | `PieceFragment.realized: bool` distinguishes offers from realized inventory/world objects. | Proposal fixture only; renderers may surface `offer` as an advisory tag. |
| Roll outcomes | No typed engine fragment; web/Tk/reference clients can inspect/render proposal `roll` fragments. | `fragment_type="roll"` for auditable random/stat outcomes. | Proposal fixture only; reference port renders a text fallback summary. |
| Presentation profiles | No typed engine model; older web world theming exists as ad hoc `ui_config`. | `WorldInfo`/presentation catalog plus envelope `metadata.presentation_context` refs. | Advisory design target; do not treat as gameplay state or imperative UI commands. |

`piece` replaced the older UI `token` term because it avoids the engine singleton conflict
while staying general enough for cards, counters, documents, dice, actors, and
board cells. `chip` is a viable renderer word, but it is too visual and too
small-object-specific for the portable contract.

## Contract Reality Map

| Surface | Engine status | Web status | v1.1 target | Fixture status |
| --- | --- | --- | --- | --- |
| `RuntimeEnvelope` | Current in `tangl.service.response`; includes `metadata`. | Current; `StoryFlow` consumes direct fragments. | Tier S. | Include. |
| `ProjectedState` union | Current: `scalar`, `kv_list`, `item_list`, `table`, `badges`. | Current renderer exists; layout polish remains. | Tier S. | Include all value types. |
| `content` | Current `ContentFragment`. | Rendered. | Tier S. | Include. |
| `attributed` / `dialog` | Current `AttributedFragment` plus `DialogFragment`/group variants. | Rendered through dialog groups. | Tier S. | Include dialog with avatar/media binding. |
| `media` | Current `MediaFragment`, including `content_format="rit"`. | Rendered; pending RIT placeholder exists. | Tier S. | Include pending and update-to-ready media. |
| `group(scene)` | Current `GroupFragment`. | Scene shell is the primary flow unit. | Tier S. | Include. |
| `group(dialog)` | Current via `group_type="dialog"` and `fragment_type="dialog"`. | Rendered. | Tier S. | Include. |
| `group(overlay)` | Engine accepts arbitrary `group_type`, but no specific semantics. | No dedicated overlay treatment. | Vocab target. | Defer. |
| `group(status_sidecar)` | Engine accepts arbitrary `group_type`, but no specific semantics. | No dedicated in-stream sidecar rail. | Vocab target. | Defer or mark visual-only until emitted. |
| `kv` fragment | Current, but with `OrderedTupleDict` rather than record `KvRow`. | Rendered from tuple-like arrays. | Record `KvRow`. | Include current shape; add migration fixture later. |
| `choice` available/locked | Current `ChoiceFragment`. | Rendered, disabled semantics covered. | Tier S. | Include. |
| `accepts.kind="text"` | Current as dict payload metadata. | Rendered by `ChoiceInputView`. | Tier S/P1 typed target. | Include. |
| `accepts.kind="quantity"` | Current as dict payload metadata. | Rendered by `ChoiceInputView`. | Tier S/P1 typed target. | Include. |
| `accepts.kind="pieces"` | Current web/conformance pressure fixture; engine type is untyped dict and no dedicated piece fragment decoder exists. | Rendered with `group_type="zone"` and `fragment_type="piece"`. | `piece_ids`. | Include as the targetable-state pressure surface. |
| `accepts.kind="raw_command"` | Current as reserved choice shape; backend resolution remains authoritative. | Rendered by `ChoiceInputView`; `metadata.grammar` is scene-local and advisory. | Tier P1/Tier S candidate. | Include web fixture; backend interpretation fixture can mature later. |
| `control(update/delete)` | Current `ControlFragment`. | Applied to registry. | Tier S. | Include. |
| `user_event` | Current `UserEventFragment`. | Rendered as status alert. | Tier S. | Include. |
| `interpretation` | Not a typed engine fragment. Unknown fragments fallback in web. | Fallback-only. | Tier P1. | Defer typed assertions; fallback fixture is ok. |
| `compose` | Not current. | Not rendered. | Tier P1. | Defer. |
| `cost_previews` | Not current. | Not rendered. | Tier P1 plural preview list. | Defer until typed accepts settle. |
| `predicate_ref` | Not current. | Not rendered. | Tier P2. | Defer. |
| `piece` / `zone` typed surface | Not current in engine. | Web has `piece`/`zone` pressure widgets. | Tier P2 typed target. | Current pressure fixture; typed engine support remains target. |
| `piece.realized` | Not current in engine. | Rendered as generic offer/availability tags. | Tier P2 lifecycle field. | Proposal fixture only. |
| `accepts.kind="place"` | Not current. | Rendered as source-piece selection into a referenced target zone. | Tier P1/P3 pressure surface for equipment/placement. | Proposal fixture only. |
| `roll` | Not current. | Rendered as a structured outcome row. | Tier P2 structured outcome fragment. | Proposal fixture only. |
| `metadata.presentation_context` | Not current. | Not rendered. | Advisory profile refs and semantic tokens. | Document only until a world catalog shape exists. |

## First Fixture Suite

The first conformance pass added JSON fixtures under
`engine/contrib/conformance/fixtures/` for repo-current surfaces only:

- `crossroads_inn.json`: content, kv, available and locked choices, user event.
- `dialog_with_avatar.json`: attributed dialog and avatar/dialog media binding.
- `pending_media_update.json`: unresolved RIT media plus `update` to a ready
  URL/data payload.
- `projected_state_all_values.json`: one `ProjectedState` with scalar,
  `kv_list`, `item_list`, `table`, and `badges`.
- `quantity_payload.json`: `accepts.kind="quantity"` with min/max/unit.
- `sandbox_payload.json`: text, quantity, current `pieces`/zone pressure
  surface, and decision-legibility references.
- `command_hints.json`: reserved `interpret_command`,
  `accepts.kind="raw_command"`, and advisory `metadata.grammar`.
- `control_delete.json`: delete removes a visible registry entry without
  rendering the control fragment.

Do not include `compose`, typed `interpretation`, `cost_previews`,
`predicate_ref`, `place`, `roll`, or `piece.realized` semantics in the gating
suite yet. Those belong in proposal or migration fixtures until the engine
emits them and the CLI reference port can commit the interaction.

## Proposal Fixture Suite

Non-gating proposal fixtures live under
`engine/contrib/conformance/proposals/`. They are JSON load and reference-port
inspection targets, not conformance requirements.

- `record_kvrow.json`: record-shaped scene-bound `kv` rows with `max`, `unit`,
  `hint`, and `emphasis`.
- `piece_realization.json`: `piece.realized=true/false` as the replacement for
  older offer-specific widget ideas.
- `place_accepts.json`: `accepts.kind="place"` with source and target zones.
- `roll_fragment.json`: `fragment_type="roll"` with dice inputs and explicit
  outcome.
- `carwars_garage_turn.json`: compact garage pressure turn combining slot
  zones, catalog offers, `place`, `pieces`, and advisory drag/stat hints.

These fixtures intentionally use `piece` and `piece_ids` only. There are no
legacy clients outside this repository, so any remaining UI `token` vocabulary
should be fixed in place when found rather than supported through adapters.

## Multi-Envelope Sequence Suite

Sequence fixtures live under `engine/contrib/conformance/sequences/`. They
exercise the fragment registry over time rather than a single turn snapshot.

- `garage_buy_mount.json`: starts with a pending media placeholder, a catalog
  offer, an empty inventory zone, an empty slot zone, and an unknown fallback
  fragment; then updates media to a ready URL, deletes the stale offer, adds a
  realized piece, moves that piece into the slot, and deletes the fallback.

The sequence harness asserts the same invariants a thin client needs: update
fragments preserve UID identity, delete fragments remove stale registry entries,
piece movement updates both zone membership and piece state, and every open
choice references state renderable in the current scene shell.

## Webapp Remediation Backlog

These are the concrete migrations implied by the unified vocabulary:

1. Add typed engine fragments or decode support for the `piece`/zone surface.
   UI fixtures and payloads already use `piece`/`piece_ids`; backend model
   support should follow that vocabulary directly.
2. Replace tuple-like kv payloads with record-shaped `KvRow` in engine
   `KvFragment`, projected state, fixtures, and web rendering.
3. Add a typed `InterpretationFragment` with `result` and `text`, while keeping
   unknown-fragment fallback for older payloads.
4. Decide whether `/story/do` keeps `choice_id` as the transport field or
   migrates to `edge_id`; document any compatibility adapter explicitly.
5. Add typed `place` accepts and a CLI commit path before web/Tk placement
   widgets.
6. Add typed `RollFragment` support once at least one engine-side stat/random
   outcome emits it.
7. Implement `overlay` and `status_sidecar` only when the engine emits worked
   examples.
8. Add more sequence fixtures as soon as a feature depends on cross-envelope
   registry behavior rather than single-turn rendering.
9. Build or update the CLI reference port before graduating any P1/P2 widget
   into Tier S.

## Wireframe Guidance

Use this reconciliation table before commissioning new wireframes. A Tier-S-only
wireframe should include only the fixture-current surfaces above, and should
annotate every rendered widget with a back-reference to
`STORYTANGL_WIDGET_VOCAB.md`. A separate proposal wireframe may use
`carwars_garage_turn.json`, but it should be labeled P1/P2/P3 exploration and
not compared against current web conformance.

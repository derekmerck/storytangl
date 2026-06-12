# Backend Fragment Contract Reconciliation

Status: active reconciliation note.

StoryTangl has two related but separate output surfaces:

- the **service/backend Python API**, consumed directly by Python clients such as
  cmd2, Rich, Tk, and in-process tools;
- the **FastAPI REST server**, which transcribes those Python objects to and
  from HTTP JSON.

The service/backend API is the contract owner for runtime widget-shaped data.
The REST server is intentionally thin: authentication, request routing,
transport serialization, HTTP error mapping, and transport-adjacent media
dereferencing. It should not invent a second fragment model or merge fragments
back into legacy display blocks.

## Target Shape

Service story-session methods return typed Python objects:

| Service method | Python return |
| --- | --- |
| `create_story` | `RuntimeEnvelope` |
| `resolve_choice` | `RuntimeEnvelope` |
| `get_story_update` | `RuntimeEnvelope` |
| `get_story_info` | `ProjectedState` |
| acknowledgement-only methods | `RuntimeInfo` |

`RuntimeEnvelope.fragments` is an ordered list of independent `BaseFragment`
instances. A choice's fragment `uid` identifies the renderable choice fragment;
its `edge_id` identifies the action to submit back to `resolve_choice`. These
identities must remain distinct.

`RuntimeEnvelope.ux_events` is a typed side channel for transient client
guidance. Inline command feedback, validation failures, achievements, and
shell-level notices do not become journal fragments unless they are genuinely
part of the narrative record.

## Responsibility Split

Backend/service responsibilities:

- Return typed Python `RuntimeEnvelope`, `ProjectedState`, and `RuntimeInfo`
  objects.
- Preserve independent fragments and fragment `uid`s.
- Populate action-facing `ChoiceFragment.edge_id`, `accepts`, `ui_hints`,
  availability, and blockers.
- Populate advisory envelope metadata such as `info_affordances`,
  `info_state`, `world_id`, `ledger_id`, and command grammar hints.
- Accept the typed direct-edge / exploratory `find_edge` request union.
- Resolve exploratory queries through Story policy before committing an edge.
- Validate submitted choice payloads during action resolution.
- Return typed UX events when an exploratory request cannot advance.

REST responsibilities:

- Parse HTTP request bodies and query params into service-call arguments.
- Enforce authentication and service-method access policy.
- Serialize typed Python response objects into JSON-safe payloads.
- Apply explicitly requested render profiles such as `html` text conversion.
- Apply transport-adjacent media policies, such as RIT placeholder or media
  server URL conversion.
- Preserve service-owned identities and semantic fields while adding only
  harmless compatibility aliases such as `label`.

REST must not:

- rewrite a choice fragment `uid` to equal its `edge_id`;
- collapse sibling fragments into a `block` payload;
- require clients to submit fragment `uid` when the contract says `edge_id`;
- turn exploratory command text into a synthetic choice or journal fragment;
- create backend semantics from presentation-only hints.

## Current Status

The service layer returns Python-native `RuntimeEnvelope` objects for story
creation, updates, and edge resolution. `resolve_choice()` accepts either a
`DirectEdgeRequest(edge_id=...)` or a
`FindEdgeRequest(find_edge=CommandEdgeQuery(...))`. Story dispatch owns command
matching against the current open `Action` surface. A unique match follows the
ordinary ledger path; no match, ambiguity, or rejection returns the current
turn with an inline, non-replayed `UxEvent`.

The first pinned backend
contract test now asserts that a simple story emits sibling content and choice
fragments, not a legacy block, and that `uid` and `edge_id` stay separate.
Additional contract tests pin authored `Action.accepts`, `Action.ui_hints`,
plural typed `CostPreview` values, and typed player-facing `Action.blockers`
through service envelopes, REST JSON, and remote Python-client hydration.
Fixed action costs belong in `UIHints.cost_previews`; input-specific previews
belong on the relevant `Accepts` variant. Internal VM provisioning blockers are
projected into journal `Blocker` values at the story boundary rather than
exposed directly. These are UI-facing intent contracts, even when the engine's
internal vocabulary also uses fields named `kind`; any future service adapter
that maps UI intent onto engine mechanics should be explicit and narrow rather
than handled by the REST serializer.
`RuntimeEnvelope.to_dto()` projects fragments through the journal fragment DTO
pathway, preserving concrete fragment subclass fields while omitting
transport-only stream bookkeeping. In-process Python clients, diagnostic
fixture generation, REST serialization, and remote Python rehydration all
operate on that same widget-shaped payload surface.
The reference CLI stores runtime updates from `RuntimeEnvelope.to_dto()` before
rendering, while still accepting lightweight object-shaped stubs in tests and
diagnostic harnesses.
The same pattern applies to `ProjectedState`: service methods own the typed
section/value model, `ProjectedState.to_dto()` emits the client-facing
`value_type` discriminated DTO surface, REST and CLI use that projection, and
remote Python clients decode it back into typed projected-state values.

The credentials demo now provides the first real mechanic-to-widget vertical
slice. Entering its `HasGame` block asks the game handler for a current-state
projection before any round has completed. The handler emits a candidate
`PieceFragment`, a packet `GroupFragment(group_type="zone")`, and document
`PieceFragment` members alongside the block's authored prose and provisioned
choices. `ServiceManager.resolve_choice()` returns those same typed siblings in
the `RuntimeEnvelope`, and `RuntimeEnvelope.to_dto()` preserves their identities,
zone references, structured properties, and text fallbacks. The engine-side
field is named `piece_kind` because `kind` is reserved for constructor-form
persistence; fragment DTO metadata maps it to and from the widget contract's
`kind` key.

The same slice exercises input in the reverse direction. The credentials game
provisions one `ChoiceFragment(accepts.kind="pieces")` targeting the packet
zone. `GameHandler` owns the small generic hooks that declare a move's
`Accepts` contract and resolve submitted widget data into an engine move.
Selecting a document's `piece_id` therefore becomes the existing credentials
inspection move before rule evaluation; malformed or stale selections fail at
that mechanics boundary. `Action` preserves the nested accepts discriminator
through graph snapshots, while service and REST remain generic. The test in
`engine/tests/integration/test_credentials_widget_flow.py` pins the complete
path.

Nim provides the second use of the same hooks for bounded integer input.
`get_available_moves()` remains the rules-facing list of legal takes, while
`get_provisioned_moves()` projects those moves as one
`ChoiceFragment(accepts.kind="quantity")`. The submitted quantity is validated
against the current heap and resolved back to the ordinary integer move before
the round runs. This distinction keeps client action aggregation out of the
mechanics API and is the intended pattern for future “how many?” interactions.

The REST layer validates the same `EdgeResolutionRequest` union, calls the
service method directly, and serializes `RuntimeEnvelope.to_dto()`. Any manual
shaping remains limited to HTTP-adjacent concerns such as media profiles and
optional markdown-to-HTML conversion. The serializer remains a transcription
boundary and does not preserve retired request or fragment aliases.

Story create, update, and action endpoints publish
`RuntimeEnvelopePayload` as their FastAPI response model. This is an outer DTO
schema for `RuntimeEnvelope.to_dto()` output, not a second fragment hierarchy:
`fragments` remains a list of independent JSON records. Using the engine
`RuntimeEnvelope` model directly as the REST response model would rehydrate
fragments as `BaseFragment` and restore internal `seq`, `step`, and `tags`
defaults, so the transport schema deliberately avoids that shape drift.

`RuntimeEnvelope.metadata.grammar` is a reserved typed sub-key rather than a
second command model. The service synthesizes `GrammarHint` values from the
current visible fragment surface: choice text supplies exact examples and verb
frames, while visible pieces supply noun-to-piece mappings. This projection is
advisory; command resolution still uses the Story-owned `find_edges` dispatch,
and raw command submission remains valid when grammar metadata is absent or
ignored.

## Diagnostic Fixtures And Transcripts

`engine/contrib/conformance/backend_widget_demo.py` now generates the first
backend-emitted diagnostic payloads:

- `engine/contrib/conformance/diagnostics/backend_widget_contract_runtime.json`
- `engine/contrib/conformance/diagnostics/backend_widget_contract_projected_state.json`

These are not canonical conformance fixtures yet. They prove that the current
service layer can emit a real widget-shaped `RuntimeEnvelope` and
`ProjectedState` covering content, typed choices, blockers, plural cost
previews, `accepts`, `ui_hints`, `metadata.info_affordances`,
`metadata.info_state`, and generic projected-state values.

Diagnostic transcripts should be generated only after backend output can be
captured as a real `RuntimeEnvelope` stream. The durable source of truth should
be:

```text
backend emitted RuntimeEnvelope
  -> canonical JSON fixture
  -> CLI/Rich/web rendered transcript
```

Until that path is real for a world/demo, transcript-like prose and UI mockups
remain design references rather than regression baselines.

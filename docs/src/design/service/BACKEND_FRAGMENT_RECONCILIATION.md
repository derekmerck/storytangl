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

## Responsibility Split

Backend/service responsibilities:

- Return typed Python `RuntimeEnvelope`, `ProjectedState`, and `RuntimeInfo`
  objects.
- Preserve independent fragments and fragment `uid`s.
- Populate action-facing `ChoiceFragment.edge_id`, `accepts`, `ui_hints`,
  availability, and blockers.
- Populate advisory envelope metadata such as `info_affordances`,
  `info_state`, `world_id`, `ledger_id`, and command grammar hints.
- Validate submitted choice payloads during action resolution.

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
- create backend semantics from presentation-only hints.

## Current Status

The service layer already returns Python-native `RuntimeEnvelope` objects for
story creation, updates, and choice resolution. The first pinned backend
contract test now asserts that a simple story emits sibling content and choice
fragments, not a legacy block, and that `uid` and `edge_id` stay separate.
Additional contract tests pin the authored `Action.accepts` and `Action.ui_hints`
path through service envelopes and REST JSON. These are UI-facing intent
contracts, even when the engine's internal vocabulary also uses fields named
`kind`; any future service adapter that maps UI intent onto engine mechanics
should be explicit and narrow rather than handled by the REST serializer.
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

The REST layer starts from `RuntimeEnvelope.to_dto()` and keeps any remaining
manual shaping limited to HTTP-adjacent concerns: media profiles, optional
markdown-to-HTML conversion, and harmless compatibility aliases such as
`choice.label`. That is acceptable as long as the serializer remains a
transcription boundary and keeps service semantics intact.

## Diagnostic Fixtures And Transcripts

`engine/contrib/conformance/backend_widget_demo.py` now generates the first
backend-emitted diagnostic payloads:

- `engine/contrib/conformance/diagnostics/backend_widget_contract_runtime.json`
- `engine/contrib/conformance/diagnostics/backend_widget_contract_projected_state.json`

These are not canonical conformance fixtures yet. They prove that the current
service layer can emit a real widget-shaped `RuntimeEnvelope` and
`ProjectedState` covering content, typed choices, `accepts`, `ui_hints`,
`metadata.info_affordances`, `metadata.info_state`, and generic projected-state
values.

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

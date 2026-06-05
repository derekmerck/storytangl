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

The REST layer still performs JSON serialization manually because it owns HTTP
transport concerns such as media profiles and optional markdown-to-HTML
conversion. That is acceptable as long as the serializer remains a transcription
boundary and keeps service semantics intact.

## Diagnostic Fixtures And Transcripts

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

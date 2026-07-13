# Journal Compose Contract

> Status: Current contract
> Authority: This note defines the current `compose_journal` contract alongside `engine/src/tangl/vm/dispatch.py` and `engine/src/tangl/journal/fragments.py`.

`compose_journal` is the post-merge story seam for transforming ordered journal
fragments after raw JOURNAL handlers run and before service projection or client
rendering begins.

## Current Runtime Contract

- `render_journal` handlers produce ordered raw fragments.
- `compose_journal` handlers run in registry order (dispatch layer, then
  priority) and **fold**: each handler receives the *current* composed batch
  in `fragments` — the output of earlier compose handlers, starting from the
  merged render output in stream order.
- `compose_journal` operates on normalized fragment values only; raw textlike
  inputs belong in `render_journal`, not this seam.
- A compose handler may return:
  - `None` — the batch passes to the next handler unchanged
  - one `Record` or `BaseFragment`
  - an iterable of `Record` or `BaseFragment`
- A non-`None` return becomes the input to the next compose handler and, for
  the last handler that replaced anything, the composed output.
- Invalid replacement shapes raise `TypeError`.
- Handler results are still mirrored onto `ctx.results` for observability,
  but chaining no longer requires inspecting them: write each handler against
  the `fragments` it receives.

## Reference Transform

- The canonical reference implementation is
  `tangl.story.system_handlers.compose_dialog_markup`.
- It rewrites only eligible `ContentFragment` values containing explicit dialog
  micro-block markup.
- It is order-preserving except for the local replacement of those eligible
  fragments.
- Non-eligible fragments pass through unchanged.
- Richer peer fragments may continue to later service and client layers, which
  remain responsible for capability-specific handling.

## Blessed Stanzas

`tangl.journal.compose` names the recurring composition moves so handlers
stay short and uniform:

- `replace_first(fragments, match, replacement, insert_missing=False)` —
  swap the first fragment matching a predicate (visibility substitution).
- `assemble_slots(fragments, order=..., classify=...)` — reorder a merged
  batch into named syuzhet slots; `REST_SLOT` places everything unclassified.
- `beat_overlay(members, beat=..., **metadata)` — emit a `GroupFragment`
  binding a composed beat for segmentation-aware retrieval.

The worked example for the full gather → enrich → compose pipeline is the
`composed_beat_demo` world bundle and its loader test.

## Allowed Transformations

- pass through raw fragments unchanged
- split one fragment into many
- merge many fragments into one replacement
- annotate or enrich fragments with hints or speaker metadata
- synthesize additional peer fragments
- emit relational overlays such as `GroupFragment(member_ids=[...])`

## Forbidden Transformations

- client-format shaping such as HTML policy or transport DTO construction
- media dereference or client capability negotiation
- mutation of runtime, world, or graph state
- silent erasure of provenance metadata when an equivalent replacement trail is possible

## Metadata Preservation

When a fragment carries `step`, `source_id`, `origin_id`, `tags`, or hint models,
a transform must preserve those fields unless the replacement fragment explicitly
supersedes them and still carries an equivalent provenance trail.

## Semantic Attribution And Derived History

Fragment identity and attribution make the realized journal queryable story
state, not merely rendered text. `source_id` identifies the entity or edge that
donated ordinary content, `origin_id` preserves the producer trail, and
attributed dialog may additionally carry stable `speaker_id` and speaker
metadata. Composition must preserve these references.

`Ledger.get_slice()` exposes the ordered fragment stream with optional
`Selector` filtering. Higher-level story queries can therefore derive facts such
as a concept's first appearance, its most recent attributed line, or every
fragment donated by one interaction. Do not cache those answers as mutable
concept fields unless a concrete performance or policy requirement justifies a
separate index.

Prose references are late-bound while generating a fragment. A template such as
`<dragon.color>` reads the dragon's current state, so a runtime change affects
subsequent projections and an authored correction affects a recompiled or
replayed story. Once emitted, however, the fragment records what was disclosed
at that historical step. Current-state changes must not silently rewrite past
journal content; explicit reference/control fragments may update a live
presentation while the authoritative stream retains its provenance.

## Placement Rules

- VM render: produce raw ordered fragment contributions
- story `compose_journal`: normalize and enrich the fragment stream
- service projection: convert engine-native fragments and projected-state models into transport-ready payloads
- client render: ignore unsupported fragment kinds safely and apply client-specific presentation policy

## Examples

Good example:

- rewrite dialog micro-block text into attributed fragments
- preserve `source_id`, `step`, and hint metadata
- add a `GroupFragment` overlay when grouping is useful

Bad example:

- emit HTML snippets or transport-specific card payloads from `compose_journal`
- fetch media URLs or inline binary data for a specific client
- mutate ledger or world state as part of output composition

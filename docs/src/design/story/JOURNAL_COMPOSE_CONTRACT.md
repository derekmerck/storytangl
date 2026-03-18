# Journal Compose Contract

> Status: Current contract
> Authority: This note defines the current `compose_journal` contract alongside `engine/src/tangl/vm/dispatch.py` and `engine/src/tangl/journal/fragments.py`.

`compose_journal` is the post-merge story seam for transforming ordered journal
fragments after raw JOURNAL handlers run and before service projection or client
rendering begins.

## Current Runtime Contract

- `render_journal` handlers produce ordered raw fragments.
- `compose_journal` receives the merged fragment list in stream order.
- `compose_journal` operates on normalized fragment values only; raw textlike
  inputs belong in `render_journal`, not this seam.
- A compose handler may return:
  - `None`
  - one `Record` or `BaseFragment`
  - an iterable of `Record` or `BaseFragment`
- Invalid replacement shapes raise `TypeError`.
- Later compose handlers may inspect earlier compose results on `ctx.results`.

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

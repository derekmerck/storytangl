# Presentation boundary

`tangl.presentation` owns small, domain-neutral syntax that a client may
render, arrange, or solicit: interaction intent, styling and staging hints,
transient guidance, command grammar, and disclosed projected state. It depends
only on Pydantic, Core value machinery, and shared type hints.

It is not a widget library, renderer, authority source, transport surface, or
alternate journal. Journal fragments retain their identity, provenance,
persistence, replay, grouping, update, and deletion semantics; they may carry
presentation values. Service envelopes likewise carry values without owning
them. Backend state remains authoritative for every action.

The cross-layer projection pipeline and its separate projection-resolution and
realization-binding extension points are defined in
`docs/src/design/story/EPISODE_SYUZHET_RENDERING.md`. This package supplies the
domain-neutral vocabulary used at those seams; it does not own the pipeline.

## Status

Current — Slice 2 also owns `UxEvent`, advisory grammar, `ProjectedState`,
`ProjectedSection`, section value variants, info affordances/state, and the
exact-channel `ProjectionRequest` that lower-layer providers consume. An empty
request discovers `ProjectedState.channels`; a non-empty request selects only
those exact ids and returns ordinary typed sections. World-static and
story-dynamic scopes share this model without sharing authority or freshness.
`presentation_dispatch` is the application-level contributor registry for
presentation tasks; its decorators are the registration vocabulary for generic
mechanics. Service retains operations, outer dispatch, response
envelopes, and remote hydration; its fold includes this registry with story,
world, and runtime-local authorities. There is no widget class, client binding,
or transport policy here.

Slice 3 adds surface geometry: `NormalizedRect`, and the `Surface` / `SurfaceSlot`
/ `HasSurface` vocabulary for describing an extent with named slots on it. A slot
names the `piece_kind` that lies there and nothing more. Slot rectangles are
advisory: they say where a thing would be drawn, never that it may be chosen —
current offered-choice state remains the only source of selectable behaviour.

Geometry arrived here from two places that were only ever its first consumers:
the rectangle sat in `journal` because a fragment carried it, and the surface
types sat in `mechanics` because a game block declared one. Neither owned the
vocabulary, which is the same accident this whole extraction undoes.

`sprite_sheet` describes an optional animated alternative to a staged still,
in a normalized, client-facing shape: the sheet and canvas sizes, each frame's
rect, trim offset, duration and resolved pivot, and named clips with a direction
and pass count. It describes the bytes only. `StagingHints.media_clip` selects a
clip per use, and looping stays with `media_timing`, because authored sheets
cannot express "forever".

Only that vocabulary lives here. Reading an Aseprite export, the filename and
compact shorthands, and pairing sheets with stills are authoring and indexing
concerns, and live in `tangl.media.sprite_sheets`; presentation stays a
vocabulary rather than a format library.

The module carries two laws -- which frame shows when, and where a frame lands
over its still -- with a Python reference implementation of each. The reference
is not code other clients share. The portable contract is the laws plus
`engine/contrib/conformance/sprite_sheets/playback.json`, which the reference and
the pygame port both run, and which a web client implements against in its own
language.

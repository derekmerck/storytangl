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

Staging an image answers two different questions, and `StagingHints` keeps
them apart. `media_x` / `media_y` each take either a *name* or a *fraction*.

A name — `left`, `mid`, `right`, `top`, `bottom` — is a **station**, and is
advisory in the same sense as a slot rectangle: it says where a figure belongs,
never what that comes to in pixels. No mapping from names to coordinates lives
here, deliberately. Publishing one would turn advice into a coordinate every
client owes, which is a far stronger promise than the vocabulary makes, and
would relocate every figure already staged by name in a client that had read
the advice differently. One port tucks the outer stations against the edge with
a gutter; another may centre them on quarters; a text client honours none of
it. All three conform.

A fraction is a **placement**, and is exact everywhere. `media_x` places the
image's horizontal *centre*, `media_y` its *bottom* — the centre so a fraction
means the same place whatever the image is wide, the bottom because a staged
figure stands on something and its baseline is the part a placement is about.
Both agree with the bottom-centre anchor a sprite sheet frame already resolves
against, so there is one anchor convention rather than two.

Placements may sit outside the frame, within `[-2, 3]`. Off-stage is a
position: an image entering from the left passes through negative fractions,
and every frame before it arrives is partly outside. The bounds exist only to
separate a position from a unit mistake — someone who wrote `50` meaning half
way — and are wide enough to park a whole image clear of either edge.

`media_keep` (`whole` / `width` / `height` / `none`) asks that a *station* be
held inside the frame on the axes named. It does not apply to fractions.
Holding an image on screen preserves what a name means — "right" pulled in is
still over that way — and destroys what a number means: `0.75`, for an image
wider than half the frame, lands near the middle, which is a different position
wearing the same hint. A world that cannot honour a coordinate should say a
name; that is what names are for. `none` is a member rather than an absence,
because an unset hint defers to client policy while `none` insists the
placement is exact, and an image meant to leave the frame must be able to say
so without knowing what the client would otherwise have done.

How often `media_keep` does anything is a property of the client, not of the
hint, and both outcomes conform. A port that tucks stations against the edge
with a gutter has already put them inside the frame, so the hint only bites for
an image wider than the stage itself; a port that centres stations on quarters
needs it routinely, because a wide image at three-quarters clips long before it
is that large. The same is true vertically, where a shared baseline pushes a
tall figure off the top of a short frame in any reading. This is the advisory
nature of a station showing through rather than an inconsistency to resolve: a
hint that governs interpretation does as much work as the interpretation leaves
it.

The module carries two laws -- which frame shows when, and where a frame lands
over its still -- with a Python reference implementation of each. The reference
is not code other clients share. The portable contract is the laws plus
`engine/contrib/conformance/sprite_sheets/playback.json`, which the reference and
the pygame port both run, and which a web client implements against in its own
language.

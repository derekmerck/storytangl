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

## Portrait association (#538 slice 1)

Journal media's optional `speaker_id` identifies the resolved provider, while
resource/source/origin IDs keep their existing asset/provenance meanings.
pygame merges associated `avatar_im`/`dialog_im` presentations by speaker plus
the existing optional `presentation_handle`, preserving first appearance order
and omitted placement, flip, visibility and clip bindings. Supplied axes and
explicit false flip override; omitted DTO hints must not become explicit defaults.
Unassociated decoration and default placement retain their existing policy.

This is final staging for a response. Ordered expressions with their passages
remain #587: generated portraits follow their attributed line and must be paired
with that preceding line before showing its beat. Paging, focus/dimming, side
selection, slides and audio changes remain separate slices.

## Explicit text intent (#592 slice 1)

`TextAccepts` and its existing validator models are syntax, not an enforcement
engine. Story now enforces explicitly declared text Actions at ordinary pre-move
VALIDATE; `STORY_DESIGN.md` records the exact rules. Effective payload text must be
a string, including optional explicit empty; missing/null is not empty. Text is
preserved, length counts Unicode code points, regex is Python search with `i`/`m`/`s`,
and enum case-insensitivity uses `lower()`. BackendValidator remains opaque and
relies on ordinary domain validation. Client checks are advisory, including current
web UTF-16/regex differences. No new model, serializer or forms middleware is added.

## Compact disclosed status (#581)

Status: the optional compact-row follow-up consumes public `ui-branding` separately from
optional story-dynamic exact `ui-status`. The latter is ordinary ordered
`ProjectedSection` data, not a HUD/widget type or a second state authority.
Section ids identify entries; titles, existing values and advisory `hints.icon`
provide the readable floor. Backend/world contributors choose disclosed facts,
entry order and meaningful time/item wording. Clients choose layout and glyph
treatment; they must not parse English labels, assume a calendar or inspect a
private graph to reconstruct status.

`PresentationHints.placement` is optional coarse advice (`start`, `middle`, `end`),
not a coordinate. `icon_only` defaults to false and requests glyph-only compact
presentation only where the client can realize the icon; unknown/missing icons
retain text. Full label/value remains inspectable. These hints introduce no
parallel section type, mandatory layout, persistent UI state or icon-media loader.

Scope resolution belongs to existing projection contributors and `PhaseCtx.get_ns`.
A world can advertise status across ordinary blocks, including called scenes,
without tying availability to one menu node kind. Empty sections are meaningful.
No new context, implicit call origin, journal channel or persistent HUD cache is
introduced. The optional sandbox contributor uses its existing shared scope;
arbitrary non-sandbox worlds can provide the same exact channel independently.

Pygame reserves one font-metric, density-scaled row outside the logical world
canvas only while exact `ui-status` is advertised. Public branding alone does
not enable it. An advertised empty/null section list retains the opted-in row;
channel removal drops the allocation and clears inspection. Provider order is
stable within placement groups; unhinted entries join start in provider order.
Pygame maintains one
coordinate transform for input, and offers paged compact entries with local
mouse/keyboard details. InfoState availability and dirty/version hints govern
read-only refresh; rendering and preferences do not poll. Story/world switches
reset dynamic freshness even at equal steps; branding is independently cacheable.
The general inspection-channel browser, theme/icon library and finer invalidation
remain follow-ups rather than part of this slice.

## Presentation roles and explicit overrides

Presentation has two complementary author-facing modes.

A **symbolic presentation role** introduces indirection. Names such as
`primary`, `secondary`, `accent`, `metallic`, `leather`,
`speaker:bob`, or `tone:warning` are not renderer instructions. They are
resolved through the current world/client presentation profile. Changing the
profile can therefore restyle every occurrence without changing story state or
authored content. A costume catalog may, for example, bind `metallic` to
silver in one world presentation and titanium in another; all role-bound parts
follow automatically.

A **bounded explicit presentation value** is the escape hatch for an intentional
exception. One heirloom hairpin may request gold even though its ordinary role
is `metallic`; one word in a paragraph may explicitly request blue even though
the surrounding speaker treatment comes from `speaker:bob`. The local explicit
value wins for that presentation coordinate.

Roles and literal values must converge on the same small typed presentation
coordinate system. The portable contract may eventually carry coordinates such
as color, background, weight, text style, or decoration, but it must not carry
arbitrary CSS properties, HTML attributes, ANSI escapes, renderer objects, or
an open-ended style dictionary. Add a coordinate only when a real cross-client
consumer requires it.

The intended resolution order is conceptually:

```text
world/theme role bindings
    -> entity or character presentation defaults
    -> fragment-level explicit overrides
    -> inline explicit overrides
    -> client accessibility / medium constraints
```

The final client remains authoritative over legibility and what its medium can
express. Unsupported roles or literal values must degrade without losing
content or interaction meaning.

This distinction is presentation-level and independent of semantic narrative
facts. A fragment can semantically identify Bob as the speaker while carrying a
`speaker:bob` presentation role; the speaker identity remains true even on a
plain client that ignores the role. Likewise a literal request for blue does
not make “blue” a new story fact unless some mechanic separately models it.

Author markup, where supported, is an input syntax rather than the transport
contract. A bounded Markdown/Pandoc-like form may express either mode, for
example `[Stop]{.warning}` or `[blue]{style.color=blue}`, but codecs must
normalize such syntax into typed presentation values before fragments cross the
service boundary.

## Status

#571 slice 2a implements explicit `PresentationTarget` values (fragment UUID,
RIT UUID, screen role, authored handle) carried by the existing ControlFragment.
The target values live here; matching/folding canonical journal intent lives in
`journal.presentation`, because this dependency-floor package cannot import
journal models. Service invokes that read-only projection before windowing or
capability shaping and delivers a `presentation.music` synchronization snapshot.
Empty is explicit null. Restart is an occurrence-level control action, separate
from the selected recording's loop mode; no historical action is replayed by
the snapshot. There are no playback clocks or second persisted state stores.
The canonical
[media design addendum](../media/MEDIA_DESIGN.md#control-targets-and-desired-music-571-slice-2a)
records the shipped wire spelling and lifecycle policy. Pygame now owns one
co-located-path BGM stream with RIT continuity, fresh restart UID deduplication,
and client-local mute/volume controls, separate from image/history rendering.
Create/get/reconnect uses only desired state. Optional music/device/decoder
failures do not block play. Pygame now also plays fresh AUDIO/`character_vox`
occurrences serially per immediate presentation batch, with client-local music
attenuation. New presentation cancels old voice; redraw/history/restore does not
enqueue it. Source/occurrence provenance stays on ordinary fragments, and native
completion wakes an idle client without controlling story progression. Web
playback, generic effects/voice policy, remote pygame loading and exact-position
restoration remain deferred.

Reference correction (#551): intent zone references and ``PlaceAccepts.edge_ref``
accept ``EntityRef`` — a UUID identity or an exact symbolic label, not Core's
broader bytes/hash-capable ``Identifier``. UUID spellings canonicalize through
normal typed validation; non-UUID labels remain unchanged and case-sensitive.
Producers holding UUIDs pass them directly. Constructor-form JSON restoration
keeps the established decoder's UUID/date recovery contract; no serializer
changes are required. JSON DTOs still expose UUID references as portable strings.
The pygame selection boundary uses the same reference type to match native or
JSON-form piece references. Opaque ledger names and predicate ids remain text.

Slice 2 adds declarative client preferences: worlds may publish typed boolean
or finite ordered enum declarations through exact `ui-preferences` world-info.
Clients retain values locally per world. Explicit `media_visibility` and
`media_clip_binding` tables are checked against those domains while compiling a
world; a client only realizes the prepared values locally. A visibility binding
states the preference values that show an occurrence. A clip binding names one
or two preference axes and maps full value rows to clip names; a missing row
falls back to the authored clip or still. These values are presentation-only:
they neither contact Service nor mutate story state, and client preference
changes preserve resident occurrence slots and elapsed playback.

Slice 3 remains design-only: it asks how a turn may advertise a local cycle over
the alternatives its own staging declares. Such controls appear only while those
alternatives are present, reset on a genuine new turn, and compose with these
world-static viewer preferences. Its schema and reset boundary remain open; it
does not add server persistence, dynamic disclosure/status, or a new dispatch/
widget surface.

The pygame reference port binds only `F1` through `F12`; every declaration is
also a clickable local control, and two-row control pages cycle locally when
needed. Unsupported shortcut suggestions are labels neither promised nor bound.

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

`StageExtentValue` is the fixed logical width and height to which a world's
staged presentation is composed. It is cacheable world metadata projected
through the exact `ui-stage` world-info channel, not narrative state or a
journal field. It deliberately carries no renderer scale, font, DPI, theme,
widget, or asset-pack path: clients remain responsible for their local window
zoom and may refuse extents they cannot lay out faithfully.

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

Depth, where a port draws staged figures at all, comes off the **resolved
baseline** rather than off the hint. A station and a placement are two ways of
saying where a figure's feet land, so once both are resolved they are the same
kind of thing and order against each other on equal terms. Ordering on the
fraction alone silently ranks every station at zero, and a figure stationed at
`top` then paints over one placed near the floor purely by arriving later —
which is the painter's rule exactly inverted, and invisible until a scene mixes
the two vocabularies.

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

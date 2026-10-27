# StoryTangl Pygame Client

A second non-web reference port, alongside `apps/renpy`. StoryTangl keeps
ownership of session lifecycle, traversal, and fragment production; this app
adapts typed `RuntimeEnvelope` output into a small turn model and draws it.

## Status

Adapter proof of concept. The bridge and turn model are covered by ordinary
`pytest`; the renderer is deliberately thin. #592 slice 2 adds local text editing
over the existing authoritative Action submission path.
The #538 first slice replaces speaker-associated expression portraits in place;
The #587 first slice adds optional compact local paging with ordered visuals;
beat-synchronized audio remains deferred.

## What Is Included

- `src/tangl/pygame_client/models.py` — `Turn`, `Line`, `Choice`, `StageImage`.
- `src/tangl/pygame_client/bridge.py` — `ServiceManager` → turn model. Imports
  no pygame, so the whole adaptation layer is testable headlessly.
- `src/tangl/pygame_client/stage.py` — renders one turn to the disclosed logical
  stage, scaled nearest-neighbour by a client-local factor.
- `src/tangl/pygame_client/music.py` — one persistent client-local BGM stream,
  separate from images and historical turn rendering.
- `src/tangl/pygame_client/__main__.py` — event loop.
- `src/tangl/pygame_client/text_entry.py` — one local text editor and bounded modal.
- `src/tangl/pygame_client/presentation.py` — shared stage fold and ephemeral ordered snapshots.
- `tests/` — adapter and live-session tests.

## Design Commitments

**The client holds no world knowledge.** Backgrounds and portraits are selected
by `media_role` (`narrative_im`, `cover_im` → background;
`dialog_im`, `avatar_im` → portrait), never by block label. A world with no art
still plays, rendering flat colour plus text. Art is purely additive.
Image geometry remains an orthogonal staging hint: Repartee's backgrounds use
`media_shape: landscape`, while this stage is free to promote the current
`narrative_im` to its full-frame background.

**Expressions keep the speaker's established placement.** An authored base may
declare `speaker: host` with its `name`, `media_role: avatar_im` and staging hints.
Adopt the existing naming binder: the exact in-scope key resolves the current
Role/Setting provider, including inherited scene cast and recasting. The backend
carries that provider's `speaker_id` on both base and following packed portraits.
Names, paths, resource IDs and provenance never establish speaker identity.

Associated `avatar_im` and `dialog_im` share one portrait family. Expressions
replace that speaker in first-appearance order, retaining omitted position,
fractions, flip, visibility and clip preference bindings. Supplied hints override
only their coordinates; false flip works. `presentation_handle` separates
deliberate independent presentations of one speaker. Variant arrivals consume
no extra slots. An unstaged speaker takes normal deterministic placement; missing
packed art keeps the explicitly staged base. Unassociated decoration is unchanged.

At pygame's existing room-restatement boundary (a `narrative_im` backdrop or
`staged_im` figure), omitted associated portraits retire. Restated speaker/handle
presentations keep their established staging, including when the new expression
supplies no hints. A room statement without portraits retires the old associated
cast; an art-free continuation keeps it. The rule is the same within a batch and
across responses and does not change unassociated decoration's existing policy.
FIFO residency bounded by supported portrait stations and explicit authored
dismissal through existing controls remain separate #538/#409 design work.
`speaker_id` is semantic association, not a control target: existing
`presentation_handle` is the route for deliberate addressing. This is pygame's
room realization policy, not universal backend stage lifecycle.

**Scrolling shows final-response staging; paging follows passages.** The local
pager pairs #613's immediately following generated portrait with its PRECEDING
attributed line before displaying either. Explicit block/base images, including
images emitted after prose, apply before that block's text using existing
step/source boundaries. Each snapshot uses the #622 stage fold, hint inheritance
and room retirement. Future rooms/expressions stay hidden; Back displays an earlier
snapshot without replaying traversal. No journal or transport pagination is added.

## Compact paging (#587 first slice)

Scrolling remains the default when a world makes no suggestion. A world may use
the existing `metadata.ui_preferences` declarations, discovered through the
ordinary world-info catalog and exact `ui-preferences` channel:

```yaml
metadata:
  ui_preferences:
    - id: pacing
      kind: enum
      label: Reading
      values: [scrolling, paged]
      default: paged
```

The reader can override this locally with Ctrl+P or the Pages/Scroll control.
Declared preference controls/F-key shortcuts still work. Mode and page position
are client-local for this run; there is no account setting or backend page state.

The window allocates FOUR wrapped body rows, one bounded attribution row and
one navigation row. Wrapping uses the actual font's pixel metrics and preserves
paragraphs/words, splitting oversized tokens when necessary. Failed visible images retain
their existing text floor, measured into bounded pages in their visual scope.
Carried-forward failures do not duplicate captions; deliberately hidden media
stays suppressed. Preference changes remeasure once and clamp the current page,
while redraw/Back/mode switches do not append captions during drawing. Compatible
narration or same-speaker fragments combine while they fit. Speaker identity, wording/style,
mode, attitude/expression and step/source/visual boundaries keep incompatible
passages apart. The panel sits at the bottom of the existing logical stage; no
world coordinates or portrait natural sizes are moved. Headless pixel witnesses
at 320×200 and 640×400 keep both faces of naturally sized 112/224-pixel portraits
visible above the window. Arbitrary authored face positions remain the author's
staging choice, not an automatic relocation policy.

Up/Down and PageUp/PageDown move between pages. Space/Enter, a click on the prose,
or `>` advance locally; `<` goes back. End and its visible clickable control skip
to the final page. An advance event never doubles as a choice activation.
Choices, letter/number hotkeys, map regions and typed interactions become actionable
only on the last page or after deliberate skip. Terminal menus retain independent
bounded scrolling (Shift+Up/Down/PageUp/PageDown, wheel and pointer controls), full
wording, refusal state, numbering and payloads. Existing surface/selection/editor
views remain in use once an interaction is opened. Empty/media-only and single-page
responses are immediately actionable. Status chrome describes committed runtime
state; paging does not rewind game state or call Service.

Only fresh opening/choice output gets pages. The runner currently starts a new
story; it does not offer a resume command. Bridge refresh/readback remains an
ordinary history operation, and the presentation entry point accepts `fresh=False`
to show that history without replaying pages. Redraw/Back/mode switches are local.

**Audio synchronization is deferred.** BGM/barks retain their existing batch
application on fresh responses. Paging, redraw and Back do not synchronize/requeue
them; refresh retains existing non-fresh audio policy. A later #587 slice must move
bark/BGM application to beat boundaries. Paging does not claim audio follows text.
Focus/dimming, automatic opposite-side placement, slides, FIFO station arbitration,
avatar control realization and web rendering remain separate follow-ups.

## Stage and interaction conventions

**Text geometry stays local to Stage.** `row_text_left` is the text inset (8
logical pixels); `backing_padding` adds 3 pixels outside the glyph region. Both
scale once with density. A new text renderer takes its actual `pygame.Rect`
region to `Stage.text_bounds()`, measures/wraps within that result, and gives
the same region width to `_backing()`. The narrower prose region beside a state
panel follows the same rule. Clipping takes that measured width rather than
assuming the full window. Header/body backing edges stay aligned, including
the compact-page header fixed in #624.

The existing extra 2-pixel right clearance for scrolling prose remains explicit
as `prose_wrap_clearance`; paged prose and choice wrapping keep their symmetric
insets. Scrolling header controls retain their 5-pixel gap; compact-page controls
retain their distinct 8-pixel gap. Labels are bounded before controls so long
attributions/counters cannot paint over the state panel or navigation. Control
hitboxes use the rendered glyph surface intersected with its region and active
clip; they do not extend into invisible text. Body/choice row pitches, fonts,
state-panel padding and the staging-only `gutter` remain separate policies.
No common numeric value makes two of these policies the same, and no legacy
`margin` alias exists. Paging/audio and stage lifecycle contracts are unchanged.

**Logical extent comes from world info; window scale stays local.** Before it
constructs `Stage`, the bridge discovers exact world-info channel `ui-stage`.
Pygame supports declared extents 320×200 and 640×400 in this slice, with density
1 and 2 layout metrics respectively; another declaration fails clearly before
drawing. Worlds that advertise no channel retain the explicit client fallback
of 320×200, which is not treated as a world declaration. `--scale` controls only
the local window multiple. Backgrounds and map plates fill the logical surface;
`staged_im` figures remain at natural pack size and are not rescaled a second
time.

**Everything on stage stands on the stage.** Staged ornaments and portraits
share one floor -- the logical surface's own bottom -- and the choice list is
drawn over them. Flooring portraits at the top of the list instead made the UI
load-bearing: it cost them exactly the height the list took, so the same
character stood higher and drew smaller on a turn that happened to offer more
options, while ornaments beside them never moved. The list is UI drawn over the
room; the room does not rest on it.

**A portrait draws at the size its pack chose.** Once a world declares its
extent, the packer has already answered how big a face is on that stage, so
re-answering it here can only resample art that was already right -- and at a
fraction, which drops rows of pixel art unevenly. The client keeps one size
decision, a ceiling: a portrait taller than the surface is brought down to
leave `24 * density` of headroom, because nothing else will bring it down.
That number is the old fit-to-`112` mechanism's own: it is the height at which
that mechanism used to start shrinking. The shipped demo art is conformed to
exactly 112, so it is unaffected either way.

**Every click resolves to an `edge_id`.** The input layer never commits a
bespoke action, so a map hotspot produces the same payload as selecting the
numbered choice (widget vocabulary §5.3, Input Parity). That is now exercised
rather than merely intended — see the map view below.

**Unavailable choices render dimmed with their `unavailable_reason`** rather
than being hidden (§5.1, Decision Legibility).

**Ordinary prose and choices have independent, bounded text windows.** Fresh
prose opens at its first row; redraws and preference changes retain the current
position. Up/Down move one prose row, Page Up/Down move one visible page. Hold
Shift for the same operations on ordinary choices. Overflow headers show the
visible row range and clickable Previous/Next controls; the mouse wheel scrolls
the window under the pointer. These controls never submit a story action.
Choice labels and refusal reasons wrap in full, including unbroken tokens and
choices taller than a page. Continuations keep the original choice marker and
payload, and only visible text is clickable. The menu uses at most 40% of the
available text height by default (`Stage.choice_fraction`, range 0.2–0.6).

Choice shortcuts are global, not page-relative: `1`–`9`, then lowercase letters,
then uppercase letters, excluding `x` and `X` (reserved for refusals). These 59
positions do not change as the menu scrolls; later choices remain click-only.
Pending piece selection keeps its separate seven-candidate / 8-confirm /
9-more / 0-cancel controls. Maps retain their existing bottom-opened footer.
This is the first bounded slice of #554; columns, attribution presentation,
Markdown styling, and compact-layout negotiation remain separate follow-ups.

**A sprite plays a clip only when its staging asks for one.** When a portrait's
payload carries `sprite_sheets` and its `staging_hints` name a `media_clip`, the
stage draws that clip's current frame over the still's box, where the manifest's
placement law puts it -- anchor on anchor, trim offset included -- so starting or
switching a clip never moves the character. The frame comes from the manifest's
`frame_index_at`, on an injectable clock, and this port runs the same portable
vectors as the Python reference (`engine/contrib/conformance/sprite_sheets/`).
Frames are cut from the sheet before mirroring. Each staged occurrence keeps its
own clock, so one sprite staged twice animates twice. `media_timing` is kept as
stated and honoured: `loop` repeats; `restart` starts over each time a new turn
states it; `pause` holds the current frame and `stop` the first; `start` or
nothing plays as the sheet times it and holds the last frame. A clip also restarts
when it changes, and carries on when a turn merely restates it.
With no clip, no sheet that has it, or a sheet this port cannot load, the still is
drawn. The event loop sleeps until input, and ticks at about thirty frames a
second only while a clip is actually playing.

## Compact gameplay chrome (#581)

The runnable client adds a single compact row **only when exact `ui-status` is
advertised**. Branding, a sidebar, a clock or inventory alone never enable it.
Without that advertisement there is no reserved gameplay strip. The window
caption remains available. The row sits **outside** the world's logical canvas:
a 320×200 world remains 320×200. Its font-metric height is about 14 logical pixels
at density one (28 at 640×400), then the existing integer window zoom applies.
Art, map regions, surfaces, prose, choices and pending selections retain their
world coordinates. `Stage.window_point()` and the inverse input transform account
for the shell offset, including when availability changes during play.

Branding comes from public `ui-branding`, cached separately per world. An optional
logo is resolved by `ServiceManager.get_world_media` through normal inventory and
media-profile delivery; pygame consumes only supported co-located image/vector
paths. Missing, unfetched LFS, unsupported or undecodable logos retain the world
name in local details. There is no alternate filename loader or media downloader.
The initial logo also becomes the window icon before the window opens; without a
readable logo, the client uses StoryTangl's glyph. Later icon changes are
best-effort because some platforms only accept an icon at window creation.
The window caption is just the public world title (`ui-branding.name`), falling
back to its technical world label. It does not display audio state or shortcuts.

The optional exact story channel `ui-status` supplies ordered `ProjectedSection`
values. The backend chooses entries, identities, wording, disclosure and icon
suggestions; pygame arranges width-bounded pages of up to six entries in one row.
Optional `hints.placement` (`start`, `middle`, `end`) groups entries, preserving
provider order within each group; unhinted entries join the start group.
`hints.icon_only` defaults to false. A recognized token can use just its glyph;
unknown/missing tokens always retain readable text. Full labels and state stay
available in details. The client does not parse English
field names, inspect a graph, compute inventory rules, assume a calendar/daypart
count, or read the host clock. Unknown icons keep their readable text floor.

- Click an entry, or press `Ctrl+I`, for its full label/value/details.
- Click `i` to open/close details, including branding/logo and help on an empty row.
- In details, `Tab` / `Shift+Tab` visits entries (including overflow pages),
  `PageUp` / `PageDown` or the wheel pages long text, and `Esc` closes.
- Click `>` to cycle compact pages. Details never submit a choice.
- Music controls and native voice completion remain active while inspecting.

Runtime-envelope `InfoState` governs refresh. The bridge discovers availability
initially and when it changes; it fetches exact status once on first availability
and on new dirty versions. Equal-version removal/reappearance is handled.
Redraws, animation, preferences and repeated envelopes do not refetch status.
Story/world switches reset dynamic freshness, even at equal steps; public branding
has its own cache. Removed channels/sections clear old contents. None of this is
persisted in the journal or used as game authority.

Sandbox worlds may opt in by registering
`advertise_compact_status` / `project_compact_status` from
`tangl.mechanics.sandbox.compact_status` on their ordinary world dispatch for
`advertise_story_info_channels` / `get_story_info`, with `Block` and
`wants_exact_kind=False`. Those contributors use the existing scoped namespace,
so a called scene under the same `SandboxScope` retains its clock and carried
items. Nearest `ui_status` locals may replace the default set with ordinary
projected-section data; `[]` / `None` explicitly remove entries without removing
chrome while the channel stays advertised. Channel absence, unlike empty content,
removes the row and clears old inspection targets. Worlds choose optional
`period_labels` / `period_icons` suggestions.
`period_icons` uses string period identities, for example `{"4": "moon"}`, so
keys remain unchanged through JSON restoration. Lookup uses the mechanic's
actual period identity, not its displayed label; integer-key aliases are not supported.
Non-sandbox worlds can provide the same exact channel through their own ordinary
projection handlers, without adopting a sandbox clock or inventory.

For example, after constructing the world's ordinary `World` authority:

```python
from tangl.story import Block
from tangl.mechanics.sandbox.compact_status import (
    advertise_compact_status, project_compact_status,
)

world.dispatch.register(
    advertise_compact_status, task="advertise_story_info_channels",
    wants_caller_kind=Block, wants_exact_kind=False,
)
world.dispatch.register(
    project_compact_status, task="get_story_info",
    wants_caller_kind=Block, wants_exact_kind=False,
)
```

Omit these registrations to opt out. A non-sandbox world's advertisement handler
returns `InfoAffordance(channel_id="ui-status")`; its `get_story_info` contributor
returns ordinary sections only when `"ui-status" in request.requested_channels()`.
No `show_status` flag or special metadata is required.

The default sandbox provider suggests title at start, carried items in the middle
and day/period at end. Compact sandbox source assets may declare `icon: lamp`,
`icon: key` or `icon: bag`; `SandboxAssetSpec.icon` compiles to the ordinary
`AssetType.icon` default inherited/delegated through tokens, then to `hints.icon`.
Those three tokens have distinct drawn treatments. Arbitrary tokens remain legal
and degrade to text, not a guessed filename. Custom scoped sections can carry
`hints: {placement: middle, icon: key, icon_only: true}`. Icon images/media bindings
remain deferred. This does not change the documented excluded holder-map staging
surface or add inventory persistence; graph tokens retain their existing references.

Always-on Service-backed witnesses cover scoped call/return, time/charge and item
changes, custom non-sandbox calendar wording, purity, query counts and fallbacks.
Headless rendering covers both supported extents and long/overflow entries;
map/surface input regressions also run with and without chrome. Headless images
are layout evidence, not human-confirmed interactive or audible verification.
The general info-channel browser/drawer, title screen, universal theme/icon system,
per-item art and precise dirty tracking remain deferred; #581 stays open.

## Background music (#571)

The runnable client opts into AUDIO and resolves `presentation.music` through
the bridge's ordinary PASSTHROUGH media profile. Only a co-located `path` can be
loaded by pygame in this slice. URL/inline delivery is reported as unsupported;
there is no remote downloader or URL-to-path guessing. Bridges without a music
owner still default to omitting audio. AUDIO never becomes a StageImage.

One music owner uses `pygame.mixer.music`. The same `rit_id` continues across
redraws, prose, contests, maps, and adjacent scenes. A different RIT replaces it;
explicit empty/unavailable snapshots and stops clear it. Loop/start repetition
is honored on load or deliberate restart. Merely restating a snapshot never
restarts music. A changed repetition suggestion takes effect on the next load
or explicit restart, not by seeking/restarting an unchanged stream.

Create/get/restore/reconnect synchronizes only the current desired track, not
historical cues or controls. Live choice responses may restart a matching current
track once per fresh control UID, using the shared fragment/resource/role/handle
targets. Final snapshots win over stale controls. Story/world switches and
teardown stop old playback; changing scenes does not. No playback state is sent
to Service or stored in the journal.

Local keyboard controls:

- `Ctrl+M`: mute/unmute.
- `Ctrl+[` / `Ctrl+]`: volume down/up in 10% steps.
- `--mute`, `--volume 0.5`: initial local settings (volume range 0–1).

They do not collide with choice letters, numeric selection, or world preference
F-keys, and persist through redraws and track changes. Missing optional files,
unsupported delivery, unavailable devices and decoder failures are logged;
device/decode failures remain available through local diagnostics. Prose and choices
remain usable. There is no completion-dependent progression, generic SFX, remote
pygame audio, crossfade, playlist, or playback-position restoration.

### Character barks

Ordinary block media declarations with `media_type: AUDIO` and
`media_role: character_vox` play on a separate serial voice channel. A block may
declare several clips (for example, two characters' call and response); they
play in emitted order without timestamps. Existing source/step/occurrence and
authored handle/caption provenance stays on the canonical fragments. There is
no inference from displayed character names and no new utterance/timing model.

Fresh story openings and choice output enqueue new occurrences once per fragment
UID, not once per recording: two occurrences of the same clip may play twice.
Refresh, reconnect, JSON-restored history, redraw and preference changes do not
replay barks. Advancing to another presentation cancels old active and pending
dialogue, including when the new presentation is silent. Prose and choices never
wait for audio. Missing/pointer/unsupported clips and decoder/device failures
log and skip; remaining playable clips continue. Paths use normal media-profile
resolution, never filename guessing or a separate downloader.

While voice plays, music gain is 25% of the *current* user music setting (or zero
if music is muted). Adjacent queued clips retain attenuation. Drain, cancellation
and teardown restore the current setting; they never restart a stopped track.
Track changes inherit the active attenuation. Ctrl+M and brackets remain music
controls, not global voice controls. Native channel completion events wake even
an idle, non-animated window; obsolete events cannot interrupt a newer busy clip.
All queue, device and completion state stays local to pygame, not in Service or
the journal. Web playback, generic SFX/voice selection, TTS and advanced mixing
remain separate work.

Marmoset Island declares one opening cue, `music/theme.mp3`. Its island and
orbital packs use the same relative name; the selected pack supplies the bytes.
Optional themes remain in Git LFS, excluded from default fetches. Fetch just them
without changing persistent exclusions:

```bash
git lfs pull -I "worlds/repartee_loop/media/music/theme.mp3,worlds/repartee_loop/media_spaceport/music/theme.mp3" -X ""
```

No fetch is needed to play silently. Tests always generate tiny WAVs for lifecycle
and failure coverage. Optional real-theme tests run separately for each pack when
actual bytes exist, skip absent/LFS-pointer files, and fail real decode/continuity
errors. SDL dummy audio proves decoding/play invocation, not human-confirmed
audible output. Tests never fetch media or depend on git-lfs being installed.

## Typed Choices

Most choices are answered by their `edge_id` alone. Some want a value first, and
`accepts.kind` says which (§6.1). This port collects `pieces` and `text`;
quantity/place/compose remain inert with a reason rather than guessing a payload.

### Text entry (#592 slice 2)

An available `TextAccepts` choice opens the same editor through its original
number/letter shortcut or pointer hitbox. Its label remains the instruction and
its placeholder is guidance, never input. A disclosed string activation `text`
prefills the buffer; otherwise it opens empty. The local `PendingText` state is
separate from piece counters and never reaches Service or persistence.

The modal fits 320×200 and 640×400, with or without the optional status shell.
It uses a steady focused caret and a horizontal viewport with overflow markers;
the full value is retained, not truncated to the visible substring. Left/Right,
Home/End, Backspace/Delete edit one Unicode code point at a time. Character input
uses pygame `TEXTINPUT`, with `start_text_input` / `stop_text_input`; `TEXTEDITING`
composition is only local pre-edit until committed by the text system. Enter
while composing does not submit the unfinished composition. This is bounded
desktop composition handling, not a broad IME/mobile or clipboard framework.
See the [pygame text-input API](https://www.pygame.org/docs/ref/key.html#pygame.key.start_text_input).
SDL text input is stopped before the first gameplay frame as well as after editing,
so the activation shortcut cannot type itself into the new buffer. Gameplay's ASCII
letter shortcuts retain Shift/Caps mapping without assembling editor text from keys.

Enter or clickable Submit sends the exact buffer as `{"text": value}` through
`commit_payload` → `bridge.choose(edge_id, payload)`. The new text path does not
duplicate Frame's authored/submitted activation merge. No trimming, normalization,
capitalization, name-only restrictions, cancellation words or hidden truncation:
literal `eof` is ordinary text. Optional `""` is a real submission. Required blank
has useful local feedback; all other declared/domain constraints are checked by
the existing authoritative backend. A normal submission `ValueError` retains the
same editable buffer/caret and shows feedback for retry. Other exception types
propagate; no general rollback or failure-atomicity guarantee is implied.

Escape or clickable Cancel closes without a Service call, narrative time, or
journal record. Focus suppresses choice shortcuts, map/piece/paging/preference
actions and underlying pointer/chrome interaction. Window close, native voice
completion and local Ctrl music controls remain active. Music ownership and
sprite clocks are not paused; a still stage still sleeps rather than polling to
blink a caret. Cancel/success/session loss stops text input. Native glyph support
depends on the bundled pygame font; missing glyphs do not rewrite the buffer.

Pending input belongs to the user/ledger/world, turn step and selected offer.
Session replacement or offer withdrawal/unavailability/replacement cancels it;
queued old input cannot submit another offer. Equivalent same-turn restatements,
local redraws/preferences and animation retain the buffer. Keystrokes/redraws do
not fetch Service state. Choice numbering and source edge identity are unchanged.

Headless tests cover keyboard/pointer parity, focus, editing/overflow at both
extents and chrome states, Unicode/whitespace/empty/`eof`, composition, rejection
and exactly-once retry, session/offer resets, native completion and animation.
A real JSON-backed inline world stores a Cedar-shaped name through its authored
Action effect and proves activation merge and ordinary restore; no private world
or LFS asset is needed. Rendered layouts are inspected as pixel evidence, not
human-confirmed native IME or audible playback validation.

**Future boundary, not implemented:** completion is editing, not committing.
Selecting a completion will fill the buffer, not submit it. `EnumValidator.values`
can declare a finite restricted vocabulary; non-restricting advisory suggestions
need a separate future hint contract. `metadata.grammar` concerns exploratory
command-to-edge resolution, not this already-selected Action's text argument.
No suggestion fields, autocomplete, command entry or general forms framework are
included here. Web/CLI and #604's prompt/EOF work remain separate.

### Piece selection

A `pieces` choice opens a second numbered list of the pieces it will take, and
the payload is built only once that list has been answered:

```
1. Inspect a document          ->     1. passport
2. Choose pass                        2. work permit
3. Choose deny                        0. Cancel
```

Three things about that are load-bearing.

**The two lists are numbered independently, both from 1.** The CLI takes the
same selection as positional values after the choice number (`do 1 0:passport`),
so the same key names the same piece in both ports. Escape or `0` leaves the
selection without committing — a mode a mouse can enter but only a keyboard can
leave is not a usable surface, so Cancel is a clickable row too.

**Only a full selection commits itself.** At `max` there is nothing left to
decide. Anywhere between `min` and `max` there is no moment the client can infer,
so `8. Confirm` appears once the minimum is met — which is also the only way a
`min=0` choice can be submitted empty. Below the minimum the row reads
`Pick N more` and does nothing.

**Long lists page.** Seven candidates at a time, `9. More (2/3)` to advance,
wrapping back to the first page. Numbering restarts per page, so the number a
player reads is the key they press wherever they are in the list.

Seven rather than eight because the controls are drawn from the same keypad the
candidates are — `8` confirms, `9` pages, `0` cancels — and an eighth candidate
would be clickable but unreachable by key.

**Which pieces are offered comes from the choice, not the renderer.** A
`pieces` choice constrained to `target_zone_ref` is satisfiable only by pieces in
that zone, so `selectable_pieces` reads the constraint and the candidate — a
piece too, but outside the packet — never appears. That is §5.1 again: the
player is only offered what the backend will actually accept.

**The finished payload follows §6.1.1's table**, so a hotspot and a numbered key
commit the same thing. It is not byte-identical to the CLI in every case: the CLI
discards an authored activation payload and this port preserves it, which is a gap
on that side rather than a divergence to copy. Validation here is advisory — the
backend re-checks and is authoritative (§6.1.2) — and refusing early only keeps a
doomed commit off the wire.

Every click and key still resolves to `(edge_id, payload)`; `BeginSelection`,
`PickPiece` and `CancelSelection` are client-local steps that never reach the
service. That is what keeps Input Parity true for a choice that takes two
actions to answer.

**Attribution decides presentation.** An `AttributedFragment` renders as a
speaker bubble; a plain `ContentFragment` renders as narration. The client does
not parse prose prefixes.

## The State Panel

A turn carrying pieces, zones or findings reserves the right-hand column for
them. The space is taken from the prose rather than shared with it, because a
document that scrolled away is a document the player cannot evaluate — and §5.1
makes rendering it a requirement, not a flourish.

```
                          Edda Marrow
  You inspect the         CREDENTIALS PACKET
  work permit.             passport - already
  The work permit          inspected
  was never sealed         work permit - already
  by the issuer.           inspected
                           baggage
  1. Inspect a document    FINDINGS
  2. Review packet ...      work permit: The work
```

**A zone renders even when empty.** A targetable container with nothing in it is
information, not an absence.

**Findings keep the engine's `emphasis` word** — `ok`/`warn`/`danger`/`subtle`
choose a colour. The client never re-derives severity from the prose.

**A spent piece is dimmed with its reason and cannot be selected.** That is the
generic `available` / `unavailable_reason` pair, read exactly as it is on a
choice. `credential_gate` sets it on documents already inspected; before that
existed, the only way to learn a document was spent was the backend error raised
after committing it.

**An over-full panel pages.** At 320x200 a nine-choice turn leaves the panel
about eight rows, and a full packet plus findings exceeds that. It paginates and
shows `page 1/2 tab`; `tab` advances it and the label is a hitbox too. An earlier
draft drew an overflow notice instead, which told the player state was hidden
without giving them any way to read it — not what §5.1 asks for.

## The Map View

When the cursor publishes a plate, the client draws it instead of the ordinary
scene layout: the plate full-frame, an outlined box per region, and the choice
number pinned inside each box.

The two halves arrive by different routes and are joined in the client, which
is the point of the design:

- **Geometry** comes from story-info, requested by name as `map_plate` and
  `map_regions`. It is reference state — it changes when the art changes, not
  when the reader moves — so a client that cannot draw maps never asks for it.
- **Liveness** comes from the ordinary choice list. A travel choice carries a
  `ui:plate:<plate>:<region>` tag, and the renderer boxes the region whose name
  a live choice claims.

Everything else falls out of that intersection rather than needing a rule. A
region no choice claims is drawn nowhere and clicks nowhere, which is how "not
currently on offer" differs from "offered and refused" — the latter is a real
choice with `available: false`, so it gets a dimmed box and its
`unavailable_reason` in the legend.

**At most one choice may claim a region.** The engine refuses to project an
ambiguous one — whether two locations claim the same region, or one location is
reachable by two authored routes — and this renderer skips it rather than
picking a winner. Choosing between claimants would hide a dropped choice behind
a hitbox that looks perfectly correct. The routes stay offered in the legend;
only the hitbox is withheld.

The plate drawn is the one the geometry *names*, not merely the first `map_im`
staged. Picture and rectangles arrive by different routes, so a batch that
crosses between two maps could otherwise pair one map's image with the other's
hitboxes.

The footer is capped and pages. It is drawn over the plate, so hit-testing runs
in reverse draw order and a legend row wins the pixels it visibly covers.

The pin carries only the number. A 70px box cannot hold "Go to The Practice
Yard", and shortening it would mean parsing prose the client does not own, so
the names stay in the legend below and the number ties the two together. Every
choice appears there, boxed or not.

A refused region pins `X` instead, and its legend row reads `x)`. Numbering is
positional over the whole list, which the widget vocabulary settles in §2.6.1
and the CLI follows: the key a row shows is the key that commits it, and a row
this port cannot commit has no key, because printing its position would invite
a press that silently does nothing. Live rows therefore run 1, 3, 6 — the gaps
are the refusals, and every key on screen works.

Capital `X` on the plate rather than lowercase, because at 11px the default
font rasterizes a lowercase `x` as a featureless blob; the legend keeps `x)`,
where the bracket carries the shape.

Keys run `1`-`9` and then `a`-`z`, skipping lowercase `x` since that is the
mark for a row without one. Past the end of that alphabet a row prints no key
at all and stays clickable — an unreachable ordinal would be the same broken
promise as a number on a refused row.

`map_im` is deliberately outside `BACKGROUND_ROLES`. A plate is full-frame but
is not scenery, and a client with no map view must not stage it as a backdrop —
it renders the numbered list instead, which is exactly what this client did
before this feature existed.

## Running

pygame-ce is a **dev/test** dependency, not a runtime one — `poetry install`
brings it in so the renderer tests run in CI, while the engine and service never
import it. That is a different question from the Ren'Py app's convention of not
vendoring an SDK: pygame-ce is an ordinary wheel, so there is no reason it
cannot be a test requirement.

The bridge and session tests import no pygame at all and run regardless; only
the renderer tests need it, and they skip cleanly when it is absent.

```bash
PYTHONPATH=engine/src:apps/pygame/src:worlds/repartee_loop \
  python -m tangl.pygame_client --world repartee_loop --scale 3
```

`--assets DIR` resolves relative media sources. `--screenshot PATH` renders one
frame and exits, which works headless under `SDL_VIDEODRIVER=dummy`; a clip in
that frame shows its first frame, so captures are reproducible.
`--reduced-motion` holds every clip on its first frame. The pose still shows --
it is story state -- only the motion stops.

```bash
PYTHONPATH=engine/src:apps/pygame/src poetry run pytest apps/pygame/tests
```

## Test Isolation

`tests/conftest.py` carries world-singleton isolation that engine tests get from
`engine/tests/conftest.py`. The `repartee_world` fixture additionally repairs a
real cross-suite interaction: `PhraseType` definitions register when the world's
domain module is imported, and a full-suite run can clear those registries while
the module is still in `sys.modules`, so a later compile finds no definitions and
badge construction fails validation. The fixture reloads only when the singletons
are actually missing — an unconditional reload rebinds classes that live
instances still reference.

This is a property of singleton-registering worlds, not of this client. Any
second consumer loading such a world through `ServiceManager` after the engine
suite runs would hit it.

## Divergence From The Ren'Py Adapter

Two ports now build near-identical turn models. Rather than pre-extracting a
shared adapter layer, this file records where they actually differ, so the
decision to share is made on evidence.

**Same in both, and non-obvious enough to be worth sharing eventually:**

- Session bootstrap. `create_user()` must be called for a real user id; an
  invented `uuid4()` is rejected by `ServiceManager.open_user`.
- `ledger_id` travels in `RuntimeEnvelope.metadata`, not as an attribute.
- Media payloads name their source by `path`/`url` depending on
  `content_format`, never `content` or `source`. Both bridges therefore carry
  the same `("path", "url", "src", "ref")` probe.
- `ChoiceFragment` stores its activation override in `activation_payload`
  (wire alias `payload`), not `choice_payload`.
- Group fragments must be flattened before per-step grouping.
- Media that cannot be dereferenced degrades to its text floor, and the service
  may supply that text itself in a content-shaped payload.

The first four were each rediscovered the hard way while writing this port —
three of them by shipping the bug first. That is the strongest argument so far
for extracting a shared envelope-adaptation helper: none of these is guessable
from the type signatures, and a third port would pay the same tax again.

**Genuinely different, and reasons not to unify the turn model yet:**

| | Ren'Py | pygame |
|---|---|---|
| media | ordered `scene`/`show` ops, stateful | flat per-turn image list, stateless |
| speaker | `portrait_tag` for a defined character image | resolved `speaker_id`, optional presentation handle, and portrait role family |
| choices | menu built by the runtime | hitboxes owned by the renderer |
| typed input | not attempted | two-step numbered selection for `pieces`, paged |
| turns | one per step, played in sequence | merged into one actionable frame |

The media model is the real divergence: Ren'Py has a persistent stage that
`scene` clears and `show` mutates, while this client redraws from scratch each
turn. A shared model would have to pick one or carry both.

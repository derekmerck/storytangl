# Repartee Loop

`repartee_loop` is the launchable CLI reference world for the completed
call-response feature track. It composes three layers without adding another
mechanic:

- the fixed call-response kernel resolves one exchange and writes typed evidence;
- world-owned UPDATE aftermaths award a learned response after loss and a
  separately typed prize after victory;
- stable hub choices read current repertoire and prize possession through
  ordinary namespace predicates.

The dockhand's reply is earned through a normal catalog transaction. The salon
master's later call owns the relation that recognizes that old reply, so the
player's retained badge is enough to answer it in a fresh contest. The brass
token opens the final salon choice only while it is held.

It is a compact conformance world for three things — the call-response loop,
the media path, and the visual map — not a full trading campaign.

## The quay district

The quay is a hub of five places. The map is one of them: standing on it is
standing on the quay looking at the district, so `current_location` is always
honest and there is no map-mode for a client to get stuck in.

Travel is ordinary choices. The plate declares named regions; each place claims
one; the fanout offers travel to whichever places claim a region on the plate
you are standing on. Neither side references the other, which is what lets a
place claim a region on a second plate it has never heard of.

The *names* survive a reskin. The *rectangles* do not yet: they are world-owned,
so a pack whose plate composes the district differently cannot be dropped in
without editing world data. See #419 — and see below for why the two packs here
are not evidence to the contrary.

Entry conditions live with the place that guards itself:

```yaml
salon:
  plates: [quay:salon]
  conditions:
    - "prizes.has_prize('repartee_salon_token')"
```

so the salon stays on the map, dimmed, with its reason, until the brass token
is won. A guarded place is visibly there and refused, never quietly absent.

The claim reaches clients as an ordinary fragment tag, `ui:plate:quay:salon`.
A client that draws maps intersects those tags against the plate's regions and
puts a hitbox on the matching choice; every other client ignores them and
renders the numbered list. Both commit the same `edge_id`. The CLI floor for
the map therefore needs no map code — it already ships.

The plate itself is media with `media_role: map_im`, which no stage mistakes
for scenery, and its geometry is served through story-info on its own
explicitly requested channel. The reader-facing `map` channel stays a
gazetteer of place names; a text client asking to see the map is not handed a
table of hitbox coordinates it cannot draw.

## Art packs

Assets are world-owned and resolved by name through the bundle's media
registry, so an alternative art pack is a sibling directory holding the same
asset names. Swapping is one line in `world.yaml`:

```yaml
media_dir: media_spaceport   # default: media
```

Nothing else changes — not the script, not the staging hints, not any client.
`media/` is the quayside set; `media_spaceport/` reskins the same beats as a
night spaceport, with the clerk as a service robot and the dockhand as an
alien stevedore.

### Capturing a pack

[`scripts/capture_world_frames.py`](../../scripts/capture_world_frames.py)
renders one frame per pack headlessly, so screenshots of a reskin are
reproducible rather than taken by hand:

```bash
poetry run python scripts/capture_world_frames.py --advance 1
```

Two things about that are easy to get wrong, and the script exists because of
them. The pygame client's `--assets` flag does **not** switch packs: it only
applies to relative media sources, and the engine hands the client absolute
paths resolved through this bundle, so every pack renders identically and the
flag looks broken. The pack is chosen by `media_dir` above, which is a world
setting, not a client one. And `pygame-ce` lives in the dev group
(`poetry install --with dev`), since it is a renderer test dependency rather
than a runtime one.

Advance the same number of turns for every pack. The prose and choices come out
identical because the graph is identical; only the art differs, which is the
claim a reskin screenshot is making.

Each pack carries a `manifest.json` whose top-level `size`, `mode`, and
`sha256` describe the **shipped** file, with the render as generated recorded
under `conformed_from`. A test asserts the manifest matches the assets, since
conforming images after writing a manifest is exactly how the two drift apart.

Only `media_spaceport/` has generation provenance: per-asset source and
generation hashes, the background-removal model, and a `provenance/` directory
with the workflow templates and batch receipts that produced it. The base pack
predates that capture and records only shipped files and the conformance step —
its map plate included, which was rendered outside the batch helper and carries
only its source hash and conformance transform.

Assets are conformed to the client's target rather than stored at generation
size: backgrounds resample to the 320x200 logical surface and sprites are
trimmed to their alpha bounds and scaled to a common height, both
nearest-neighbour so the result sits on a real pixel grid.

The map plate is the strongest test of the interchangeability rule, because
both packs must agree on geometry as well as names: the world's region table is
authored once and has to land on the right building in either skin. The
spaceport plate was generated from the quayside plate as a pixel reference, so
the same four rects fit both — starfield for water, docked craft for ships,
same doorway at the top of the same steps.

That agreement is luck rather than structure, and should not be read as proof
that geometry is portable. The world owns the region *names*, which is right — a
place claiming `quay:salon` is world truth. It also owns the region *geometry*,
which assumes every pack's plate shares a composition. That held here only
because the spaceport plate was generated from the quayside plate as a pixel
reference, so it preserves the source composition by construction.

A pack drawn independently would need its own rects for the same names, and
there is nowhere to put them short of editing the world. Geometry belongs to the
pack, beside the plate it measures, with the world's table as the fallback.
Tracked in #419; the contract stays provisional until then.

Its batch manifest (`provenance/map-jobs.json`) is also the first one authored
in factored form: the shared style clause and output size sit in pack-level
`params`, and the job carries only its subject, seed, and prefix. That is what
makes "render the whole pack again, but at dawn" one edit instead of six, and
`comfy_batch.py` has supported it all along. The other six jobs still carry
whole hand-written prompts with that clause copied into each, and converting
them is mechanical.

Because staging hints live on the block rather than the asset, a pack must keep
the same names and roughly the same composition. The spaceport pack retains the
source staging layouts for exactly this reason, so `media_x` placement and the
clerk's flip stay correct across both.

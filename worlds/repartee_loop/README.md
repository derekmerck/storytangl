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
you are standing on. Neither side references the other, which is what lets the
art be redrawn, rescaled, or replaced without touching the world — and lets a
place claim a region on a second plate it has never heard of.

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

Each pack carries a `manifest.json` whose top-level `size`, `mode`, and
`sha256` describe the **shipped** file, with the render as generated recorded
under `conformed_from`. A test asserts the manifest matches the assets, since
conforming images after writing a manifest is exactly how the two drift apart.

Only `media_spaceport/` has generation provenance: per-asset source and
generation hashes, the background-removal model, and a `provenance/` directory
with the workflow templates and batch receipts that produced it. The base pack
predates that capture and records only shipped files and the conformance step.

Assets are conformed to the client's target rather than stored at generation
size: backgrounds resample to the 320x200 logical surface and sprites are
trimmed to their alpha bounds and scaled to a common height, both
nearest-neighbour so the result sits on a real pixel grid.

The map plate `quay_map.png` is named by the world but not yet drawn in either
pack. Until it is, the plate resolves to nothing and degrades to its text
floor: the district still plays, as a numbered list of places. Art is additive
here in the strict sense — the map works before the map exists.

Because staging hints live on the block rather than the asset, a pack must keep
the same names and roughly the same composition. The spaceport pack retains the
source staging layouts for exactly this reason, so `media_x` placement and the
clerk's flip stay correct across both.

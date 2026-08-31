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

This is a compact conformance world, not a full trading campaign or a richer
presentation proof.

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
alien stevedore. Each pack carries a `manifest.json` recording per-asset source
and generation hashes, and a `provenance/` directory with the workflow
templates and batch receipts that produced it.

Assets are conformed to the client's target rather than stored at generation
size: backgrounds resample to the 320x200 logical surface and sprites are
trimmed to their alpha bounds and scaled to a common height, both
nearest-neighbour so the result sits on a real pixel grid.

Because staging hints live on the block rather than the asset, a pack must keep
the same names and roughly the same composition. The spaceport pack retains the
source staging layouts for exactly this reason, so `media_x` placement and the
clerk's flip stay correct across both.

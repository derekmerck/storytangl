# Grand Grotto

A Colossal Cave-inspired sandbox demo of movement, light, inventory, and
spatial affordances. Start the `adventure_sandbox_slice` world in a StoryTangl
client.

The world loads its asset definitions as a catalog before any story is created.
Each story creates its own mutable tokens. JSON restoration recovers those graph
nodes and their state, but does **not** yet restore location, player, or container
custody: holder asset maps are excluded from persistence. A restored inventory is
therefore not yet a playable continuation; the custody contract is tracked under
[issue #641](https://github.com/derekmerck/storytangl/issues/641).

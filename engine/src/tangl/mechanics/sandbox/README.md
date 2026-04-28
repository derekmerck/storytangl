`tangl.mechanics.sandbox`
=========================

`tangl.mechanics.sandbox` is the incubating family for dynamic scene-location
hubs.

The package does not introduce a second interaction model. Sandbox locations
generate ordinary StoryTangl `Action` choices from scoped state such as location
links, present entities, inventory, world time, and schedules.

Current first-pass surface:

- `SandboxScope`: a chapter-like ancestor that donates sandbox rules to child
  locations and exposes a lightweight player asset holder.
- `SandboxLocation`: a `MenuBlock` facade with location links, simple local
  lockables, and held assets.
- `SandboxInventory`: a ready-at-hand `HasAssets` holder used by sandbox scopes
  for player inventory in the first slice.
- `SandboxLockable`: a tiny local fixture for locked doors, grates, and similar
  objects that can project unlock choices.
- `WorldTime`: deterministic derived time from `world_turn`.
- `ScheduleEntry` / `Schedule` / `ScheduledEvent` / `ScheduledPresence`: small
  schedule matching primitives.
- `project_sandbox_location_links`: planning handler that projects movement
  links into normal dynamic actions, unless a manual action already covers that
  direction/target.
- `project_sandbox_asset_actions`: planning handler that projects present assets
  as take/read choices and player-held assets as drop choices.
- `project_sandbox_wait`: planning handler that projects wait as a normal
  self-loop choice.
- `project_sandbox_scheduled_events`: planning handler that projects matching
  scheduled events and concept-provider events as normal dynamic actions.
- `project_sandbox_unlocks`: planning handler that projects locked local objects
  as self-loop unlock choices with normal edge availability, effects, and
  selected-action journal text.
- `advance_sandbox_time_on_wait`: update handler that advances sandbox-local
  time when a wait choice is selected.

The wait action intentionally mirrors the `tangl.mechanics.games` self-loop
pattern: planning creates a dynamic `Action`, the action targets the current
node, selected payload is read during UPDATE, and normal ledger/journal behavior
does the rest.

Scheduled sandbox events use the same VM edges. An `activation` value maps to
the same `Action` trigger phase used by authored story actions. A
`return_to_location` event is just an `Action` with `return_phase=PLANNING`, so
the return step reprojects the current location before journaling choices; a
`once` event is suppressed after its target has been marked visited by the
generic VM `mark_visited` handler.

Asset projection is deliberately modest. Locations are `HasAssets` holders, and
the nearest `SandboxScope.player_assets` holder stands in for ready-at-hand
player inventory. Generated take/drop actions call the normal
`AssetTransactionManager`; generated read actions emit selected-action journal
text. This is enough for keys, lamps, leaflets, and treasures in a toy
Adventure-like subset while leaving graph-backed ownership relations for a
later asset slice.

Concept providers can opt in by exposing `get_sandbox_events(caller, ctx, ns)`.
The sandbox projector discovers those providers from the gathered namespace, so
roles, settings, locations, actors, and asset tokens can donate choices without
becoming sandbox-specific base classes.

The older `scratch/mechanics/sandbox` code remains prior art. Mine it for
calendar, schedule, mobile-actor, and event ideas, but do not promote it
directly without rederiving it against v38 contracts.

See `SANDBOX_DESIGN.md` for the current design note.

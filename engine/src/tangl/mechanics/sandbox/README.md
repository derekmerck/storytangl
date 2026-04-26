`tangl.mechanics.sandbox`
=========================

`tangl.mechanics.sandbox` is the incubating family for dynamic scene-location
hubs.

The package does not introduce a second interaction model. Sandbox locations
generate ordinary StoryTangl `Action` choices from scoped state such as location
links, present entities, inventory, world time, and schedules.

Current first-pass surface:

- `SandboxScope`: a chapter-like ancestor that donates sandbox rules to child
  locations.
- `SandboxLocation`: a thin `MenuBlock` facade with location links.
- `WorldTime`: deterministic derived time from `world_turn`.
- `ScheduleEntry` / `Schedule` / `ScheduledEvent` / `ScheduledPresence`: small
  schedule matching primitives.
- `project_sandbox_location_links`: planning handler that projects movement
  links into normal dynamic actions.
- `project_sandbox_wait`: planning handler that projects wait as a normal
  self-loop choice.
- `project_sandbox_scheduled_events`: planning handler that projects matching
  scheduled events and concept-provider events as normal dynamic actions.
- `advance_sandbox_time_on_wait`: update handler that advances sandbox-local
  time when a wait choice is selected.

The wait action intentionally mirrors the `tangl.mechanics.games` self-loop
pattern: planning creates a dynamic `Action`, the action targets the current
node, selected payload is read during UPDATE, and normal ledger/journal behavior
does the rest.

Scheduled sandbox events use the same VM edges. An `activation` value maps to
the same `Action` trigger phase used by authored story actions. A
`return_to_location` event is just an `Action` with `return_phase=UPDATE`; a
`once` event is suppressed after its target has been marked visited by the
generic VM `mark_visited` handler.

Concept providers can opt in by exposing `get_sandbox_events(caller, ctx, ns)`.
The sandbox projector discovers those providers from the gathered namespace, so
roles, settings, locations, actors, and asset tokens can donate choices without
becoming sandbox-specific base classes.

The older `scratch/mechanics/sandbox` code remains prior art. Mine it for
calendar, schedule, mobile-actor, and event ideas, but do not promote it
directly without rederiving it against v38 contracts.

See `SANDBOX_DESIGN.md` for the current design note.

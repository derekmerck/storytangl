`tangl.mechanics.sandbox`
=========================

`tangl.mechanics.sandbox` is the incubating family for dynamic scene-location
hubs.

The package does not introduce a second interaction model. Sandbox locations
generate ordinary StoryTangl `Action` choices from scoped state such as location
links, present entities, inventory, world time, and schedules.

Current first-pass surface:

- `SandboxLocation`: a thin `MenuBlock` facade with location links.
- `WorldTime`: deterministic derived time from `world_turn`.
- `ScheduleEntry` / `Schedule` / `ScheduledEvent`: small schedule matching
  primitives.
- `project_sandbox_location_links`: planning handler that projects movement
  links into normal dynamic actions.
- `project_sandbox_wait`: planning handler that projects wait as a normal
  self-loop choice.
- `project_sandbox_scheduled_events`: planning handler that projects matching
  scheduled events as normal dynamic actions.
- `advance_sandbox_time_on_wait`: update handler that advances sandbox-local
  time when a wait choice is selected.

The older `scratch/mechanics/sandbox` code remains prior art. Mine it for
calendar, schedule, mobile-actor, and event ideas, but do not promote it
directly without rederiving it against v38 contracts.

See `SANDBOX_DESIGN.md` for the current design note.

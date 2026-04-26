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
- `ScheduleEntry` / `Schedule`: small schedule matching primitives.
- `project_sandbox_location_links`: planning handler that projects movement
  links into normal dynamic actions.

The older `scratch/mechanics/sandbox` code remains prior art. Mine it for
calendar, schedule, mobile-actor, and event ideas, but do not promote it
directly without rederiving it against v38 contracts.

See `SANDBOX_DESIGN.md` for the current design note.

`tangl.mechanics.sandbox`
=========================

`tangl.mechanics.sandbox` is the incubating family for dynamic scene-location
hubs.

The package does not introduce a second interaction model. Sandbox locations
generate ordinary StoryTangl `Action` choices from scoped state such as location
links, present entities, inventory, world time, and schedules.

Sandbox is a specialized instance of a broader StoryTangl pattern: scoped
containers publish facts, children pull on those facts through dependencies and
phase handlers, and the runtime renders the result as namespace entries,
journal fragments, choices, effects, or projection filters. In this package the
facts are location-centered: exits, assets, fixtures, light, schedules, and
presence.

Current first-pass surface:

- `SandboxScope`: a chapter-like ancestor that donates sandbox rules to child
  locations and exposes a lightweight player asset holder.
- `SandboxLocation`: a `MenuBlock` facade with location links, simple local
  lockables, and held assets.
- `SandboxExit`: an optional structured link declaration for custom egress
  text, message exits, and fixture-gated traversal while preserving the simple
  `direction -> target` table form.
- `SandboxInventory`: a ready-at-hand `HasAssets` holder used by sandbox scopes
  for player inventory in the first slice.
- `SandboxLockable`: a tiny local fixture for locked doors, grates, and similar
  objects that can project unlock choices.
- `SandboxVisibilityRule` / `SandboxProjectionState`: a small projection filter
  for rules such as darkness that change what a location can truthfully reveal.
- `WorldTime`: deterministic derived time from `world_turn`.
- `ScheduleEntry` / `Schedule` / `ScheduledEvent` / `ScheduledPresence`: small
  schedule matching primitives.
- `project_sandbox_location_links`: planning handler that projects movement
  links into normal dynamic actions, unless a manual action already covers that
  target. Direction aliases such as `n`, `s`, `e`, `w`, `u`, and `d` are
  normalized into canonical UI hints while preserving the raw authored key.
- `project_sandbox_asset_actions`: planning handler that projects present assets
  as take/read choices and player-held assets as drop choices.
- `project_sandbox_fixture_actions`: planning handler that projects openable
  local fixtures as open/close choices.
- `project_sandbox_wait`: planning handler that projects wait as a normal
  self-loop choice.
- `project_sandbox_scheduled_events`: planning handler that projects matching
  scheduled events and concept-provider events as normal dynamic actions.
- `project_sandbox_unlocks`: planning handler that projects locked local objects
  as self-loop unlock choices with normal edge availability, effects, and
  selected-action journal text.
- `compose_sandbox_visibility_journal`: compose handler that can substitute a
  darkness-style journal fragment when projection rules suppress the location
  description.
- `advance_sandbox_time_on_wait`: update handler that advances sandbox-local
  time when a wait choice is selected.

The wait action intentionally mirrors the `tangl.mechanics.games` self-loop
pattern: planning creates a dynamic `Action`, the action targets the current
node, selected payload is read during UPDATE, and normal ledger/journal behavior
does the rest.

Structured sandbox exits are still ordinary actions. A link such as
`down: {through: grate, to: below_grate}` projects movement whose availability
is gated by the local fixture's open state. A link such as
`down: {kind: message, journal: "You don't fit!"}` projects a self-loop with
selected-action journal text.

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

Visibility projection is also deliberately modest. A scope or location can
carry `SandboxVisibilityRule`s. The default rule models Adventure-like darkness:
when the location is not lit and the player has no lit light source, the rule
substitutes a dark journal fragment and suppresses local asset/fixture
affordances. Carried light-source assets still project a turn-on/turn-off
self-loop action, so a lamp can restore normal room detail and object choices
without treating darkness as a movement gate.

The Adventure import goal is semantic compression, not faithful emulation. A
compact world schema should declare locations, exits, assets, fixtures, mobs,
world concepts, traits, and initial state; reusable sandbox handlers and narrow
world authorities should turn those declarations into behavior. That keeps
object declarations as semantic facts like `portable`, `lockable`,
`provides_light`, or `requires_charge` rather than miniature behavior scripts.
The first hand-compiled slice lives in
`engine/tests/mechanics/test_sandbox_adventure_slice.py`.

Base sandbox links are explicit and one-way. Do not infer reverse exits here:
old IF maps often use one-way travel, weird loops, and conditional returns. A
future `GridSandbox` specialization can add RPG-map-style symmetric adjacency
defaults for tile or grid worlds without changing the base sandbox contract.

Concept providers can opt in by exposing `get_sandbox_events(caller, ctx, ns)`.
The sandbox projector discovers those providers from the gathered namespace, so
roles, settings, locations, actors, and asset tokens can donate choices without
becoming sandbox-specific base classes.

Generated sandbox actions carry provenance in `ui_hints`: the projection
`source`, contribution kind, source label/kind, and sandbox scope. This is still
local metadata rather than a general VM receipt model, but it keeps dynamic
choices explainable and leaves a clear promotion path if non-sandbox systems
need the same debug surface.

The older `scratch/mechanics/sandbox` code remains prior art. Mine it for
calendar, schedule, mobile-actor, and event ideas, but do not promote it
directly without rederiving it against v38 contracts.

See `SANDBOX_DESIGN.md` for the current design note.

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
  fixtures, and held assets.
- `SandboxExit`: an optional structured link declaration for custom egress
  text, message exits, and fixture-gated traversal while preserving the simple
  `direction -> target` table form.
- `SandboxInventory`: a ready-at-hand `HasAssets` holder used by sandbox scopes
  for player inventory in the first slice.
- `SandboxFixture`: a place-bound object composed from typed facets such as
  `OpenableFacet` and `LockableFacet`.
- `OpenableFacet` / `LockableFacet` / `SwitchableFacet` / `LightSourceFacet` /
  `ContainerFacet`: runtime capability surfaces lowered from compact authoring
  traits.
- `ChargeFacet`: a first tick-compatible observer facet housed here while the
  sandbox simulation seam is being proven. It is a useful template for
  consumption mechanics, but not part of sandbox's core identity.
- `SandboxMob`: a graph-backed actor-like concept with stable location and
  mutable state that can project affordances when present.
- `SandboxInteraction`: a sponsored local choice that lowers to an ordinary
  `Action` with target, activation, optional call/return, availability,
  effects, selected-action journal text, and provenance hints.
- `SandboxSliceCompiler`: an experimental compact-slice compiler that lowers
  trait-bearing sandbox facts into a runtime `StoryGraph` for pressure tests.
- `SandboxVisibilityRule` / `SandboxProjectionState`: a small projection filter
  for rules such as darkness that change what a location can truthfully reveal.
- `WorldTime` / `SandboxClockPolicy` / `SandboxTimeCost`: normalized clock and
  action-duration vocabulary. Authoring layers may speak in minutes, periods,
  turns, oil, or watts, but runtime sandbox ticking consumes normalized integer
  counters.
- `ScheduleEntry` / `Schedule` / `ScheduledEvent` / `ScheduledPresence`: small
  schedule matching primitives. `ScheduledEvent` is a time/presence gate over
  the same sponsored interaction surface used by locations, mobs, assets, and
  fixtures.
- `project_sandbox_location_links`: planning handler that projects movement
  links into normal dynamic actions, unless a manual action already covers that
  target. Direction aliases such as `n`, `s`, `e`, `w`, `u`, and `d` are
  normalized into canonical UI hints while preserving the raw authored key.
- `project_sandbox_asset_actions`: planning handler that projects present assets
  as take/read choices, player-held assets as drop choices, and present/carried
  asset interactions as ordinary choices.
- `project_sandbox_fixture_actions`: planning handler that projects openable
  local fixtures as open/close choices and fixture interactions as ordinary
  choices.
- `project_sandbox_mob_actions`: planning handler that projects present mob
  affordances and interactions as ordinary choices.
- `project_sandbox_location_interactions`: planning handler that projects active
  location-sponsored interactions as ordinary choices.
- `project_sandbox_wait`: planning handler that projects wait as a normal
  self-loop choice.
- `project_sandbox_scheduled_events`: planning handler that projects matching
  scope, location, mob, asset, fixture, and concept-provider scheduled events
  through the normal sponsored interaction path.
- `project_sandbox_unlocks`: planning handler that projects locked local objects
  as self-loop unlock choices with normal edge availability, effects, and
  selected-action journal text.
- `compose_sandbox_visibility_journal`: compose handler that can substitute a
  darkness-style journal fragment when projection rules suppress the location
  description.
- `advance_sandbox_time_on_action`: update handler that advances sandbox-local
  time for selected sandbox actions and invokes the domain-local sandbox tick
  chain.
- `tangl.mechanics.sandbox.incremental`: optional adapter that lets hosted
  `IncrementalGame` blocks project allocation choices into a sandbox location
  and resolve production/upkeep as a sandbox tick observer.
- `tangl.mechanics.sandbox.story_info.SandboxStoryInfoProjector`: optional
  adapter for the existing service story-info seam. It projects disclosed
  sandbox state into ordinary `ProjectedState` sections for clients that want
  status rails, inventory panels, map modals, or ebook-style summaries.

The wait action intentionally mirrors the `tangl.mechanics.games` self-loop
pattern: planning creates a dynamic `Action`, the action targets the current
node, selected payload is read during UPDATE, and normal ledger/journal behavior
does the rest.

Sandbox time is a normalized runtime counter. A scope-level
`SandboxClockPolicy` defines default durations by action kind; generated actions
may carry `SandboxTimeCost` to override or explicitly set zero duration. The
compiler owns conversion from world units such as "15 minutes" or "one period"
into normalized action duration. Journal and story-info projection own the
reverse conversion back into reader-facing clock labels. Runtime code should not
solve dimensional analysis.

Sandbox ticking is a domain-local refinement of VM UPDATE, not a new VM phase.
Selected-edge and node UPDATE effects run first; then
`advance_sandbox_time_on_action` advances the sandbox clock and calls the
sandbox tick chain once per normalized tick. Current tick consumers include
charged assets. Future consumers such as hazards, deadlines, mobile actors, or
queueing simulation events should attach to the same chain rather than adding a
parallel update loop.

The tick chain is an observation seam, not a list of sandbox-owned mechanics.
Sandbox owns the scoped clock, action-duration interpretation, and invitation to
observe time advancing. A hosted mechanic owns its own meaning: charges own
resource counters and consumption predicates; an incremental game owns
allocation, upkeep, and production; a queueing simulator owns arrivals,
service, and utilization. Each can be run manually outside a sandbox or
registered as a sandbox tick consumer when hosted in a world with scoped time.

Current tick observers bridge into JOURNAL with small local stashes. That should
be treated as scaffolding: effect-phase content wants a phase-local receipt or
context slot, not persistent `locals`, so transient render material does not
become serialized story state.

Structured sandbox exits are still ordinary actions. A link such as
`down: {through: grate, to: below_grate}` projects movement whose availability
is gated by the local fixture's open state. A link such as
`down: {kind: message, journal: "You don't fit!"}` projects a self-loop with
selected-action journal text.

Scheduled sandbox events use the same VM edges and interaction payloads. The
schedule fields decide whether the affordance is primed at the current
`WorldTime`, location, and actor-presence set. After that, `target`,
`activation`, `return_to_location`, `availability`, `effects`, and
`journal_text` follow the same `SandboxInteraction` path as any other sponsored
choice. A `once` event is suppressed after its target has been marked visited by
the generic VM `mark_visited` handler.

Asset projection is deliberately modest. Locations are `HasAssets` holders, and
the nearest `SandboxScope.player_assets` holder stands in for ready-at-hand
player inventory. Generated take/drop actions call the normal
`AssetTransactionManager`; generated read actions emit selected-action journal
text. This is enough for keys, lamps, leaflets, and treasures in a toy
Adventure-like subset while leaving graph-backed ownership relations for a
later asset slice.

Container projection is the first transfer-preflight extension. A
`ContainerFacet` can sit on a fixture or portable asset. Fixture containers use
the fixture's open/locked state before exposing contents; portable containers
carry their own open state. Generated put/take-from actions still move tokens
through `AssetTransactionManager`, so capacity, trait acceptance, closed
containers, and the current no-nested-containers rule are transaction policy
rather than a second inventory path.

Visibility projection is also deliberately modest. A scope or location can
carry `SandboxVisibilityRule`s. The default rule models Adventure-like darkness:
when the location is not lit and the player has no lit light source, the rule
substitutes a dark journal fragment and suppresses local asset/fixture
affordances. Carried light-source assets still project a turn-on/turn-off
self-loop action, so a lamp can restore normal room detail and object choices
without treating darkness as a movement gate.

Charged assets are normalized counters. A `requires_charge` compact trait lowers
to a `ChargeFacet` with current/max charge, consumption trigger, optional
predicate, warnings, and exhaustion text. Lit charged assets keep consuming
charge during sandbox ticks even when left offscreen. Exhaustion mutates the
asset state globally, while journal text is emitted only when the event is
observable from the current location.

This charge support is intentionally parasitic on sandbox time. Flashlight
batteries, lamp oil, oxygen tanks, ammunition drip, cooldowns, fatigue, and
similar counters are better understood as consumption mechanics that can observe
ticks than as sandbox primitives. If the same counter logic becomes useful in
non-sandbox contexts, promote the generic counter/consumption vocabulary out of
`mechanics.sandbox` and leave only the sandbox tick adapter here.

The incremental-game adapter follows the same rule. `IncrementalGameHandler`
owns allocation, production, upkeep, and cycle resolution. The sandbox adapter
only discovers hosted incremental blocks under the active `SandboxScope`,
projects their available moves as ordinary self-loop sandbox actions, and calls
the handler's cycle operation when sandbox time ticks. The same game can still
run manually in a modal `HasGame` block without sandbox.

Mob projection is schedule/presence plus simple asset holding. `SandboxScope.mobs`
holds stable `SandboxMob` nodes, each with a fallback sandbox location label,
optional `Schedule`, and the story-level `HasAssets` facet. At projection time
the mob's effective location is derived from `WorldTime`; when that location
matches the current sandbox location, its present description, authored mob
affordances, and player/mob asset transfers become ordinary sandbox actions.
Scheduled mobs also count as present actors for scheduled-event gates. This
establishes a runtime home for offscreen actors without adding pathing, fleeing,
combat, trade negotiation, or lazy dialog scene generation yet.

Sponsored interactions are the first shared local-choice surface. A
`SandboxInteraction` lowers to a normal `Action` edge with target, activation,
optional call/return, availability, effects, selected-action journal text, and
provenance hints. Present mobs and active locations can sponsor these
interactions, as can present/carried assets and reachable fixtures. This is a
sandbox instance of a broader StoryTangl pattern: a concept that is in scope can
sponsor a choice without owning a separate runtime.

The Adventure import goal is semantic compression, not faithful emulation. A
compact world schema should declare locations, exits, assets, fixtures, mobs,
world concepts, traits, and initial state; reusable sandbox handlers and narrow
world authorities should turn those declarations into behavior. That keeps
object declarations as semantic facts like `portable`, `lockable`,
`provides_light`, or `requires_charge` rather than miniature behavior scripts.
Those traits are authoring compression: the compiler lowers them into typed
runtime facets, and handlers project ordinary StoryTangl actions from the
facets.
The compact compiler pressure test lives in
`engine/tests/mechanics/test_sandbox_adventure_slice.py` and runs through
`SandboxSliceCompiler`. A playable world-bundle version lives in
`worlds/adventure_sandbox_slice`; it declares the map as ordinary near-native
world blocks and uses a small domain setup handler to attach the shared scope,
assets, fixtures, and pirate. The compiler is intentionally below the full
loader stack: future codecs can decode source formats into the compact slice
schema, and later world-bundle integration can decide how much of this should
become a shared story/world compiler layer.

The compact schema can also declare materialization policy. The current sandbox
slice compiler is allowed to be fully eager: declared locations, assets, and
fixtures become real runtime objects immediately. That is the simplest fit for
offscreen simulation, where a scheduled mob, parked actor, mutable treasure
cache, or timed fixture needs a runtime home before the player observes it.
Hints such as `scope.materialization.stable` and per-concept
`runtime_identity.stable` name the concepts that must remain addressable if a
future loader uses a hybrid policy. In that future shape, stable sandbox state
can be eager while optional encounter/dialog scenes are created lazily from the
current relationship and world state when the player invokes them.

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

Projected state is a disclosed-status surface, not world truth. The optional
service projector emits only generic `kv_list` and `item_list` sections such as
current location, world time, player inventory, visible local assets, visible
fixtures, visible mobs, and visible exits. Darkness and other visibility rules
filter that surface the same way they filter local affordances. Hidden mobs,
undisclosed schedules, secret exits, and puzzle truth stay backend-only.

Humane sandbox design matters. Sandboxes are useful because they let a story
project ordinary choices into spatial, temporal, and social terms: where to go,
who is present, what is ready at hand, and what opportunities are currently
discoverable. They become tedious when that projection degrades into "hunt for
the event" clicking. Empty travel, stochastic search, or repeated ritual should
exist only when it is doing narrative or game work: tension, uncertainty,
resource pressure, rule discovery, optimization, or atmosphere. Otherwise the
world should prune dead space, bias or move interesting affordances toward the
reader, close irrelevant routes, or summarize repeated traversal as a
macro-affordance with the same authoritative costs and risks.

Ritual is allowed to be meaningful. Dice rolls, travel montages, repeated
searches, farming loops, and other ceremonies can help a player feel suspense
or effort even when the backend already owns the authoritative outcome. But the
ritual should be skippable or summarizable once repetition stops serving
meaning, and StoryTangl mechanics should never normalize monetizing relief from
intentionally induced tedium. Premium content, tools, hosting, cosmetics, or
patronage are one thing; paywalling the removal of artificial friction is a
hostile design pattern.

The older `scratch/mechanics/sandbox` code remains prior art. Mine it for
calendar, schedule, mobile-actor, and event ideas, but do not promote it
directly without rederiving it against v38 contracts.

See `SANDBOX_DESIGN.md` for the current design note.

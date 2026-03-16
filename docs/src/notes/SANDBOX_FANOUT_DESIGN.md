# Sandbox Hubs as Fanout Operators

**Status:** 🟡 DESIGN NOTE — future direction, v38 vocabulary update
**Prior art:** `sandbox_v30.py`, `sandbox.py`, `sandbox_handler.py`, `schedule.py`
**Relevant layers:** `story.episode`, `vm.provision`, `story.fabula.materializer`

---

## Core Insight

The v3.0 "sandbox" system was an independent subsystem with its own traversal
handler, schedule evaluator, event dispatcher, and grid cursor. In v38, all of
its moving parts decompose into existing primitives:

- **SandboxNode** is a **MenuBlock** with multiple fanouts
- **SandboxEvent** is a **tagged Block** (or Scene) with availability conditions
- **MobileActor** is an **Actor** whose current location is a scheduled namespace value
- **SandboxLocation** is a **Location** with conditional admission
- **Schedule** is a **namespace provider** that publishes world-time into the condition evaluator
- **Connections** are **Action edges** between hub MenuBlocks (possibly with travel-cost effects)
- **Forced events** are **redirects** with conditions (already supported)
- **Selectable events** are **Fanout-discovered menu items** (the MenuBlock pattern)

A sandbox hub is not a new node type. It is a MenuBlock with several
concurrent fanouts operating over different provider scopes.

---

## The Hub Pattern

A sandbox location ("town square", "tavern", "crossroads") is a re-entrant
hub that dynamically composes its available choices from multiple sources
each time the cursor arrives. In v38, this is authored as:

```yaml
blocks:
  - label: town_square
    kind: MenuBlock
    content: >
      The town square bustles with activity.
      A fountain burbles in the center.
    menu_items:
      # Fanout 1: local activities at this location
      - has_tags: [activity, town_square]
      # Fanout 2: present NPCs (actors whose schedule puts them here)
      - has_tags: [conversation]
        has_ancestor_tags: [npc_present]
    actions:
      # Static connections to other hubs
      - text: "Go to the market"
        successor: market
        effects: ["world.advance_time(1)"]
      - text: "Head to the tavern"
        successor: tavern
        effects: ["world.advance_time(1)"]
```

Each `menu_items` entry becomes a `Fanout` at materialization time. When
the cursor enters the hub, the resolver gathers all eligible providers,
the provisioner projects them as dynamic `Action` edges, and the journal
handler renders them alongside the static choices. This is exactly what
`test_menu_fanout.py` validates.

---

## Discovery Channels

The v3.0 sandbox mixed three discovery mechanisms into one `events` property.
In v38, each is a separate fanout with its own selector scope:

### 1. Location Activities (place-scoped fanout)

Blocks tagged with the hub's location tag and `activity`. These are
the "things you can do here" - visit a shop, explore ruins, rest.

```yaml
# Activity block - discovered by the town_square hub
- tags: [activity, town_square]
  action_name: "Visit the blacksmith"
  content: The forge glows with heat...
  conditions: ["blacksmith_open"]
```

In v3.0 this was `HasSandboxEvents._include_selectable_events`. In v38
it's a standard fanout with `has_tags: [activity, town_square]`.

### 2. Present NPCs (schedule-gated fanout)

Actors move between locations on a schedule. Their conversation/event
blocks are only discoverable when the actor is "present" at the current
hub. In v38, this is a two-part mechanism:

**Part A - Actor presence** is a local namespace publication. The actor's
current location can be derived from its own stored schedule state and then
gathered into scoped runtime views:

```python
from tangl.core import contribute_ns


@contribute_ns
def provide_location_symbols(self):
    return {"current_location": self.locals.get("current_location")}
```

**Part B - Conversation fanout** uses the presence value as a condition.
The hub's fanout discovers blocks tagged `conversation`, and the block's
own conditions gate on the actor being present:

```yaml
- tags: [conversation]
  action_name: "Talk to the merchant"
  conditions: ["merchant.current_location == 'town_square'"]
  content: The merchant adjusts her spectacles...
```

In v3.0 this was `SandboxRole` with `sb_schedule` and
`_include_inferred_role_req`. In v38, the schedule is just data in
`locals`, the presence check is a condition expression, and discovery
is a standard fanout.

### 3. Forced Events (redirect with conditions)

Time-gated or state-gated events that preempt player choice. In v3.0
this was `SandboxEventHandler.get_redirect_event` with
`event_activation == "forced"`. In v38, these are authored as
redirects with conditions:

```yaml
- label: town_square
  redirects:
    - successor: festival_scene
      conditions: ["world_time.season == 'summer' and world_time.day == 1"]
```

No fanout needed - this is static compilation. The redirect fires
during the ENTER phase if its conditions are met.

---

## World Time as Namespace

The v3.0 system had `WorldTime` as a dedicated model with period/day/
month/season/year. In v38, this can be published locally on the story
graph or world and then gathered into scope:

```python
from tangl.core import contribute_ns


@contribute_ns
def provide_world_time_symbols(self):
    turn = self.locals.get("world_turn", 0)
    return {
        "world_time": WorldTime.from_turn(turn),
        "world_turn": turn,
    }
```

`WorldTime` itself can be a simple dataclass or Pydantic model. It
doesn't need to be part of the graph structure - it's a derived value
from the world turn counter, which is a ledger-level concern.

The `advance_time` effect on connection actions increments the turn
counter in the ledger namespace. All schedule evaluations recompute
from the new turn value on the next provision pass.

---

## Connections and Travel

In v3.0, `SandboxNode.connection_refs` were explicit edge lists, and
`SandboxGrid` inferred connections from grid adjacency. In v38, both
patterns are supported:

**Explicit connections** are authored as static actions on the hub
MenuBlock. Travel time is an effect on the action:

```yaml
actions:
  - text: "Travel to Fort Worth"
    successor: fort_worth
    effects: ["world.advance_time(4)"]
    conditions: ["player.has_vehicle"]
```

**Grid-inferred connections** would be a compile-time step in a grid
codec or a domain-specific materializer hook. The codec reads the
grid map and emits explicit actions with computed travel costs. The
compiler sees the same dict shape either way.

---

## Anonymous Activity Blocks

Many sandbox activities are one-off interactions that don't need global
labels. These are the anonymous blocks we implemented - unlabelled
blocks with tags that the hub's fanout discovers:

```yaml
blocks:
  - label: town_square
    kind: MenuBlock
    menu_items:
      - has_tags: [activity, town_square]

  # Anonymous - discovered by tag, no label needed
  - tags: [activity, town_square]
    action_name: "Pet the dog"
    content: A friendly mutt wags its tail.

  - tags: [activity, town_square]
    action_name: "Toss a coin in the fountain"
    content: The coin glints as it sinks.
    conditions: ["player.gold > 0"]
    effects: ["player.gold -= 1", "player.luck += 1"]
```

The compiler assigns synthetic labels (`_anon_0`, `_anon_1`). The
fanout finds them by tag. The `action_name` field provides the menu
choice text via `MenuBlock.action_text_for`.

---

## Re-entrancy

The defining characteristic of a sandbox hub is re-entrancy: the player
visits, makes a choice (talk to NPC, do activity, travel), and returns
to the same hub afterward. In v3.0 this was ad-hoc logic in
`SandboxActionScript` defaulting `successor_ref` to `"return"`.

In v38, re-entrancy is a VM-level concept (call stack return) or an
authored pattern (activity block's action points back to the hub):

```yaml
# Activity that returns to the hub
- tags: [activity, town_square]
  action_name: "Rest at the inn"
  content: You take a nap...
  effects: ["player.health = player.max_health", "world.advance_time(8)"]
  actions:
    - text: "Wake up"
      successor: town_square  # explicit return
```

Or, if the hub declares `return_when_done: True` on its `menu_items`,
the VM pushes a return frame and the activity block doesn't need to
know which hub invoked it. This is the call-stack pattern and it's
cleaner for activities that multiple hubs might share.

This same pattern is broader than sandbox travel loops. It also covers
repeatable activity kernels and game-like interactions:

- a tavern hub can call into a reusable "play cards" block and return
- a workshop hub can invoke a short crafting loop and return
- a game block can project a self-fanout of move edges until a terminal result
  is reached

The shared design question is whether a revisit means:

- returning to the same provider instance,
- calling into a provider and then returning to the invoking hub, or
- materializing a fresh per-visit instance so replay and journal lineage stay
  more explicit

For sandbox-oriented hubs, the default should usually be "call and return" or
"reuse the same provider" unless a concrete story need justifies per-visit
instancing.

---

## What This Replaces

| v3.0 concept | v38 equivalent |
|---|---|
| `Sandbox` (class) | World or StoryGraph with `world_turn` in locals |
| `SandboxNode` | `MenuBlock` with fanouts |
| `SandboxEvent` | Tagged `Block` or `Scene` with conditions |
| `SandboxLocation` | `Location` concept with conditional admission |
| `SandboxRole` / `MobileActor` | `Actor` concept with schedule in locals |
| `SandboxSchedule` | Namespace provider + condition expressions |
| `WorldTime` | Derived dataclass, published locally via `get_ns()` / `@contribute_ns` |
| `SandboxConnection` | `Action` edge with travel-time effects |
| `SandboxGrid` | Grid codec producing standard hub + action topology |

---

## Why This Is Better

The old sandbox system was conceptually rich but structurally separate.
The v38 fanout interpretation is better because it:

- reuses the same provisioning and traversal machinery as everything else
- makes sandbox locations authorable in the same block/scene idiom as story hubs
- keeps schedule and availability in the condition/namespace layer
- lets newly introduced providers appear naturally without hand-editing hub menus
- supports "always something interesting where the player wants to go" by
  gathering only currently eligible events

This is not just a cleanup. It makes sandbox mechanics composable with
all the other systems already in the engine.

# Game Mechanics Design

**Status:** CURRENT REFERENCE + FUTURE FAMILY NOTE  
**Scope:** the `tangl.mechanics.games` family, its Layer 3 VM integration, and the
future game shapes still worth preserving as design intent  
**Canonical runtime surface:** `Game`, `GameHandler`, `HasGame`, package handlers,
and `create_game_block()`

---

## Core Idea

Game mechanics in StoryTangl are best understood as **re-entrant interactive
blocks**.

A game block repeatedly re-enters a recognizable continuation point, provisions
move choices from current game state, resolves one round, emits journal output,
and only exits to the wider story frontier when a terminal condition is reached.

That is why the current design fits naturally inside the VM rather than beside
it:

- moves are generated as traversable choices
- round resolution is a normal UPDATE-phase concern
- round narration is a normal JOURNAL-phase concern
- victory/defeat/draw are ordinary predicate-friendly namespace facts

This note supersedes the older migration-era scratch notes. The core framework
is no longer speculative; what remains here is the stable model plus the future
family directions that still look worth keeping.

---

## Stable Runtime Contract

The current games package revolves around a small, stable contract:

- **`Game`** holds state, score/history, and lightweight serialization-friendly data
- **`GameHandler`** is the rule object that sets up a game, offers moves, receives
  moves, resolves rounds, and evaluates terminal state
- **`HasGame`** is the author-facing facade that attaches a game to a story node
- **package handlers** connect games to VM PREREQS, PLANNING, UPDATE, JOURNAL,
  and CONTEXT phases
- **`create_game_block()`** is the ergonomic story-layer factory for the common
  "challenge block with outcome exits" pattern

This split is important:

- rule logic lives in handlers
- mutable round state lives in the game object
- narrative routing lives in the story/VM integration surface

That separation is what keeps games from turning into opaque one-off scripts.

---

## Rounds Versus Story Turns

The key modeling distinction is:

- **story turn**: one traversal step through the wider narrative graph
- **game round**: one cycle inside a game block

Many rounds may occur while the cursor remains on one recognizable story block.
The runtime therefore needs to track both story progression and local game
progression without confusing them.

The current implementation already uses this distinction in practice:

- traversal history and step/turn helpers belong to the VM
- game round state belongs to the game family
- round outcomes are projected back outward through journal and namespace hooks

---

## Phase Mapping

Games fit into the existing VM pipeline rather than introducing a second hidden
subsystem.

| VM phase | Game role |
|---|---|
| **PREREQS** | one-time setup on first entry when needed |
| **PLANNING** | provision currently available move choices |
| **UPDATE** | receive the chosen move and resolve one round |
| **JOURNAL** | emit round recap and score/status fragments |
| **CONTEXT** | expose `game_won`, `game_lost`, `game_draw`, round facts, and similar flags |
| **POSTREQS** | allow authored victory/defeat/draw exits to route onward |

This is the durable design insight from the longer scratch document: games do
not need a parallel engine. They are a specialized VM participant with one
highly legible re-entry shape.

---

## Taxonomy Worth Keeping

The useful taxonomy from the apocryphal design doc is still worth preserving,
even though only part of it is implemented today.

### Player Relationship

- **solo**: player versus environment or house
- **competitive**: player versus opponent
- **cooperative**: players together versus environment
- **multiple**: more than two participants or mixed incentives

### State Model

- **simple**: no persistent equipment or field state
- **token**: fungible markers or counts
- **picking**: targets versus distractors or validation patterns
- **card**: ordered unique markers with rank/suit-like semantics
- **board**: positional token state
- **incremental**: resource evolution over repeated rounds

### State Dependency

- **state-independent** rounds such as classic RPS
- **state-dependent** games where cumulative history matters

This taxonomy is more useful than a deep inheritance tree. It gives the family
a vocabulary for future expansion without forcing premature abstraction.

---

## What Is Implemented Today

The current package already proves the family shape:

- simple competitive games are real, not hypothetical
- self-loop move provisioning works in the VM
- journaling and predicate exposure work end to end
- outcome exits route cleanly through authored story blocks

The clearest reference example remains the RPS family and its integrated world
fixture. That reference is sufficient to keep the current architecture honest.

---

## Future Shapes Still Worth Preserving

The longer design note contained several future directions that still seem
valuable, even though they are not commitments:

- **token games** such as Nim or marker-exchange contests
- **picking/verification games** such as inspection or credential checks
- **card games** with ordered hands, decks, and discard logic
- **incremental games** where generators or resources evolve over rounds
- **aggregate-force or winding-RPS battles** where the interesting part is the
  composition of a hand or force rather than one atomic throw

These are worth keeping because they stress different aspects of the family:

- richer runtime state
- more complex move generation
- stronger crossover with progression, assets, and provisioning
- more elaborate journal projection

None of them require changing the core contract first. They mostly require
implementing new kernels and handlers against the existing family surface.

---

## Integration With Other Mechanic Families

Games are not an island. The most promising crossover points are:

- **progression**: stats, situational modifiers, and task-style resolution can
  affect move outcomes or difficulty
- **assembly / assets**: equipment, decks, or token pools can become game setup inputs
- **presence / media**: opponent tells, revealed cards, or board state can project
  into prose or media surfaces

The important design constraint is that these remain explicit integrations.
Game handlers should ask for the inputs they need; they should not quietly
smuggle writeback or progression logic into opaque side effects.

---

## Non-Goals

This design does not imply:

- a separate mini-engine outside the VM
- a mandatory deep subtype hierarchy for every game shape
- hidden continuous simulation
- real-time or twitch mechanics support
- multiplayer support as a prerequisite for expanding the family

Those may become relevant later, but they are not needed to justify the current
family architecture.

---

## Review Questions

When extending `tangl.mechanics.games`, the best review questions are:

1. Does the new game keep rule logic in the handler and state in the game object?
2. Does it fit the re-entrant block model cleanly?
3. Does it expose player-facing consequences through journal and namespace rather
   than private internals?
4. Does it compose explicitly with progression, assets, or provisioning instead
   of bypassing those systems?
5. Is the new shape genuinely a new family member, or is it just a one-off world script?

If those answers stay clear, the family can grow without losing the elegance of
the current reference implementation.

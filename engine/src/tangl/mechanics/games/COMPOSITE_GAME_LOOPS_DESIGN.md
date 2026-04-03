# Composite Game Loops Design

**Status:** DRAFT FAMILY NOTE  
**Scope:** composite mechanics built by nesting or sequencing simpler
`tangl.mechanics.games` kernels inside one larger authored loop  
**Motivating scratch references:** `scratch/mechanics/games/incremental/incremental.py`,
`scratch/mechanics/games/token_games/bag_rps.py`, and the broader scratch
subpackage ontology

---

## Why This Note Exists

Some of the most interesting authored systems are not one game kernel pushed to
its limit. They are **compositions**:

- an outer shell that manages long-term pressure and resource state
- one or more inner contests that resolve short-term tactical or dramatic spikes
- rewards, losses, and unlocks that flow back into the outer shell

This was always implicit in the older taxonomy. The point of separating simple,
token, card, incremental, and perception families was not merely classification.
It was to make it possible to build larger loops by combining those families in
deliberate ways.

---

## Core Idea

A composite loop is best understood as **shell + spikes**.

### Shell

The shell is the long-running stateful loop:

- resource growth
- upkeep or overhead
- worker allocation
- building and unlock progression
- collection, sorting, hoarding, or training
- promotion or conversion choices
- long-term win/lose pressure

This is usually incremental, but not always.

### Spikes

The spikes are shorter sub-contests entered at specific moments:

- a bag-RPS challenge
- a corridor contest
- a picking or credential check
- a one-hand card showdown

These are not side minigames in the architectural sense. They are explicit
sub-loops whose outcomes matter because they feed back into the shell.

---

## Other Familiar Shapes

The colony example is not the only recognizable instance of this pattern.

### Collectible / Training Shells

Collectible card and monster games often use the same architecture:

- an outer loop of discovery, capture, collection, sorting, training, and deck
  or roster construction
- a focused contest loop that tests the current build
- battle outcomes that feed back into what can be collected, trained, evolved,
  or challenged next

Trading card games, creature collection games, and similar systems are often
best understood this way: the contest is only one part of the larger mechanic.
The outer collection and preparation loop is just as structurally important.

### RPG Overworld / Battle Structure

Many RPGMaker-style games are also a shell-and-spikes composition:

- an overworld loop where the player explores, discovers resources, talks to
  NPCs, unlocks routes, gathers gear, and trains
- battle encounters that consume and test those accumulated resources
- victory outcomes that gate further exploration, materials, story beats, or
  mobility options

So the composite-loop pattern is not niche. It describes a very common way of
structuring game interactions across genres.

---

## Motivating Colony Example

One concrete version of this pattern is a colony-management loop:

- a queen creates mandatory overhead
- workers can be assigned to foraging, queen care, infrastructure, or promotion
- forage options are gated by unlocks and geography
- infrastructure is gated by resources and in turn gates later actions
- promotion converts generic workers into typed force
- typed force participates in aggregate-force contests
- contest outcomes produce attrition, loot, unlocks, tribute, or deposition

In the colony skin described so far:

- **generic tokens** are workers
- **resource gates** constrain where and how workers can forage
- **overhead** rises as the colony grows because the queen becomes hungrier or greedier
- **promotion** turns workers into `spies (paper)`, `guards (rock)`, or
  `soldiers (scissors)`
- **upgrades** can increase token weight above `1` for aggregate-force purposes
- **victorious contests** can yield both immediate rewards and long-term tribute
- **terminal failure** can mean external defeat or internal collapse when the
  queen devours the colony

This is a strong example because it makes the compositional idea obvious:
incremental labor management, conversion, aggregate-force contest, and strategic
unlock pacing are all present at once.

It is also a good reminder that "resources" need not mean only currency. In
other worlds the shell may revolve around a deck, a creature roster, a party, a
stable of trained specialists, or some other curated stock of capabilities.

---

## Composition Rather Than Exception Logic

The right design lesson is not "build one giant special colony game." The right
lesson is:

- identify the constituent kernels
- decide which one owns long-term state
- make the others explicit sub-loops
- route results back through ordinary state updates

For the colony example, the constituent kernels are:

- **incremental shell** for labor, upkeep, unlocks, and production
- **conversion kernel** for promoting generic workers into typed force
- **aggregate-force contest** for colony-versus-colony encounters
- optionally **picking / corridor / card** spikes for diplomacy, scouting, or rituals

That is exactly the sort of "reduce richer interactions to combinations of
simpler ones" thinking the original taxonomy was trying to support.

---

## Policy Axes

Many of the most important design questions for a composite loop do not change
the underlying kernel. They are **world-policy choices**.

For the colony pattern, all of these may reasonably vary by world:

- whether labor and combat bodies are literally the same tokens
- whether committed force is consumed, tied up temporarily, or mostly recoverable
- whether promotions are permanent, reversible, or stance-like
- whether typed force requires upkeep
- whether challenge windows are fixed, threshold-triggered, or player-initiated
- whether rewards are immediate loot, unlocks, tribute streams, map access, or
  deposition rights
- whether losses cause only attrition, or also social or economic penalties

The important implication is: the live family should expose these as policy
knobs and state transitions, not bake one answer into the kernel.

---

## Recommended Runtime Shape

For StoryTangl, the cleanest shape is:

1. **Outer re-entrant block**
   Runs the shell loop, updates economy state, and provisions macro actions.
2. **Challenge entry**
   A choice from the shell enters a dedicated contest block with explicit stakes.
3. **Contest resolution**
   The subgame resolves using its own handler and journal projection.
4. **Outcome application**
   Rewards, attrition, tribute, unlocks, or routing consequences are written
   back to shell state through ordinary updates.
5. **Return to shell**
   The larger loop continues until a terminal shell condition is reached.

That keeps each kernel understandable and lets authored worlds decide how hard
the boundary between shell and spike should feel.

---

## Why Not One Monolithic Kernel

A monolithic implementation would blur several distinct concerns:

- economy pacing
- tactical commitment
- attrition math
- unlock structure
- diplomacy or tribute policy
- authored dramatic cadence

That would make the system harder to reason about and harder to reuse.

By contrast, a composite design lets us say:

- the shell owns resource and progression truth
- contest blocks own tactical exchange truth
- authored story logic decides what outcomes unlock or route

That matches the current `HasGame` architecture much better than a giant
all-purpose meta-engine.

---

## What The Live Package Might Need

This pattern is a good argument for a few reusable kernels rather than one
infinite `Game` abstraction:

- `IncrementalGame` for recurring production, upkeep, and allocation
- `AggregateForceGame` for pooled typed-force contests
- `CorridorGame` for shared-threshold pressure contests
- `PickingGame` for inspect/reveal/identify loops
- and, at the shell level, some notion of collection/training or expeditionary
  progression when the outer loop is not purely economic

Then larger authored systems become combinations of those kernels rather than
special frameworks.

The outer shell may also need explicit support for:

- snapshotting or staking tokens into sub-contests
- applying structured reward payloads on return
- marking one-time unlocks versus recurring tribute
- exposing shell state and contest state together in journal and namespace

---

## Authoring Constraints

When building composite loops in the live package:

1. Keep the shell legible on its own.
2. Make contest entry explicit and intentional.
3. Keep stake transfer and reward transfer explicit in state.
4. Avoid hidden nested engines with opaque side effects.
5. Let different worlds choose different policies for recovery, tribute,
   promotion permanence, and upkeep.

If those constraints hold, composite loops can stay expressive without becoming
unreadable.

---

## Narrative Value

Composite loops are especially useful when the story wants both:

- a sense of long-term stewardship, accumulation, or decline
- and punctuated moments of tactical confrontation

That makes them a natural fit for colonies, courts, gangs, cults, expeditions,
companies, insurgencies, collectible training stories, and RPG-style overworlds
where preparation and confrontation feed each other over time.

In other words, they are not an edge case. They are one of the main reasons to
have a compositional mechanics taxonomy at all.

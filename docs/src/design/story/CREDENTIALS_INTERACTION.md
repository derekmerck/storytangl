# Credentials Interaction and Picking-Game Pattern

**Document Version:** 0.1  
**Status:** DESIGN NOTE - consolidated from scratch prototypes and v38 planning  
**Prior art:** `scratch/mechanics/credentials/README.md`,
`scratch/mechanics/credentials/notes.md`,
`scratch/mechanics/credentials/credential.py`,
`scratch/mechanics/credentials/credentialed.py`,
`scratch/mechanics/credentials/screening.py`,
`scratch/mechanics/credentials/credential_script_models.py`,
`scratch/mechanics/credentials/credentials-2/cred_check_game.py`  
**Relevant layers:** `tangl.mechanics.games`, `tangl.story.episode`,
`tangl.story.fabula`, `tangl.journal`

---

## Problem Statement

The "credentials" mechanic is StoryTangl's recurring sketch for a Papers
Please-style interaction:

- a candidate appears with some presented facts and documents
- the world exposes current rules or restrictions
- some information may be hidden, forged, incomplete, or false
- the player investigates discrepancies
- the player chooses a final disposition such as allow, deny, or arrest

Several iterations explored this space, but each mixed together too many
concerns:

- candidate generation
- credential packet modeling
- puzzle interaction
- scene/challenge flow
- media rendering
- narrative extras like bribes or threats

This note consolidates those ideas into a cleaner v38 direction.

---

## Core Insight

At heart, the credentials interaction is a **spot-the-difference / inspect and
reveal puzzle**.

The player compares:

- authored or generated rules
- candidate presentation
- hidden underlying truth

and uses a small set of inspection moves to discover whether the presentation is
consistent.

Only after that does the player make a final disposition.

That means the mechanic should not start as a giant credential simulation or a
special scene framework. It should start as a **small interactive game block**
with repeated inspect / pass / disposition choices.

---

## What the Scratch Iterations Established

### 1. The candidate packet model is useful

The early credential models established a strong domain vocabulary:

- `origin`
- `purpose`
- `contraband`
- required credential types
- visible presentation versus hidden truth
- invalid, missing, forged, or hidden credentials

That remains useful and should survive into any modern implementation.

### 2. Disposition is not the only state

The scratch notes and enums made an important distinction between:

- real underlying status
- presented or partially revealed status
- disposition chosen by the player

This is what gives the interaction texture.

The game is not merely "pick allow or deny." The player progressively uncovers
or confirms discrepancies before making that decision.

### 3. Mediation is a second layer, not the first layer

Older iterations also modeled:

- request missing credential
- request search
- verify holder identity
- relinquish contraband
- blacklist / whitelist overrides

These are good ideas, but they are second-pass mechanics.

The first playable implementation does not need all of them.

### 4. Later iterations were already converging on `PickingGame`

The `credentials-2` sketch explicitly reframed the interaction as a
`PickingGame`.

That is the cleanest interpretation:

- the player is shown a field of inspectable evidence
- some picks are distractors
- some picks reveal meaningful findings
- some follow-up moves become available after a finding
- one terminal move finalizes the case

---

## Why the Old Scene / Challenge Model Should Not Return

Older versions used custom challenge scenes, round objects, and attrs-based
action classes to hold the whole mechanic together.

That was reasonable before the current v38 block/VM patterns existed, but it is
too heavy now.

In v38, this should be modeled using ordinary story infrastructure:

- a block that owns game state
- `HasGame` lifecycle integration
- normal planning / update / journal phases
- optional normal story edges for aftermath or repetition

This keeps the mechanic aligned with other interactive story nodes instead of
reintroducing a parallel challenge framework.

---

## Recommended v38 Shape

### Story-facing block

Create a normal story block type, something like:

- `CredentialCheckBlock(HasGame, Block)`

This block is where the cursor sits during the interaction.

### Game state

The embedded game should hold the full case state:

- current rules or restriction map
- candidate truth
- candidate presentation
- visible evidence items
- revealed findings
- current case status
- final decision, if any

### Handler

A game handler should:

- initialize the case on first visit
- determine available inspect / reveal / disposition moves
- apply one move at a time
- update current findings and case status
- determine whether the case is still in progress or terminal

### Journal

Journal output should narrate:

- what the player inspected
- what was revealed or confirmed
- what the candidate said or did in response
- the current standing of the case

---

## Start Smaller Than "Papers Please"

The clean implementation path is incremental.

### Phase 1: simple spot-the-difference

The first version should be much simpler than the full old design.

The player sees:

- a short rules panel
- a presented candidate packet
- a small number of inspectable items

The player can:

- inspect an item
- get either "looks in order" or "revealed discrepancy"
- finally choose pass / deny / arrest

No mediation yet.
No haggling yet.
No dynamic policy changes yet.

This is the smallest useful interaction and proves the core loop.

### Phase 2: findings unlock follow-ups

After the simple loop works, allow some findings to unlock response moves:

- request missing credential
- request search
- verify identity

These are still just moves in the same game block, not a new subsystem.

### Phase 3: generated cases and distributions

Once the interaction loop is stable, add the richer case generation ideas from
the scratch models:

- expected disposition ratios
- extras and authored candidate pools
- region- or purpose-specific rule tables
- generated invalid / forged / hidden packets

### Phase 4: narrative pressure

Only after the above works should the interaction grow extra narrative layers:

- bribery
- threats
- whitelist / blacklist politics
- reputation consequences

---

## Generic Pattern: Picking Game with Hints

Our recent discussion suggested a more general reusable pattern behind
credentials:

**Picking game with hints**

That pattern looks like this:

1. present a field of inspectable evidence
2. allow the player to pick an item or issue
3. reveal either a distractor or a meaningful finding
4. optionally unlock a follow-up move
5. repeat until the player commits to a terminal decision

This pattern could support more than credentials:

- inspection puzzles
- detective scenes
- hidden-object variants
- "find the faulty component" technical scenes

Credentials are simply the strongest motivating example.

---

## What the Generic Layer Actually Needs

The current `mechanics.games` framework is already close, but a generic picking
game would benefit from a few conventions:

- structured moves rather than bare enums
- move labels or action builders for inspectable targets
- journal hooks for "finding discovered" narration
- namespace export of current findings and decision state

That is still much smaller than inventing a whole new interaction framework.

The likely generic pieces are:

- `PickingGame`
- `PickingGameHandler`
- structured pick / inspect move payloads
- a standard way to represent visible items, hidden facts, and revealed findings

The credentials mechanic can then be the first concrete domain user of that
pattern.

---

## Domain Concepts Worth Preserving

Even in a simplified v38 implementation, these credential-domain concepts are
worth keeping from the scratch work:

- **Restriction map**
  What origins, purposes, or contraband states are currently permitted.

- **Candidate truth**
  The actual underlying facts about the candidate.

- **Candidate presentation**
  What the player currently sees or is told.

- **Credential packet**
  The presented supporting documents and their legitimacy state.

- **Finding**
  A revealed discrepancy, confirmation, or cleared suspicion.

- **Disposition**
  The final player decision.

These are stable domain nouns even if the old implementation scaffolding is not.

---

## What to Drop from the Older Iterations

The following ideas should be deferred or avoided in the first modern pass:

- custom `ChallengeScene` / `ChallengeRound` infrastructure
- attrs-era action subclasses for every micro interaction
- deep coupling of packet generation and scene traversal
- trying to solve media generation, puzzle interaction, and narrative branching
  all at once
- modeling every possible Papers Please escalation before the basic loop works

The goal is a playable interaction first, not complete historical feature parity
with every scratch prototype.

---

## Example v38 Mental Model

### Minimal case

A credential block owns one case:

- rules: "workers require permit"
- presentation: candidate claims to be a worker
- shown packet: ID card only
- hidden truth: permit missing

Available moves:

- inspect declaration
- inspect ID card
- pass
- deny

Likely progression:

- inspect declaration -> reveals worker purpose
- inspect ID card -> looks in order
- deny -> correct terminal disposition

This already captures the core loop.

### Expanded case

A richer case adds:

- forged permit
- wrong holder
- hidden contraband
- request search
- request ID test

These are additive follow-ups on the same interaction pattern, not a separate
mechanic.

---

## Proposed Implementation Order

### Phase 1: minimal credential spotting game

Implement:

- `CredentialCheckGame`
- `CredentialCheckHandler`
- `CredentialCheckBlock`

with only:

- inspect target
- reveal finding or distractor
- pass / deny / arrest

### Phase 2: structured findings

Add explicit finding types and better journal output:

- suspicious
- confirmed invalid
- confirmed forgery
- cleared

### Phase 3: follow-up moves

Add:

- request search
- request missing document
- verify identity

### Phase 4: authored and generated case pools

Add script models that describe:

- candidate templates
- restrictions
- expected outcome distributions
- special narrative consequences

This is the point where the old script-model work becomes useful again.

---

## Summary

The credentials mechanic should be understood in v38 as:

- a **story block with embedded game state**
- implementing a **spot-the-difference / inspect-and-reveal loop**
- likely using a small generic **PickingGame** pattern
- starting with simple discrepancy spotting
- only later layering on mediation, generated cases, and political narrative

That keeps the best ideas from the scratch implementations:

- strong credential-domain vocabulary
- candidate generation concepts
- rich discrepancy taxonomy
- disposition-driven consequences

while discarding the older custom scene/challenge scaffolding that current
StoryTangl no longer needs.

# Credentials Loop Design

**Status:** PROMOTED FAMILY NOTE  
**Scope:** the credentials / checkpoint interaction as a stacked picking-game
composition inside `tangl.mechanics.games`  
**Background sources:** `docs/src/notes/CREDENTIALS_INTERACTION.md`,
`scratch/mechanics/credentials/README.md`,
`scratch/mechanics/credentials/notes.md`, and the older scratch credentials
package  
**Prior art:** Lucas Pope's *Papers, Please* and similar checkpoint-inspection
games

---

## Why This Note Exists

The credentials mechanic has been one of the longest-running design threads in
the repository. It already has a substantial background note in
`docs/src/notes/CREDENTIALS_INTERACTION.md`, but it is important enough to
deserve a short, live-facing mechanics note too.

The main reason is that credentials is not just "another picking game." It is a
**stacked composite loop** built from several smaller patterns:

- local spot-the-difference checks on individual documents
- packet-level consistency checks across the whole presented case
- a final disposition choice with narrative consequences
- circumstance and prior memory that can skew any of the above

That is exactly why it made sense to defer it until simpler kernels were
proven.

---

## Papers, Please Decomposition

What made *Papers, Please* compelling was not only the fiction. It was the way
it layered a few simple interaction patterns:

- compare visible evidence against current rules
- inspect for discrepancies or confirmations
- manage time, suspicion, and partial information
- make a final bureaucratic disposition
- carry narrative and economic consequences outward into a larger loop

That combination gives the player the feeling of performing a procedural task
while actually navigating a tightly authored dramatic machine.

StoryTangl's credentials mechanic should preserve that layered structure rather
than flattening it into a single yes/no check.

---

## Core Structure

The credentials interaction should be thought of as three explicit layers.

### 1. Document Loop

Each credential has its own local inspection game:

- what should this document look like?
- what visible fields or seals are present?
- what details are missing, forged, inconsistent, or suspicious?

This is the most direct descendant of a picking or Kim's Game style loop:

- inspect a feature
- reveal either a distractor, confirmation, or discrepancy
- record the finding

### 2. Packet Loop

The full credential packet then has its own consistency game:

- do the documents agree with each other?
- do they match the declared purpose, origin, and identity?
- do they satisfy the current checkpoint rules?
- are there missing supporting documents for the declared situation?

This is not identical to any one document check. It is a second-order
comparison between the candidate's full presentation and the current policy.

### 3. Disposition Loop

After inspection, the player chooses a terminal disposition such as:

- allow / pass
- deny
- arrest
- defer, extort, request search, or other world-specific outcomes later on

This is where narrative consequences enter most directly. The disposition is not
just scoring. It can affect later plot state, reputation, rewards, risk, and
future encounter structure.

---

## Context Layer

Any of those three layers can be informed by circumstance or prior memory.

Examples:

- "I have seen this candidate before."
- the candidate is on a whitelist or blacklist
- the candidate offers a bribe
- the current checkpoint rules changed this morning
- the player is under pressure from quotas, supervisors, smugglers, or scarcity

This is a crucial design property. Credentials is not only a static discrepancy
spotter. It is an inspection loop whose available moves, findings, and correct
dispositions can be bent by world context.

That context should be modeled as explicit game state and policy input, not as
hidden exception logic.

---

## Domain Vocabulary Worth Preserving

The older scratch work and consolidated docs note already established strong
domain nouns. Those are still the right building blocks:

- **restriction map** or current checkpoint rules
- **candidate truth**
- **candidate presentation**
- **credential packet**
- **document finding**
- **packet finding**
- **disposition**
- **whitelist / blacklist**
- **bribe / threat / pressure**

These are more stable than any one old implementation scaffold.

---

## Why This Is A Composite Loop

Credentials sits at the overlap of multiple family notes:

- it is a **picking game** because the player inspects and reveals findings
- it is a **composite loop** because document checks, packet checks, and
  disposition are stacked
- it is often a **narrative pressure game** because circumstance and prior
  knowledge bias the available choices and outcomes

That makes it a good test case for whether the mechanics taxonomy is actually
compositional rather than merely descriptive.

---

## Recommended First Live Implementation

Even though the conceptual structure is layered, the first live implementation
should probably *not* be a literal nested `HasGame` inside `HasGame` inside
`HasGame`.

The simpler and safer v1 is:

- one outer `CredentialsGame`
- staged internal phases such as `inspect_document`, `inspect_packet`, and
  `decide`
- findings recorded at both local and packet scope
- context injected as explicit state that affects move generation and evaluation

In other words, the first implementation can treat the inner loops as
**virtual subgames** inside one outer game state machine.

That keeps the runtime surface manageable while still preserving the conceptual
stack.

---

## Later Directions

Once the simplified outer-game version is proven, richer versions can add:

- request missing credential
- request search
- verify identity
- challenge a claimed exemption
- accept or reject a bribe
- memory-driven special handling for recurring candidates
- packet generation driven by distributions, regions, and authored policy tables

At that stage we can revisit whether any inner layer deserves extraction into a
reusable generic kernel.

---

## Relationship To Existing Reference Games

The current live references already point in this direction:

- `KimGame` proves cue-driven inspection and reveal
- `CredentialsGame` proves a compact inspect-and-dispose loop
- the picking-game conventions in the handlers prove that findings can surface
  through move labels, notes, journal fragments, and namespace

What remains is the stacked form: local mismatch, packet mismatch, then
disposition under context.

---

## Implementation Guidance

If the credentials family is expanded next, the live design should aim for:

1. document findings and packet findings as separate recorded categories
2. explicit context inputs for prior memory, whitelist/blacklist, bribery, and
   changing rules
3. a disposition layer that routes narrative consequences outward
4. a first implementation that stages subloops inside one outer game
5. only later, if justified, true nested subgames or reusable picking kernels

That should preserve the best lessons from the old *Papers, Please*
deconstruction without forcing the first implementation to solve everything at
once.

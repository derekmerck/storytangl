# Concept Seeds

Prospective designs, not executable worlds or newly scheduled work. They share a
page until one needs a developed brief. Existing issues retain implementation
scope; an open issue does not establish that its consumer or architecture exists.

## Constraint-Collapse Mystery

**Stage:** concept seed. **Implementation:** none selected.
**Lineage:** [#210](https://github.com/derekmerck/storytangl/issues/210) and
[#396](https://github.com/derekmerck/storytangl/issues/396).

**Premise and invariant.** A murder has no predetermined solution. Investigation
eliminates possible histories; the player forecloses unacceptable accounts or
exposes inconsistent declared truths. They determine which accounts can still be
true, rather than discover one answer fixed all along.

**Presentation lineage and mechanic.** Inspired by *Umineko*'s red/blue truth
distinction, this original mystery makes the colors derive from the remaining
admissible histories. A proposition is **blue** while true in some but not all
remaining histories, **red** when every remaining history entails it, and
**excluded** when none does. An empty solution set is a **paradox**, not a state
where vacuous entailment makes every proposition red. The visible transformation
is how the reader experiences possibility contracting; it is not just decoration.
The statuses also need a readable expression for clients that do not show color.

Earlier journal passages may retain their emission-time colors/statuses while a
retrospective reading projects the current status of the same claims. That later
reading is another projection, not a rewrite of historical journal fragments.
This borrows a presentation distinction, not *Umineko*'s plot or its exact rules.

**StoryTangl connection.** Ordinary state, choices, history, and JOURNAL could carry
an explicitly finite authored possibility set. Constraint commitments and necessary
versus possible propositions would pressure a later solver-backed realization.
The optional archived Clingo evidence does **not** establish this game: #396 owns
generated observational analysis, not runtime choice authority. A solver-owned
deduction game needs its own bounded contract under #210.

**Unresolved question.** What makes investigation legitimately establish a
constraint rather than permit arbitrary player declarations? How does contradiction
remain legible without silently rewriting established events?
Which authored claims receive checkable status, and how do retrospective readings
keep their references while changing the presentation?

**First playable proof / unlock.** A tiny original mystery with multiple consistent
solutions, a meaningful exclusion path, and an intentionally modeled paradox. Start
with an inspectable finite set and normal runtime choices. This tests evidence,
commitment, and admissible fabula without making a new solver VM a prerequisite.

## The Council in Your Head: competing inner voices

**Stage:** concept seed; no new implementation selected.
**Existing work:** [#340, Guides / inner voices](https://github.com/derekmerck/storytangl/issues/340).

**Provenance and prior art.** The inspiration is the interacting skills and
internal monologues of [*Disco Elysium*](https://discoelysium.com/). In StoryTangl
this idea predates the proposed world: [`MU_AFFORDANCES.md`](../notes/MU_AFFORDANCES.md)
explicitly describes both a Disco-style voice and the *Stormbringer* worked
example. The drawn sword donates light, a whispered line, and an alternative
action, while suppressing commerce and sheathing until it has been used. That is
a proposed multi-channel composition, **not** proof that every illustrated
facet is shipped. The earlier [RoleGrant work (#141)](https://github.com/derekmerck/storytangl/issues/141),
[scoped concept projection (#255)](https://github.com/derekmerck/storytangl/issues/255),
[named text (#336)](https://github.com/derekmerck/storytangl/issues/336),
and [#340](https://github.com/derekmerck/storytangl/issues/340) are the
continuing implementation lineage. [Narrative Control](../design/story/NARRATIVE_CONTROL.md)
explains why a contribution may be prose, an authored beat, or a donated
affordance instead of always needing graph machinery.

**Premise and experiential invariant.** A protagonist's apparent inner
monologue is a council of partially independent perspectives: duty, curiosity,
grief, pride, fear, or a possessed object. These voices read the same situation
differently, retain recognizable registers, and sometimes offer, reinterpret,
or obstruct possible actions. The world does not centrally enumerate the voices
the protagonist happens to carry. **Who is present in the mind changes both
what the reader hears and what the character can choose.**

**Narrative pressure.** In a returning-home mystery, one voice remembers a
promise not to open a locked room, another notices a recently changed lock, and
a third wants to avoid the memory altogether. A cursed sword might insist that
a lock is something to cut. The voices need not all be correct, benevolent,
or obeyed. Distinguish advice, evidence, temptation, and actual coercion:
an interesting disagreement is not automatically permission to remove player
agency. Two contexts should let the same voices recur with changed relevance,
not merely deliver one-liners in a single exposition scene.

**StoryTangl connection.** Scope and concept ownership nominate contributions;
the current namespace and ordinary phase dispatch determine what is relevant.
Prose contributions belong in attributed JOURNAL, and action offers or
restrictions must use the existing planning/affordance path. The same concept
can have both roles. These integrations, deterministic multi-voice composition,
source attribution, and disclosure-safe suppression remain the concrete
proof of #340; they are not a reason to invent a parallel voice runtime, new
emotion meters, or a universal passive skill-check system.

**Unresolved questions.** When two voices disagree, what is simply competing
speech, and what genuinely constrains a choice? How are overlapping contributions
ordered and attributed without silent overwrite? What does a hidden or unavailable
voice reveal, if anything? Can a voice's history and tone persist across situations
without the host scenes hard-coding its lines?

**First playable proof / unlock.** Two contrasting situations, two or three
recurring internal voices, and one external contributor (such as the sword).
A single beat receives *two attributed interjections*; one voice contributes
an ordinary available action and another applies a justified restriction. The
player's response has a durable callback on returning to a prior context.
Test the normal JOURNAL/Service/text-client path first. Keep all personality,
setting, and conflict policy world-owned until a second consumer justifies more.

## The Long Way There: emergent road-trip narrative

**Stage:** showcase concept seed; implementation not selected.

**Provenance and prior art.** This revisits the recurring road-story discussion
inspired by [*Keep Driving*](https://store.steampowered.com/app/2756920/)
and [*Dustland Delivery*](https://store.steampowered.com/app/2943280/Dustland_Delivery/).
StoryTangl's [Interactive Narrative Capability Matrix](../notes/research/interactive_narrative_capability_matrix.md)
already identifies both in **A10, Attrition-driven emergent narrative + sifting**:
encounters over depleting resources, cooldown-bearing items/skills, companion
modifiers, and a retrospectively sifted history. **A00, Entity-collection
management sim** names Dustland Delivery for its per-entity state and periodic
aggregate rules. Those entries are research hypotheses, not evidence that
sifting or a driving game already ships. Relevant ongoing threads are
[the showcase portfolio (#395)](https://github.com/derekmerck/storytangl/issues/395),
[gameplay compositions (#332)](https://github.com/derekmerck/storytangl/issues/332),
[sandbox/adventure (#236)](https://github.com/derekmerck/storytangl/issues/236),
and [scheduled concept contributions (#556)](https://github.com/derekmerck/storytangl/issues/556).

**Premise and experiential invariant.** A small, characterful journey by car or
delivery van across a graph of towns and roads. The protagonist has a destination,
a vehicle, limited supplies, and reasons to stop; passengers carry their own
destinations, needs, skills, and social histories. Road challenges, diversions,
odd jobs, repairs, and encounters change what is possible at subsequent stops.
**The story is not a chosen sequence of authored plot branches: it is what
happened to these people, with these obligations, on this route.** Give space
to quiet roadside conversation, incidental kindness, comedy, and melancholy,
not only attrition or optimized delivery.

**Narrative pressure and progression.** Traversing an edge costs time, fuel,
condition, or opportunity; an encounter can be a short turn-limited mini-game,
not a continuous vehicle physics simulator. A hitchhiker may help repair the
engine but consume food or demand a detour before Friday. Missing that
appointment changes later dialogue or closes a favor. Vehicle equipment,
skills, relationships, cargo, and reputations modify both encounter options
and the interpretation of arrivals. The same town should feel different on
a desperate return than it did on an optimistic outbound leg.

**StoryTangl connection.** The location/travel graph, sandbox time/resources,
re-enterable game challenges, inventory/progression, and concept-contributed
opportunities have existing independent precedents; their sustained journey
composition remains unproved. Passengers should carry portable contributions
instead of each road scene knowing every possible passenger. A world-owned
retrospective can initially select consequential receipts from the journal
rather than demanding a generic narrative-sifting framework. Distinguish
*mechanical momentum* (deadlines, depletion, commitments) from *perceptual
momentum* (moving scenery, audio, changing weather, pacing). Pygame is a
natural first visual consumer; [media/client breadth (#410)](https://github.com/derekmerck/storytangl/issues/410),
[staged identity (#409)](https://github.com/derekmerck/storytangl/issues/409),
and [audio parity (#571)](https://github.com/derekmerck/storytangl/issues/571)
provide presentation lineage, **not** a requirement that the engine adopt a
pygame-specific travel clock. Web and text clients should retain the same
causal story floor even if their journey presentation differs.

**Unresolved questions.** What constitutes a committed travel leg versus an
interrupting encounter? How do cooldowns, NPC availability, and obligations
survive travel, return journeys, and reload? Which events earn a place in the
trip's remembered narrative, without simply summarizing every ledger step?
Which elements of continuous movement are client-local presentation rather
than story-time authority?

**First playable proof / unlock.** Six road legs, three depleting resources,
one repeatable encounter family with cooldowns, two hitchhikers with distinct
costs/contributions and personal destinations, and a small progression choice.
Show two substantially different arrivals or returns based on actual journey
history. End with a short authored *road journal* that selects and interprets
several prior events. Prove the same transitions and consequences through
Service/text before adding a modest pygame traveling presentation; no new
vehicle runtime, full trade economy, or automatic story-sifting system is a
prerequisite.

## Two Readers, One Graph

**Stage:** developed mechanism/premise seed. **Implementation:**
[#346](https://github.com/derekmerck/storytangl/issues/346).

**Premise and invariant.** A head-to-head combat gamebook gives each opponent the
book describing the other's body receiving consequences. Two perspectives share
one fight, but each reader does not simply receive narration of their own success.
The focalization matters independently of the chosen transport.

**StoryTangl connection.** Existing contest/game, payload, and attributed-fragment
surfaces support a hot-seat experiment. Genuine reader lanes require separate
cursor/history/channel behavior and coordinated concealed input. Two roles or a
second narrator key do not establish multi-cursor support. #346 owns that proposed
integration and its open questions.

**Unresolved question.** What must be simultaneous, concealed, and attributable at
commitment, and what is simply a decision about who reads an emitted perspective?

**First playable proof / unlock.** Two small original fighters, a bounded move
matrix, one persistent restriction, and a hot-seat exchange with both observer-
oriented outcomes. A later two-lane witness must prove shared state and separate
delivery, not relabel the stand-in. This tests participant/channel boundaries and
literary POV. Source-book extraction in #346 remains a separate content/provenance
decision; this seed imports no book corpus.

## Automata Chop-Shop

**Stage:** integration concept seed. **Implementation:**
[#333](https://github.com/derekmerck/storytangl/issues/333).

**Premise and invariant.** In a workshop and neighboring activity hubs, the player
constructs, certifies, trains, and deploys an automaton. It remains the same machine:
what makes it useful also changes what is legal, repairable, or possible.

**StoryTangl connection.** Assembly, credential vetting, progression/challenges,
transactions, and sandbox opportunities have independent rails. Their agreement
on one automaton is the unproven composition. Legacy parts and credential catalogs
are domain evidence, not a runtime architecture to resurrect.

**Unresolved question.** What capability/indication projection can serve vetting and
action eligibility without storing competing descriptions of the robot?

**First playable proof / unlock.** One assembly, one legal and one remediable
configuration, one challenge/upgrade, and one sandbox opportunity changed by it.
Reload keeps the same components and machine. This provides a composition precedent
for Patient Zero without requiring a universal robot framework or paperdoll first.
A showcase expansion would add recurring people and pressures to the workshop,
rather than only more mechanics screens.

## Second Bell

**Stage:** showcase seed. **Implementation direction:**
[#395](https://github.com/derekmerck/storytangl/issues/395).
**Existing proof:** [Hall Monitor](https://github.com/derekmerck/storytangl/tree/main/worlds/hall_monitor).

**Premise and invariant.** A school day of conflicting instructions, recurring
students, limited attention, and bureaucratic comedy distinguishes rules-correct,
rewarded, compassionate, and actually beneficial outcomes. A local ruling returns
later as a consequence for a recognizable person.

**StoryTangl connection.** Hall Monitor proves attributable delayed consequence
over credentials. A sibling could add bell pressure, changing announcements, and
competing obligations over the same facts. Mira's inhaler proof should remain a
narrow fixture, not become a fragile full-day script.

**Unresolved question.** How does the reader learn that institutional success and
helping someone can diverge, without a hidden morality score doing the explaining?

**First playable proof / unlock.** One bell-to-bell interval, two conflicting
demands, a ruling, and the student's return. Test whether existing credentials,
schedule, and authored aftermath carry the distinction. No generic ethics or
relationship subsystem is implied.

## Fogbound Manifest: a showcase sibling

**Stage:** showcase seed. **Implementation direction:**
[#395](https://github.com/derekmerck/storytangl/issues/395).
**Existing proof:** [the composition demo](https://github.com/derekmerck/storytangl/tree/main/worlds/composed_beat_demo),
already titled *Fogbound Manifest*.

**Premise and invariant.** Old Maro, fog, an inaccurate manifest, and disputed cargo
make trust, inspection, concealment, and delivery matter to one incident. Later
reconstruction changes the meaning of an earlier transaction.

**StoryTangl connection.** The current world proves gather/enrich/compose and a
reputation change. A larger mystery could combine inspection, a warehouse sandbox,
transactions, and delayed revelation. The composer proof does not establish that
this larger plot already plays.

**Unresolved question.** Which claims are supported, which are merely believed,
and what does each participant remember when the cargo changes hands?

**First playable proof / unlock.** One cargo, one disputed document, two
dispositions, and a return scene depending on trust and the actual disposition.
Keep the compact fixture intact. The sibling tests whether composed beats and
mechanics mutually constrain a mystery instead of decorating disconnected systems.

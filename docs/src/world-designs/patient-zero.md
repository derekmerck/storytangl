# Patient Zero

**Stage:** developed brief; no executable world is claimed.
**Purpose:** prospective companion/survival-horror showcase.
**Implementation:** [#397](https://github.com/derekmerck/storytangl/issues/397),
under the [showcase portfolio](https://github.com/derekmerck/storytangl/issues/395).

This extracts the narrative intent of #397. That issue retains implementation
slices, dependencies, and acceptance criteria. The configuration model is a world
design, not an engine-owned companion ontology.

## Premise and experiential invariant

Patient Zero, a young former research subject, wakes in a sealed pharmaceutical
facility. Their former doctor is infected and feral. At first the doctor is a
dangerous but useful instrument: the player can feed, restrain, and direct them.
Treatment restores technical ability and communication, then judgment and a memory
of the player's behavior. The person who can finally help also has reasons to refuse.

**Increasing mastery expands the player's ability to configure the companion
while reducing their practical ability and moral entitlement to command them.**

One companion remains the same person across treatment, learning, augmentation,
betrayal, and cooperation. The systems must constrain the same durable facts,
rather than appear as unrelated minigames.

## Pressure and dramatic structure

The facility descends from corporate laboratories through older military
infrastructure into buried original research. This reverses a simple improvement
curve: upper levels reward cognition, while deeper routes make selective regression
and physical adaptation useful again.

| Configuration | Capability and pressure |
| --- | --- |
| Feral | Physically potent, hungry, cognitively limited; food, restraint, and conditioning can direct behavior. |
| Transitional | Able to learn and adapt, but physically and cognitively weak. |
| Lucid | Communicative and technically capable, physically fragile, and increasingly unwilling to accept coercion. |

Later, partial body/mind decoupling permits stronger hybrids, but autonomy,
appetite, stress, or burnout undermine the original control structure. Permanent
cybernetic augmentation supplies reliable shortcuts while narrowing later
biological configurations or solutions.

Time, treatment reagents, hunger, safe containment, and trust make configuration
situational. Restraining a hungry feral companion can prevent harm; doing the same
to a lucid person can produce betrayal. Learned tricks and memories survive changes
in form. Affection, guilt, contempt, and loyalty can be authored interpretations of
a few durable historical anchors, without a meter for every feeling. Prefer
deterministic capability gates when uncertainty adds nothing to the situation.

## StoryTangl connection

The reusable rails exist independently; this particular composition is unproven.

| Existing rail or precedent | Proposed use and remaining proof |
| --- | --- |
| Owner-bound [assembly](https://github.com/derekmerck/storytangl/tree/main/engine/src/tangl/mechanics/assembly) | One graph-owned companion has components and permanent locks; the world defines configuration legality and derived capability. |
| Transactions, wallets, progression, and tokens | Treatment consumes resources; learning survives transformation. Costs, upgrades, and later gates must agree on one state. |
| Sandbox schedules, scoped namespace, ordinary actions | Location, ability, willingness, and time expose opportunities without a private traversal loop. |
| Attributed JOURNAL and current-provider naming | The companion speaks and is recognized through existing prose. Configuration-dependent voice contributions remain a specific proof in [#340](https://github.com/derekmerck/storytangl/issues/340). |
| Constructor-form persistence and replay | Reload retains the person, components, learned tricks, and treatment history, rather than generating a replacement. |

The [Automata Chop-Shop](https://github.com/derekmerck/storytangl/issues/333) is a
planned composition precedent, not a shipped robot world.
[#255](https://github.com/derekmerck/storytangl/issues/255) owns broader scoped
concept-projection convergence. Check those dependencies before a slice; do not
rebuild their mechanisms privately in this world.

The world-owned residual is infection vocabulary, configuration rules,
capability/willingness predicates, pressure thresholds, and interpretation of
remembered treatment. A second consumer would be needed before extracting a
general companion or relationship framework.

## First playable proof

The bounded vertical in #397 is smaller than the whole facility:

1. Wake with a treatment deadline and recover the feral doctor.
2. Use physical force to pass a damaged service route.
3. Teach a trick in the transitional configuration and retain it after changing.
4. Restore cognition to access a console and a more truthful conversation.
5. Resolve one hunger/night beat through feeding, containment, trust, or a costly
   alternative.
6. Establish an anchor: a kept promise, involuntary restraint, or withheld treatment.
7. Install one permanent augmentation that helps now and changes a future path.
8. Unlock one independent body/mind adjustment, not the full combination space.
9. Complete one of two viable exits: coercive and reliable, or cooperative and
   preparation-dependent. The aftermath recalls an attributable earlier choice.

Use an ordinary supported-client transcript and real save/reload of the same
companion. The vertical can end at escape from the first layer or entry to the
deeper complex, without settling the outbreak or universal cure. Conversation and
aftermath are part of the experience. This would establish a concrete test of
whether assembly, agency, time, and prose can share one person without a bespoke runtime.

## Unresolved questions

- Which controls cease to be possible when cognition returns, and which remain
  possible but change willingness or memory?
- What is the smallest configuration model that makes the permanent shortcut
  legible without overwhelming the first vertical?
- Which acts deserve durable anchors, and which can be answered from history?
- Which unsolicited behavior is ordinary scoped opportunity, and which part, if
  any, exposes a missing shared mechanism?

Full facility content, exhaustive configurations, NG+, campaign resources, and a
generic companion ontology remain outside the first proof. Progress is not defined
as turning the doctor into a permanently obedient instrument.

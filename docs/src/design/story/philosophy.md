# Conceptual Foundations

> Why the system works the way it does, and the metaphors that keep it honest.
> Package-level runtime architecture now lives in
> `engine/src/tangl/story/STORY_DESIGN.md`; this page remains the higher-level
> conceptual rationale.

StoryTangl models interactive narrative as a **graph of interdependent possibilities**
that **collapses into a specific story** through traversal.  This document explains
the conceptual vocabulary behind that sentence — where it comes from, why it matters,
and how each idea maps to real machinery in the engine.

Every metaphor here earns its place by corresponding to an implemented (or
concretely planned) mechanism.  If a concept doesn't connect to code, it belongs
in the research agenda, not here.

---

## The Central Thesis

**A story is a structured collapse of possibility into experience.**

An author defines a *space* of potential narratives — characters who could meet,
events that could transpire, objects that could matter.  A reader (or player, or
algorithm) navigates that space, and the act of navigation progressively resolves
ambiguity into commitment.  What was once "the villain *could* be anyone" becomes
"the villain is Marta."  What was once "you *could* go east" becomes "you went
east, and now the west road is buried."

The engine's job is to make this collapse **auditable** (every decision is logged),
**deterministic** (the same choices reproduce the same story), and **extensible**
(new kinds of narrative content and mechanics plug in without changing the core
loop).

### Why "Untangling"

The original backronym — *the Abstract Narrative Graph Library* — described the
data structure.  The working metaphor is better: the story space starts
**tangled**, a web of interdependent requirements, roles, and consequences, and
the engine's job is to **untangle** it into a single coherent thread.

This is not merely poetic.  The resolver literally walks the dependency graph,
finds nodes that satisfy open requirements, binds them, and advances the frontier.
Each step reduces the degrees of freedom in the remaining graph.  The journal that
emerges is the untangled thread — a linear narrative extracted from a
combinatorial space.

---

## Three Models, Three Layers

StoryTangl separates *what could happen* from *what does happen* from *what the
reader sees*.  This separation is the engine's most important architectural
commitment.

### Fabula — the Possibility Space

The **fabula** is the complete graph of events, characters, places, and their
relationships — everything that *could* be narrated.  It is the "tangled" state:
a castle exists, a dragon exists, a knight exists, and there are dependency
edges encoding that the dragon guards the treasure and the knight needs a sword.

In the engine, authored fabula first lives as a compiled
`StoryTemplateBundle`: a set of structural templates (scenes, blocks, actions),
concept templates (actors, locations, assets), and dependency declarations
capturing what could be instantiated.  Materialization then turns that compiled
possibility space into one navigable runtime `StoryGraph`.

The fabula contains more stories than any single traversal will realize, just as
a chessboard contains more games than any single match will play.

**Implementation:** `StoryCompiler` → `StoryTemplateBundle`;
`StoryMaterializer` → `StoryGraph`.

### Episodic Process — the Traversal

The **episodic process** is what happens when a cursor moves through the fabula.
At each step, the engine validates the proposed move, provisions any unresolved
dependencies, applies state updates, and emits journal fragments.  This is the
resolution pipeline — the phase bus that drives the story forward.

The episodic process is where possibility collapses into commitment.  Before a
block is visited, its role slots might be open ("this scene needs *a* villain").
During provisioning, the resolver binds a specific actor to that role.  After
the block is visited, that binding is frozen — the villain is Marta, permanently,
for this story instance.

**Implementation:** `Frame.follow_edge()` → the eight-phase pipeline
(VALIDATE → PLANNING → PREREQS → UPDATE → JOURNAL → FINALIZE → POSTREQS →
advance frontier).

### Syuzhet — the Realized Narrative

The **syuzhet** is the journal — the linear sequence of content fragments that
a reader actually experiences.  It is the "untangled" thread: prose paragraphs,
character descriptions, choice prompts, media references, emitted in the order
the traversal produced them.

The syuzhet is presentation-agnostic.  The same journal can be rendered as
terminal text, a rich web page, or an ebook.  Fragment types carry semantic
roles (narrative content, dialog, choices, media).  Presentation advice travels
with them as optional hints that a client may honour or ignore.
The service layer translates fragments into a specific presentation format based
on client capabilities.

**Implementation:** an `OrderedRegistry` of `BaseFragment` subclasses
(`ContentFragment`, `ChoiceFragment`, `MediaFragment`); service-layer render
profiles transform fragments for specific clients.

### Why This Separation Matters

The same fabula can produce radically different syuzhets depending on:

- **Player choices** — different traversal paths through the structural graph
- **Provisioning outcomes** — different actors cast into the same roles
- **Discourse rules** — different ordering, focalization, or pacing applied to
  the same underlying events (planned, not yet implemented)

This is not a theoretical nicety.  It means you can test structural properties
(reachability, completability, role satisfaction) against the fabula *before*
any traversal happens, and you can reproduce a specific walk from its starting
configuration and its choices (see Determinism and Replay).

## Working Laws

These are the rules the design is trying to obey, stated by the designer during
a whole-project review in November 2026.  They name no classes on purpose: they
should hold for any implementation.  They are intent.  Where the current code
differs, the package design notes and the issues that own the area say so.

### 1. Four orderings of one space

The three models above are four levels once the possibility space is split into
what is authored and what is instantiated.  Each level adds order to the one
before it.

| Level | What it is | Order |
| --- | --- | --- |
| World | templates and rules | none |
| Story graph | one grounded configuration of that space | relations only |
| Episodic process | the walk through the traversable concepts | partial |
| Journal | what was told | total |

The episodes mediate between the linear journal and the non-linear story
graph, which is itself one configuration of the ambient story space: like using
a graph to order data with a heapsort.  The fabula covers the first two rows.

The order belongs to the walk, not to the authored graph.  Hubs and self-loops
make the authored traversable graph cyclic; it is the sequence of occurrences
that is ordered.

Journal fragments were once leaves hanging off the episodes that produced them,
and a journal was read out by walking any group of episodes.  They are stored
apart from the graph now, for size and so that story state can be compared
without the telling.  The full tree, from world to fragment, can still be
reassembled.

### 2. Concepts and episodes

- Any node in a story graph is a **concept**.
- A traversable concept is an **episode**.  One is a block.  A group is a scene,
  which is primarily a scope for shared names.
- Concepts that are not episodes are mostly a **person, place, or thing**.  They
  are bound through roles and settings, or tracked as single tokens or fungible
  holdings.
- Themes, arcs and motifs are the same kind of concept, contributing narrowly
  through their relationships to other concepts.

### 3. Two readings of one rule

A world can be written imperatively, in the manner of a gamebook: *if this and
this, then go there*.  It can be written declaratively: *this is what can be
reached when that and that hold*.  These are two readings of the same rule, and
a world may be made entirely of either.  Both exist because episodes beg for
the if-then form, while most concepts do not need to be ordered.

Materialization assembles what was declared so that it can be walked.  Eager
materialization assembles everything.  Provisional materialization assembles
what is here and coming up.  A template is an affordance for the provisioner: a
concept or episode that comes into being when its conditions are met.  It reads
as an imperative only because it is created on demand.

It follows that assembling is repeatable: the same declarations against the same
state should change nothing.

### 4. Pull and push

An open link is an edge with one end fixed and a requirement describing the
other.  A **dependency** is fixed at the one that needs something, and pulls.
An **affordance** is fixed at the one that offers something, and waits.  A
**fan-out** is a set of dependencies generated at a node, reaching for nearby
satisfiers.  A **fan-in** is the set of latent affordances, created when their
scope is entered, that can offer themselves on a node: home offers *go home*,
a character offers *call her*.  See
[AFFORDANCE_MODEL.md](../planning/AFFORDANCE_MODEL.md) for the canonical
treatment.

### 5. Shape and state

- **Shape** should change only during provisioning.
- **State** should change during update or finalize when possible.
- There are two update phases because of prose.  If the text says the player
  drops the sword they are carrying and the sword has already been dropped, the
  text can no longer say what happened.  So the drop is recorded after the
  telling, and the telling reads the starting state.
- The **telling may change state on what it is talking about**: a speaker's
  attitude as it moves through a conversation, whom they are addressing, what
  they last said, what has been introduced to the reader.  It should not bring
  new concepts into being, and should touch only what this piece of prose is
  about.
- Reading a journal that has already been committed changes nothing.

### 6. Scope and navigation

A container is two things under one name.

| Role | What it answers |
| --- | --- |
| Scope | who and what is shared here |
| Navigation unit | where a walk enters and leaves |

Scope is the origin and the primary meaning: assign a villain to *this* scene,
refer to them by name in the content, and if they are recast every episode in
the region knows.  The navigation role accreted because scopes are jumped into
and out of.

A navigation unit has one source and one sink.  The source sets up wherever the
walk should land and forwards it there.  The sink finalizes the container and
forwards the walk out, back or onward.  Entered at the source and left at the
sink, a whole container is a single node at the next level up, and the whole
story is the outermost container.  An intended ending is a sink; running out of
choices anywhere else is a softlock.

A world may bind a place to an episode, so that moving between places is moving
between episodes, as in a cave adventure.  It may instead bind a place to a
scene as a setting, as in a calendar of events.  These are two lowerings of the
same idea.

### 7. What belongs to story

Story is what affects the shape of, and the path through, a story space.
Prose, media and mechanics refine appearance, presentation and interactivity.
Voice and point of view belong to prose or media.

The same test applies at other scales.  Two states belong to the same
**equivalence class** when nothing downstream can tell them apart: leaving a
room and returning with nothing changed is no move at all, and picking
something up now or later is the same if nothing depends on when.  (The term
follows Andrew Plotkin's
[PlotEx](https://eblong.com/zarf/plotex/).)  At what scale "tell apart" is
judged is left open.

Games here are interactive storytelling affordances.  They may be fair, and a
fair game is a good first step, but an author must be able to put a thumb on
the scale to any degree.  Chance should dress an outcome more often than decide
it.

### 8. Two kinds of similarity

- **Self-similarity.**  Given one starting configuration, the same walk
  reproduces.
- **Outcome similarity.**  A different starting configuration and the same
  choices land on essentially the same story state, though identities differ
  and the telling may differ entirely: the journal might be in French.

A seed is an option for testing, not a requirement.  The second kind holds only
where chance has little influence on provisioning and on which paths are open.
Replay does not have to be draconian; determinism becomes fuzzier the lighter
the author's thumb, and that is acceptable.

### 9. Whom the rules bind

These rules are firm for work on the engine itself.  For authors and plugins
they are rules of thumb: off-label use is unsupported and theirs to own, and
the engine does not guard against it.  Even the firm rules are negotiable.
When a real case collides with one, the rule is kept and the smallest exception
that meets the need is carved out.

---

## Concepts As Continuity Anchors

The practical motivation for the graph is continuity. Branching authoring tools
make it easy to accumulate scattered booleans such as `met_dragon`,
`has_special_sword`, or `helped_pirate`, then forget which later passages should
read or update them. A story developed in phases can therefore contradict its
own earlier events even when every local branch is individually correct.

StoryTangl instead encourages authors to reify a recurring noun as one durable,
addressable concept. The person, sword, dragon, robot, permit, or place persists
as the same graph-owned thing wherever it reappears. It can carry current state,
participate in relationships, retain committed interaction history, contribute
affordances, and project its own context-sensitive description. Later content
queries or gathers that concept rather than reconstructing it from a collection
of passage-local flags.

Different kinds of continuity still belong in different places:

| Question | Continuity surface |
| --- | --- |
| What is this thing currently like? | Concept state, facets, components, and managers |
| What is it wearing or carrying? | Durable assignments, holdings, or other relationships |
| How does this person regard another? | Actor-to-actor relationship state |
| What committed interaction occurred? | Ledger history, receipts, and consequent concept/relationship mutations |
| What did this concept previously contribute or say? | Derived query over attributed journal fragments |
| What has this narrator identified or disclosed? | Concept-local narrator knowledge |
| Where did this runtime concept or binding come from? | Template, provisioning, and projection provenance |

Prefer derived history queries over cached summary flags when the journal
already contains the answer. Attributed dialog fragments retain stable speaker
identity, and other fragments retain source and origin provenance. The first or
last thing a dragon said can therefore be recovered from the ordered journal;
it does not need `dragon.first_line` and `dragon.last_line` fields that can drift
away from the realized story.

Descriptions are derived views over those facts. A person's prose can mention
the current outfit and relationship posture; a weapon can render as "a sword"
before identification and "Glamdring" afterward; a mobile actor can contribute
different interactions after an earlier encounter. The prose is not another
authoritative copy of the state it describes.

This distinction also prevents several seductive category errors. A dragon
being considered or bound by the planner is not the same as the dragon meeting
the player. A dragon appearing in disclosed prose or a visible choice can change
reader or narrator knowledge without changing the dragon's knowledge. Only a
committed diegetic interaction should establish that the dragon recognizes,
likes, fears, or remembers the player. Planning provenance, disclosure state,
and world relationships may inform one another, but they are not interchangeable.

Durable concepts do not eliminate authorial responsibility or infer facts that
were never recorded. They make consequences composable. When an interaction is
expressed through a semantic operation and receipt, a later mechanic can begin
responding to that operation without teaching every earlier passage a new
boolean. If an old event recorded only prose, recovering its missing semantics
still requires an explicit migration or reinterpretation.

---

## The Compiler Metaphor

The fabula/episodic/syuzhet separation maps directly to a compiler pipeline:

```
Source:       YAML, Twee, passages, document vaults, ...
                 ↓ codec-owned structural decode
Cardinal:     portable story mapping
                 ↓ compile              ↑ deterministic decompile
Fabula IR:    StoryTemplateBundle / compiled template graph
                 ↓ traverse + resolve
Syuzhet:      Journal fragments
                 ↓ render
Presentation: CLI / Web / PDF / ...

Cardinal data  → codec-owned encode → normalized source artifacts
```

Like LLVM's intermediate representation, the story graph is a **universal
substrate** that captures narrative intent while abstracting away both the
source format and the target medium.

This is why interchange between interactive-fiction formats is architecturally
natural: a Twine file and a StoryTangl YAML script are different projections
through the same cardinal boundary. The compiled graph does not care where its
content came from, while each codec remains responsible for reporting what its
source representation preserved, normalized, approximated, or could not
express.

And like a compiler, the engine's phases are **deterministic, ordered passes**
over the IR.  Each phase has a defined contract (what it reads, what it may
mutate, what it returns).  The pipeline is auditable because every phase
produces receipts.

**Implementation:** `StoryCompiler.compile()` (front-end) →
`StoryTemplateBundle` (IR) → `StoryMaterializer.create_story()` +
`Frame.follow_edge()` phases (back-end passes) → `Journal` (output).

---

## Narrative Debt and Credit

When the episodic process recruits a concept — say, casting an actor into a
role — but the journal hasn't yet introduced that concept to the reader, the
story carries **narrative debt**.  The reader doesn't know who Marta is yet,
even though the engine has already committed to her as the villain.

Conversely, when the journal introduces a concept before it becomes
structurally necessary, the story holds **narrative credit**.  Mentioning the
gun on the wall in Act I creates credit that Act III's crisis may draw down.
(Chekhov knew this, but didn't have a dependency
graph.)

This maps directly to the provisioning system:

- **Narrative debt** = an unsatisfied dependency edge (the role slot is
  open, or is filled but the corresponding concept hasn't been journaled)
- **Narrative credit** = a concept published to the namespace before any
  structural node requires it (foreshadowing, world-building)
- **Debt resolution** = the journal handler that emits an introduction
  fragment when a newly-bound concept first appears in rendered output
- **Bankruptcy** = a structural dead end where required concepts cannot be
  provisioned (a softlock, which formal verification should catch)

A well-structured story balances its narrative books: debts are incurred
strategically (mysteries, in medias res openings) and resolved before they
become confusing.  The engine's dependency system makes this balance
*mechanically visible* — you can query the graph for outstanding debts at
any point in the traversal.

---

## Superposition of Possible Stories

Forward-looking: this is conceptual design for a future constraint authority
over the fact ledger, not a fully implemented subsystem today.

StoryTangl can also be understood as maintaining a **superposition of possible
stories**.  A linear narrative fixes beginning, middle, and end before the
reader begins.  A traditional branching story pre-considers many deterministic
paths.  A more dynamic story can instead begin with a field of compatible
latent truths: possible motives, identities, relationships, role assignments,
symbolic meanings, future beats, and story arcs.

Traversal collapses that field gradually.  Each journaled disclosure removes
some possibilities and strengthens others.  What has been disclosed to the
reader becomes hard to revise; what has only been assumed by planners,
handlers, or hidden state can remain soft.  If an unexpected choice or event
occurs, the engine may retcon any still-unobserved soft truth so the new beat
fits the evidence already fixed in the syuzhet.

This suggests a useful distinction:

- **Observed truth**: fixed within one realized journal because it has appeared
  there or has been explicitly committed by the runtime ledger.
- **Committed hidden truth**: fixed internally, but not yet disclosed.
- **Soft truth**: provisional assumptions used by planners or authorities, but
  still revisable if the story can re-solve coherently.
- **Potential truth**: candidate explanations, identities, motives, roles, and
  payoffs still available in the design space.
- **Contradicted truth**: no longer available unless reframed as dream, lie,
  rumor, hallucination, mistaken identity, fiction-within-fiction, or another
  explicit interpretive move.

Under this model, retcon is not cheating.  It is a controlled narrative
operation over soft truth, constrained by the observed ledger.  The design goal
is not to make every possible hidden fact mutable forever.  It is to know which
facts have become accountable to the reader and which facts remain negotiable.

A tooling-level retcon can go further by producing a revised realized journal:
replay the same path against corrected state, regenerate affected attributed
fragments, and preserve tombstones or replacement lineage for the old version.
That does not make observed truth soft inside the original history; it creates
an auditable new revision of that history.

### Latent Hooks and Foreshadowing

Foreshadowing is retrospective.  A disclosed element becomes foreshadowing only
when a later payoff makes the earlier disclosure matter in hindsight.  Until
then, the same element may be ordinary world-building, atmosphere, a motif, a
red herring, or unused texture.

The gun on the wall is therefore not inherently Chekhov's gun.
At first it is a **latent hook**: a disclosed story element with possible
affordances and meanings.  If Act III needs a threat, crime, clue, inheritance
dispute, family memory, or ironic accident, the gun can be promoted into payoff.
If no compatible future beat calls for it, the gun remains world-building.  If
too much salience was spent on it, the story may need to pay it off, deflate it,
or intentionally reclassify it as misdirection.

This gives future planning systems a concrete question to ask:

- Which disclosed hooks remain latent?
- Which hooks are compatible with the current telos and emerging story arc?
- Which hooks have accumulated enough salience that they should pay off,
  invert, or be deliberately retired?
- Which proposed twist can be supported by earlier disclosures without
  violating the observed syuzhet?

The implementation implied by this section is not present yet.  It points
toward a future constraint authority over the fact ledger: hard disclosures,
soft assumptions, latent hooks, morphology/genre constraints, and authorial
telos would be solved together before the next beat is reduced to journal
prose.

---

## Landmarks in Story Space

The graph's nodes are **landmarks** — fixed points of authored narrative
content.  Between them lies interpolation territory: template-driven text,
procedurally selected details, contextual descriptions drawn from the
namespace.

The density of landmarks determines the confidence of the narrative:

- **Dense landmarks** (many authored blocks, specific dialog) → a tightly
  controlled experience, closer to a traditional novel or visual novel
- **Sparse landmarks** (few key scenes, procedural connections) → a more
  emergent experience, closer to a tabletop RPG or roguelike narrative
- **Mixed density** → the typical case, where critical plot points are
  densely authored and transitional content is procedurally generated

This is the "authoritative nonsense" principle: between landmarks, the engine
generates confident, detailed-sounding descriptions through vocabulary banks
and templates.  The same mechanical seed ("roll on the tavern atmosphere
table") renders through different thematic vocabularies to produce genre-
appropriate prose.  The reader experiences *specificity*; the author only
wrote *structure*.

**Implementation:** Template registries with scope-based selection; vocabulary
banks as namespace contributors; render handlers that interpolate authored
content with contextual detail.

---

## Parametric Story Space

Stories exist in a low-dimensional **parametric space** defined by structural
properties: protagonist agency, dramatic tension, stakes, pacing, moral
complexity.  These parameters are the *controls* of the narrative — the
knobs an author or algorithm can turn.

The fabula graph encodes specific points in this space.  Different traversals
through the same fabula trace different curves through the same parameter
space.  A path where the player always cooperates traces a different
tension curve than a path where the player always defies authority.

This parametric view enables several capabilities:

- **Similarity metrics** — quantify how "different" two story paths are by
  measuring distance in parameter space
- **Interpolation** — generate a story "between" two known paths by
  blending their parameter trajectories
- **Style transfer** — project the same parameter trajectory through
  different thematic vocabularies ("tell this tension curve as noir" vs.
  "tell it as comedy")
- **Verification** — check that all traversals through a fabula stay
  within acceptable bounds on critical parameters (e.g., tension never
  drops to zero, agency never becomes illusory)

The key insight: because the parametric space is defined by the graph
structure (not by the prose), it provides **ground truth** for controlled
experiments.  You can manipulate a clean semantic model and observe how
it projects into narrative — unlike LLM-based approaches where the
parameters and the prose are entangled.

**Implementation status:** Parametric space is conceptually defined but
not yet instrumented.  The graph structure *implies* these parameters;
extracting them requires analytics tooling that is on the research
roadmap.  See the research agenda for "Narrative Shape Space" directions.

---

## The Observer Roles

```{storytangl-topic}
:topics: multi_lane
:facets: overview, design
:relation: documents
:related: journal, ledger, traversal
```

Three roles interact with the narrative system, each engaging a different
layer:

| Role | Engages | Primary Actions |
|------|---------|-----------------|
| **Creator** | Fabula | Define story world, write scripts, set up concept templates and dependencies |
| **Navigator** | Episodic process | Make choices, trigger traversals, observe state changes |
| **Presenter** | Syuzhet | Format journal output for a specific medium and audience |

These roles may be filled by humans, algorithms, or AI agents — the engine
doesn't care.  A human author creates the fabula; a human player navigates it;
a web client presents it.  But equally: an LLM could author worlds, a
Monte Carlo tree search could navigate for testing, and a PDF generator
could present for print.

The **multi-lane** extension (planned) allows multiple navigators to traverse
the same fabula simultaneously from different perspectives, producing
interleaved syuzhets that can be cross-referenced.

The important conceptual move is that **navigation is an orthogonal role**.
The navigator is not necessarily the presenter, and is not necessarily the
creator. A human reader may pick choices directly, but so may a scheduler, a
test harness, an AI policy, or a replay driver. Multi-lane stories extend that
same idea rather than introducing a new ontology: several navigators operate on
the same underlying fabula, each with its own visibility, perspective, and
decision policy, while the service/presentation layer remains free to surface
one lane, several lanes, or a stitched cross-reference view.

**Implementation:** Creator → `StoryCompiler` + `WorldBuilder`;
Navigator → `Frame` + `Ledger` (user choices drive `follow_edge`);
Presenter → typed journal fragments + an application/client presentation adapter.

---

## Determinism and Replay

Working law 8 states the intent: a walk reproduces from its starting
configuration, and the same choices from a different start land on essentially
the same story state.  This section says why that matters and what the engine
currently does about it.

It is a **narratological commitment** as much as an implementation choice.  The
syuzhet is a *particular* collapse of the fabula.  To study narrative
structure, you need to be able to reproduce that collapse, branch from a point,
and compare alternative collapses.  Without that, the engine would be a
storytelling tool.  With it, the engine is a **narratological instrument**.

What supports it today:

- **A record per step.**  The ledger keeps a step record and a state delta for
  every traversal hop, and a full checkpoint at the start and periodically
  thereafter.  Rollback restores a checkpoint and applies the deltas after it;
  each delta carries the state hash before and after, so a mismatch is
  detected.
- **Seeded chance.**  Random draws during a step come from a generator seeded
  from the current story state, the cursor and the step, so re-planning the
  same step gives the same result.
- **Ordered dispatch.**  Handlers run in a defined priority order within each
  phase, and receipts record what ran.
- **Recorded realizations.**  The journal stores what was told, so reproducing
  a telling does not depend on re-running whatever produced it.  Generated
  media keeps the request it was made from and the hash of its content.

What it does not yet do:

- Two stories created from the same world do not share identities, so a list
  of choices from one cannot be applied to another by identifier.
- The step record names the edge that was chosen but not any payload that came
  with the choice.
- Nothing re-executes a list of choices and compares the result with the
  recorded one.

**Implementation:** `Ledger` (step records, replay deltas, checkpoints);
`DiffReplayEngine`; the seeded generator on `Frame`; `CallReceipt` on every
dispatch.

---

## Theoretical Heritage

StoryTangl draws on established narratological theory, but treats it as
**engineering specification** rather than literary criticism.  The question
is not "is Genette's taxonomy correct?" but "can we implement it as code,
and does the implementation reveal anything the theory didn't predict?"

Key correspondences:

| Theorist | Concept | Engine Mapping |
|----------|---------|----------------|
| **Bal** | Fabula / Story / Text | Graph / Frame / Journal |
| **Genette** | Order, duration, frequency, focalization | Phase bus operations (planned discourse layer) |
| **Chatman** | Kernels vs. satellites | Required vs. optional dependency edges |
| **Barthes** | Nuclei vs. catalyzers | Planning-phase offers (critical) vs. provisioning backfill (optional) |
| **Propp** | Morphological functions | Re-entrant subgraph templates (cycle patterns) |
| **Aarseth** | Scriptons / textons | Journal output / graph + ledger |
| **Short** | Storylets + QBN | Offer system with dependency preconditions |

The engine is designed to validate these theories empirically: if Bal's
three layers genuinely capture independent concerns, then modifying the
discourse layer should change how a story *reads* without changing what
*happens*.  If Chatman's kernel/satellite distinction is real, then removing
satellite nodes should leave the story structurally complete.  These are
testable claims, and the engine provides the apparatus to test them.

For implementation-specific follow-up, see the subpackage design notes and the
research-direction summary in the root README.

### Crawford's Erasmatron — research antecedent

Chris Crawford, "[Assumptions Underlying the Erasmatron Interactive Storytelling
Engine](https://www.cs.cmu.edu/~michaelm/nidocs/Crawford.pdf)" (1999), in *Narrative Intelligence*, AAAI Fall Symposium,
Technical Report FS-99-01, pp. 112–114, argues for **verb-centered**
interactive drama rather than choosing character or plot as its primary atom.
An authored dramatic *sentence* binds a verb to participating actors and
secondary objects; each role carries options for plausible reactions. The
engine automates comparatively mundane behavior, such as movement and gossip,
while artist-specified decision equations guide dramatically significant verb
choices. Crawford's proposed **assisted storytelling** instead lets the user
direct characters by selecting among viable actions.

His example of Lancelot's gossip algorithm telling Arthur about the affair
with Guinevere illustrates how a locally sensible decision can fail against
the larger relationship context. His **complexity-threshold** argument and
reported difficulty getting authors to finish storyworlds are useful warnings
about the gap between correct transitions and believable drama, and about the
cost of authoring behavioral policies.

This is historical prior art for the parked [Project Deikto research issue](https://github.com/derekmerck/storytangl/issues/643):
dramatic situation schemas, role-bound action/reaction affordances, and
navigation/selection policy are separable concerns. It is **not** a claim that
Erasmatron's historical language or autonomous dramatic behavior is already
implemented in StoryTangl.

---

## What This Document Does Not Cover

- **How** the phase pipeline works → see `engine/src/tangl/vm/VM_DESIGN.md`
- **How** the graph primitives work → see `engine/src/tangl/core/CORE_DESIGN.md`
- **How** story concepts are modeled → see `engine/src/tangl/story/`
- **Where** a narrative distinction should live (prose, structure, or a
  contributed affordance) → see [NARRATIVE_CONTROL.md](NARRATIVE_CONTROL.md)
- **How** the service layer transforms fragments → see `engine/src/tangl/service/`
- **What** research directions follow from this → see the root `README.md`
  and package-level design notes

This document is the **why**.  The subpackage design docs are the **how**.

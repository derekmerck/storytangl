# Conceptual Foundations

> Why the system works the way it does, and the metaphors that keep it honest.

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

In the engine, the fabula is the **story graph** after compilation: a set of
structural nodes (scenes, blocks, actions), resource nodes (actors, locations,
assets), and dependency edges connecting them.  The fabula is authored — it comes
from YAML scripts, compiled by the story compiler and materialized into a
navigable graph.

The fabula contains more stories than any single traversal will realize, just as
a chessboard contains more games than any single match will play.

**Implementation:** `StoryCompiler` / `Materializer` → `StoryGraph`; the graph
and its registries encode all structural and conceptual possibilities.

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
roles (narrative content, dialog, choices, media) but not rendering instructions.
The service layer translates fragments into a specific presentation format based
on client capabilities.

**Implementation:** `Journal` / `OrderedRegistry` of `BaseFragment` subclasses
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
any traversal happens, and you can replay a specific syuzhet deterministically
from a snapshot plus a choice log.

---

## The Compiler Metaphor

The fabula/episodic/syuzhet separation maps directly to a compiler pipeline:

```
Front-end:  Scripts (YAML, Twee, Ink...)
               ↓ parse + compile
IR:         Story Graph (the fabula)
               ↓ traverse + resolve
Back-end:   Journal Fragments (the syuzhet)
               ↓ render
Output:     CLI / Web / PDF / ...
```

Like LLVM's intermediate representation, the story graph is a **universal
substrate** that captures narrative intent while abstracting away both the
source format and the target medium.

This is why transpilers between interactive fiction formats are architecturally
natural: a Twine file and a StoryTangl YAML script are different front-ends
compiling to the same IR.  The graph doesn't care where it came from.

And like a compiler, the engine's phases are **deterministic, ordered passes**
over the IR.  Each phase has a defined contract (what it reads, what it may
mutate, what it returns).  The pipeline is auditable because every phase
produces receipts.

**Implementation:** `StoryCompiler.compile()` (front-end) → `StoryGraph`
(IR) → `Frame.follow_edge()` phases (back-end passes) → `Journal` (output).

---

## Narrative Debt and Credit

When the episodic process recruits a concept — say, casting an actor into a
role — but the journal hasn't yet introduced that concept to the reader, the
story carries **narrative debt**.  The reader doesn't know who Marta is yet,
even though the engine has already committed to her as the villain.

Conversely, when the journal introduces a concept before it becomes
structurally necessary, the story holds **narrative credit**.  Mentioning the
old sword on the mantelpiece in Act I creates credit that Act III's sword
fight will draw down.  (Chekhov knew this, but didn't have a dependency
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

**Implementation:** Creator → `StoryCompiler` + `Materializer`;
Navigator → `Frame` + `Ledger` (user choices drive `follow_edge`);
Presenter → `GatewayHooks` + render profiles in the service layer.

---

## Determinism and Replay

Every mutation in the engine is **event-sourced**: state changes are captured
as patches in the ledger, and the complete history of a story instance is
reproducible from a snapshot plus the patch log.

This is not just an implementation convenience — it's a **narratological
commitment**.  The syuzhet is a *particular* collapse of the fabula.  To
study narrative structure, you need to be able to replay that collapse,
branch from any point, and compare alternative collapses.  Without
deterministic replay, the engine would be a storytelling tool.  With it,
the engine is a **narratological instrument**.

Determinism requires discipline:

- **Seeded RNG** — random choices during provisioning use a seed derived
  from `(story_id, step, choice_hash)`, so the same choice at the same
  point always produces the same outcome
- **Ordered dispatch** — handler execution follows deterministic priority
  ordering within each phase; receipts record exactly what ran
- **External IO logging** — any non-deterministic input (LLM responses,
  media generation) is recorded in the patch so replay doesn't need to
  re-invoke external services

**Implementation:** `Ledger` (event-sourced patch log); `DiffReplay`
(snapshot + patches → reconstructed state); seeded RNG in resolver;
`JobReceipt` audit trail on every dispatch.

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

For a detailed survey, see the *StoryTangl Literature Review (2025)* and
the research agenda.

---

## What This Document Does Not Cover

- **How** the phase pipeline works → see `engine/src/tangl/vm/VM_DESIGN.md`
- **How** the graph primitives work → see `engine/src/tangl/core/CORE_DESIGN.md`
- **How** story concepts are modeled → see `engine/src/tangl/story/`
- **How** the service layer transforms fragments → see `engine/src/tangl/service/`
- **What** research directions follow from this → see `storytangl-research-agenda.md`

This document is the **why**.  The subpackage design docs are the **how**.

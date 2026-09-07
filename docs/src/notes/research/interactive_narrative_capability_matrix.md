:::{admonition} Repository context
:class: note

This is a non-normative research note archived on 2026-08-29 from an
agent-produced capability overview supplied for StoryTangl design discussion.
It is useful as an adversarial coverage map and source of demo hypotheses, not
as evidence of current implementation or as an implementation roadmap.

Claims about StoryTangl must be checked against live code and governing design
documents. Comparative engine, toolchain, corpus, and extraction claims remain
unverified unless separately sourced; the document's Appendix B makes that
boundary explicit. The current fixture-to-showcase lifecycle is tracked in
[GitHub issue #395](https://github.com/derekmerck/storytangl/issues/395), and
the canonical mechanics/demo policy remains in
[`MECHANICS_FAMILIES.md`](../../design/story/MECHANICS_FAMILIES.md).
:::

# Interactive Narrative Capability Matrix

*Revision 2. Changes from r1: per-row facet tags, an explicit falsifier, a dual scorecard separating
build value from argument value, and relocation of all engine-internals and shipped-format claims to
a clearly marked unverified appendix.*

---

## What this is

Not a survey, and not a roadmap. It is an **adversarial coverage map**: the interactive-narrative
design space, organized by the smallest formal object each work requires an engine to represent, so
that a demo program can be checked for coverage gaps and for claims it hasn't earned.

It is deliberately silent on what is built. Rows describe possibility space; whether a given row is
already evidenced, one extension away, or a genuinely new capability is a separate judgment that
belongs next to the code and changes weekly. The `Status` field on each row is left empty for that
reason — fill it in against reality, not against this file.

**It does not replace an incremental build order.** Demos should continue earning primitives one
reusable pressure at a time, in implementation-dependency order. This map's job is to periodically
ask what that order is *not* covering, and to keep each demo's claim honest.

## The two scorecards

A demo can be architecturally redundant and rhetorically essential, or vice versa. These are
different axes and collapsing them causes bad prioritization in both directions.

- **Build value** — does this force a reusable primitive, compose with existing rails, and expose
  framework friction? Optimizes for a compact engine.
- **Argument value** — does this demonstrate something the alternatives structurally cannot do?
  Optimizes for legibility to someone deciding whether the project is interesting.

Every row carries both. High-build/low-argument rows are good next slices. Low-build/high-argument
rows are north stars — and are often better served by a **paper probe** (a written spec plus a
hand-traced execution against current contracts, no implementation) than by a build. A probe that
reveals a missing type costs a day; discovering the same thing after six demos have accreted around
the wrong assumption costs a quarter.

## Facets

A single "features exercised" column is not commensurable across rows, because rows test different
kinds of question. Each axis is tagged with the facets it actually stresses:

| Tag | Facet | The question |
|---|---|---|
| **R** | Runtime representation | Can the model hold this state and these transitions? |
| **S** | Static analysis | Can something *prove* a property before play? |
| **A** | Authoring compactness | Can an author declare this without unrolling it by hand? |
| **P** | Presentation / syuzhet | Can the same history be projected into different orderings and voices? |
| **C** | Client affordance | Can the player see what the system permits? |
| **M** | Measurement / corpus | Is this a study rather than a demo? |

A system may represent a mechanic without proving it, prove it without presenting it legibly, or
render it without offering compact syntax. Rows that are thin on R/S are not weak rows; they are
rows about something else.

## Cross-cutting parameter: traversal budget

*Referenced by A04, A14, A15, A20. This is a parameter of the analysis, not a property of any one
row.*

**Soft-lock is not a property of the graph. It is a property of the graph plus a traversal model.**
"Is this completable?" is malformed until you say under which model, because a dead end under
unlimited rewind is not a dead end — it's a leaf you visit and back out of.

The print corpus makes this obvious in a way the digital descendants obscured. Readers played
gamebooks with a thumb on the choice page, reading each outcome and keeping a second thumb on the
preferred one: depth-first search with cheap backtracking. That was never cheating. **A codex is
random-access**, holds multiple positions at once, makes backtracking free, and exposes branch
structure physically as thickness. Twine has vastly more computational power and strictly less
affordance — one position, no lookahead, invisible graph. That is a regression, and it happened
because the tooling modeled the fiction's traversal rather than the reader's.

So Plotkin's Cruelty Scale is best read not as a difficulty ladder but as **a family of traversal
models parameterized by rewind budget**:

| Level | Rewind budget | Failure detectability |
|---|---|---|
| Merciful | unlimited | n/a — cannot lock |
| Polite | bounded (n nodes / n saves) | immediate |
| Tough | zero | immediate signal |
| Nasty | zero | delayed signal |
| Cruel | zero | none |

Two consequences worth holding onto:

**Completability analysis takes the budget as an input.** The same declaration yields different
answers at different budgets, and reporting the *budget at which a story becomes completable* is a
more informative result than a boolean.

**The rewind affordance can be a designed, diegetic, costed move.** Shipped precedents: an explicit
rewind that is designed rather than tolerated (inkle's *Sorcery!*); the branch graph as first-class
navigable UI (*428: Shibuya Scramble*, the Zero Escape flowchart, *Steins;Gate*) — a convention the
Japanese VN tradition adopted and Western choice fiction largely didn't, likely as an immersion-wing
genre inheritance rather than a considered position; and the diegetic version, where foreknowledge is
in-fiction (Elsinore's prophecy board, Outer Wilds' ship log). **A foreknowledge view is a journal
read forward** — the same reconstruction machinery, projecting into "what I know is possible" rather
than "what happened."

**Design tension worth preserving.** If dead ends mint knowledge tokens (loss as replay prestige,
A04), then a rewind affordance means *forfeiting the token you were about to earn*. The cheat is not
mercy for weak players; it is the impatient path, and a completionist never touches it. That is
self-balancing without tuning — but only if the forfeit isn't fully legible, because a legible
forfeit makes the cheat strictly dominated for anyone optimizing, and a dominated option is dead
content. Two fixes: charge a *different* currency so it's a cross-type trade (time, standing,
condition), or leave the forfeit **opaque** — you know the dead end would have taught you something,
not what. The second is preferable. It isn't obfuscation; it's the engine of replay, and it keeps the
rewind a choice made under uncertainty rather than an arithmetic comparison.

## Row fields

- **Facets / Scorecard / Status** — as above.
- **Formal object** — what must be representable, in one paragraph.
- **Minimal witness** — the smallest artifact that demonstrates it. Scope pressure made visible.
- **Capability claim** — the smallest formal distinction being proved. Not "mechanics that appear."
- **Falsifier** — *what outcome would show the demo proved nothing* — i.e. that the engine merely
  hand-authored the same branch structure with extra ceremony. **This is the most important field.**
- **Exercised** — which representational or analytic pressure the row applies. Phrased as pressures,
  not as claims about any existing contract.
- **Corpus signal** — what the shipped artifact's *shape* reveals about authoring strategy. Firsthand
  forensics only; format and toolchain specifics live in Appendix B.
- **Out of scope** — what does not survive translation. Scope defense, not modesty.

**Prior art.** Ashwell, *Standard Patterns in Choice-Based Games* (topology only); Swinehart, *One
Book, Many Readings*; Aarseth, *Cybertext* (right move, dated axes); Kreminski & Wardrip-Fruin,
storylet design space (ICIDS 2018); Short on quality-based and salience-based narrative; Nelson,
*Craft of Adventure*; Plotkin's Cruelty Scale; Martens, *Ceptre*; Ryan on story sifting. None index
on engine capability; that's the gap.

---

## A00 — Entity-collection management sim

**Facets:** R, S, A · **Build:** high · **Argument:** high · **Status:** _____

**Exemplars.** **Free Cities**, Stardew Valley / Harvest Moon, Dustland Delivery, Beholder.

**Formal object.** N tracked entities with per-entity typed state; a periodic tick applying rule sets
across all of them; aggregates derived rather than stored; narrative triggers on both individual and
aggregate thresholds, via distinct mechanisms.

**Minimal witness.** Twelve entities, three tick rules, four trigger passages — two per-entity, two
aggregate.

**Capability claim.** Collection-typed state with per-element predicates can be declared once and
applied across a population, and cross-tick data flow is inspectable rather than emergent from
untracked globals.

**Falsifier.** If the twelve entities have to be enumerated in the source, or if adding a thirteenth
requires touching anything but data, the demo is a bespoke twelve-branch story wearing a loop.
Secondary falsifier: if a flag written and never read cannot be surfaced without playing.

**Exercised.** Population-scoped declaration; read/write summaries across a tick boundary; derived
aggregates as functions of history; deterministic replay of population effects.

**Corpus signal.** Free Cities is the pathological case: content and program are the same object.
Passages are string-producing expressions over live save state, so "what does this passage say" is
only answerable by executing it with a world state produced by other passages. A static extractor
isn't hard, it's ill-posed. The bundled sanity checker is the diagnostic — someone felt the absence
of static analysis acutely enough to write a checker, and the format gave them nothing to check
with, so it degenerated into runtime assertions over a live save. It can tell you the ship is
sinking; it can never tell you it will.

**Out of scope.** Balance. Ship it visibly untuned so nobody mistakes it for a game.

---

## A01 — Resource vs. knowledge tokens, with retry semantics

**Facets:** R, S · **Build:** high · **Argument:** high · **Status:** _____

**Exemplars.** **Disco Elysium** (white/red checks), Long Live the Queen, Citizen Sleeper.

**Formal object.** Red checks are one-shot; failure is consumed and becomes canon. White checks are
retryable only after world state changes. That's the linear/intuitionistic split made playable. The
Thought Cabinet adds an under-formalized object: a knowledge token with **acquisition latency** and
**sunk cost** — it cooks for N scenes and may land net-negative, with an unlearning price. Citizen
Sleeper adds a third class: renewable-per-cycle but *quality-degrading*, distinct from both
consumables and knowledge, and the reason clocks feel tense rather than arithmetic.

**Minimal witness.** One scene, three checks: a red check whose failure text is referenced later; a
white check gated on acquiring a specific token; a cycle-renewable pool whose face values shift with
a condition track. One thought with two-scene latency and a bad modifier.

**Capability claim.** Consumed and persistent tokens are distinguishable *by type*, not by author
convention, and a retry gate's satisfiability is decidable against the reachable token set.

**Falsifier.** If "one-shot" is implemented as a boolean the author remembers to set, the type
distinction is decorative. The claim only lands if something can answer "is this white check ever
passable from here" without playing.

**Exercised.** Token typing; modality on gate predicates; delayed effect scheduling; failure edges
as definitions consumed downstream.

**Out of scope.** Prose voice. The skills-as-interlocutors chorus is the famous part and the cheapest
part to imitate; building the demo around it turns it into a writing sample.

---

## A02 — Epistemic typing: assertion as a first-class move

**Facets:** R, S, P · **Build:** low · **Argument:** highest · **Status:** _____

**Exemplars.** **Umineko** (red truth / blue truth), Obra Dinn, Golden Idol, Orwell, Her Story.

**Formal object.** Red truth is an axiom asserted by the game master and guaranteed sound. Blue truth
is a player-side conjecture standing unless refuted. A two-sided proof system with an explicit
soundness contract, embedded in a VN. Red statements constrain fabula; blue statements are hypotheses
about fabula; the game is played entirely in the gap. Obra Dinn is the same axis with a coarse
difficulty valve (three-at-a-time confirmation is proof-checking with partial credit). Orwell's verb
is the same family: the player composes an assertion and the assertion is the move.

**Minimal witness.** A five-room murder. Three red statements. Blue statements composed from a fixed
predicate vocabulary; the system either refutes by producing a counter-model consistent with all red
truths, or concedes.

**Capability claim.** The epistemic status of a statement is a typed object, and refutation is
computed rather than authored.

**Falsifier.** If the set of accusations is enumerated in advance and each has a hand-written
rebuttal, this is a dialogue tree with a courtroom skin — which is what every VN mystery already is,
and the reason they all have three suspects.

**Exercised.** Knowledge tokens with provenance and truth-status; counter-model generation as a
lowering target; presentation independence from event order.

**Recommended form.** **Paper probe before build.** This row demands epistemic assertion types, a
compositional claim surface, solver-backed countermodels, and syuzhet machinery simultaneously — a
poor incremental slice and an excellent north star. Hand-trace one refutation against current
contracts. If epistemic status can't be carried without a new type, that finding is worth having
early and costs a day.

**Corpus signal.** In the source work the red/blue system is pure convention — the engine has no idea
a red line is an axiom. The formalism lives entirely in author and reader. That's the point.

**Out of scope.** The metafictional trial frame. Model the proof system, not the theology.

---

## A03 — Deduction over a static in-world corpus

**Facets:** R · **Build:** medium · **Argument:** low · **Status:** _____

**Exemplars.** **Strange Horticulture** / Antiquities, Sherlock Holmes Consulting Detective,
Heaven's Vault.

**Formal object.** A fixed reference text plus observable specimen properties. Deduction lives in the
player's head; state is only "which label is attached to which specimen." Zero simulation, maximum
knowledge-token purity — and per-item labeling is the *fine-grained* confirmation valve that Obra
Dinn lacks.

**Minimal witness.** Eight specimens, four observable properties, a reference book with
overlapping-but-discriminating entries, and two entries separable only via a clue delivered in a
later scene.

**Capability claim.** Non-consumable knowledge with no resource confound; and the discriminating
clue's availability before the puzzle needing it is checkable.

**Falsifier.** If the late clue's ordering is guaranteed by authoring it into a linear sequence, the
scheduling claim is vacuous.

**Exercised.** Static authored corpus addressable by the gate language; forward reachability
(Chekhov's gun run in the loading direction).

**Out of scope.** Atmosphere — which is most of why the exemplar works, and none of it is an engine
property. **Use this row as the control:** it is expressible everywhere, so it isolates knowledge
tokens without proving anything competitive.

---

## A04 — Loop-and-grow: death as information transfer

**Facets:** R, S · **Build:** high · **Argument:** high · **Status:** _____

**Exemplars.** **Long Live the Queen**, Save the Date, Outer Wilds, Overboard!, Elsinore.

**Formal object.** One line: knowledge persists across reset, resources don't. The token split made
*playable* rather than merely modeled. Outer Wilds is the extreme — nothing persists but player
knowledge, and the save file is literally a ship log.

**Minimal witness.** Four lessons, one assassination, three death-states each yielding exactly one
knowledge token. Run 1 unwinnable and provably so; run 3 winnable and provably so. **The proof is the
deliverable; the game is scaffolding.**

**Capability claim.** A reset boundary is an engine-level notion with declared persistence typing,
and completability is decidable per run given the carried token set.

**Falsifier.** If persistence is a convention ("these variables live in the outer scope") rather than
a declared property, nothing prevents a token from being silently cleared — the bug that manifests as
"the game is unwinnable and nobody knows why." If that bug remains undetectable, the row proved
nothing.

**Exercised.** Cross-boundary persistence typing; must-modality reachability; distinguishing "locked
out" from "not yet unlocked"; deterministic replay across runs.

**Traversal budget.** A loop *is* a rewind budget expressed diegetically — the reset is the
backtrack, and the knowledge token is what survives it. This row and A14 are the same analysis under
two skins, which is worth stating: if loss mints prestige, then any out-of-fiction rewind affordance
must forfeit that mint or the economy collapses. See the cross-cutting section.

**Out of scope.** Making repetition feel good. That's pacing.

---

## A05 — Syuzhet manipulation as mechanic

**Facets:** P, R · **Build:** medium · **Argument:** highest · **Status:** _____

**Exemplars.** **Spider and Web**, Her Story, Photopia, Sorcery! rewind, Umineko perspective stacking.

**Formal object.** Presentation is not a traversal of fabula. Spider and Web's interrogation frame
retroactively re-types everything already played as unreliable — you replay your own past under a new
soundness assumption. Her Story makes query order the plot order, so the arc is a property of the
search sequence, not the corpus.

**Minimal witness.** A six-event fabula, two projections: chronological, and interrogation-order with
one event revealed as fabricated. The reveal must be a *re-typing* of an existing record, not the
insertion of a new one.

**Capability claim.** Fabula and syuzhet are separable at the load-bearing extreme: one history, two
orderings, one retraction that does not mutate the record it retracts.

**Falsifier.** If producing the second projection requires authoring the scene twice, the separation
is nominal. Write both projections from one declaration or the row fails.

**Exercised.** Journals as reconstruction algorithms projecting traversal into a different coordinate
system; append-only retraction (a new record referencing an old one); voice/reliability as a
projection parameter.

**Note.** This is the clearest structural differentiator in the file. Twine, Ink, and ChoiceScript
can all approximate storylets; none has principled fabula/syuzhet separation.

**Out of scope.** The specific twist. Twists are authored; the engine only makes them cheap.

---

## A06 — Conversation as a system, not a tree

**Facets:** R, A, C · **Build:** highest · **Argument:** medium · **Status:** _____

**Exemplars.** **Monkey Island insult swordfighting**, Oxenfree (timed overlap / interruption),
Va-11 Hall-A (indirect verb), Versu, Valve's rule-database dialogue (Ruskin, GDC 2012).

**Formal object.** Comebacks are knowledge tokens acquired *by losing*; resolution is a matching
relation over a lexicon learned incrementally. The failure state is the acquisition channel. Oxenfree
adds temporality — options have windows, silence is a move, interruption is a distinct verb. Va-11
Hall-A adds indirection: you choose what to serve, and the conversation is downstream.

**Minimal witness.** An eight-item lexicon, a matching relation, acquisition-on-loss, and one
opponent using a phrase you cannot counter (forcing a loss to progress). Then the same encounter with
a timing window.

**Capability claim.** Response selection is dispatch over a fact set rather than an authored branch,
so the lexicon can grow without editing a tree.

**Falsifier.** If adding a ninth phrase requires touching anything but data, this is a match table
with extra steps.

**Exercised.** Best-match dispatch; token acquisition on failure edges; timed affordances; the
print-vs-interactive channel distinction, which matters more than usual when silence is a move.

**Corpus signal.** The matching relation is a table — a few hundred bytes. The mechanic scales with
lexicon size, not content size. Direct evidence for A16.

**Note.** Highest build value on the list: a compact second consumer of existing conversational,
progression, and persistence rails. Natural next slice.

**Out of scope.** Timing feel. Window tuning is real-time UI.

---

## A07 — Rulebook application and the discretion gap

**Facets:** R, S, A · **Build:** high · **Argument:** high · **Status:** _____

**Exemplars.** **Papers, Please**, Beholder, Not Tonight, Orwell, *hall monitor*.

**Formal object.** Rules accrete; new rules conflict with old ones on constructible cases; the player
applies them under incomplete information; the gap between rule and conscience is the drama.

**Minimal witness.** Day 1: one rule. Day 5: six rules, at least two conflicting on a constructible
case, and one case where compliance harms a sympathetic party.

**Capability claim.** Rules are declarative data over a shared predicate vocabulary, and the
conflicting case can be *enumerated by the system* and handed to the author as a report.

**Falsifier.** **If the author has to know the conflicting case exists in order for the report to
find it, nothing was proved.** The whole claim is that the analysis discovers cases the author didn't
construct. This is the sharpest falsifier in the file and the row should be built to meet it.

**Exercised.** Rule sets as data; satisfying/conflicting instance enumeration; per-day scoped
summaries; distinguishing "this case is possible" from "this case is inevitable."

**Note on scorecards.** A runtime hall monitor may be architecturally redundant with existing gating
work while remaining rhetorically essential, because *the compile-time conflict report is the
argument*. A rich runtime vertical is what Twine already does adequately-if-painfully. Score this row
on both axes separately.

**Out of scope.** Dexterity. Roughly 40% of the exemplar's fun is manual speed under time pressure
and none of it transfers. Put that in the README rather than pretending otherwise.

---

## A08 — Schedules and legible opportunity cost

**Facets:** R, A, P · **Build:** high · **Argument:** medium · **Status:** _____

**Exemplars.** **I Was a Teenage Exocolonist**, Princess Maker, Citizen Sleeper, Pentiment.

**Formal object.** Fixed slots, more claims than slots, every allocation visibly foreclosing another.
Exocolonist's memory deck is the best steal available: **the deck is the event log, surfaced as a
mechanic.**

**The near-miss, which is the useful part.** Those cards resolve to flat stat checks, so the
autobiography never talks back to the simulation. The deck is a beautiful read-only view of history.
Making it *write* is the open design space.

**Minimal witness.** Twelve turns, three slots each, four activity tracks. Each completed activity
mints a memory card **derived from the actual event record, not from a template keyed by activity
type**, and cards are playable into later challenges in a way that alters world state rather than a
check total.

**Capability claim.** Content can be generated from history at resolution time, rather than
pre-decided at authoring time.

**Falsifier.** If the card text is chosen from a fixed set keyed by which activity was picked, this
is a stat tracker with a scrapbook. The derived-from-record property is the entire claim.

**Exercised.** History as queryable structure; sifting predicates over traversal; derived content
generation; opportunity-cost reachability under a slot budget.

**Out of scope.** Twenty-year lifepath scope. Twelve turns proves the mechanism.

---

## A09 — Autonomous fabula the player intersects

**Facets:** R · **Build:** high · **Argument:** medium · **Status:** _____

**Exemplars.** **Deadline** (1982), Overboard!, Elsinore.

**Formal object.** NPC schedules execute whether observed or not; knowledge propagates between
characters on co-location; the player is a perturbation rather than a protagonist. Elsinore adds the
loop, making knowledge the only lever.

**Minimal witness.** Four NPCs, a twenty-tick schedule, three locations, one murder, NPC-to-NPC
knowledge propagation. **The player can be absent and the crime still resolves.**

**Capability claim.** The world advances under concurrent autonomous agents with per-agent knowledge
state; the player is one effect source among several.

**Falsifier.** If replay with the player elided doesn't produce an identical log from the same seed,
the autonomy is entangled with player traversal. That's a strong, cheap test and it should be the
demo's assertion.

**Exercised.** Resolution frontier under concurrency; per-agent rather than global knowledge;
deterministic replay without input.

**Corpus signal.** The 1982 exemplar's daemon structure is visible in disassembly. The phase
separation between world-model and text was better forty years ago than in most modern narrative
tooling — a recurring theme, and the strongest evidence that the trend since is regression.

**Out of scope.** Believable social simulation. Four NPCs on rails is the target; Versu is a research
program.

---

## A10 — Attrition-driven emergent narrative + sifting

**Facets:** R, P, A · **Build:** high · **Argument:** high · **Status:** _____

**Exemplars.** **Keep Driving**, Dustland Delivery, Death Road to Canada, Oregon Trail,
Where the Water Tastes Like Wine (negative), Sunless Sea.

**Formal object.** Narrative as a byproduct of bookkeeping. Encounters are small turn-limited puzzles
over parallel depleting resources (fuel, energy, time-of-day) where items and skills are
cooldown-bearing cards and hitchhikers are walking modifier sets with their own consumption. The
story is "what state was I in when I arrived" — a sifting problem over history, not an authored
branch. WTWTLW is the honest failure: it separates acquisition from retelling and then makes the
retelling inconsequential, so the sifting layer is inert.

**Minimal witness.** Six legs, three depleting resources, an encounter deck with cooldowns, two
hitchhikers with consumption modifiers — plus a **post-hoc journal produced by sifting the history**
for salient subsequences: near-misses, resource nadirs, who was aboard for the worst leg. **The
journal is the demo; the driving is scaffolding.**

**Capability claim.** Salience is computed after the fact from a queryable history.

**Falsifier.** If anything in the run sets a "this was memorable" marker at authoring time, the row
proves the opposite of its claim. Pre-deciding what will matter is exactly the failure mode.

**Exercised.** Sifting over append-only history; journal-as-reconstruction; multi-resource typed
consumption; procedural encounter selection under declared preconditions.

**Out of scope.** Driving feel, pixel-art vibes, and journal *prose* quality — output structured
beats, not sentences. Natural-language quality is a separate problem and claiming it here would
undermine the real result.

---

## A11 — Recipe systems / timed multiset rewriting

**Facets:** R, C · **Build:** medium · **Argument:** medium · **Status:** _____

**Exemplars.** **Cultist Simulator** / Book of Hours, Potion Craft.

**Formal object.** A timed multiset-rewriting engine with good typography. Cards carry typed aspects;
verbs consume card sets matching a pattern; timers produce new cards; everything is consumed on use.
Linear logic in the wild.

**The instructive failure, and the reason this row is here.** The recipe space is opaque, so play
degenerates into wiki consultation. **Expressive preconditions with no affordance surface produce
spreadsheet play, not discovery.** Book of Hours partly fixes it by making the reference material
diegetic — the library *is* the wiki — which is the design answer worth stealing.

**Minimal witness.** Twelve cards, three aspect types, five pattern-preconditioned verbs, timers, and
a **legibility layer** answering "what could I do with what I hold" without an external source. Then
instrument it: what fraction of the reachable recipe space does a player find unaided?

**Capability claim.** The precondition language is *introspectable* — affordances can be projected
out of it — which is a stronger and more design-relevant property than being solvable.

**Falsifier.** If the affordance list is hand-authored alongside the recipes, the projection claim is
false and the two will drift apart within a week of content additions.

**Exercised.** Aspect-typed linear tokens; pattern-matched consumption; scheduled effects; affordance
projection from the gate language.

**Out of scope.** Content volume. The exemplar is a library; the witness is a shelf.

---

## A12 — Obligation tokens: promises now, constraints later

**Facets:** S, R · **Build:** medium · **Argument:** high · **Status:** _____

**Exemplars.** **Suzerain**, Fabled Lands (codewords), Lone Wolf.

**Formal object.** A speech act in Act 1 creates a token checked in Act 3 with no intervening
representation. An unpaid promise is a **dangling definition**. Fabled Lands is the analog ancestor:
codewords are boolean knowledge flags persistent across volumes, checked by book-and-paragraph
lookup, and every operation had to be cheap enough for a human to execute by hand. If a formalism
can't express codewords trivially, something is wrong with it.

**Minimal witness.** Three acts. Four promises available in Act 1, of which two can be made. Act 3
checks all four. Produce an author report: which are dead, which are unkeepable, which form an
unsatisfiable conjunction.

**Capability claim.** Long-range data flow across region boundaries is analyzable in both directions
— promise never checked (unfired gun), check with no reachable promise (unloaded gun).

**Falsifier.** If the report is generated from a hand-maintained list of long-arc flags, it's a
spreadsheet. The claim requires the flags to be *discovered* from the declaration.

**Exercised.** Cross-region def-use; bidirectional Chekhov analysis; scoped import/export summaries.

**Corpus signal.** Watch flag naming: long-arc flags almost always carry a prefix convention
(`ACT1_PROMISED_X`). **People invent scopes out of string prefixes when the language doesn't provide
them** — the convention is itself evidence of the missing feature, and it's the cheapest forensic tell
in the file.

**Note.** This is the single most common real bug in long-form choice fiction, and it's currently
found by spreadsheets and beta readers.

**Out of scope.** Political simulation depth. The exemplar's economy is authored, not simulated.

---

## A13 — Spatial/combinatorial layout as narrative gate

**Facets:** R, S · **Build:** medium · **Argument:** high · **Status:** _____

**Exemplars.** **Blue Prince**, Sunless Sea/Skies (overworld + storylet coupling), roguelite maps.

**Formal object.** The map is generated per run under constraints; permanent progress is *player
knowledge about the constraint system*. The story is accumulated understanding of a generator.
Sunless Sea is the coupling case, where the interesting failures happen at the seam between
traversal-as-resource-layer and storylet-as-content-layer.

**Minimal witness.** A 5×5 grid drafted from a room deck under adjacency constraints; one goal room
reachable only via a particular configuration; and a report giving the fraction of seeds where the
goal is unreachable.

**Capability claim.** Reachability holds across a *generated* rather than authored space — which is
where solver-backed analysis stops being an implementation detail.

**Falsifier.** If the generator is constrained to always produce a solvable layout by construction,
the analysis is unnecessary and the row is a level generator.

**Exercised.** Generation under declared constraints; reachability over generated space; knowledge
tokens whose referent is the rule system rather than world state.

**Corpus signal.** Even perfect extraction yields the room deck and constraints but *not* the
reachable space, which must be computed. Good illustration that the interesting property is derived —
which is precisely why an IR beats a content dump.

**Out of scope.** Generator tuning. Fun distributions are a designer's problem.

---

## A14 — Analog constraint: the human interpreter as budget

**Facets:** A, S, M · **Build:** low · **Argument:** high · **Status:** _____

**Exemplars.** **Fighting Fantasy**, Lone Wolf, Fabled Lands, For the Queen / Microscope / Kingdom,
Demian's Gamebook Web Page (corpus of record).

**Formal object.** Every mechanic must be executable by a bored teenager with a pencil. That budget
forces tiny numeric state, boolean codewords, paragraph jumps. And the format's defining affordance
is **random access with free backtracking** — thumb-DFS was the dominant reading mode, not a
degenerate one. A formalism that can't represent "the reader will back up" is describing a game
nobody played. Prompt decks are storylets with a *human* arbiter, which cleanly isolates the
arbitration axis from the content axis.

**Minimal witness.** A twelve-paragraph gamebook fragment with three stats, two codewords, one
instant-death node — analyzed across the traversal-budget family: report the *minimum rewind budget
at which the fragment becomes completable*, rather than a completability boolean.

**Capability claim.** Completability is parameterized by traversal model, and the parameter is an
input to the analysis rather than a rendering switch. Merciful→Cruel is a rewind budget crossed with
failure detectability, not a difficulty ladder.

**Falsifier.** Two. If a print lowering can't be emitted from the same declaration, the compactness
claim is unsupported — a print target is a compression test, since it only works if the content
really was data. And if the analysis can only answer at one budget, cruelty is a label rather than a
parameter.

**Exercised.** Traversal budget as an analysis input; minimal-state lowering; graceful degradation to
a human-executable target.

**Corpus signal.** Digitized gamebook paragraph graphs are cheap, real test input for reachability
passes, and hobbyist reconstructions already exist.

**Out of scope.** Dice fidelity. Nobody needs a demo to prove 2d6 works.

---

## A15 — Parser-era world model and the cruelty inheritance

**Facets:** R, S · **Build:** medium · **Argument:** high · **Status:** _____

**Exemplars.** **Zork** / Colossal Cave, Sierra AGI/SCI, Monkey Island (as the reaction against),
Anchorhead.

**Formal object.** A simulated world with objects, containment, and physical predicates, where "dead
man walking" states were an era feature later treated as a defect. Sierra's reputation rests on
undetectable unwinnable states; LucasArts' on refusing them. **That argument is the prehistory of any
finishability formalism and the demo should say so.**

**Minimal witness.** A four-room fragment with one wastable consumable, in three variants: Cruel
(waste it, no signal, unwinnable), Polite (waste it, immediate signal), Merciful (can't waste it).
**Generating all three from one declaration is the demo.**

**Capability claim.** Soft-lock modality is a player-facing *output parameter*, not just an analysis
result — the same source emits different cruelty levels. Where A14 takes the traversal budget as an
analysis input, this row takes it as a *generation* input: the budget selects which signals and
rewind affordances get emitted into the played artifact.

**Falsifier.** If the three variants are three sources, this is three demos.

**Exercised.** Modality driving content generation; world-model predicates in the gate language;
Nelson's Player's Bill of Rights as a checkable property set rather than a style guide.

**Note.** Credit Inform 7 explicitly and precisely. It has a real world model and a real compiler;
what it lacks is solver-backed completability analysis and fabula/syuzhet separation. **Overclaiming
against Inform is the fastest way to lose the audience most likely to care.**

**Out of scope.** Parsing. Natural-language input is a separate research area.

---

## A16 — Story compression: pre-articulation vs. dynamic assembly

**Facets:** A, M · **Build:** low · **Argument:** highest · **Status:** _____

**Exemplars.** **Minuet** (negative), Dream Daddy (negative), Hatoful Boyfriend (negative),
Class of '09 (negative but funny), Loathing games and Monkey Island tables (positive).

**This axis is a measurement, not a demo, and it may be the headline result.**

**Formal object.** Minuet ships thousands of lines representing a couple hundred lines of actual
story content, pre-articulated across state combinations rather than assembled at runtime. That is
**manual loop unrolling of prose**. The string table is the diagnostic: near-identical paragraphs
differing in one clause are a Cartesian product an author enumerated by hand because the engine
offered no way to declare the axes.

**The claim has two halves, and the second is the interesting one.** Hand-unrolling doesn't just
bloat — it **undercovers**, because authors only enumerate combinations they thought of. A
declarative version covers combinations nobody wrote, which is simultaneously the selling point and
the risk (unbounded generation of unvetted text). The honest result reports both.

**Minimal witness (as a study).** One Minuet-shaped scene re-expressed as a fabula event + state-axis
declarations + an assembler. Emit all variants. Diff against the hand-written set. Report: source
lines, variants produced, **variants the original missed**, and **variants the assembler produces
that are bad**. That last number is the honest one and it must be published.

**Capability claim.** Surface realization is separable from event structure, and the separation
yields a measurable compression ratio *with a coverage gain rather than a coverage loss*.

**Falsifier.** If the assembler needs a special case per variant, the compression is illusory —
you've moved the unrolling into the assembler. Secondary: if the bad-variant rate is high enough to
require per-variant review, the coverage gain is not real, and the study should say so.

**Corpus signal — the most original material here.** **String-table shape reveals authoring
strategy.** Massive near-duplicate blocks ⇒ hand-unrolled. Templates with interpolation markers ⇒
runtime assembly. Sparse tables plus large code ⇒ generative, probably unextractable. Recommend
computing **duplication ratio** (near-identical n-gram blocks / total strings) per corpus. It's a
script, it's cheap, and it's a legible quantitative version of the entire argument.

**On timing.** Everything else quantitative can wait for defensibility. This one shouldn't — one real
number early is what keeps the compression claim from drifting into a slogan, and the corpora are
already decompiled.

**Out of scope.** Prose quality of assembled text. Assemblers produce serviceable, not good.

---

## A17 — Metafiction and engine violation

**Facets:** C · **Build:** none · **Argument:** low · **Status:** out of scope (see below)

**Exemplars.** **Doki Doki Literature Club**, Pony Island, Undertale's persistent save.

**Formal object.** The engine lies about its own state or the existence of its own content. Demands
land on the presentation layer, not the narrative layer.

**Recommendation: don't build this.** Write the boundary statement instead — which parts are
expressible (content that *claims* a passage was deleted; out-of-band persistence), which are
presentation-layer concerns deliberately not owned, and which are genuinely out of scope. **Knowing
where the boundary is beats a demo that half-crosses it.** This row exists as scope defense; the
finding is that there's nothing here to exercise.

**Corpus signal.** The exemplar ships its own "corrupted" assets as authored content, so a naive
extractor recovers them faithfully and learns nothing. Pleasant edge case for the forensics section.

---

## A18 — Tone-carrying systems (comedy as a mechanic)

**Facets:** — · **Build:** n/a · **Argument:** constraint · **Status:** _____

**Exemplars.** **West of Loathing** / Kingdom / Shadows of Loathing, South Park: The Stick of Truth &
The Fractured But Whole.

**Not a demo — a constraint on the demo set.** The South Park games are the masterclass: gameplay
supports character and character justifies gameplay, in both directions, so neither reads as a skin
over the other. If every demo is a formal exercise in a gray box, the project reads as a solver
looking for a problem. **One demo should be funny**, and A07's hall monitor is the natural candidate —
the bureaucratic absurdity *is* the rule-conflict analysis made visible.

**Out of scope.** Everything else. Do not attempt to formalize humor.

---

## A19 — Quality-based narrative and the coupling law

**Facets:** R, A · **Build:** medium · **Argument:** medium · **Status:** _____

**Exemplars.** **Fallen London**, Sunless Sea/Skies, StoryNexus, Mask of the Rose (negative).

**Formal object.** Qualities as typed state; storylets with quality preconditions; a selection policy
over the eligible set. The direct ancestor of any contract-layer design and worth citing as such —
Kreminski & Wardrip-Fruin's paper is largely a formalization of it.

**Two negative results worth recording.**

1. Fallen London couples content gating to a time-monetized action economy. The QBN structure is
   sound; the pacing layer is a business model. Keep those separate, because people conflate
   "storylet games are slow" with "storylets are slow."
2. **Mask of the Rose is the most useful failure on the list**, because the studio should have nailed
   it. Deduction bolted onto a relationship sim, neither system constraining the other — an
   underdetermined mystery beside a thin affinity model.

**The coupling law, which generalizes.** *Two systems must constrain each other or ship as one.* Two
systems that don't interlock read worse than one system alone. This applies directly to the demo
suite: **any demo combining two axes must make them mutually constraining, or it will demonstrate
less than either axis would separately.** A capstone where several systems mutate the same durable
object satisfies this; a sampler where six minigames share a menu does not.

**Falsifier for any multi-axis demo.** Remove one system. If the other still plays essentially the
same, they weren't coupled and the demo is a sampler.

**Out of scope.** Economy design.

---

## A20 — Structural navigation as a player affordance

**Facets:** C, P, S · **Build:** medium · **Argument:** high · **Status:** _____

**Exemplars.** **428: Shibuya Scramble** and the Zero Escape flowchart (branch graph as navigable
UI), Steins;Gate, inkle's *Sorcery!* (designed rewind), **Elsinore's prophecy board** and Outer
Wilds' ship log (diegetic foreknowledge), gamebook thumb-DFS (the analog original).

**Formal object.** The reader is shown the *shape* of the possibility space and can move within it,
rather than occupying a single position in an invisible graph. Three families, in increasing order of
interest: an out-of-fiction flowchart; a costed in-fiction rewind; and a **diegetic foreknowledge
view**, which is a journal read forward — the same reconstruction machinery projecting into "what I
know is possible" instead of "what happened."

**Minimal witness.** A twelve-node fragment with a derived navigation view showing visited nodes,
known-but-unvisited nodes, and known-to-exist-but-unreached nodes as three distinct states — plus one
rewind move that costs something and forfeits an unearned knowledge token *without revealing what the
token was*.

**Capability claim.** The navigation view is **derived from the graph and the play history**, not
authored alongside them; and rewind is a costed move in the same economy as everything else, not an
out-of-band UI feature.

**Falsifier.** If the flowchart is hand-maintained, it will drift and lie — and a navigation aid that
lies is worse than none. Derivation is the whole claim. Secondary: if the rewind's forfeit is fully
legible, the affordance is strictly dominated for any optimizing player, which makes it dead content;
opacity is a design requirement, not a polish item.

**Exercised.** Forward projection of the reachable frontier (adjacent to reachability analysis, but
rendered rather than reported); three-valued node knowledge state (visited / known / rumored);
rewind as a typed transaction against the token economy; the print-vs-interactive channel split,
since a prophecy board is content and a flowchart is chrome.

**Note.** This row is where the traversal-budget parameter becomes visible to the player, and it is
the strongest answer to "what does the analysis layer *give the reader*." Reachability analysis that
only ever produces author reports is invisible to everyone who isn't the author; a derived
foreknowledge view is the same computation, shipped.

**Out of scope.** Graph layout and visualization quality. Emit structure; drawing it well is a UI
problem, and a text listing is sufficient to prove derivation.

---

## Using this map

**Per demo, four annotations** (fitting alongside whatever decomposition record already exists):

1. **Capability claim** — the smallest formal distinction proved.
2. **Witness** — the minimal interaction or artifact demonstrating it.
3. **Falsifier** — what outcome would show it's hand-authored branch structure with ceremony.
4. **Compactness evidence** — reused kernels/data vs. bespoke residual. Qualitative first;
   quantitative only where defensible (A16's duplication ratio is the exception — measure it early).

**Per row, one classification**, made against the code and not against this file: already evidenced /
reachable via a planned extension / needs a genuinely new capability / research-and-measurement only /
presentation-layer or deliberately out of scope. That last bucket is load-bearing, not bookkeeping:
a substantial part of this map's value is **scope defense**. A17 exists to say *don't build this*.
The dexterity, prose-quality, atmosphere, and humor exclusions exist so that a mechanics proof is
never later mistaken for a fun proof. Finishability applies to the project too.

**Ordering heuristic.** Prefer high-build rows that are second consumers of existing rails (A06
repartee, A09 scheduled actors). Reserve high-argument/low-build rows (A02, A05) for **paper probes**
until the pressure they'd apply is worth a build. Let demos expose framework friction rather than
letting this map prescribe abstractions so that every row has a thick features column — that's how a
compact engine becomes a research-platform checklist.

---

## Design requirements that survive scrutiny

1. **Content should be statically extractable without executing the story.** Falsifiable, and the
   round-trip test (content out to a plain story database and back) is the check.
2. **Every precondition the gate language can express should have an affordance projection.** From
   A11. Solvability is not legibility; expressive gates without introspection produce wiki play.
3. **Two coupled systems must constrain each other or ship as one.** From A19.
4. **Soft-lock modality is a player-facing output parameter, not only an analysis result.** From A15
   and Plotkin's scale.
4b. **Completability is undefined absent a traversal model.** From the cross-cutting section. Every
   completability claim carries a rewind budget, and the more informative report is the *minimum
   budget at which a story is completable* rather than a boolean. Corollary: any rewind affordance
   offered to the player is a costed move in the token economy, and its forfeit must be opaque or it
   becomes dominated and therefore dead.
5. **Content derived from history must be derivable at analysis time, not pre-decided at authoring
   time.** *(Restated from r1, which claimed "the log is the story; flags are a cache." That was an
   ontological overreach — it implied flattening distinct stores with distinct lifecycle roles into
   one semantic event corpus, which is a major architectural decision and not something that falls
   out of examples. The requirement above is the actual finding from A08 and A10, it's the thing that
   `$memorableThing = true` violates, and it holds regardless of how many distinct stores exist.)*

---

## Appendix A — Recurring forensic observations

Firsthand, cheap, and the most original material in the document.

- **Data extracts; code doesn't.** The ratio between them measures a format's phase separation.
- **The trend is regression.** The formats with the cleanest separation are the oldest (text as a
  resource section, world model as a separate structure) and the most explicitly data-driven modern
  outliers. Ergonomics drove it: conditional text inside a passage is syntactically painful in the
  dominant tools, so the path of least resistance is copy-paste. **Engine ergonomics determine corpus
  shape** — which is why VN scripts are enormous and VN stories are small.
- **String-table shape reveals authoring strategy** (A16). Duplication ratio quantifies it.
- **Naming conventions reveal missing language features** (A12). People invent scopes out of string
  prefixes.
- **A checker that can only assert over live state is a validator, not a linter.** Its existence
  proves the need; its form proves the format couldn't support it.
- **Server-side content is the limit case** — logic and content live where extraction can't reach,
  which is a business decision with an epistemic side effect.

## Appendix B — Unverified claims

Everything below is recollection or inference and **none of it is load-bearing**. Verifying claims
about specific engines, toolchains, and shipped corpora to publication standard would consume real
effort without advancing any proof. Park it; cite it only if a paper needs it, and re-verify then.

- Comparative engine claims: Inform 7's world model and compiler vs. absent completability analysis
  and syuzhet separation; Ink's text-as-data-with-holes and knot enumeration; Ren'Py's script-as-data
  with embedded Python escape hatches (each `python:` block being a small Free Cities); ChoiceScript's
  convention-based persistence; SugarCube's absent scoping.
- Format and tooling specifics: Z-machine/Glulx disassembly and string sections; SCUMM resource
  layout; Ren'Py archive and bytecode decompilation; Godot pack extraction; Unity asset ripping and
  its il2cpp/mono split; NScripter archive obfuscation; Articy-derived dialogue databases.
- Per-title internals: Disco Elysium's condition language; Papers, Please's rule representation;
  Exocolonist's card definitions and text sourcing; Keep Driving's encounter and resource
  definitions; Suzerain's flag conventions; Strange Horticulture's reference-book layout; Cultist
  Simulator's JSON content model; Sunless Sea's entity files.
- **Exception worth promoting when confirmed firsthand:** any corpus already decompiled, where the
  duplication ratio can simply be computed. Minuet is the priority — it's carrying A16.

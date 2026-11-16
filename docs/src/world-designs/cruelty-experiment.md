# Cruelty Experiment: one world, different failure contracts

**Stage:** developed experimental demo-world brief; **implementation not
selected**. This is the proposed name of a future sibling world
(`cruelty_experiment`), not an existing executable world.
**Research origin:** the
[Interactive Narrative Capability Matrix](../notes/research/interactive_narrative_capability_matrix.md),
especially cross-cutting *traversal budget*, A14 (*analog gamebooks*),
A15 (*parser-era cruelty inheritance*), and A20 (*structural navigation*).
**Historical origin:** Andrew Plotkin's
[original Cruelty / Forgiveness Scale (1996)](https://eblong.com/zarf/essays/cruelty.html)
and [2019 reconsideration](https://eblong.com/zarf/essays/cruelty-revisited.html).
**Nearby proofs:** [Grand Grotto](https://github.com/derekmerck/storytangl/tree/main/worlds/adventure_sandbox_slice)
(spatial adventure, objects, inventory, light, locks, choice projection);
[One Red Paperclip](https://github.com/derekmerck/storytangl/tree/main/worlds/red_paperclip)
(ASP export and validated plan); and
[#396](https://github.com/derekmerck/storytangl/issues/396)
(optional observational formal-analysis contract).

## The experience

Give different readers **the same four-room puzzle**: a small map, one
irreplaceable consumable, a tempting way to waste it, and a local goal that
depends on keeping it. Every reader gets the same authored locations, object
identity, underlying causal puzzle, and ending objective. What differs is
the game's *contract with the reader*: what becomes visible before and after
a dangerous action, which actions can be committed, and which repairs or
retries are possible.

One reader may complete the puzzle, one may accidentally foreclose the only
solution and never learn why, and another may be protected from that mistake.
The comparison should make the distinction legible, not shame the player for
choosing a more punitive profile. **Cruelty is an intentional policy of
disclosure and recoverability, not a synonym for puzzle difficulty.**

## Original scale versus the proposed StoryTangl experiment

Plotkin's 1996 categories describe when an irreversible mistake becomes
recognizable and what the player must do to avoid redoing play. They were
**not** specified as rewind-budget values or a general API for changing a
game's transition relation. The matrix's traversal-budget interpretation
is a useful **StoryTangl research proposal**, not the historical definition.

| Plotkin category | What the reader can recognize |
| --- | --- |
| **Merciful** | They cannot become permanently stuck pursuing the defined goal. |
| **Polite** | They can become stuck, but that failure is immediately obvious. |
| **Tough** | They can become stuck, but the impending *irreversible* commitment is obvious beforehand. |
| **Nasty** | They can become stuck; an action's irreversibility is evident when it is done, though the damage may not yet be known. |
| **Cruel** | They can become stuck without an action's irreversibility being evident, even in retrospect. |

For an experimental realization, keep three dimensions conceptually separate:

1. **Failure policy:** which transitions are permitted, prevented, or
   furnished with alternate routes.
2. **Disclosure policy:** what the reader learns *before* committing,
   *immediately after*, and later about irreversibility or goal loss.
3. **Recovery policy:** whether the reader can restart, rewind, restore,
   pay a diegetic cost, or find a forward recovery path.

A **Merciful** profile need not expose infinite undo: it may simply block a
goal-destroying consumption or provide another route. **Tough** and **Nasty**
can differ in warning timing even if neither offers rewind. A rewind
operation can change the experience under any category; it is not the
category's definition.

## One authored declaration, three initial realizations

**First pass:** Cruel, Polite, and Merciful over one common world; defer
Tough, Nasty, and rich structural navigation until the narrower witness
works.

| Profile | Treatment of the same consumable action |
| --- | --- |
| **Cruel** | The player may trigger the fatal action, but its *irreversibility itself* is not apparent from the observations; the resulting soft lock is likewise undisclosed. |
| **Polite** | The player may spend it; the post-action response clearly explains that the declared goal has become unreachable. |
| **Merciful** | The player cannot enter the foreclosed state, e.g., because the waste action is blocked with a legible reason. A forward recovery path is a valid later alternative. |

The profile is **not a separately authored world or a copy of the scene**.
It is a policy applied to the same declared actions, state, and goal at an
explicit boundary. Changing whether a dangerous action can be committed
changes the *effective reachable transition system*; it is not merely
visual styling. It also must not silently mutate settled history when a
different client or policy replays the same journal.

A proposed future implementation might use ordinary action blockers,
post-choice journal contributions, and client-visible affordance hints.
No reusable `CrueltyPolicy`, rewind subsystem, new VM phase, or
solver-owned runtime choice authority is claimed to exist here.

## What should be analyzed

For a designated goal `g` and a modeled current state `s`:

- **Existential reachability:** is there at least one admissible continuation
  from `s` reaching `g`?
- **Foreclosure:** did a choice lead from a state where `g` was reachable to
  one where it is not?
- **Recoverability:** after the choice, does the selected recovery model
  make `g` reachable again?
- **Detectability:** what evidence of irreversibility or foreclosure was
  actually observable to the player at commitment and afterward?
- **Guaranteed completion under uncertainty:** is there a strategy that
  reaches `g` for every modeled possibility consistent with the player's
  observations and budget? This is a substantially harder, later question;
  ordinary existential plan search does not answer it.

A declared *goal* is required to interpret `unwinnable`: in an open-ended
commune, losing one tenant's quest is not necessarily losing the entire
story. Specify whether the test is about one optional goal, a protected set
of outcomes, or the whole game.

Analysis can use a target-specific logical projection, including Clingo,
but its results must say what state, actions, automatic transitions, and
horizon they cover. `UNSAT` to a finite horizon is not an unconditional
unwinnability theorem. Replay any candidate witness or counterexample
through normal StoryTangl `Ledger` transitions when the represented
subset permits it, rather than treating the solver model as a second
runtime authority. See
[Specialized Projections](../design/story/SEMANTIC_PROJECTIONS.md).

## First playable proof and falsifiers

**Bounded witness:** four rooms, one scarce consumable, one optional
waste action, one gated goal, a single local soft-lock transition, and
three selectable profiles. Show before/after player-visible choices and
journal receipts in a text/Service client first; replay on another client
only after the semantic baseline agrees. Keep the playable puzzle and
its analysis report reproducible from one declared world source.

The **central proof is a derived counterfactual foreclosure boundary**,
not three differently worded failure messages. From one authored world and
declared goal, the analysis should show:

- a successful witness from the pre-action state, followed by a candidate
  action whose committed successor no longer admits that goal;
- one source-attributed foreclosure finding derived from the modeled
  transitions, with an honest horizon/completeness label, **not** an
  independently authored list of dangerous choices;
- Cruel permitting that transition without making its irreversibility
  apparent; Polite allowing it but reporting goal loss immediately;
  Merciful preventing or repairing it, all consuming the same finding; and
- identical unaffected story facts across profiles, and coherent
  journal/history under each profile.

**Falsifiers:** three independently authored puzzle graphs; hand-maintained
lists of fatal actions that can drift from the rules; an analyzer that
finds foreclosure only because it was manually labeled; or a
"Merciful" rendering that merely hides an actually reachable fatal
action without enforcing its declared policy. A demonstration of the
three UI labels alone proves nothing.

**Deliberate omissions:** no parser implementation, full undo/redo
architecture, multi-session time-loop campaign, probabilistic player model,
exhaustive strategy synthesis, or graphical flowchart as prerequisites.
Later work can test whether the same semantic history supports a
derived visited/known/rumored graph view (matrix A20) or an analog
gamebook projection (A14).

## Review addenda: observation, counterfactuals, and recovery

These points sharpen the **future implementation acceptance tests**; they
do not select implementation work or expand the first slice into a rewind
framework. They follow review of the original three-profile proposal.

### Distinguish Cruel from Nasty by what is observable

A player who visibly destroys a **known unique** scroll can recognize an
irreversible loss, even if they cannot yet know that the missing scroll makes
the final puzzle unsolvable. That may illustrate **Nasty**, not **Cruel**.
Merely hiding the soft-lock warning does not establish a Cruel realization.

For the one fatal action, document the intended observable information at
three moments, separately from the underlying state:

| Observation point | Question for the player-facing contract |
| --- | --- |
| **Before commitment** | Can the reader tell that this act is irreversible or threatens a future option? |
| **Immediately after** | Does the visible result establish permanent loss, or could the reader reasonably expect replacement/recovery? |
| **At the blocked goal** | Does the later failure reveal what happened and which prior act caused it, or is the permanent cause still opaque? |

Choose the puzzle's item and presentation so the *irreversibility itself*
is not clearly disclosed in Cruel. Preserve the same objective state
transition across Cruel and Polite; vary what is disclosed. Record the
observation contract explicitly rather than relying on prose tone.
The five Plotkin labels above remain historical categories, not a promise
to implement five profiles in this first experiment.

### One source-derived foreclosure result, several policy consumers

Let `R_base(s, g)` mean that goal `g` is reachable from `s` under the
declared **underlying** world transitions, within the analysis scope.
For a candidate action `a` with successor `s' = T_base(s, a)`,
the central counterfactual is:

```text
forecloses_base(s, a, g) := R_base(s, g) and not R_base(s', g)
```

Evaluate that property **before** applying a Merciful action filter or
recovery rule; otherwise the policy may eliminate the very transition
we are trying to characterize. A pre-action witness, a successor-state
negative reachability result, and the source action/goal references
constitute the author-facing finding. Bounded non-reachability remains
bounded evidence, not an unqualified impossibility proof.

The same finding should drive the intended Cruel, Polite, and Merciful
treatments. An offline analysis artifact is acceptable for the bounded
proof if its scope/provenance are explicit and it is checked against
ordinary `Ledger` transitions. The **runtime policy** must still enforce
what a player can actually do; neither a hand-maintained fatal-action
table nor an unchecked solver assertion is authoritative.

### Retain a one-step rollback as a follow-up experiment

The initial three profiles exercise prevention and disclosure; they do
**not** by themselves demonstrate the matrix's stronger traversal-budget
or rewind claims. Keep a narrowly specified follow-up:

1. In a **cloned Ledger** at the pre-action state, verify a goal-reaching
   continuation; commit the fatal action in another trace and establish
   that the goal is no longer reachable under the baseline transitions.
2. Compare that result with a model allowing **one rollback** to the
   previous state. This tests recoverability under a historical operation,
   rather than ordinary forward reachability.
3. Only if worth implementing, expose that rollback to a player and
   verify its journal, state restoration, and replay semantics. This is
   not a prerequisite or a claim that StoryTangl already has a general
   undo/redo facility.

A snapshot-based counterfactual is an analysis witness, **not** evidence
that an actual client-facing rewind works. Guaranteed success for a
player who does not know the right action remains a separate, harder
information-constrained strategy problem.

## Connections to other opportunities

The cruelty distinction complements the [Apartment Commune](concept-seeds.md)
(where a local quest can be foreclosed without ending the world) and a
future *loop-and-grow* experiment (A04: knowledge persists across reset,
resources do not). It is **not** a replacement for the existing
Grand Grotto teaching world, and the Red Paperclip solver witness is an
analytical precedent rather than proof that the generic world-analysis
contract is finished.

**Documentation disposition:** the capability matrix retains the
adversarial analysis claim, minimal witness, and falsifier. This brief
retains the reader experience and design/proof boundary. A future
implementation issue, if the demo is selected, should own executable
fixtures, actual API choices, and acceptance tests; this brief opens
none of that work.

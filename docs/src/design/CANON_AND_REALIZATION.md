# Canon, Realization, and Residue

**Status:** ACTIVE METHOD NOTE
**Use:** how StoryTangl's conceptual vocabulary stays true as the code moves
**Companion:** [SIMPLIFICATION_SPEC.md](SIMPLIFICATION_SPEC.md) holds the *what* —
the concepts a reimplementation would need to preserve. This note holds the *how* —
the method by which that stays honest.

---

## Why this exists

Canonical documents rot in a specific way: they record *where* a concept is realized,
and then the realization moves. Most drift found in review is of exactly this shape —
a document names a symbol that no longer exists. Repairing the instances is endless;
the fix is to separate the registers so canon has nothing to rot.

## Three registers

| Register | Answers | Rots? |
|---|---|---|
| **Portable canon** | what must be true in *any* implementation | no — it names no symbols |
| **Realization** | where this codebase currently makes it true | constantly — and should be **generated**, not hand-maintained |
| **Residue** | transitional paths, compatibility shims, migrations in flight | yes, by design — it is scheduled for deletion |

Canon is implementation-free by construction. Residue is tracked because it is
operationally live, and excluded from the algebra because it is not part of what the
system *is*.

**Realization should be generated rather than hand-maintained — this is the target, not
today's state.** `tangl-devref` indexes symbols and topic-annotated artifacts, which is
what makes generation *feasible*; it does not yet map canonical claims onto symbols.
`map` returns a topic's indexed artifacts, nothing more. Closing that gap is the
proposed `devref audit` (issue #282 lineage), and until it exists the realization column
is maintained by hand and will keep drifting.

## The negotiation

The registers are not three filing buckets. Canon and realization are in continuous
negotiation, and **both directions are legitimate**:

```text
canon  ──▶ realization      normative:  "this must hold; make the code conform"
canon  ◀── realization      evidential: "this turned out to be necessary; canon is
                                         incomplete or wrong"
```

A mismatch is therefore **not automatically a defect in the code**. `Fanout` entered
canon because the taxonomy had an unnamed cell — realization pressing upward, correctly.
`Requirement is-a Selector` is a won convergence discovered in code that canon never
recorded. Conversely, a canonical chapter describing deleted modules is canon that
failed to move.

The review question is never "which one is broken" but **"which direction wins here."**

### Three mismatch classes

Naming them matters because two are mechanical and one is not:

| Signal | Direction | Resolution |
|---|---|---|
| Canon names a symbol that does not exist | canon decayed | mechanical — fix canon |
| A public symbol or behaviour exists that canon never mentions | realization pressing up | apply the promotion gate |
| Both exist and disagree on meaning | genuine negotiation | judgment; the expensive, rare case |

The first two are *mechanizable* — the index already stores symbols, so a checker could
verify referenced symbols exist and surface public symbols canon never mentions. No such
command exists yet, and prose references would need to be annotated (or restricted to a
recognizable form) for it to work. When it does exist, automating those two will not
remove the review; it will **concentrate** the review on the third class, which is the
only one that needs a person.

### The upward admission test

When realization presses up, the question is whether the pattern joins canon. Consumer
count is the wrong test — a demo is an instrumented probe, not a sample. Use two keys:

1. its invariants state **without reference to the demo it emerged in**; and
2. there is positive reason to predict multiple future mechanism-consumers.

There is a third exit that is often correct: **name without promoting** — give the
pattern a canonical term and recorded invariants, without lifting it into core
mechanism. Naming is itself a coarsening operation, and most mid-band work ends here.

## Residue is not citable

Residue is important now and irrelevant to the algebra. That implies something stronger
than a label: **residue must be unreachable from a canon read.** Otherwise a future
reader — human or agent — takes it as precedent.

The specimen this note was written from: `ARCHITECTURE.md` stated that `World` is a
singleton `TraversableGraphFactory` subclass — true (`story/fabula/world.py:205`) — while
144 lines later forbidding "any wrapper layer that pretends `World` is already a
`GraphFactory` subclass **when it is not**." That prohibition was residue, a guardrail for
a migration, and it outlived the migration that made it moot. Sitting canon-shaped and
unmarked, it contradicted the canon above it. A neighbouring transitional bullet had the
same defect, describing the label-based world round-trip as a *pending* migration when it
is in fact the designed consequence of singleton identity.

**Both were repaired in the change that introduced this note** — canon decay, fixed
mechanically, which is the whole point. A method note that identifies live decay and
declines to repair it is arguing against itself.

Residue belongs in a marked section (ARCHITECTURE's "Transitional Seams" is the right
shape), never inline with canon, and always with the condition that retires it.

## Worked example: presence, story, and the dispatch layers

The most useful negotiations sharpen canon rather than merely confirming it.

**The signal.** `story/presentation.py` imports `tangl.mechanics.presence`. Read
naively against the four-layer DAG (`core ← vm ← story ← service`), this is realization
saying the layer model is wrong — 20 sites import `mechanics → story`, and here is
`story → mechanics` in the other direction. That reading would have amended canon to
admit eight layers.

**The examination.** The three imports exist for one purpose: supplying concrete types
to `wants_caller_kind=` on five `@on_render_text` registrations. There is no functional
dependency. Meanwhile `mechanics/credentials/presentation.py` registers its own handlers
from the mechanics side and imports only `on_render_text` from story — the same job,
correct direction, already in the tree.

**The finding.** The imports were residue (type-checking artifacts) covering a real
defect: story *wires* a mechanic on behalf of every world. Because worlds are the
composition root, importing `story` should not transitively load presence.

**The result — canon sharpened, not merely upheld.** We began with "story must not
import mechanics" and ended with a stronger, testable law:

> **Engine layers do not wire optional mechanics.** Engine layers legitimately register
> their own system handlers — VM and story both do, deliberately. What they must not do
> is wire *optional* mechanics on another party's behalf. Mechanics register themselves
> on import; **worlds choose which mechanics to import**. Story knows only that it calls
> `x`; anything wishing to participate registers with `x` and produces something
> `x`-shaped.

**Status: landed through #368.** `story/presentation.py` now contains only the generic
controller. Presence owns and registers its five `@on_render_text` handlers through
`mechanics/presence/presentation.py`, while Credentials explicitly activates that
intrinsic dependency for its bound-subject rendering.

Note what is *not* the defect: presence is legitimately a *shipped default mechanic*
whose handlers land in the shared story registry, and that is fine. Once de-wired, a world
that never imports presence will not load it, and a single-world server can run with it as
dead code. The defect is neither the layer nor the shared registry — it is **who causes
the import**. (Layer confers no visibility at all — see *Layers order; registries scope; folds decide*
in the [glossary](glossary.md).)

## Review rhythm

Conceptual integrity is maintained continuously at several periods, not by episodic
audits alone. Each scale is the same reconciliation at a different grain:

| Scale | Trigger | Unit | Result |
|---|---|---|---|
| **Change** | every substantial PR | "does this introduce or redefine a noun, verb, lifecycle, extension seam, or wire shape?" | accept · rename · update canon |
| **Topic** | routine | one devref topic | one bounded dossier, at most one correction |
| **Layer** | periodic | core / vm / story / service / mechanics | primitive census; duplicates and leaked policy |
| **Coarse** | **triggered** by a canon-level change | whole coarse grid | reconcile canon before any detailed sweep |

The change-scale question is the cheapest guard and prevents more drift than any sweep
repairs. The topic sweep is the normal working unit. The coarse pass is rare and
*triggered* — running one against a canon that has not moved is relaxing against a
reference that is not changing.

**Dossiers are disposable.** A topic review produces a working artifact; only its
conclusions land in canon. Do not accumulate a second encyclopedia that itself needs
maintenance.

## What this asks of a reviewer

- State which register a claim belongs to before arguing about it.
- On a mismatch, decide the *direction* before proposing a fix.
- Never cite residue as precedent; if residue is load-bearing, it is not residue.
- Prefer naming to promoting; prefer promoting to inventing.
- A null result — "this zone is already coherent" — is a successful review.
- Fix passes are the highest-risk edits in the process: they arrive with momentum and
  skip the verification the original claims received. Re-verify them at the same
  standard, then sweep for contradictions introduced by the fix itself.

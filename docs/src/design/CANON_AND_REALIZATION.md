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

Canon is implementation-free by construction. Realization is a map produced from the
index (`tangl-devref`), not a column an author keeps up to date. Residue is tracked
because it is operationally live, and excluded from the algebra because it is not part
of what the system *is*.

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

The first two are detectable by tooling — the index already stores symbols. Automating
them does not remove the review; it **concentrates** the review on the third class,
which is the only one that needs a person.

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

The failure mode is live in the tree. `ARCHITECTURE.md:446` states that `World` is a
singleton `TraversableGraphFactory` subclass, which is true (`story/fabula/world.py:205`).
`ARCHITECTURE.md:590` forbids "any wrapper layer that pretends `World` is already a
`GraphFactory` subclass **when it is not**." That prohibition was residue — a guardrail
for a migration — and it outlived the migration that made it moot. It now sits
canon-shaped, 144 lines from the canon it contradicts.

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
defect: story was *wiring* a mechanic on behalf of every world. Because worlds are the
composition root, importing `story` should not transitively load presence.

**The result — canon sharpened, not merely upheld.** We began with "story must not
import mechanics" and ended with a stronger, testable law:

> **The engine wires nothing.** Mechanics register themselves on import; **worlds choose
> which mechanics to import**. Story knows only that it calls `x`; anything wishing to
> participate registers with `x` and produces something `x`-shaped.

Note what did *not* change: presence is still legitimately an APPLICATION-layer mechanic,
because application scope means *available everywhere*, not *used everywhere*. A world
that never imports presence never loads it, and a single-world server can run with it as
dead code. The defect was never the layer — it was who caused the import.

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

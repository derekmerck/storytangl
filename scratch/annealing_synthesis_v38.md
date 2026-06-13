## Architecture synthesis: v38 Aardvark annealing direction

I read the three reviewer comments, the red-team response, and re-checked the
claims against current `origin/main`. The headline result is unchanged from the
reviews: this audit found **architectural tension, not architectural rot**.

Two things have moved since the reviews were written, and both shrink the
remaining scope:

- **#269 merged** `docs/src/design/planning/AFFORDANCE_MODEL.md` v2.1
  (CANONICAL) — resolving Reviewer 1's "the model lives in GitHub comments"
  finding.
- **#271 merged** the backend fragment-contract audit: canonical fragment /
  envelope / projected-state DTOs shared by service, REST, CLI, and remote
  clients; pinned choice-payload contracts and fragment action identities;
  vertical slices for credentials piece selection and Nim quantity input.
  This lands a large share of Reviewer 3's direction at the **wire layer**,
  with the remaining widget rows (Blocker, Interpretation, grammar, roll,
  zone layout) explicitly tracked in **#235**. Reviewer 3 findings should
  route to that track, not be double-tracked here.

But the synthesis should be *smaller* than a naive aggregation of the reviews,
for one specific reason: the canonical doc
[`docs/src/design/planning/AFFORDANCE_MODEL.md`](docs/src/design/planning/AFFORDANCE_MODEL.md)
**v2.1** (CANONICAL, merged in #269) already does much of what the reviewers
asked for as net-new. It defines the open link as the planning primitive, gives
the planning-matrix axes, specifies the #255 audit table *and its columns*,
inventories the convergence debt with concrete code paths, sets the audit-first
guard, and names the one near-term consolidation. Reviewer 1's "the model lives
in GitHub comments / I can't find the doc" finding is **resolved** — the doc
landed ~1h after the issue opened.

So the right annealing unit is not "produce these artifacts." It is:

> Finish and reconcile what the canonical doc already started — fill in its audit
> table (with a few implementation columns it deliberately omits), reconcile this
> comment's vocabulary with the doc, then add minimal cleanup-attribution
> *after* the table names what current tags mean. Do not centralize projection.

Collapse mechanism; protect projection. And — applied reflexively — **do not let
the synthesis fork the doc's vocabulary while annealing the code's.**

---

### Target model

Unchanged and already canonical in AFFORDANCE_MODEL.md:

```text
The open requirement-bearing link is the planning primitive
(fixed endpoint + Requirement(open endpoint) + policy).

Dependency and Affordance are one object with opposite fixed endpoints
(addressed pull vs broadcast offer). Fanout is a cardinality/rule-generation
mode, not a third form.

Every mechanism is a coordinate in the planning matrix
(origin, direction, provider state, target kind, use state, cardinality,
arbitration).

Domain systems may PROJECT a currently-admissible coordinate into an ordinary
runtime Action. Backend validation and mutation remain authoritative. Clients
render fragments / choices / accepts / info affordances / projected state and
submit a backend-issued interaction id + payload.
```

The framing question for any new mechanic is the doc's:

> **"Which row of the planning matrix is this?"** — not "what new
> interaction/event/action mechanism do we need?"

---

### Concept ownership table

| Concept | Owner | Non-owner |
|---|---|---|
| Requirement satisfaction / binding | VM provisioning / resolver | Frontend, widgets, transport |
| Runtime choice legality | VM / story / domain handlers | Client-side validation |
| Generated-choice projection | Story / domain / mechanics phase handlers | Core, frontend |
| Generated-choice cleanup ownership | Projecting handler/domain | Unreviewed tag convention as the *only* ownership signal |
| Interaction submission | Service/client contract over backend-issued interaction id + payload | Client-invented semantic action ids |
| Payload collection | Client, guided by backend `accepts` | Client-side story authority |
| Payload validation | Backend authoritative; client advisory | Client-only validation |
| Story-info disclosure | Service / info projection path | Runtime choice mutation path |
| Journal output | JOURNAL phase / fragments (incl. approved phase-local injection) | Parallel content channels |
| UI rendering | Client / adapters | VM / story semantics |
| Projection vocabulary | Adapter / domain / client docs | Core ontology |

Note: the cleanup-ownership row deliberately does **not** name "shared
provenance vocabulary" as the owner yet. Whether provenance is the right
mechanism is decided by the audit table (below), not asserted here.

---

### Pattern promotions

1. **Dynamic action projection** — name it in docs as the phase-local creation
   of an ordinary `Action` from a scoped source coordinate, with explicit
   admission, payload, availability, projection, cleanup, and (optionally)
   provenance. Do **not** require one shared implementation.

2. **Scoped contribution** — the cross-domain phrase for "a concept visible in
   the current scope contributes a phase-appropriate artifact (action, info
   affordance, journal fragment, modifier, redirect)." `SandboxInteraction`
   stays the sandbox authoring term; the pattern is not owned by sandbox.

3. **Self-fanout** — keep as the conceptual name for re-entrant game blocks that
   re-project available moves until a terminal state routes outward. Do not
   force `HasGame` through provision fanout.

4. **Projection provenance / cleanup ownership** — promote as a lifecycle
   concept, **additive and non-authoritative**, and *contingent on the audit
   table*. Code-checked status, **corrected by the Job-1 audit (PR #274)**:
   cleanup ownership today is a compound key — each `_clear_dynamic_*_actions`
   helper is scoped to its own source node's `edges_out` *and* a discriminator
   tag triple (`{dynamic, fanout, menu}`, `{dynamic, fanout, game}`,
   `{dynamic, sandbox, <action_kind>}` with nine per-kind sandbox callers,
   plus a fourth engine-side family `{dynamic, sandbox, incremental}` with its
   own helper). The **engine-owned** discriminators are mutually non-subsuming
   (a subset antichain — they intentionally share tags like `dynamic`, so the
   contract is non-subsumption, not set disjointness) and now pinned by an
   invariant test that observes every engine-owned family. But the audit found
   **one live overlap in world-owned code**: adventure hazard actions wear
   `{dynamic, sandbox, adventure, movement, hazard}` — a superset of both the
   world's discriminator and the engine's movement discriminator, so two
   cleanup families claim them. Behavior survives only via projector re-run
   priority ordering, which is load-bearing and currently unpinned. So the
   payoff of explicit provenance is **legibility and contract for engine
   families, and a genuine fragility fix for world-owned families** — an
   earlier draft of this comment claimed "no live collision"; that was true
   only of the engine families. Plus two real drifts the code read surfaced:
   - the tag vocabulary already lies slightly: game self-loop moves wear the
     `fanout` tag without touching fanout machinery, while sandbox actions
     (the doc's actual convergence candidates) don't wear it at all;
   - the sandbox already **has** rich provenance — `_project_sandbox_interaction`
     emits `source`, `contribution`, `source_label`, `source_kind`,
     `interaction`, `target` — but carries it in `ui_hints`, conflating
     lifecycle metadata with presentation hints. Menu and game projectors emit
     only tags.

---

### Approved changes (in implementation order)

The order matters: classification and characterization **precede** any
provenance code.

#### A. Finish the canonical #255 audit table (in AFFORDANCE_MODEL.md)

> **Status: DONE — PR #274** (doc v2.2 + cleanup-discriminator invariant
> tests). Findings: the adventure hazard cleanup overlap and the incremental
> fourth family, both described in the amended promotion 4 above.

The table is already *specified* in the doc's "audit-first guard" section and
*partly populated* in its "Convergence debt" section. The approved work is to
fill it in as a diff to that doc — **not** a new table with new headers in a
comment.

Use the doc's existing columns, plus exactly these additions:

- **new columns:** `Source concept`, `Cleanup owner`, `Existing tags / hints`
- **refinement (already blessed by the doc's "Availability is after binding"
  section):** split `Availability predicates` into `Admission/binding
  predicates` and `Live availability predicates`

Rows (one per mechanism), extending the doc's inventory:

- `Action` destination dependency (`_destination_dependency` /
  `_preview_destination_viability`)
- menu fanout (`project_menu_affordances`)
- sandbox location exits
- sandbox fixture / asset / mob interactions (`_project_sandbox_interaction`)
- sandbox built-in verbs: take/drop, open/close, switch (hand-rolled `Action`)
- sandbox scheduled events (`event.as_interaction()` →
  `_project_sandbox_interaction`; provider via `get_sandbox_events`)
- sandbox wait / default / time action
- game self-loop moves
- Adventure movement hazards
- Adventure magic words
- Adventure treasure deposit / scoring
- incremental / cycle actions (if in scope this iteration)
- story-info / info affordances — adjacent, **separate** projection surface
  (row included to mark it as deliberately distinct, not to converge it)

Purpose: make every downstream decision data-driven, in one canonical home.

#### B. Add characterization tests for current projection shapes

Before any extraction, lock current behavior (not uniformity) across
representative paths: one menu fanout action, one sandbox sponsored interaction,
one scheduled-event action, one game self-loop move, optionally one Adventure
overlay. Capture: label, tags, `ui_hints`, payload, admission vs live
availability, source/owner identity if present, cleanup behavior, journal
expectations. These are golden/characterization tests — they record differences,
they do not demand convergence.

Scope note: **#271 already pinned the wire layer** (DTO round-trips, choice
payload contracts, fragment action identities). B targets the layer #271 did
not: VM/story projection shape — tags, cleanup ownership, admission predicates.
To keep the table and the tests from drifting apart, each characterization test
should cite its audit-table row (mechanism name), making B the executable form
of A.

Added by the Job-1 audit findings: B must also **pin the adventure
hazard-rewrite ordering** — the engine movement cleanup deletes the world's
hazard actions each PLANNING pass and the adventure projector re-rewrites them
afterward; that priority ordering is load-bearing and currently unpinned. A
double-provision characterization (hazards survive repeated PLANNING passes,
no duplicates, no plain-movement leak-through) closes it.

#### C. Reconcile vocabulary in the cardinal docs

The open-edge model doc has landed; the remaining work is reconciliation.
Cross-link, do not re-derive. Update `ARCHITECTURE.md`,
`docs/src/design/glossary.md`, `VM_DESIGN.md`, `SCOPE_MATCHING_DESIGN.md`,
sandbox/game design notes, and widget/interaction docs to use the doc's
vocabulary and the `binding/admission → projection → live availability →
submission → backend validation → mutation → journal` ordering (availability is
a use-time filter applied *after* projection — see the doc's "Availability is
after binding"; corrected in f93a21e7). Note (deferred) the doc's own
pending filename rename (`AFFORDANCE_MODEL.md` → `OPEN_LINKS_*`); keep the
filename stable for #255 / CodeRabbit reference continuity.

#### D. Normalize existing provenance — *gated on A*

This is less "add fields" than the reviews assumed: the sandbox projector
already emits a six-field provenance vocabulary inside `ui_hints`, while menu
and game projectors emit only discriminator tags. The work, after the audit
table's `Cleanup owner` / `Existing tags / hints` columns name what each
tag/hint means, is:

1. decide which of the existing sandbox hint fields are **lifecycle metadata**
   vs **presentation hints**, and where lifecycle metadata lives (Reviewer 3
   listed `source_kind` / `contribution` among hints that should "stay
   advisory" — that holds for presentation, but cleanup ownership is lifecycle
   and shouldn't hide in a presentation channel);
2. extend the **smallest** attribution to menu/game so all three projector
   families are equally explainable. Start with one token (e.g.
   `cleanup_owner` / `source`), not a multi-field schema;
3. fix the tag-vocabulary lie (game's `fanout` tag) only as part of an
   intentional, characterized migration — not as a drive-by.

Constraints:
- additive, optional, ignorable by old worlds/clients/fixtures;
- diagnostic/lifecycle metadata only — never legality authority;
- do **not** fix final field names or storage location until the table
  identifies which existing tag/hint/edge fields are lifecycle vs presentation
  metadata;
- preserve existing tag behavior until intentionally migrated.

Richer fields (`source_handler`, `projection_reason`, `source_kind`, …) are a
**may-add**, not part of approved scope.

#### E. Inventory (don't remove) compatibility seams

Catalog, with no removals this iteration: legacy `payload_type` / old `input`
accepts; choice-label normalization; old/new choice fragment compat; `edge_id`
usage in client + fixture contracts; the tag conventions used by the dynamic
cleanup helpers. Removal requires evidence that worlds, fixtures, clients, and
conformance harnesses no longer depend on the seam.

#### F. Opportunistic provider-surface unification — *gated on A, touched-code only*

The canonical doc names this as "the near-term consolidation," so the synthesis
adopts it rather than blanket-deferring it: where new or touched sandbox code
already routes through `_project_sandbox_interaction`, prefer one
interaction-donating provider protocol over the split `get_sandbox_events` + a
would-be parallel `get_sandbox_interactions`. **Opportunistic on touched code
only** — not a sweep, and not before the audit table classifies the rows.

---

### Deferred findings (each with a concrete trigger)

| Deferred | Trigger that promotes it |
|---|---|
| Shared dynamic-action projector / `ContributionProvider` framework | Audit table shows ≥2 rows identical across admission + cleanup + payload + return-phase columns |
| Scheduled-event activation split (gate → activate concept → project) | A non-sandbox consumer needs the same schedule→activation→projection shape |
| Timed-process runtime (ticks / charge / incremental / queueing) | The smallest shared shape ("counter/progress changed → journal receipt") recurs across ≥2 non-adjacent callers |
| Credentials extraction into a generic picking/inspection kernel | A second live mechanic exhibits the same reveal/commit/mediate rhythm |
| `edge_id` → `interaction_id` wire rename | A concrete client/compat need, not doc aesthetics |
| `payload_type` removal | The compat inventory (E) proves it dead or safely isolated |
| Games handlers register on story dispatch, not VM (`games/handlers.py:26` TODO) | A second symptom turns the layer-posture smell into an actual bug, or the dispatch boundary is being touched anyway |
| `OpenLink` base object; content/challenge/inner-guide affordance seams | Already marked "do NOT build yet" / "Future Extensions" in the doc; promote only when a concrete consumer needs them |

---

### Rejected (over-readings, not findings)

No reviewer finding is wrong. These *interpretations* are rejected:

- "Repeated `Action(...)` construction proves we need a projection framework."
- "All scheduled/timed things should merge into one scheduler."
- "Credentials is large, therefore it must be extracted."
- "Client-side form validation is a frontend mechanics leak."
- "Info affordances should collapse into runtime choices."
- "Projection differences are duplication."

---

### Protected projection differences

Web buttons/chips/drag-drop/forms/status-rails/media; CLI numbered choices and
status text; Ren'Py turn grouping and sprite ops; parser command bars and
magic-word grammar; Adventure hazards projecting as *attempted movement* (not a
generic trap), magic words as command-like affordances; scheduled events
preserving forced-vs-selectable-vs-merely-disclosed distinctions; Credentials'
visible-evidence discipline and document/packet/disposition distinctions.

Projection differences are product surface.

---

### Cardinal doc reconciliation

- AFFORDANCE_MODEL.md — host the completed audit table (item A); resolve the
  internal "Origin" axis vs "Explicitness" column wording drift to one term.
- `docs/src/design/glossary.md` — open link, dependency, affordance, fanout,
  scoped contribution, projection, interaction request, cleanup ownership.
- ARCHITECTURE.md, VM_DESIGN.md, SCOPE_MATCHING_DESIGN.md, sandbox/game design
  notes, widget/interaction docs — vocabulary + ordering reconciliation (item C).

---

### Test reconciliation

- **Invariant:** sandbox-architecture tests (sandbox = ordinary Story/VM); VM
  dispatch/ctx tests for phase-local journal injection; conformance tests for
  backend-authoritative interaction + fragment stream.
- **Golden behavior:** Adventure slice; sandbox movement/fixture/asset/event;
  Credentials; game move projection; widget/CLI conformance fixtures.
- **Legacy seam:** tests asserting exact tag sets / normalized labels / old
  payload formats — do not rewrite until E (compat inventory) + B
  (characterization) explain what is intentional.
- **Delete candidates:** none yet; deletion waits on the audit table proving a
  protected dead abstraction vs an active compat seam.

---

### Breaking-change contract

This iteration is non-breaking.

- **Permitted:** the audit table; characterization tests; doc reconciliation;
  additive cleanup-attribution (gated, minimal); opportunistic touched-code
  provider-surface unification (gated); compat inventory; internal dead-state
  cleanup where tests show no behavior change.
- **Requires a follow-up issue/PR:** `edge_id` rename; required provenance
  schema; `payload_type` removal; a shared projector; generic scheduled-event
  activation objects; Credentials extraction; moving sandbox vocabulary into
  VM/Core.

---

### Budget classification

| Change | Budget | Status |
|---|---:|---|
| Mark open-edge doc finding resolved | S | Done (PR #269) |
| A. Finish canonical audit table (+3 cols, +avail split) | M | **Done — PR #274** |
| B. Projection characterization tests | M | Approved |
| C. Doc vocabulary reconciliation | S/M | Approved |
| D. Normalize existing provenance (lifecycle vs presentation) | S/M | Approved, gated on A |
| E. Compatibility inventory | S | Approved |
| F. Opportunistic provider-surface unification | M | Approved, gated on A, touched-code only |
| Shared projection framework | L/XL | Deferred (trigger above) |
| Scheduled-event activation split | L | Deferred |
| Timed-process abstraction | L/XL | Deferred |
| Credentials extraction | L | Deferred |
| `edge_id` rename | L | Deferred |
| `payload_type` removal | M/L | Deferred pending E |

---

### Acceptance criteria

1. The #255 audit table is filled in **inside AFFORDANCE_MODEL.md**, covering the
   listed mechanisms, using the doc's columns + the three additions, with no
   forked vocabulary.
2. Characterization tests capture current projection shapes without forcing
   uniformity.
3. Cardinal docs share one vocabulary and the binding→…→journal ordering.
4. Any cleanup-attribution added is minimal, optional, post-table, and ignorable
   by existing consumers.
5. Where touched, the sandbox provider surface moves toward one interaction
   donor; no sweep occurs.
6. Existing clients/worlds/fixtures still pass.
7. No shared projector, activation objects, or extraction land without a
   follow-up.
8. Protected projection differences remain intact.

---

### Bottom line

```text
fill in the canonical audit table (+ cleanup-owner / tags / source columns)
+ characterization tests
+ doc vocabulary reconciliation
+ minimal cleanup-attribution, gated on the table
+ opportunistic touched-code provider-surface unification
+ compatibility inventory
```

The architectural conclusion: **generated choices already have working
ownership semantics — a compound key of source-node scoping plus discriminator
tags — and the sandbox already carries rich provenance, just in the wrong
channel (`ui_hints`).** The compound key is non-subsuming and now test-pinned
for engine families; the Job-1 audit found it already bends in world-owned code
(adventure hazards claimed by two families, held together by projector
ordering). This pass makes that ownership contractual and testable, in the doc
that already frames it, without centralizing projection or flattening
domain-specific presentation. The annealing is finishing what the canonical
doc started — not starting something new.

---

### Amendments

- **2026-06-12 (post Job-1):** Item A complete (PR #274: AFFORDANCE_MODEL.md
  v2.2 audit table + cleanup-discriminator invariant tests). Corrected
  promotion 4: the earlier "no live collision" claim held only for
  engine-owned families — the audit found a live two-family overlap on
  adventure hazard actions, and a fourth engine-side family (incremental)
  with hand-rolled hints. Item B scope extended to pin the hazard-rewrite
  ordering.
- **2026-06-12 (post PR #274 review):** terminology corrected from "pairwise
  disjointness" to **mutual non-subsumption** (families intentionally share
  tags like `dynamic`; the contract is a subset antichain). Invariant
  strengthened to require every engine-owned family observed in generated
  actions (unlock/lock/incremental fixtures added).

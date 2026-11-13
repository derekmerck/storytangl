# StoryTangl review tally (Nov 2026)

Running record of the review: plan, findings, and the week's todo list.
Working notes, uncommitted. Updated as the review proceeds.

Last updated: 2026-11-10.

## Ground rules

- **North star (the only fixed point):** navigate a story space with a formally
  verifiable, deterministic process; roughly a self-evolving graph mediating
  between a space of possibilities and a linear output.
- Design notes, AGENTS.md, devref and tests are working understanding. A
  mismatch with code is a question. Each one is classified as:
  - **drift** (code wandered from a sound guideline)
  - **stale guideline** (code is right, the note is behind)
  - **residue** (plumbing left from ideas that converged)
  - **unification** (two things that are one thing)
- Method: a clean-slate sketch, then time-boxed probes per operator, then back
  up to the sketch. Anneal high to low and back; do not stay in the weeds.
- The sketch feeds a planned clean TypeScript bootstrap, then a Python 3.9
  rewrite. Tests are not the parity basis.

## Handoff: what is stable (2026-11-11)

For a design or implementation agent picking this up. Read "Corrections after
the board comparison" first. Statements attributed to Derek are intent;
measured and reproduced items are evidence; both clean-slate sketches and
anything marked "mine" are hypotheses and are not part of this handoff.

Experiment scripts are in `scratch/review_probes/` on this branch. Run them
with the project interpreter and `PYTHONPATH=engine/src`.

### A. Ready to do: small, decided, no design call needed

| # | Work | Basis | Done when |
|---|---|---|---|
| A1 | Raise the default `checkpoint_cadence` above 1 | Derek: cadence 1 was scaffolding; finding 25 | default changed; rollback tests still pass |
| A2 | Gate the pre-journal whole-graph hash behind the debug check | finding 53 | hash taken only when debug logging is on |
| A3 | Large-graph timing guard: one synthetic graph, a per-choice budget | finding 55; Derek expected this test to exist | test fails if a choice exceeds the budget |
| A4 | Hoist the identical `set_provider` / `set_successor` bodies of `Dependency` and `Affordance` to `HasRequirement` | finding 4, confirmed by the board agent | one implementation; tests unchanged |
| A5 | Cold-process tests pass the source path explicitly | finding 20 | they pass from a worktree with a stale editable install |
| A6 | Make `test_manual_topic_facets_drive_find_map_and_pack` build from a fixture | corrections section | passes with and without `tmp/devref/issues.json` |
| A7 | Service conformance test: remote client and REST routes match the `ServiceMethodSpec` table | finding 48; Derek agrees on a single source | test fails on drift; nothing generated |
| A8 | Validator, report only: edges that enter a container at a member or leave from a non-sink member | finding 77 | `validate_traversal_contracts` lists them; no world fails |
| A9 | Invariant test, expected to fail on hubs for now: planning a node twice against unchanged state leaves ids and order unchanged | grounding must be repeatable | test exists, marked expected-fail where it fails |
| A11 | Guard test: no `json.dumps`, `json.loads`, `model_dump` or `model_validate` in `core`, `vm` or `story` outside an allow-list (today: `core/bases.py`, `core/base_fragment.py`, `core/token.py`, `story/episode/action.py`, `story/fabula/compiler.py`, `story/analysis.py`) | Derek, 2026-11-12: agents write their own serializers unless stopped; finding 89 | test fails on a new site; allow-list is explicit |
| A12 | Each client's tests load the portable fixtures in `engine/contrib/conformance/fixtures` and, for each one, either render it or refuse it explicitly. Start with the in-process Python clients (pygame bridge, Ren'Py bridge, the real CLI controller); then the web client, reading the same JSON files in place of its own copies. Use pygame's `UnsupportedAccepts` as the model for refusal | Derek, 2026-11-12; finding 112 | one parametrized test per client over the fixture directory; a crash or a silent drop fails; each client's refusals are listed in one place |
| A10 | Done: PR 676 merged to `main` as `e95281c1` on 2026-11-11 (Python dependency update; web job pinned to Ubuntu 24.04). Follow-up: return the web job to `ubuntu-latest` once that image installs cleanly; the web lockfile and three held-back Python packages are still open | dependency alerts | done |

### B. Ready to write down: Derek's stated intent, not yet in the design notes

Each is a short section in an existing, already linked design file. Use his
wording from the cited part of this tally.

| # | Topic | Tally source | Suggested home |
|---|---|---|---|
| B1 | Four levels as progressive orderings: world, story graph, episode DAG, journal | sketch v2, "The stance" | `ARCHITECTURE.md` |
| B2 | Declarative and imperative as two readings; materialization as assembling the declared set | sketch v2, "The stance" | `AFFORDANCE_MODEL.md` |
| B3 | Fan-out and fan-in in his terms | sketch v1 vocabulary | `AFFORDANCE_MODEL.md` |
| B4 | Container source and sink: the setup and cleanup bottleneck; the story as the outermost container | "Containers: one source, one sink" | `VM_DESIGN.md` |
| B5 | Intrinsic contribution, extrinsic assembly (`get_ns` and `gather_ns`; journal handlers) | finding 33 | `VM_DESIGN.md` |
| B6 | Two kinds of similarity; games as narrative devices with an authoring thumb on the scale | P5 | `VM_DESIGN.md` replay notes; mechanics design note |
| B7 | Authoring vocabulary: authors write `conditions` and `effects`; field is `availability`; type is `Predicate` | finding 72 | story or loader design note |

### C. Evidence to attach to existing issues

| Issue | Attach |
|---|---|
| #560 | The reproductions: `call_stack_probe.py` (frame outlives callee; interjection renders sender twice), `resume_probe.py` (both return phases loop), `resume_rule_probe.py` (resume after the calling edge works in five cases, including with re-planning). Note that the frame escape is a consequence of the "jump does not unwind" floor. |
| #548, #472 | The profile (finding 50) and the three timings; `ledger_cost.py` for stream growth |
| #556 | The downstream site-arrival handler as first witness (finding 37) |
| #438, #461 | The push-side demo gap (finding 73) and the witness-world list (P9) |

### D. Not stable; do not implement from this tally

Thumbprint ids and occurrence identity (P1); a VM fan-in operator (P2); the
shared hub helper beyond studying the #527 retained-binding path; resume in
the engine (owned by #560, policies not approved); lowering edges through
source and sink (P10); the story as root container; multi-lane; the parity
basis (P3); lowering `predicate:` (needs a compatibility check across nine
worlds first); per-hop tracing on a cadence (measured, but changes what
rollback can rely on; needs an owner's decision in #548 or #472); both
clean-slate sketches.

## Corrections after the board comparison (2026-11-11)

The issues-board agent compared this tally with the roadmap. Checked against
the code and the issues, these of its points are errors or omissions here:

- **#560 already owns jump, resume and re-enter.** Opened 2026-10-14. It
  specifies resuming a redirect scan strictly after the calling edge, keeps
  re-entry at PLANNING for hubs, names the late-choice gap after a POSTREQS
  return, and uses the companion and dream examples. Findings 56 to 68 and
  P8 were written without reading it. They add reproductions, not a design.
- **#560 states that a jump inside an open call does not unwind it.** So the
  frame that outlives its callee (finding 65) is the documented floor, and the
  teleport is its consequence. "Discard or refuse" is a change to an agreed
  position, to be raised there with the reproduction, not a bug fix.
- **Retained bindings already exist.** Sandbox scheduled events re-use their
  action across re-provisioning (`reuse_retained_binding`, from #527). The
  claim under finding 68 that hubs rebuild every dynamic edge with a new id is
  too broad. That retained path is the prior art for the shared hub helper.
- **`_visit_count` counts executed visits, not rendered ones** (finding 60).
  It is incremented in UPDATE, before JOURNAL. There are three facts, not
  two: traversed, executed, presented.
- **The count of issues without devref labels is out of date** (finding 19);
  the board was audited on 2026-11-10.

- **Why #560 was missed.** It carries `devref:traversal` and `devref:frame`
  today, but it is not in the issue snapshot this review synced on
  2026-11-09, and the review did not re-sync or query those topics before the
  control-flow probe. The channel worked once the board was relabelled; the
  review did not use it. Habit to keep: re-sync and `map` the topic before
  each probe.
- **One devref test reads the local issue snapshot.**
  `test_manual_topic_facets_drive_find_map_and_pack` fails when
  `tmp/devref/issues.json` exists, because synced issues fill the notes pack.
  The test should build from a fixture, not from a disposable local file.

Derek's caution on the above, same day: do not overweight the board either.
It is not authoritative even when it is not stale; it is another view, focused
on tasks where the design notes are focused on tropes. Rediscovering what
#560 says, independently and with reproductions, is confirmation that #560 is
not stale. The reverse does not hold: some old issues track aspirations that
now have better approaches, and some describe a better design than the one
that was implemented as an expedient. An issue is read like a guideline: one
view, to be classified against the code and the stated intent.

Provenance, to read the rest by: statements attributed to Derek are design
intent. Items marked measured or reproduced are evidence. Items marked "mine"
and both clean-slate sketches are hypotheses.

## Clean-slate sketch (v1)

| Layer | Operators |
|---|---|
| Core | shape, creation, collection, selection, behaviours |
| VM | step; provision (match open edges against scope, both directions); fold; hub projection (generator to choice set) |
| Story | narrative names and basic building blocks |
| Service | API shape and behaviours, persistence |
| Mechanics | assemblies (collections with rules); re-entrant nodes with rules |

Open-link vocabulary, as agreed in this review:

- A requirement always describes the open end of an edge.
- **Dependency:** fixed at the requester, open destination. Pulls; may create
  its provider.
- **Affordance:** fixed at the provider, open source. Waits, and attaches
  wherever its requirement is met; active only when its conditions hold.
- **Fan-out:** dependencies generated at a node, reaching for nearby satisfiers.
- **Fan-in:** latent affordances, created when their scope is entered, that can
  offer on this node ("go home" from home, "call mom" from mom).
- Affordances attach to the active node, nearby nodes and the provisioning
  frontier, not only the cursor.
- Episodes are one kind of concept. A choice is an edge between traversable
  nodes. A concept may afford an episode it owns.

## Clean-slate sketch (v2, 2026-11-11): patterns across the VM

After the provisioning, hub, ledger, fold and control-flow probes, and with
several demo worlds exercising them, four patterns account for most of what
was found. Mine, for discussion.

### 1. One edge, several coordinates

Dependency, affordance, fan-out result, menu choice, redirect and call are one
record: an edge with a fixed end, an open end and a requirement. They differ
only in coordinates.

| Coordinate | Values |
|---|---|
| Which end is open | destination (pull) or source (push) |
| Who makes it | authored once, or generated by a provider or hub |
| How it is taken | chosen by the reader, or triggered at a phase |
| Whether it returns | jump, call, or contribution (no cursor move) |
| What the caller gets back | resume or refresh |

The ten control-flow intents (finding 56) are points in this space, and so are
"choice", "sandbox event" and "scheduled appointment".

### 2. One fold: gather from scope, match, arbitrate, reduce

| Instance | Candidates | Reduction |
|---|---|---|
| Offer discovery | seven named sources | best by priority |
| Namespace | ancestor chain plus handlers | layered merge |
| Triggered edges | the node's edges in order | first available |
| Hub menu | generated actions | all available |
| Downstream arbitration | scenes contending for a place or actor | first per contended thing |
| Journal compose | handlers | pipe |

Dispatch already has the reductions. What varies is where candidates come
from, and the engine walks the scope chain separately each time.

### 3. One bug class: identity across regeneration

Whenever something is rebuilt, whatever referred to it by id or position
breaks: the resume marker on a hub, a call frame after its callee is left, a
recorded choice in another session, an edge after a re-plan. Two remedies
cover all of them: re-use what is still wanted, and derive ids from content.

### 4. One ambiguity: lifecycle states sharing a name

Most of the recurring confusions are two states under one word: exists and
available (#527); attached and active; provisioned and viable; passed through
and rendered ("visited"); returned and refreshed. Naming the states once
(latent, bound, available, taken, rendered, returned) is cheaper than fixing
each pair separately.

### The asymmetry

The pull side is one mechanism in the VM. The push side is implemented three
times in story and mechanics and again in a downstream world. The overhaul's
centre of gravity is making push as much a VM operator as pull.

### The stance behind the push side (Derek, 2026-11-11)

The push side is hard to articulate because it is the declarative versus
imperative stance, "wanting to both have and eat cake."

- A world can be made entirely of dependencies, CYOA style: "if this and this
  condition, then go there."
- Or declaratively: "this is the thing you can reach if that and that state."
- Eager materialization declares "here are all the affordances; assemble them
  so we can pass through them imperatively."
- Provisional materialization is a smaller step of the same: what affordances
  are here and coming up; assemble the neighbourhood.
- Templates are affordances for the provisioner to create concepts and
  episodes when their conditions are met. They feel imperative only because
  they are created when needed, and because Python is imperative.

Refinement (Derek): both formalisms are used only because episodes,
traversable concepts, beg for the if-then form, while most concepts do not
need to be ordered. The episode DAG mediates between the linear journal space
and the non-linear story graph, which is itself one configuration of the
ambient story space, the world of templates and rules. "Like using a graph to
order data with a heapsort."

| Level | What it is | Order |
|---|---|---|
| World | templates and rules | none |
| Story graph | one grounded configuration | relations only |
| Episode DAG | traversable concepts and their edges | partial |
| Journal | what was told | total |

Each level adds order. The imperative voice is needed exactly where order is,
which is the episode DAG; everything else can stay declarative. Edge order
(finding 61) is then the comparator that breaks ties, and deserves to be
stated as such.

History (Derek): content fragments were originally leaf nodes hanging off the
episodes that generated them, and a journal was produced from any group of
episodes by a breadth-first walk, "exactly like reading out a heapsort."

Where that stands now: fragments live in the ledger's output stream, not the
graph, but each still carries `source_id` (the entity or edge that donated the
content), `origin_id` (the producer) and a step, and `get_slice` filters the
stream by step span and selector. So "a journal from any group of episodes" is
still expressible as a query. Keeping fragments out of the graph is also what
lets story state be compared without the journal (P5), and it is why the
JOURNAL phase is expected not to change the graph (finding 53).

Derek's caveat: the split disguises the synergy between world, story and
journal as progressive orderings of the same space. The other reason for it
is size: static journal entries have no business staying in the mutable story
registry. The full graph, rooted at the world, through the story graph, down
to every fragment leaf, can still be reassembled from the ledger; it is just
not represented that way in practice.

What follows from it (mine, for discussion):

- The two voices are two readings of one rule, from the state side or from the
  goal side. Both lower to the same edge record (pattern 1). Neither is
  second-class.
- Materialization is grounding, in the solver sense: turning declared rules
  into concrete edges against the current state. Eager grounds everything;
  provisional grounds the frontier. PLANNING is "ground the neighbourhood".
- A template is a rule that says "there exists a thing such that...". The
  thumbprint id (P1) is the standard name for such a thing: a function of the
  rule and what it was bound to. That is why the id must not be random.
- The property the VM needs from grounding is that it is repeatable:
  grounding the same declarations against the same state changes nothing.
  Pattern 3 is this property failing. It is testable directly: plan a node
  twice and compare the graph.

### A lens: linker plus interpreter

Provisioning is linking: a requirement is a symbol, scope is the search path,
a template is something to instantiate when nothing matches. Traversal is
execution: a node is a block, the phase is the micro-step, the return address
is (node, phase, edge position), containers are procedures with an entry and
an exit, fan-in is a table of handlers registered by scope. The lens is useful
where it brings settled answers: who restores state after a call, what happens
to a frame when control leaves its scope, and why ids must survive relinking.

## Probe status

| Probe | Status |
|---|---|
| Docs and contract read (ARCHITECTURE, AGENTS, SIMPLIFICATION_SPEC) | done |
| Test baseline | done: 4,614 pass, 11 fail (environment), 77 skip |
| Open link / provisioning | done |
| Re-entrant hubs (menu, sandbox, games) | done |
| Determinism and ids | done: confirmed by experiment, root cause is at story creation |
| Step and ledger | done |
| Fold (namespace, journal) | done |
| Service and persistence | done (outline level) |
| Downstream calendar world codec | done (private repo, read-only) |
| Downstream gamebook promotion ledger | done (private repo, read-only) |

Not yet read in any depth (as of 2026-11-11; compiling, materializing,
presentation, media's design, the client apps and prose were read later):
`tangl.media` beyond its
provisioners, `tangl.prose` and `tangl.lang`, `tangl.presentation`, mechanics
other than sandbox and game handlers (assemblies and components, progression,
demographics, credentials internals), the four apps (CLI, pygame, web,
server), the loaders, and the docs site as a whole. The demo worlds were read
later the same day. Core was read for
registry, graph, behaviour and entity basics only.

## Findings

Marked **V** when read in code, **I** when inferred.

### Provisioning

1. **Unification. Offer discovery is a hand-written fold.**
   `Resolver._discover_requirement_offers` (resolver.py:336) names seven offer
   sources in sequence. That is dispatch written by hand. (V)
2. **Drift. VM imports media.** Function-local imports of
   `tangl.media.media_resource.media_provisioning` at resolver.py:265 and 275,
   and vm/dispatch.py:44. Finding 1 removes the need. (V)
3. **Residue. The provider is stored twice.** `requirement.provider_id` and the
   edge's `successor_id` are kept in sync by `set_provider` / `set_successor`.
   (V)
4. **Unification. `Dependency` and `Affordance` have identical bodies.** They
   differ only in which end is open; the shared code belongs on
   `HasRequirement`. (V)
5. **Residue. The resolver does five jobs** in 1,788 lines: discovery, fan-out,
   ancestor-chain building (about 400 lines), preview, blocker diagnosis (about
   350 lines). Relates to #450. (V)
6. **Residue.** `on_resolve` has no registrants; `entity_groups` /
   `template_groups` are legacy alias fields. (V)

### Fan-out and fan-in

7. **Stale naming. The code's `Affordance` is a bound fan-out dependency.**
   resolver.py:733 is the only place a VM `Affordance` is built, one per
   provider found by a `Fanout`. (V)
8. **Gap. Fan-in has no VM implementation.** Sandbox "contributions"
   (`SandboxContributionsSpec`: interactions, scheduled events) do the job
   locally, as fan-out-then-back-in. Relates to #556, #527. (V)
9. **Unification. One hub pattern, three implementations.** Menu
   (story/system_handlers.py:164), sandbox (22 `Action` constructions in a
   2,891-line handlers file) and games (mechanics/games/handlers.py) each clear
   tagged dynamic actions and rebuild them from a generator. Only menus use
   `Fanout`. (V)
10. Current clearing is wipe-and-restore by tag. Earlier attempts: a
    multi-edge, then clone per recipient plus garbage collection. (history from
    Derek)

### Determinism

11. Frame RNG is seeded from graph value hash, cursor id and step.
    `_next_provision_uid` draws ids from it at five call sites, all for
    materialized nodes. (V)
12. **Gap. Rebuilt edges do not take seeded ids.** Fan-out results and menu,
    sandbox and game actions pass no `uid`. Needs a replay experiment to
    confirm. (I)
13. **Drift. `_next_provision_uid` silently falls back to `uuid4()`** when it
    has no context. (V)
14. Ids drawn by position in the RNG stream change when provisioning order
    changes. (I)
15. `Entity.templ_hash` already stores template provenance but the uid is not
    built from it. (V)

### Step and ledger

Measured with a scratch script on `adventure_sandbox_slice` and
`blackjack_parlour`, 12 choices each, two runs of the same choices.

22. **Keep.** The split is sound: `Ledger` holds persistent state, `Frame`
    runs one choice. One loop follows an edge, runs eight phases, and either
    redirects, returns from a call, or yields. Causality modes (clean, soft
    dirty, hard dirty) record when determinism was deliberately broken.
    Patches carry before and after hashes. (V)
23. **Gap, north star. There is no session seed, and creation ids are random.**
    `Entity.uid` defaults to `uuid4` (core/bases.py:216) and
    `World.create_story` takes no seed. Two stories from the same world share
    0 of 14 member ids. The frame RNG is seeded from the graph hash, which
    includes those ids, so two sessions making the same choices get different
    random streams. Determinism today means "replanning inside one ledger is
    stable", not "same world, seed and choices give the same story". This
    replaces finding 12: the edge ids differ, but the cause is upstream. (V)
24. **Gap. Replay restores state; nothing re-executes.** `rollback_to_step`
    applies stored patches. No function replays choices and compares hashes.
    `StepRecord` stores the edge id but not the choice payload, so a game move
    cannot be re-driven from the trace. `rollback_to_step` has no caller
    outside tests, and `state_hash` is never read outside the replay
    package. (V)
25. **Cost. Each hop copies the whole graph twice and each choice stores it
    whole.** With an observer set (always, via the ledger) a hop does two
    `unstructure`/`structure` round trips and a member-by-member diff.
    `checkpoint_cadence` is 1 and never overridden, so every choice appends a
    full graph checkpoint, which makes the patch beside it redundant. Measured:
    a 27 KB graph grows the stream by about 45 KB per choice; checkpoints are
    61% of the stream; 40 ms per choice at 50 members. (V)
26. **Unification. Ledger scalars are a fold over step records.** Cursor,
    history, four counters and the call stack are stored, and
    `rollback_to_step` recomputes all of them from `StepRecord`s. The sync
    from frame to ledger is also written twice: `Ledger._sync_from_frame` and
    by hand in service_manager.py near line 420. (V)
27. **Drift. The VM ledger knows media and story sections.**
    `Ledger.structure` binds media fragments to graph resources, and
    `_section_marker_for_trace` reads `locals["section_type"]`. (V)
28. **Residue.** `follow_edge` is split into about twenty single-use helpers,
    which hides a 40-line pipeline. Legacy aliases: `records`, `step`,
    `cursor_id`, `initialize_ledger`, `push_snapshot`. A commented-out
    `PhaseSpec` block in resolution_phase.py. `hasattr(frame, "step_observer")`
    on a typed dataclass. (V)
29. **Supports P2.** PLANNING already provisions the cursor and then each
    immediate successor through `ctx.derive`. That is the frontier fan-in
    should run over. (V)

### Fold (namespace and journal)

30. **Keep. The phase bus carries real load through one mechanism.** Handler
    counts across the engine: provision 15, gather namespace 14, update 10,
    journal 7, compose journal 4, validate 3, prereqs 2, and one each for
    postreqs, finalize and complete-call. Sandbox, games and progression all
    plug in through the same hooks. (V)
31. **Question. `ancestors` has two shapes.** On `GraphItem` it is a method
    that yields from the parent upward, excluding the item. On
    `HierarchicalGroup` (core/registry.py:495) it is a property returning
    `[self, parent, ...]`, including the item. core/graph.py:53,
    `do_gather_ns` and frame.py:384 each probe for which one they have. Derek
    recalls a subtlety about keeping uids in classes that are not registry
    aware; the docstring shows the group taking a registry, so that reason was
    not confirmed. The self-inclusion difference means this is more than a
    spelling fix. (V)
32. **Unification. One scope chain, several folds.** The cursor's ancestor
    chain is walked separately for the namespace (`do_gather_ns`), for
    provisioning candidates (`get_location_entity_groups`) and for template
    scope (`get_template_scope_groups`). In the sketch this is one "scope"
    computed once per context and read by each fold. Authorities probably
    belong to the same chain; not read. (V, I for authorities)
33. **Deliberate (answered by Derek). Intrinsic contribution, extrinsic
    assembly.** `get_ns()` is an ordinary polymorphic method that yields only
    the entity's own contribution: its locals, its named roles and settings,
    any special keys. It must not ask its parent, because the parent includes
    it. The `gather_ns` handler owns the scope: it walks the chain, calls each
    contributor, folds the results, and lets handlers that belong to no object
    join in. Journaling follows the same pattern (enrich namespace, create
    content, then voice handlers). The seam is arbitrary but should not be made
    more complex. (V)
34. **Intended, with one misleading name.** Compose-journal is meant to be a
    pipe. Dispatch was designed to run several ways (stop on first negative,
    last positive, reduce, pipe), and domain complexity was later pushed out to
    phase-manager handlers that implement a recipe and let in-scope objects
    register for sub-phases. In core, however, `AggregationMode.PIPE` is an
    alias of `LAST` (behavior.py:100): last non-empty result wins, and nothing
    is fed forward. The hand-written loop in `do_compose_journal` is the only
    real pipe. (V)
    Derek's correction: results are fed forward through the context. Each
    handler result is pushed onto `ctx.results`, nested dispatches get their
    own list via `with_subdispatch`, and the context caches a namespace per
    node, so a later handler can find earlier results and any node's
    namespace. Carrying the context along the pipe is another reason a manager
    is needed. So `PIPE = LAST` is consistent: the pipe is in the context and
    the answer is the last result.
    Checked: the mechanism is there and filled on every dispatch, but no
    handler in engine source or apps reads `ctx.results`; only tests do.
    Compose-journal handlers get the previous batch through a `fragments`
    argument. So there are two feed-forward routes, and the designed one has
    no consumer yet. (V)
35. **Residue, small.** `do_journal` has the same normalizing loop twice, for
    injected fragments and for handler results. Dispatch helpers take
    `ctx: Any` and validate it at run time. (V)

### Downstream worlds (two private sister repos, read-only)

Detail is kept in a private notes file with the same finding numbers. What
matters to the engine:

36. **A downstream calendar world implements fan-in by compiling it to
    condition strings.** Each scene builds its own offer condition (keys,
    place, hours, dates, "something would play"), and one sandbox hub holds
    every scene as a scheduled event gated by that string. The engine supplies
    the event shape; the world's codec supplies every reason an event is on
    offer. This is "exists is not available" (#527) already working. (V)
37. **A hand-written fan-in already exists in a consumer.** A provider scene
    declares a site and when it is due; any block claiming that site gets one
    kept call edge to it, gated by the predicate. Neither names the other.
    This is the fan-in contract (P2) in miniature. (V)
38. **Arbitration among offers is missing from the engine.** The world keeps
    each place and each cast member to one scene on offer at a time, by rank,
    by appending the negation of each rival's whole condition to a scene's
    availability. The dependency side already chooses among competing offers
    by priority; this is the same choice on the fan-in side. (V)
39. **Equivalence-class merging is implemented downstream.** The codec
    collects every key some condition reads and merges outcomes whose gates and
    effects on read keys match, so one lowering serves a coarse and a fine
    resolution. The engine has no read-set analysis. (V)
40. **Compile-time name checking.** Every generated condition and effect is
    parsed, and one that reads an undeclared name is refused at load. (V)
41. **Workarounds that mark engine gaps.** The clock namespace is handed to
    every node because the sandbox gives `world_time` only to its own
    locations. The sandbox scope is created inside a provision handler. A
    still-due call re-fires on return (#556). (V)
42. **Keep.** Loss records: a codec states what it does not lower instead of
    guessing. (V)
43. **Split.** That codec has a generic half (hub, scenes, outcomes at a
    resolution, keys, dates, transitions) and a presentation half specific to
    its world. (V)
44. **Keep.** The gamebook anthology keeps a promotion ledger of demo pressure
    on the engine: source, local shape, upstream pressure, evidence, status.
    Three entries have already been promoted. The calendar world has no such
    ledger. (V)
45. **Second consumers now exist** for a compose-journal transform recipe:
    both worlds register a late compose handler. (V)
46. **Candidates still open in that ledger:** cached filesystem YAML loading;
    alternate edge layers for analysis (visible, playable, author-only), which
    touches the visibility question in multi-lane (#346). (V)

### Service and persistence

47. **Keep.** Persistence is small: a 148-line manager over a storage by
    serializer grid. `@service_method` already declares access, context,
    writeback and an operation id for each of about twenty operations. (V)
48. **Unification. The service surface is written three times.**
    `ServiceManager` methods, `RemoteServiceManager` (737 lines mirroring each
    method with a hand-written verb and path), and the REST routers. The
    decorator's operation table could drive the remote client and the routes.
    For the TypeScript bootstrap that table is the language-neutral API
    contract. (V)
    History (Derek): an earlier version generated the library API from
    decorated functions and bound it into the web framework and the CLI,
    with endpoints as entities and dispatch for pre- and post-processing. It
    was dropped in rewrites for legibility and to avoid Python magic, once
    the API had settled and agents could do the copying. He agrees it should
    be a single source of authority.
    What survives: `ServiceMethodSpec` still carries name, access, context,
    write-back, capability and operation id. The remote client's paths
    already follow the operation ids (`story.do` is `POST /story/do`,
    `story.update` is `GET /story/update`), and the verb follows write-back
    in the cases read. A low-magic route back, in two steps: first a test
    that the remote client and REST routes agree with the spec table, which
    stops drift without generating anything; then, if wanted, one explicit
    loop over the table that registers routes.
49. **Cost, follows from finding 25.** A session write-back saves the whole
    ledger, stream and checkpoints included, so storage per save grows with
    every choice. Raising the cadence fixes most of it. (I)

### Jumps, calls and redirects (probe 2026-11-11)

Derek: "I keep claiming it's simple when it's actually bundling a lot of
different functionality under the same name."

The mechanism is small. An edge has three independent settings and the frame
has four rules.

| Edge setting | Meaning |
|---|---|
| `trigger_phase` (none, PREREQS, POSTREQS) | followed automatically at that phase instead of being offered |
| `return_phase` | the edge is a call: pushed on the return stack, returned to its origin later |
| `entry_phase` | which phase the destination starts at |

Frame rules: the first available triggered edge wins, in edge order; a
redirect restarts the pipeline at the new node; a call returns when the callee
has no redirect and no selectable choice; a return re-enters the call site at
`return_phase`.

56. **Those few parts carry at least ten authoring intents.** (V)

    | Intent | How it is spelled today |
    |---|---|
    | Descend into a container | PREREQS handler, anonymous edge to the entry member |
    | Skip a node before its content (gate) | authored `first` edge |
    | Interrupt on arrival (appointment) | scheduled event with activation `first` |
    | Subroutine before content | `first` edge that is also a call |
    | Auto-advance after content (pacing) | authored `last` edge |
    | Play the first eligible of several blocks (switch) | several `last` edges with conditions, in order |
    | Route a game by its outcome | POSTREQS edges on the game node |
    | Leave a scene back to its hub | `last` edge to the hub |
    | Go there and come back (chosen) | `return: true` action, sandbox `return_to_location` |
    | Refresh the call site on return | every return re-enters at PLANNING |

57. **Return is implicit and means "ran out of choices".**
    `_complete_exhausted_call` pops the stack when the callee has no redirect
    and no selectable continuation. A callee therefore has to be able to end
    itself, and one stray available choice keeps the call open. (V)
58. **Return also means refresh.** Both real call sites set `return_phase` to
    PLANNING, so a return re-plans the call site, re-runs its PREREQS, applies
    its UPDATE effects again and journals it again. That is why a still-due
    triggered call fires again on return (#556) and why `_visit_count` on the
    call site goes up per return. The docstring's example, returning at
    UPDATE, is not what any caller does. (V)
59. **Unification candidate. Containers and calls are two subroutine
    mechanisms.** A container has a declared entry (`source_id`), a declared
    exit (`sink_id`) and a `default_egress_id`. Entry is used: descent is a
    jump into the entry member. The exit is not: `sink_id` is read only by
    softlock detection and set by one line in `story/episode/scene.py`, and
    nothing returns by reaching it. Calls return by exhaustion. "Return when
    the callee reaches its sink" would be a structural, checkable rule in
    place of an inferred one. (V)
60. **"Visited" counts pass-throughs.** `visited()` and `once` read the
    ledger's cursor history, and the cursor advances before PREREQS. A node
    that a PREREQS redirect skips, and every container descended through, is
    in the history although its content never rendered. The per-node
    `_visit_count` is set in UPDATE and so counts only rendered visits. Two
    counters with different meanings. (V)
61. **Priority is edge order.** "First available triggered edge" follows
    `edges_out()` order, which is graph insertion order, which is authoring
    order. Nothing states a priority, and container descent beats triggered
    edges only by handler registration order, as its own comment says. (V)
62. **A redirect drops choices by filtering afterwards.** When POSTREQS
    redirects, the frame removes fragments whose type is "choice" from the
    journal batch it already rendered. (V)
63. **Triggered edges are previewed at redirect time.** `_target_viable` runs
    a resolver preview from PREREQS or POSTREQS for any target with unresolved
    dependencies or a container entry, so provisioning work happens outside
    PLANNING. (V)
64. **The activation vocabulary is two words for three axes.** Authors write
    `first`, `last` and `return: true`; `entry_phase` is not authorable and
    `return_phase` is always PLANNING. (V)

65. **A call frame outlives its callee (reproduced).** The stack changes in
    two places only: pushed when an edge with `return_phase` is followed,
    popped when the cursor has no redirect and no selectable choice. Nothing
    checks that the cursor is still inside what was called. Experiment: hub
    calls shop; the reader leaves shop by an ordinary choice and walks alley,
    street, dead end. The frame stays on the stack for all three moves, and at
    the dead end it pops and the reader is back at the hub. (V)
66. **A no-choice interjection renders its sender twice (reproduced).** A
    scene with a `last` call to a one-line block and two choices: one move
    renders scene, the block, then scene again; the scene's `_visit_count` is
    2 and it appears twice in the cursor history. (V)
67. **`return_phase=None` already means "do not come back".** Such an edge is
    a jump: nothing is pushed. So an interrupt that leaves for another scene
    needs no stack. The hazard in finding 65 is the opposite case, a call
    whose callee is allowed to leave. (V)

68. **Resume does not exist today (reproduced).** Derek's example: shared
    cleanup on any scene's exit at the theater, written as a silent jump and
    return from the exit block to a block with its own UPDATE, after which the
    exit block picks up where it left off. Built at the VM level with a `last`
    call and the scene's own `last` edge behind it:
    - returning at PLANNING loops: exit block and cleanup alternate, each
      updating and journaling again, until the depth limit of 50;
    - returning at POSTREQS also loops: the exit block is not re-run, but the
      same call edge is first in line again and fires until the limit.
    What is missing is small, and Derek's rule for it replaces my "once per
    visit" suggestion, which he judged probably incorrect: the frame knows
    which edge it left by, so on return it re-enters at the phase the call
    fired in, walks the caller's edges in order, discards everything up to and
    including that edge, and evaluates from the next one. The return address
    is (node, phase, position in the edge list).
    Prototyped outside the engine with an edge subclass, three cases, all
    correct, each node updated and journaled exactly once, stack empty at the
    end:
    - one shared outro: exit block, cleanup, next scene;
    - two shared outros: exit block, cleanup A, cleanup B, next scene;
    - two shared intros before content: intro A, intro B, then the block.
    Consequence: edge order becomes part of the contract (finding 61), so it
    should be stated, not incidental. (V)
    Derek's hangup, same day: re-entrant nodes are forcibly re-provisioned on
    return, because a side trip may have added concepts or changed the graph's
    shape and re-entry cannot be predicted. Existing edges normally keep their
    order, since their dependencies are still met. But if a dependent episode
    or concept was disconnected, not merely made unavailable, the order might
    change. Nodes and edges are only ever unlinked and unregistered, never
    destroyed in place.
    Checked:
    - **The marker is independent of the return phase.** A hub with two due
      arrivals that return at PLANNING, plus the marker: the hub is re-planned
      on each return, arrival A then arrival B play once each, and the hub
      updates and journals once at the end. That is #556 without a
      `not visited` guard. (V, prototype)
    - **Return at PLANNING still refreshes.** The same outro returning at
      PLANNING updates and journals its exit block twice. So intros and outros
      return to the firing phase; hubs return to PLANNING. (V, prototype)
    - **Real hubs delete the edge the marker names.** Menu, sandbox and game
      hubs each call `graph.remove` on their dynamic actions and rebuild them
      on every provision. A rebuilt action has a new random id today, so a
      marker held across a re-plan would not find its edge. Not run end to end
      on a real hub. (V for the removal, I for the consequence)
    - This is where two earlier items pay off: with thumbprint ids (P1) a
      rebuilt edge has the same id, and with a set-difference clear (todo 4)
      an unchanged edge is never removed. Either keeps the marker valid.
    - Decided (Derek, 2026-11-11): when the taken edge is truly gone,
      evaluate from the first edge. It is the principled fallback, the case is
      probably an authoring error, and it is not worth more machinery. The
      real fix is for re-entrant provisioning to re-use existing assignments
      when it can, so edges are not rebuilt in the first place (todo 4).
69. **Concepts cannot contribute updates.** Every UPDATE and FINALIZE handler
    is keyed to the cursor: edge effects, node effects, visit marking, game
    moves, stat challenges, sandbox time on block entry. Nothing lets an
    in-scope concept add an effect. Derek's position: a moment that mutates
    state should do it in its own UPDATE phase; concept-contributed updates
    would be acceptable but are not how it works. (V)

### Demo worlds (read 2026-11-11)

All 23 directories under `worlds/`: index, manifests, script keys, custom
code outline, tests that name them. Scripts were parsed for which authoring
keys they use; none was played.

Derek's framing: mostly small, dressing existing features in narrative
fabric; each exercises a subsystem that was being refined at the time, like a
logic integration test. The "two consumers" promotion rule is a rule of thumb:
he often knows the consumers from earlier versions before they exist here.

| Subsystem | Worlds |
|---|---|
| Plain traversal, tutorial | `reference` |
| Foreign authoring or host | `twine_reference`, `twine_logic_demo`, `renpy_demo` |
| One game kernel in a story shell | `rps_tavern`, `bag_rps_pit`, `blackjack_parlour`, `kim_tray`, `incremental_yard`, `ed_queue_demo` |
| Two kernels over shared state | `colony_loop` |
| Credentials: assembly, game, surface | `credential_gate`, `hall_monitor` |
| Progression under a schedule | `coronate_the_regent` |
| Sandbox hub | `adventure_sandbox_slice`, `red_paperclip`, `repartee_loop`, `destination_choice_demo` |
| Journal fold | `composed_beat_demo` |
| Naming and prose | `concept_naming_demo`, `casting_desk` |
| Wardrobe and media | `modiste_demo` |
| Redirect topology | `logic_demo` |

70. **Keep.** `worlds/README.md` is a real catalogue: it groups by the idea an
    author is looking for and states intent, not coverage. Five worlds carry
    a `cli_witness.txt` transcript. (V)
71. **The usual recipe is a block subclass plus about fifty lines of YAML.**
    Twelve worlds are a `domain.py` with one or more `Block` subclasses and
    handlers, and a short script that wires them with `actions`, `continues`
    and `trigger`. (V)
72. **Three words for one idea, plus a second mechanism.** Derek writes
    `conditions` and `effects`, from long habit; agents push `predicate` as
    the more general logical term. In the code:
    - the mixins are `HasAvailability` (field `availability`) and
      `HasEffects` (field `effects`); there is no `HasConditions`;
    - the value types are `Predicate` and `Effect`;
    - the materializer accepts both `conditions` and `availability` in a
      script and merges them into `availability`;
    - separately, an edge has a singular `predicate` field: the name of a
      namespace key that must be truthy. Nine worlds use it
      (`predicate: game_won`), `HasGame` sets it on its outcome edges, and the
      docstring calls it legacy.
    `predicate: game_won` and `conditions: [game_won]` say the same thing. So
    this is a compiler question, as Derek says: authors write conditions and
    effects; the field is availability, which is the state those conditions
    gate; `Predicate` is the type. The singular `predicate` field is the one
    redundant piece. (V)
73. **The push side has almost no demo-world witness.** No world script uses
    `return`, `once`, `effects`, `availability`, a fan-out, a menu,
    contributions, interactions, exits or dependencies. One uses
    `scheduled_events` with `return_to_location`
    (`destination_choice_demo`). `return: true` appears in one test file and
    in no world or doc; `once: true` appears nowhere in worlds, tests or docs.
    The compact sandbox spec is used only by tests; the cave world builds its
    map in Python. So the push side is witnessed by engine tests and by the
    downstream worlds, not by the teaching collection. (V)
74. **State changes are written in Python, not in scripts.** No world script
    uses `effects`; changes happen in `on_update` handlers on block
    subclasses. The declarative voice is not demonstrated in YAML. (V)
75. **A schedule already exists in the imperative voice.**
    `coronate_the_regent` runs a fixed calendar as a chain of triggered
    continues with conditions (18 triggers, 11 conditions). Next to a
    declarative calendar demo (todo 6c) it would be the same kind of story in
    both readings. (V)
76. **One world writes its own redirects.** `colony_loop` registers three
    `on_prereqs` handlers to route between its two kernels: "route by
    outcome" done in world code. (V)

Coverage of the sketch's coordinates by in-repo worlds:

| Coordinate value | Witnessed by |
|---|---|
| Pull, authored, chosen, jump | every world |
| Triggered | game worlds, `logic_demo`, `coronate_the_regent` |
| Generated by a hub | the four sandbox worlds, in Python |
| Call with refresh | `destination_choice_demo`; sandbox worlds in code |
| Contribution | `composed_beat_demo` |
| Call with resume | none |
| Fan-in | none |
| Arbitration among offers | none |
| Call that ends at a declared exit | none |

### Containers: one source, one sink (2026-11-11)

Derek's intent: source and sink exist to bottleneck setup and cleanup without
anticipating every exit pattern. Enter on the source and exit on the sink,
and a whole container reduces to a single node at the next level up. The
source sets up wherever the reader should land and forwards the cursor there.
The sink finalizes the container and wherever the reader just was, then
forwards them out, back or onward; it does not care which. The idea came from
a discrete-math teacher: however many sources and sinks a graph has, it needs
only one of each, since all sinks can drain to one and all sources can be
routed from one.

77. **The stated contract is not enforced or followed.** VM_DESIGN.md says
    edges into a container target the container and edges out originate from
    its sink. The validator checks only that source and sink resolve and are
    members. Across the 23 demo worlds, 19 worlds have a single container and
    no cross-container traffic. In the four that have more (`casting_desk`,
    `concept_naming_demo`, `logic_demo`, `reference`), all 19 entering edges
    target a member directly, and 9 of 19 leaving edges start at a member
    that is not the sink. (V, measured on eagerly materialized stories)
78. **Neither end does its job today.** The source is the first child and the
    sink is the last child, by default. Earlier versions had synthetic source
    and sink nodes; v38 designates existing members to avoid extra nodes, so
    no node exists whose job is setup or cleanup. An edge that enters at a
    member skips descent, and nothing runs at the sink. This is why shared
    intros and outros were built from calls. (V)

Derek, continuing: in that sense the whole graph is just a big container. A
story always starts on the graph's source, which decides where the cursor
should land and forwards it, and always ends at the story's terminal sink,
which updates the user account and whatever else. Today there is bespoke
logic for the first graph entry, where it should be the ordinary source
pattern any scene might have. Scenes have the same problem; it has not been
hit hard enough to solve yet.

79. **First entry is special-cased in at least five places.** (V)
    - `StoryGraph.initial_cursor_id`, set and overridden in
      `story/fabula/world.py`. (`initial_cursor_ids`, plural, is not a
      duplicate: Derek, it is for several cursors landing on one graph, the
      multi-lane case, #346.)
    - a separate `story_ready` dispatch task, used by three demo worlds to do
      setup before play, which is the source's job under another name;
    - `Ledger._resolve_entry_id`, `_seed_counters`, `initialize_entry` and the
      legacy `initialize_ledger`;
    - `ServiceManager._prime_initial_update`, which calls `goto_node` on the
      cursor if nothing has been journaled yet;
    - `Frame.goto_node`, which skips validation and enters at PLANNING.
80. **The end of a story has no place at all.** Nothing marks a story as
    finished. `stories_finished` is read from the user with a default of zero
    and written nowhere in engine or apps. There is no end-of-story hook; a
    walk that runs out of choices simply stops. The terminal sink Derek
    describes, the one that updates the user account, does not exist. (V)

### Compile and materialize (probe 2026-11-11, outline plus targeted reads)

Terms (Derek): **compile** goes from authored source content and handlers to
a `World` instance. **Materialize** goes from content rules and templates to
node instances on a graph. They look alike and share serialization code, but
they are different operations. In the four levels, compile produces the world
and materialize grounds it into a story graph. Findings 81, 88, 89 and 90 are
about compiling; 82 to 87 are about materializing.

Read: `story/fabula/world.py` story creation, the materializer's pass lists
and template hook, the compiler's shape, the codec interface. Not read: the
body of `StoryCompiler.compile`, the Twine codec, most wiring passes.

Derek's framing: the inverse problem to presentation. Many ways to represent
a story space, from near-native YAML that drops almost straight into
templates to a Twine adapter.

81. **Keep. The pipeline has the shape of the four levels.** Source, then a
    codec that decodes to near-native data and records losses (and can encode
    back), then `StoryCompiler` to a typed template bundle with diagnostics
    (and a `decompile`), then `World` holding templates, then `create_story`
    and the materializer's passes to a graph. Many representations meet at one
    intermediate form. (V)
82. **Eager and lazy are one pipeline with two switches**, as Derek describes
    them: which templates are materialized (all, or the seed groups) and
    whether the prelink passes run. Code matches intent. (V)
83. **The same pass list is written twice.** `_run_topology_passes` (batch)
    and `_run_runtime_topology_passes` (per newly attached node) each list the
    same four wiring passes. Scene contract finalizing is only in the batch
    one; lazily created scenes go through `_ensure_runtime_container_entry`
    instead, so container setup has two paths. (V; the second path not read)
84. **All four wiring passes produce requirement-bearing edges.** Block
    actions, role and setting dependencies, menu fan-outs and media
    dependencies. So on the pull side the imperative and declarative voices do
    lower to one kind of record here. There is no pass for the push side
    other than menu fan-outs. (V)
85. **Creation ids are minted in one place.**
    `StoryMaterializer.story_materialize_template` calls
    `template.materialize(uid=_next_provision_uid(_ctx=_ctx))`. With a context
    the id is seeded; at story creation it falls back to a random one, which
    is the cause of finding 23. The graph's own uid is a random default and
    `story_id` is set to it. So the root of P1 is this call and the graph
    uid. (V for the call; I that no context is passed at creation, from the
    measurement in finding 23)
86. **The template thumbprint is already load-bearing.** Entry nodes are found
    by `Selector(templ_hash=template.content_hash())`. The content hash links
    entity to template in practice; it is just not the id. Two entities from
    one template share it and `find_one` takes the first, which is the
    occurrence question the board agent raised. (V)
87. **First entry has more special cases than finding 79 listed.** Explicit
    versus seed entry templates, `_apply_story_entry_ids`, a
    `_resolve_entry_override` hook that returns nothing, `do_story_ready`, and
    a per-node `do_story_materialized`. (V)
88. **Diagnosis is interleaved with compiling**, as in the resolver (finding
    5). About the first 600 lines of `compiler.py` are issue collection and
    reporting, and `compile` itself is one method of about 280 lines. The
    diagnostics are worth keeping, in particular the report of authored keys
    that were dropped. (V)
89. **Answered (Derek): plain dicts are accepted on purpose.** Data that was
    unstructured from something legal is legal by fiat when it comes back;
    if it is not, that is an error, and checking it against the schema again
    on load is waste. Everything goes only through `structure` and
    `unstructure`, which arrange native datatypes into a class or back.
    Serialization belongs only to the persistence manager and the hasher.
    Nothing entity-like should be created except by structuring it. The
    schema is for authored input.
    Checked against that intent:
    - **`structure` validates every time.** It ends in an ordinary
      constructor call, so pydantic validates round-tripped data again;
      `model_construct` is used nowhere. In the turn profile (finding 50),
      model construction and validation during snapshot restore were about a
      tenth of the time. The principle is stated but not implemented. (V)
    - **The hasher and persistence use different encoders.** Hashing calls
      `json.dumps` with its own default function and sorted keys
      (`utils/hashing.py`); JSON persistence has its own encoder class and
      object hook, beside pickle, BSON and YAML handlers. (V)
    - **About thirty sites construct graph edges directly**, not by
      structuring: 23 in the sandbox handlers, four in the materializer, and
      one each in the resolver, the story handlers, the game handlers and the
      incremental sandbox. (V, by pattern search)
    - These connect to P1: if a generated edge is always structured from
      plain data, its id can be a hash of that data by construction.
90. **Codecs in this tree: near-native and Twine.** Other formats are
    contributed by a world's domain module through `get_story_codecs`. No
    Obsidian markdown reader was found here. The Twine codec is 1,390 lines
    against about 70 for near-native. (V)

91. **A thumbprint identity already exists for scheduled events.**
    `_scheduled_event_contribution_key` in the sandbox handlers returns "a
    replay-stable identity for one scheduled-event contribution": a SHA-256
    over the event's declared value, its source, its sponsor and, optionally,
    its index. That is the P1 recipe (declaration, requester, ordinal),
    already in use from the #527 work, and the index is the occurrence
    discriminator the board agent asked about. It is built with a hand-rolled
    `json.dumps` and `hashlib` beside `model_dump(mode="json")`, not with the
    engine's hasher, which is the habit finding 89 warns about. (V)

### Presentation (probe 2026-11-12)

Read: every class and field in `tangl.presentation`, `core/base_fragment.py`
and `journal/fragments.py`; the head of `PRESENTATION_DESIGN.md`; a census of
which fields are produced by the engine and read by each client. The census
counts whole-word matches outside tests, so common words (`placement`,
`direction`, `contribution`) are inflated on the engine side.

Derek's framing: presentation is a core contract describing what the engine
outputs, and it has strayed as the lines blur between client preferences,
semantic styles versus practical CSS-like behaviour, media formats, authored
media and prose, and generated media and prose.

92. **The stated mission is small and sound.** "Small, domain-neutral syntax
    that a client may render, arrange, or solicit", not a widget library,
    renderer, authority or second journal. The package depends only on
    pydantic and core. (V)
93. **What it carries now, sorted by the lines Derek names.** (V)

    | Kind | Examples |
    |---|---|
    | What was said | content, attributed and dialog fragments, groups, markers |
    | What can be done | choice fragments; `accepts` (pick, text, quantity, pieces, place, compose) with validators; blockers; cost previews |
    | What is disclosed | projected sections and their values (scalar, key-value, list, table, badges) |
    | Semantic advice | `style_tags`, `emphasis`, symbolic `icon`, coarse `placement` |
    | CSS-like mechanism | `style_dict`; staging hints (shape, size, position, x, y, transition, duration, timing, flip); theme colours; stage extent in pixels; surfaces and normalized rectangles; `widget`; `hotkey` |
    | Viewer preference | preference declarations; visibility and clip bindings that tie staged media to a preference value |
    | Media format | sprite sheet manifests, frames and clips; `content_format`; `media_clip` |
    | Transient guidance | UX events, grammar hints |

94. **The contract has split into two client dialects over a floor.** From
    the census:
    - read only by pygame: `icon_media`, `icon_only`, `short_label`,
      `placement`, `media_x`, `media_y`, `media_keep`, `media_flip_h`,
      `speaker_id`, surfaces, stage extent, preference values, sprite sheets,
      and nearly all of `media_visibility`;
    - read only by the web client: `style_name`, `style_dict`, `hotkey`,
      grammar hints, UX events, info affordances, theme colours, `patch_kind`,
      `display_state`, `time_delta`;
    - read by two or more clients: `style_tags`, `emphasis`, `widget`,
      `media_timing`, `media_role`, `content_format`, `presentation_handle`,
      `replaces_text`, projected sections;
    - the CLI reads almost none of the hints. It is the floor. (V, by census)
95. **Some fields have no producer or no reader.** `media_size`,
    `media_position` and `media_duration` appear nowhere outside their
    definitions. `media_transition` appears once, in a world. `hotkey`,
    `time_delta`, `patch_kind`, `display_state` and theme colours are read by
    the web client and produced by nothing in the engine. (V, by census)
96. **Four hint carriers with overlapping fields.** `PresentationHints` on
    content, groups, pieces and sections; `UIHints` on choices;
    `StagingHints` on media; and on key-value rows a `hint`, an `emphasis` and
    a free `presentation_hints` dict. `icon` is on two of them. `emphasis` has
    two vocabularies: primary, subtle, warning on choices; ok, warn, danger,
    subtle on rows. (V)
97. **Mixed base classes.** Intent models, key-value rows and targets are
    `Unstructurable`; hints, projection values and events are plain pydantic
    models. Hints are embedded in fragments, which are persisted records. By
    Derek's structure-only rule (finding 89) this is a question to settle, not
    yet read in detail. (V for the bases)
98. **A third rule language runs in the client.** Visibility and clip bindings
    are small declarative rules (this image shows when preference X has value
    Y) evaluated client-side, beside story conditions and effects. (V)
99. **The design note has become a slice log.** After its opening paragraph,
    `PRESENTATION_DESIGN.md` is a sequence of dated, issue-numbered slices,
    most describing pygame behaviour. The contract and one client's
    implementation notes are in one file, as with #402. (V)

### Media (probe 2026-11-12, outline plus design note)

Read: both media design notes, the module and class outline, the provisioning
and phase-hook outlines, the creator pipeline section. Not read: forge
internals, the resource registry, sprite sheet code.

100. **Keep. The media contract is the clearest in the repo.** Three inputs
     (an authored id or path, authored inline data, a semantic projection
     through a `MediaSpec`) arrive at one `MediaRIT`, which a `MediaFragment`
     places in the journal, the service dereferences, and the client presents.
     Authored and generated media are kept apart cleanly: only generated media
     has a spec. (V)
101. **Media is the pull side, re-used as intended.** `MediaDep` extends
     `Dependency`; offers are ordinary `ProvisionOffer`s; the note's phrase is
     "same offer protocol, different search spaces". Media dependencies are
     soft by default. (V)
102. **Media already has the careful version of thumbprint identity.** A
     generated resource keeps three payloads: the semantic request, the
     adapted backend request, and the realized request. Identity is a hash of
     a declared projection of the adapted request (`fingerprint_payload`);
     provenance that cannot change the output is kept but excluded.
     Composition identity uses child content hashes and excludes child uids.
     The note also states the distinction P1 needs: media is
     content-addressed, concepts are identity-addressed, and two actors with
     identical fields are still two actors. A concept thumbprint is therefore
     a derived name (declaration, requester, ordinal), not content equality.
     (V)
103. **Media registers on the VM from its own side, and the VM also imports
     media.** `media/phase_hooks.py` registers two `on_provision` handlers.
     The resolver separately imports media's provisioners by name (finding 2).
     The first route shows the second is avoidable. (V)
104. **A different scope chain.** Inventories resolve story, then world, then
     system: deployment scope, not graph hierarchy. It is the same gather
     step as pattern 2 over a different chain, which supports sharing the
     walk without forcing one reduction. Likewise `on_adapt_media_spec` is
     documented as ordered dispatch with in-place mutation and "last result
     wins, not fed forward", deliberately not a general reducer. (V)
105. **Negotiation exists for media and is inert for prose.** A render
     profile, a content profile and a pending policy decide what a client
     receives. `ContentFragment.content_format` is declared, produced by
     nothing, and the web client renders markup as literal text. The
     "profiles" in P11 should extend this mechanism, not add another. (V, from
     the note)
106. **Forge status, from the note's own table.** Active: checker, ComfyUI,
     DiceBear, SVG text; composition is a one-level proof. Partial: SVG
     (the largest at 1,336 lines), Stable, TTS. Stub: raster, one line. (V)
107. **Same slice-log pattern, better contained.** About 300 lines of the
     package note are dated issue slices (#571) inside an otherwise stable
     contract. Media hooks also take `ctx: Any` and read the worker dispatcher
     out of context metadata. (V)

### Client apps (probe 2026-11-12)

Read: file inventory of `apps/`, the three session bridges' outlines, the
web client's API paths, the conformance kit's layout. Counted, outside tests:
which service operations, fragment types, input kinds and envelope features
each client mentions. Counts are pattern matches, not behaviour; nothing was
run.

Derek's account: the CLI is close to his first UI pass. The web client was
the test bed for everything non-CLI. The REST server was demoted from engine
to app once it was clear it consumes a service manager like anything else.
Ren'Py is an experiment showing the CLI game loop can be embedded in another
Python host. That led to pygame, the current favourite, which is tightly
coupled and simpler to control than an adapter shim. The apps are drifting
as the floor of the client contract and the supported extras pull apart.
Prose is still open: he wants it to follow media's pattern (pass in raw
content, speakers and scene specifics; rewrite to match story state) and has
deferred it because it is less obvious how.

| App | Lines | Reaches the service by |
|---|---|---|
| CLI | 2,150 | a `ServiceManager` built by `build_service_manager` (local or remote by settings) |
| pygame | 5,540 | an in-process `ServiceManager` through `PygameSessionBridge` |
| web | 4,840 | REST, its own typed client |
| REST server | 1,310 | wraps a `ServiceManager`; reads the method spec table in one place |
| Ren'Py | 860 | an in-process `ServiceManager` through `RenPySessionBridge` |

108. **The common floor, by what all four clients mention:** content,
     attributed text, choices, media, and the `pick` and `text` input kinds.
     (V, by count)
109. **No client covers the whole contract; each leads on a different part.**

     | Feature | CLI | pygame | web | Ren'Py |
     |---|---|---|---|---|
     | Input kinds handled | pick, text, quantity, pieces | pick, text, pieces | all six | pick, text, quantity |
     | UX events | yes | no | yes | no |
     | Grammar hints | no | no | yes | no |
     | Projected state sections | yes | yes, heavily | yes | no |
     | UI preferences | no | yes | no | no |
     | Music snapshot | no | yes | no | no |
     | Control fragments | barely | yes | yes | no |
     | Find an action by typed text | yes | no | yes | no |
     | Marker fragments | no | no | once | no |

     (V, by count)
110. **Refusing explicitly is already a pattern in one client.** pygame's
     bridge defines `UnsupportedAccepts` for input kinds it cannot collect.
     That is the right behaviour for a client above the floor and below the
     full contract. (V)
111. **The session bridge is written three times.** `PygameSessionBridge`
     and `RenPySessionBridge` both define `start`, `choose`, `build_turns`,
     `_ensure_user_id` and `_payload_source`; the CLI does the same work
     inside its story controller. Folding an envelope into turns or passages
     is also done in the web client's `fragmentUtils.ts`. (V)
112. **A portable conformance kit exists and the clients do not run it.**
     `engine/contrib/conformance` holds eleven JSON envelope fixtures, a
     reference port base with CLI and Tk ports, parity and legibility checks,
     multi-envelope sequences and sprite sheet vectors. Only
     `engine/tests/conformance` loads the fixtures. No app's tests reference
     them; the web client keeps its own TypeScript fixtures. The tool built
     to hold clients to one floor is not applied to the three real clients.
     (V)
113. **`RemoteServiceManager` has no direct consumer in `apps/`.** It is
     selected by settings inside `build_service_manager`, so only the CLI can
     reach it. (V)
114. **`BlockFragment` is mentioned only by the Ren'Py bridge.** (V, by
     count)

### Prose and lang (probe 2026-11-12, outline plus the rendering contract)

Read: module and class outlines of `tangl.prose` (1,675 lines) and
`tangl.lang` (2,000 lines), import directions, and three sections of
`EPISODE_SYUZHET_RENDERING.md`. Not read: function bodies, the other prose
design notes (`PROSE_AUTHORING`, `CONCEPT_LINKED_PROSE`,
`PRESENCE_PROSE_CONTRACT`).

Derek's position: prose is still open. He wants it to follow media's pattern:
pass in raw content, speakers and scene specifics, and rewrite the content to
match current story state, as media finds or generates pictures and audio to
match it. It is less obvious how, so it has been deferred.

115. **Keep. The rendering contract already frames prose and media as one
     family without forcing one representation.** Episode plus namespace goes
     to a typed adapter, then to a fragment or a resource specification, then
     to the journal. Adapters share namespace, referents, recursion and
     provenance, and "do not need to share a template language, traversal
     algorithm, intermediate representation, or output type". It lists six
     levels of pre-baking, from a complete authored realization to generated
     content with a fallback, and a static-to-dynamic axis. (V)
116. **What prose has today.** A text-aspect seam (a target and a named
     aspect, resolved through `render_text` dispatch); a recursive template
     session (`TextRenderSession`); mu-blocks for dialog; concept-linked
     naming by what the narrator knows; portraits. In the note's six levels
     that covers authored text, template fill and recursive composition. (V)
117. **Stage by stage against media.** (V for media, from finding 100 to 105;
     V by outline for prose)

     | Stage | Media | Prose |
     |---|---|---|
     | Authored form | id or path, inline data, or a `MediaSpec` | a string or template, callouts, or a target and aspect |
     | A request object | `MediaSpec` | none |
     | An open requirement on the graph | `MediaDep` | none; text is rendered inline during JOURNAL |
     | Adapt to context | `on_adapt_media_spec` | aspect resolvers on `render_text` |
     | Select or create | inventories, then forges | template fill only |
     | Identity and re-use | content hash or spec fingerprint | none |
     | Pending and fallback | yes | no |
     | Output | `MediaFragment` | content, attributed and dialog fragments |
     | Negotiated format | render and content profiles | `content_format` declared, unused |

118. **`tangl.lang` is the rule-based rewriter that is not yet on the prose
     path.** Pronouns, nominals, personal names, conjugation, a thesaurus.
     It is imported by presence, demographics and assembly mechanics, and by
     prose in one place (`naming.py`). In media's terms it is a forge with no
     pipeline calling it. (V)
     History (Derek): `tangl.lang` began as a rewriting kit for turning
     first-person stories into CYOA form: changing names, sexes and point of
     view, reconjugating sentences, adjusting register. Parts were retired (a
     spaCy tokenizer now sits in scratch). The renaming and regendering parts
     are expected to matter again, for a character who changes outfit, name,
     avatar, hair colour or pronouns mid-story.
     That case fixes what a prose request has to carry (P13): the text, plus
     the slice of character state it depends on. When that slice changes, the
     realization's identity changes and the text is rewritten; when it does
     not, the earlier realization is re-used. Media already does this for
     appearance. Earlier journal entries keep the old name, since the journal
     records what was told.
119. **`story` and `prose` import each other.** `story` imports the render
     session, the dialog handler and mu-block types from `prose`. `prose`
     imports actors, blocks, roles, settings and the graph from `story`, but
     only in `naming.py` and `portraits.py`. So the package holds two things:
     a rendering substrate that sits below story, and two story extensions
     that sit above it. Splitting them along that line restores a strict
     import order. (V)
120. **The four-layer rule does not say where prose, media, journal and
     presentation sit.** AGENTS.md names core, vm, story and service.
     Presentation is described elsewhere as a dependency floor. The others
     are placed only by their imports. (V)

121. **Concept-linked naming is in the engine, and it is the dependency
     declaration prose needed.** Derek described it as experimental downstream
     work: content is written with proper names for ease of authoring, some
     concepts are anonymous until introduced, and the journal renderer looks
     each one up as it is encountered. In this repo, `prose/linking.py` scans
     narration for the exact spellings in an adoption table (longest first,
     whole words, backslash to escape, an `#intro` marker) and lowers the text
     to a list of literal strings and `ConceptReference`s with source offsets.
     `prose/naming.py` realizes each reference during JOURNAL as an automatic,
     anonymous or proper form according to what the narrator knows, under a
     per-concept `NamingPolicy` (concealed, proper, off), and `introduce`
     changes that knowledge. `concept_naming_demo` is its witness.
     Consequences for P13:
     - A span of text now declares which concept it depends on. That was the
       hard part of a prose request, and for names it is done.
     - Renaming and regendering are the same lookup with other aspects. A
       pronoun or a changed name is another form of the same reference, which
       is where `tangl.lang` plugs in.
     - Linking runs at render time, on each visit, when the namespace sets
       `link_prose`. The scan depends only on the text and the adoption table,
       so it could be done once when the world is compiled. (V; `linking.py`
       read in full, `naming.py` in part)

### Performance (measured 2026-11-10)

Workload: a large downstream world, about 4,800 graph members, driven through
the service layer. A choice is about three cursor hops.

| Configuration | Seconds per choice |
|---|---|
| As shipped | 5.41 |
| Checkpoints off (cadence raised) | 4.05 |
| Checkpoints and per-hop step tracing off | 0.74 |

50. **About 86% of a turn is replay bookkeeping, not story work.** Under a
    profiler: the two graph snapshots per hop are 37% of the time and building
    the patch from them is 32%. `value_hash` accounts for 52% overall, almost
    all of it inside those. The phases themselves are small: journal 8%,
    dispatch receipts 7%, planning below that. Selection is about 2%. (V)
51. **Derek's hypothesis, checked.** "Selection and materialization of stuff
    that never gets used" is right about the waste and wrong about where it
    is. What is materialized and never used is the snapshot, the patch and the
    checkpoint: rollback has no caller outside tests (finding 24). (V)
52. **Equality serializes.** `Unstructurable.__eq__` calls `eq_by_value`,
    which calls `value_hash()` on both sides, which unstructures and hashes
    each time with no caching. Any `==` or `in` on entities pays that; on a
    graph or ledger it is the whole graph. The profile shows 486,000 model
    equality calls in six choices. Relates to #548. (V)
53. **Hashes taken that nobody reads.** `_run_journal_phase` hashes the whole
    graph before the journal runs on every hop; the comparison after it is
    debug-only. `Frame.__post_init__` hashes the whole graph to seed the RNG
    on every choice. (V)
54. **Random ids are minted on every restore.** Six choices made 424,000
    calls to the system random source, from the `uuid4` default on entities
    being built during `structure`. It goes away with the snapshots. (V)
55. **No timing guard found.** Derek recalls a large-graph choice timing test.
    A search of `engine/tests` for timing calls and test names finds none for
    a turn; the nearest is a sandbox test that path work scales with eligible
    candidates. Search was by name, not exhaustive. (I)

### Core, story, docs, tooling

16. **Residue. Core legacy aliases:** `Registry.keys/items`,
    `Singleton.all_instances/load_instances/load_instances_from_yaml`,
    `Entity.is_instance`, `core/__init__._alias_legacy_module`, Ledger stream
    aliases. (V)
17. **Residue. Story transitional seams:** `World.bundle` (62 test references),
    `.domain`, `.resource_manager`, `StoryMaterializer`. (V)
18. SIMPLIFICATION_SPEC already names legacy aliases, getattr fog and resolver
    diagnostics as accidental. The docs are ahead of the code here. (V)
19. #402 is a stack of dated triage checkpoints, not a roadmap. #611's title is
    stale. 36 of the open issues have no `devref:` label. (V)
20. Eleven test failures are cold-process tests importing `tangl` from the main
    checkout's stale editable install. Environment artifact. (V)
21. Small drift: pyproject says Python 3.12 or later, AGENTS says 3.13;
    `tangldev` URLs; eight worlds lack READMEs. (V)

## Proposals

### P1. Thumbprint ids (accepted in principle)

uid = hash of (template thumbprint, requesting edge, ordinal, step), computed
once at birth and never recomputed.

- For an attachment edge: template is the latent edge, requester is the
  recipient node.
- Reserve the RNG for actual chance. No random fallback.
- Consequences: replanning reproduces ids regardless of order; clearing becomes
  a set difference and is a no-op when nothing changed; provenance is
  recoverable by re-thumbprinting the world; a port needs only a shared hash
  function to match ids.
- Open: whether step belongs in an attachment's id. Leaving it out gives the
  attachment a stable identity across steps.
- **Prior art inside the repo (2026-11-12):** scheduled events already have a
  replay-stable key hashed from declaration, source, sponsor and index
  (finding 91), and generated media has an identity projection that
  separates what determines identity from provenance (finding 102). P1 should
  be stated as generalizing those two, with the engine's hasher, and not as a
  new scheme.
- **Extended after the step probe:** the thumbprint has to start at story
  creation. Root = hash of (world, story label, session seed); every authored
  entity's id = hash of (root, template path). The RNG seed derives from the
  root, the cursor and the step, not from the graph hash.

### P5. Two kinds of similarity (Derek, 2026-11-10)

The seed is an option for testing, not a requirement. Asking for a story gives
a story.

- **Self-similarity.** Given one starting configuration, the same walk
  reproduces exactly: same ids, same state, same journal.
- **Outcome similarity.** A different starting configuration with the same
  choices lands on basically the same story state, though ids differ. The
  journal is outside this comparison; it could be in French.
- Outcome similarity holds only where chance has limited influence on
  provisioning and path availability.

Consequences drawn in review (mine, for discussion):

- A story with no seed supplied draws one and records it, so every story is
  reproducible after the fact.
- Two comparisons are needed: an exact state hash, and a canonical one that
  ignores ids and the journal.
- An id splits into a seed-dependent root and a seed-independent local
  thumbprint (template path, requester, ordinal). The local part is the name
  that lets "the same choice" be said across two stories.
- **Withdrawn:** recording shape-bearing chance in the trace. Derek: that is
  what the patch system already is, a quick stand-in for event-sourced replay,
  and tracking individual mutations is not worth it. Chance is rarely used for
  shape because random grinding is not fun. Patches stay as the "if you really
  want to" mechanism; nothing more gets built on them.
- Checked: the frame RNG has three consumers (provision uids, one site in
  traversable.py, demographics generation). About a dozen game and
  demographics modules use Python's `random` directly, outside the frame RNG.
  So shape is not random today, and game chance is not covered by the frame
  seed either.

Shape versus texture in games (Derek, 2026-11-10): in credentials the script
fixes the shape (say three passes and one arrest) and chance decides what the
candidates look like and what investigating them looks like. The end state is
the declared shape plus the decisions made.

Checked against the games package:

- Credentials: pinned encounters are scripted, as described. The rest of a
  roster draws each candidate's target disposition from
  `disposition_distribution` (credentials_roster.py:291), so the pass/arrest
  mix of a sampled shift is chance, not script. `ShiftSpec.seed` defaults to
  `None`.
- Blackjack and nim take an optional `shuffle_seed`, default `None`.
- Rock-paper-scissors opponents and one shared strategy call the global
  `random.choice`.
- None of these draw from the frame RNG, so replaying a story from the same
  state can deal a different hand.

Refined by Derek the same day:

- The line is fuzzy, like shaded pixels versus textured triangles. A missing
  signature and an expired id are both "deny": different investigations, same
  shape. A forged passport is "arrest": a different shape, because the outcome
  has a different quality, not because the investigation differs.
- Games here are not fair games. They are narrative tricks that keep a reader
  engaged while exploring the story space. Rock-paper-scissors has an escape
  hatch for forcing the result; the favoured model is "always win after three
  rounds".
- Working rule (mine): the script chooses the outcome, chance chooses the
  dress.
- Candidate definition of shape (mine, for discussion): two states have the
  same shape when nothing downstream in the story can tell them apart. The
  shape-bearing variables are then the ones some later condition, route or
  effect reads, which can be computed from the world. This matches the
  resolution-relative bisimulation idea in the story-resolution notes.

Vocabulary (Derek): the term for "indistinguishable downstream" is
**equivalence class**, lifted from Andrew Plotkin's PlotEx write-up
("PlotEx: a tool for exploring puzzle plot constraints", eblong.com/zarf/plotex,
last updated June 2012; the worked example is *Enchanter*). This tally uses
"equivalence class" from here on; "same shape" above means the same thing.

What the paper actually defines, read 2026-11-10:

- A state is a set of qualities, all assumed positive (having is never worse
  than not having). An action checks some qualities and changes others.
- An action that strictly improves a state is free: there is never a reason
  not to take it. States are grouped by their closure under free actions, and
  the search runs over those groups. *Enchanter* drops from 4,468 states to 96.
- The tool lists terminal states, marks the preferred ones, and re-runs with
  an action blocked to show where a player gets stuck.
- Stated limits: poor at timed puzzles and at arithmetic constraints.

So there are two equivalences, and they compose:

- **Plotkin's:** states that reach the same place by free moves. This is the
  "in and out of a room is a no-op" and "pick it up now or later" case.
- **Read-set merging (finding 39):** outcomes whose effects differ only on
  keys nothing reads.

The downstream calendar world's catalog is already in PlotEx's form: keys are positive booleans,
`requires` is the check, `yields` is the free gain, `gives` is the loss. Its
calendar is the part the paper says the model handles badly.

Settled for now (Derek):

- The definition is decent. At what scale "tell them apart" is judged is an
  open question, tabled.
- Replay does not have to be draconian. Under controlled conditions it should
  reach a fuzzy deterministic replay to the level wanted. "It's not a moon
  landing calculation."
- Games may be fair, and a fair game is a good first step for a framework. Each
  should also show that an author can put a thumb on the scale to any degree.
  Determinism gets fuzzier the lighter the thumb, and that is fine.
- Review consequence: no strict-determinism machinery goes on the todo list.
  The relevant check for a game is whether it exposes an authoring control
  over its outcome.

Checkpoint cadence 1 was scaffolding: it avoided validating incremental
patching while every other feature was under test. It can go up.

### P6. Promote the downstream calendar approach in four pieces (accepted 2026-11-10)

Not one port of a codec; each piece goes where its operator lives.

1. **Site arrivals become the VM fan-in** (todo 6). The downstream handler is
   the first consumer and is deleted when it lands.
2. **Arbitration becomes part of hub projection** (todo 4): an event declares
   what it contends for (place, cast) and its rank; the hub picks one per
   contended provider when it projects choices. No nested condition strings.
3. **Read-set analysis becomes a story-level tool**: keys read, keys written,
   undeclared names, and the outcome merge into equivalence classes. It also
   supplies the canonical state for P5: the state restricted to read keys.
4. **The offer builder becomes a demo**: a small calendar world in storytangl,
   a handful of scenes with a place, cast, hours, dates and keys, lowered to
   one sandbox hub by a short codec with no staging. That is the "sandbox
   enumeration" demo.

### P7. Performance track (new)

Derek's stance: do not optimize until the behaviour is settled, but playable
demos are converging and the pain points are now measured. Ordered by return:

1. **Trace per choice, on a cadence, not per hop.** The ledger attaches the
   step observer on every choice. Attach it only when a checkpoint is due, or
   make it opt-in. Measured ceiling: 5.4 s to 0.74 s.
2. **Raise the checkpoint cadence** (item 3b).
3. **Drop the unread hashes** (finding 53): gate the journal hash behind the
   debug check; seed the RNG from the recorded seed and step, which P1 needs
   anyway.
4. **Identity equality for graph items; value equality by explicit call**
   (finding 52, #548).
5. **A timing guard**: one synthetic large graph and a per-choice budget, so a
   naive addition shows up in CI.
6. Later, if replay is wanted cheaply: record changed members through the
   existing registry observer, not by copying and diffing the graph.

Then profile again; the remaining 0.74 s has not been broken down.

### P8. Name the control-flow intents (new)

Keep the three edge settings as the machine level. Above them, give each
intent in finding 56 a name, a row in one table (trigger, call, entry phase,
what "visited" means, what the journal shows) and one witness test. The
compiler already lowers `first` and `last`; it would lower the named intents
the same way. Then decide three semantics once, in the table:

1. **When a call returns:** on reaching the callee's sink (finding 59), with
   exhaustion kept as the fallback for callees that declare none.
2. **Whether return refreshes:** a return that resumes after the call
   (no re-run of PREREQS, no second UPDATE) versus one that re-enters the hub.
   Hubs want the second; subroutines before content want the first. Today
   both get the second.
3. **What counts as a visit:** rendered, or passed through. One counter, or
   two with different names.

Derek, 2026-11-11: the mechanism is mostly for two things. Shared intros and
outros, and re-entrant scenes: a menu of choices, play one, return when done.
So there are several termination conditions and several restored-state
patterns to come back to. That gives the table two axes.

| How the callee ends | Examples |
|---|---|
| Runs out of content | a linear shared intro or outro |
| Reaches a declared end | a scene's last block; a container's sink |
| The reader says so | an "all done here" choice in a hub |
| An outcome is reached | a game won or lost |

| What the caller gets back | Wanted by |
|---|---|
| Resume: carry on from just after the call | intro before content; outro after it |
| Refresh: re-plan and re-render the caller with new state | a menu or hub |
| Refresh plus a charge or effect on completion | a scheduled event that costs time |
| Leave: go on to somewhere else | a scene handing back to its hub |

Today every return is a refresh at PLANNING and every termination is
"ran out". Two cases need care:

- **Several intros due at once.** Solved by Derek's resume rule (finding 68):
  return to the firing phase and continue from the edge after the one taken.
- **An outro before the choices.** The frame has already dropped the caller's
  choice fragments when POSTREQS redirected (finding 62), so a plain resume
  would return to a node with no menu shown.

Derek's two cases, 2026-11-11, and where they land:

- **Interjection.** A concept in the scene (a companion) has a one-line block:
  say something, note a mood, bump a "last spoke" counter, return at once so
  the sender can list its choices. Today this is a call and costs a second
  render of the sender (finding 66). It does not need the cursor to move. It
  fits the journal fold: the concept contributes a fragment while the sender
  is journaled and applies its small state change in FINALIZE. That is a
  fan-in on the journal, and it matches "concepts nominate, a handler
  decides". An authored block could still be the source, lowered to a
  contribution.
- **Interrupt.** A condition fires and pushes the reader to another scene. If
  they come back it is a new visit: render again, and the redirect fails
  because it is `once`. That is a jump (`return_phase` none) plus history, no
  stack.

- **Shared outro with bookkeeping** (Derek, same day). The cleanup block
  keeps its own UPDATE phase, so it is a real call, and the caller must
  resume, not restart (finding 68). Hardcoding the call into every exit block
  is the copy-per-scene form. The setting-conditioned form is fan-in: the
  theater offers the call on any exit block whose setting is the theater.
  Fan-in attaches the edge, the call runs the callee's own UPDATE, resume
  returns. No concept-contributed updates are needed.
- The trivial interjection can still be a journal enrichment when it changes
  no state. When it does, it is the same shape as the shared outro.

So a third axis: **does the edge intend a return at all?** Jump, call, or
contribution. And one rule to add for calls: a frame is tied to what it
called, so leaving the callee by anything other than its return either
discards the frame or is refused. Which of those is a design decision.

This is documentation and a compiler table first. Frame changes follow only
where the table shows two intents that need different behaviour.

### P9. One small witness world per new operator (new)

Derek, 2026-11-11: much of what is missing here is recent work demanded by a
downstream world's format, so it lacks a consumer in this repo. And the
declarative side gets short shrift because agents helping with domain code
find if/then easier than requirements and bindings. So these worlds are also
the exemplars an agent copies from; without a declarative one in the repo,
the next world will be imperative too.

Follow the existing habit: each operator added in the overhaul gets a tiny
world that is its integration test and its teaching example, with a README
and a CLI witness. Candidates, each a few dozen lines of script and no custom
block class where possible:

- **Shared intro and outro**: two scenes that call the same intro and the
  same cleanup, with resume (item 3s).
- **Interjection**: a companion who speaks before the choices.
- **Fan-in**: "go home" and "call mom"; a site that calls whatever is due.
- **Arbitration**: two events contending for one place.
- **Calendar**: the declarative schedule (item 6c), paired with
  `coronate_the_regent` as the imperative one.
- **Effects in script**: one world whose state changes are all authored in
  YAML.

### P10. Use the container contract for setup, cleanup and call extent (new)

The source and sink already describe most of what P8 asks for. For
discussion:

- **Shared intro and outro become structural.** Setup belongs to the source
  and cleanup to the sink, once per container, however the reader gets in or
  out. The theater example needs no call and no fan-in.
- **A call's extent is a container.** "Reaches a declared end" is reaching the
  sink. A call frame that outlives its callee is an exit that bypassed the
  sink, which a validator can report at load.
- **A container is one node a level up.** That is the coarse resolution of the
  story-resolution notes, and it lets analysis treat a container as a single
  step from entry state to exit state.
- **Lowering, not policing.** Authors keep writing edges to and from members.
  The compiler can route an entering edge through the container, with an
  entry rule naming the member, and a leaving edge through the sink, carrying
  its real destination. `HasContainerEntryProjection` already has entry
  rules.

- **The story is the outermost container.** Its source does what
  `story_ready`, entry selection and the service's priming step do now, as
  one ordinary setup-and-forward. Its sink is the missing end of story: where
  the user account learns a story finished. Seen as a call, the session is
  the caller of the root container, so reaching the root sink is a return to
  the service, and the existing call-completion hook is where the account
  update would go.
- The same contract then holds at every level: world, story, scene, block.
- **Multi-lane fits the same picture.** Derek: the same story world
  experienced across two different episode DAGs that share the grounded
  concept space. The story's source forwards one cursor per lane. In the four
  levels, the story graph is shared and there is one partial order and one
  journal per lane. The first small demo is to be the Lost Worlds gamebooks:
  each reader holds the other's book, both call a move, a result grid sends
  each to the page showing what happened to the opponent from their own point
  of view. It needs no dice: the outcome is an authored table over two
  simultaneous choices, which suits "games are narrative devices".

- Derek's sizing of multi-lane: one ledger, one frame, two cursors, two
  journals, and a "both lanes ready" step held by an orchestrator in the
  service layer. The VM does not care when the lanes are ready; it steps when
  signalled. Clients: a hot-seat CLI and perhaps a Discord plugin, which
  brings networking and identity with it.
- From this review, what is per-cursor on the ledger today and would move
  into a per-lane record: cursor id, cursor history, call stack, the step
  counters, the redirect trace and the output stream. Finding 26 already says
  the scalars are a fold over step records; a lane id on each record makes
  that fold per lane.
- One interaction to settle: a lane that has committed its move and is
  waiting for the other has no selectable choice, and "no selectable choice"
  is what the frame reads as exhaustion (finding 57). Waiting has to be
  distinguishable from finished.
- "Both ready" can be an ordinary condition. Each lane's move is recorded on
  the shared node; a triggered edge to the result page is available once both
  are recorded; the orchestrator only has to step the waiting lane again when
  the other commits.

- Derek's refinement: cursor history, call stack, step counter and journal
  are properties of the ledger having a cursor, and should extend by
  definition to n cursors. The step counter is per cursor, since lanes take
  different redirects and routes. The choice counter is shared in this plan:
  it is what the orchestrator blocks on, until both lanes are ready for the
  next choice. A MUD would not block. Open, his to think about: the VM may
  need to spin several steps, a different number per cursor, before settling.
- For that open point (mine): one lane already settles this way. A frame
  follows redirects until it reaches a selectable choice or runs out, under a
  depth cap. With two lanes the same loop moves up a level: step any lane
  that has a due triggered edge, until none has. Two things then need
  stating. Lane order, since one lane settling can make an edge due in the
  other; a fixed order keeps it repeatable. And where a joint outcome is
  computed: once, on the shared node, so that the second lane reads a result
  and does not recompute it.
- Three clocks, to keep the names apart: per-lane steps (cursor hops), the
  shared choice count (the blocking turn), and arrival order (a MUD, which
  would have to be recorded to replay). `Ledger.turn` already means something
  else: distinct position changes in one cursor's history.

Open: whether source and sink are designated members with extra duties, or
return as dedicated nodes; and how the sink learns where to forward.

### P11. Re-centre presentation on three questions (new, mine)

The engine answers three things: what was said, what can be done, what is
disclosed. Those are the contract every client must honour, and the CLI
already does with nothing else.

Everything else is advice, in two tiers:

- **Semantic advice**: tags and coarse roles a client may honour or ignore
  (`style_tags`, `emphasis`, symbolic `icon`, coarse `placement`,
  `media_role`). One vocabulary, one carrier.
- **Profiles**: mechanism for a class of client, named and optional. Media
  already negotiates by render profile, content profile and pending policy
  (finding 105); profiles here extend that, they do not add a second
  negotiation. A
  staging profile (positions, clips, surfaces, visibility bindings) and a
  style profile (`style_dict`, theme colours, hotkeys). A client declares
  which profiles it understands, as the content-negotiation notes already
  propose for media and prose formats.

Then: fields with no producer or reader are removed or marked reserved; media
formats move beside media; the design note keeps the contract and each
client's slice notes move to that client.

### P12. Hold the clients to the floor with the kit that exists (new, mine)

- **Run the portable fixtures in each client's tests.** For each fixture a
  client either renders it or refuses it explicitly. A crash or silent drop
  fails. This turns "the floor" into something CI checks.
- **Each client declares what it supports**: input kinds, fragment types,
  profiles. The table in finding 109 becomes data the client publishes, and
  the engine or an author can read it. This is the same declaration P11's
  profiles need.
- **One session bridge.** `start`, `choose`, `refresh` and a fold from
  envelope to turns, in one place that pygame, Ren'Py and the CLI share.
  Whether it lives in the service layer or a small client-side package is
  open.

### P13. Prose on media's pattern: the missing pieces (mine; design is open)

Not a design, a list of what finding 117 says is absent, in the order media
acquired them:

1. **A request object.** Raw content, the speaker, the scene specifics, and
   the intent (voice, point of view, tense, language). The analogue of
   `MediaSpec`.
2. **An identity for a realization.** A hash of the request's
   rendering-relevant projection, as media does with `fingerprint_payload`.
   That makes a rewrite reproducible and re-usable, which matters more once a
   rewriter is not deterministic.
3. **A select-or-create step.** Use an authored realization if one matches;
   otherwise fill, compose or rewrite. `tangl.lang` is the first rewriter;
   a model-backed one would be another, as forges are for media.
4. **Pending and fallback**, only if a rewriter is slow. The fallback is the
   raw content, which always exists.
5. **A negotiated output format**, by switching on the `content_format` that
   is already declared.

The journal already records what was told, so replay does not depend on a
rewriter being repeatable; identity is for re-use and for re-voicing. Whether
prose needs an open requirement on the graph, as media has, is the open
question: text has no inventory to bind to today.

### P4. The save is the choice list (not discussed; deprioritized by P5)

With P1 in place, a session is (world, seed, list of chosen edge ids and
payloads). Everything else is derivable by re-execution.

- `StepRecord` gains the choice payload.
- A verifier re-executes the list and compares `state_hash` per step.
- Checkpoints and patches become an optional cache for fast rollback, taken
  every N choices, not the record of truth.
- Ledger scalars become a fold over step records, computed in one place.

Derek's later position (P5) is that patches are a hand-wave not worth more
investment, so only the cadence change is on the week's list.

### P2. Fan-in contract v0 (drafted, not yet written into the docs)

- Three states: latent, attached, active.
- Runs in PLANNING for each node the resolver plans (the cursor and its
  immediate successors, per finding 29).
- Scope: `get_location_entity_groups` neighbours plus ancestors' children.
- Match: `Requirement.satisfied_by` against the node.
- Binding sets the open source. The result is an ordinary choice if the
  destination is traversable, otherwise a concept link.
- Conditions are checked at use time.
- Witnesses: site arrivals (a scene declares a site and when it is due);
  a scene with role "mom" who owns a returning "call mom" episode; home
  affording "go home".

### P3. Parity basis for the TypeScript port (proposed; reshaped by P5)

World and choices in; fragment stream and state out, with no uids in the
trace. After P5 the comparison is on equivalence classes: the state restricted
to keys something reads, journal excluded. Plus a few properties: round-trip,
import DAG.

## Touring proof (side quest)

Open puzzle on a downstream calendar world: prove that one playthrough can
visit everything. Counting arguments show nothing is obviously impossible;
a proof is a witness schedule. Detail and runs are in the private notes.

What the attempt showed about the engine, 2026-11-10:

- A choice costs about 4.5 s on a graph of about 4,800 members, so search by
  backtracking through the engine is not feasible. This is finding 25 at
  scale.
- A greedy walk through the service layer (most constrained scene with new
  content first) fails: it visits about half the scenes, because it starves
  unlock chains and spends slots on scenes that give one new block per visit.
- The workable plan is to search on a cheap interpreter over the lowered
  conditions and effects, then replay the winning schedule once in the engine
  or the CLI as the witness. That interpreter is the explorer in item 6b.
- Scheduling ideas from Derek that generalize: slots differ in value; unlock
  order outranks local novelty; always-available scenes fill slack; pack from
  both ends, fixing forced openers and forced closers so only the middle needs
  search. The last is the critical-path method: a forward pass gives an
  earliest position, a backward pass a latest one, and the difference is
  float.

## Week sequence (draft)

Ordered so each day's work makes the next day's smaller. Item numbers refer to
the todo table below.

| Day | Theme | Items |
|---|---|---|
| 1 | Cheap fixes and writing things down | 3k step tracing; 3l unread hashes; 3n timing guard; 20 Dependabot; 3b cadence; 15 cold-process tests; 3g `ancestors`; 3i compose-journal field; 9 and 3j design notes; 13 ROADMAP; 16 devref labels (issues agent) |
| 2 | Control flow named; provisioning made smaller | 3o intent table and witnesses; 1 offer sources via dispatch; 2 single binding; 5 naming |
| 3 | Ids and seeds | 3 thumbprint ids with a recorded seed; 3e games seed from the frame |
| 4 | Hubs | 4 shared clear-and-project helper; 6a arbitration |
| 5 | Fan-in | 6 VM fan-in with site arrivals as witness; 6d sandbox gaps |
| 6 | Analysis and the demo | 6b read-set analysis; 6c calendar demo world |
| 7 | Sketch v2 and slack | 11 parity check on equivalence classes; clean-slate sketch v2 for the TypeScript bootstrap; 8 or 10 if time |

Deferred past the week: 7 lowering sandbox contributions onto fan-in; 3a, 3c,
3d ledger work; 3h scope chain; 18 service operation table; 14 tutorial; the
Salon Season, multi-lane and web attribution demos.

## Week todo list

Sizes are guesses.

| # | Item | Kind | Size |
|---|---|---|---|
| 1 | Register offer sources through dispatch; remove VM to media imports | simplify | M |
| 2 | One stored binding per open edge; hoist Dep/Aff bodies to `HasRequirement` | simplify | S |
| 3 | Thumbprint ids from story creation down, with a recorded seed (optional input); no random fallback | fix | L |
| 3a | Choice payload on `StepRecord`; re-execution verifier (deprioritized, see P4) | feature | M |
| 3b | Checkpoint cadence above 1 by default; one snapshot per hop, not two | fix | S |
| 3k | Step tracing on a cadence or opt-in, not on every hop (P7.1) | perf | S |
| 3l | Drop unread whole-graph hashes in the journal phase and frame seed (P7.3) | perf | S |
| 3m | Identity equality for graph items; explicit value equality (#548) | perf | M |
| 3n | Large-graph timing guard test with a per-choice budget | test | S |
| 20 | Dependency alerts (248 open, about 42 packages). Raise the Pillow constraint past `^11` (closes 111, including 10 of 17 critical); `poetry update` for the server stack; `yarn upgrade` in `apps/web`; add a grouped weekly `dependabot.yml` | fix | S |
| 3c | Ledger scalars derived in one place; remove the service-side copy of the frame sync | simplify | S |
| 3d | Inline `follow_edge` helpers; move media and section knowledge out of the VM ledger | simplify | S |
| 3e | Games default their seed from the frame RNG so a replayed story deals the same hand | fix | S |
| 3f | Credentials: decide whether a sampled shift's pass/arrest mix is scripted (authoring call, not a bug) | design | S |
| 3g | Decide one shape for `ancestors` (method or property, self included or not), then delete the three probes | cleanup | S |
| 3h | One scope chain per context, read by namespace, candidate and template folds | simplify | M |
| 3i | Compose-journal feeds forward through the phase context (Derek's preference): a named, typed field for the batch so far, replaced each step so it holds the settled batch after culling; `ctx.results` stays the append-only history; drop the argument rewriting | simplify | S |
| 3u | State the four levels (world, story graph, episode DAG, journal) as progressive orderings of one space in ARCHITECTURE.md, since the storage split hides it. Optional: an analysis projection that reassembles the full tree from a ledger, world to fragment leaves | docs | S |
| 3j | Write the "intrinsic contribution, extrinsic assembly" pattern and the phase-manager recipe idea into VM_DESIGN.md | docs | S |
| 3o | Control-flow intent table in VM_DESIGN.md with one witness test per intent (P8) | docs, test | M |
| 3s | Resume: a triggered call returns to the phase it fired in and evaluation continues from the edge after it (finding 68, #556). The return edge carries the call's id; the two redirect handlers start after it. Static blocks first; hubs need item 3 or 4 so a rebuilt edge keeps its id | fix | S |
| 3q | Scope call frames to their callee: discard or refuse on leaving by another route (finding 65) | fix | S |
| 3r | Interjections as journal contributions, not calls (finding 66) | feature | M |
| 3p | Decide and implement: return at sink, resume versus refresh, one meaning of visited (P8) | design, fix | M |
| 3t | Invariant test: planning the same node twice against unchanged state leaves the graph unchanged (ids and order). Expected to fail on hubs today; passes once items 3 and 4 land | test | S |
| 3v | Lower the singular `predicate:` key to a condition in the compiler and drop the edge field and its branch in `source_available`; state the vocabulary once (authors write `conditions` and `effects`) (finding 72) | cleanup | S |
| 3w | Witness worlds for new operators as they land (P9) | demo | S each |
| 3x | Validator reports edges that enter a container at a member or leave from a non-sink member (finding 77); report only at first | test | S |
| 3z | Story as the root container: fold `story_ready`, entry selection and priming into its source; add its sink as the end-of-story point that updates the user (findings 79, 80) | design | M |
| 3y | Container setup at the source and cleanup at the sink, with cross-container edges lowered through them (P10) | design | M |
| 3ab | Trusted `structure`: skip validation for data that came from `unstructure` (finding 89); measure against the timing guard | perf | S |
| 3ac | Generated edges built by structuring plain data, not by direct constructor calls (finding 89); pairs with P1 | simplify | M |
| 3aa | One wiring pass list used by both the batch and the per-node path; one path for container setup (finding 83) | simplify | S |
| 3af | Media: delete the one-line raster forge stub; move the #571 slices out of the package contract (findings 106, 107) | cleanup | S |
| 3ag | Clients run the portable conformance fixtures: render or refuse explicitly (finding 112) | test | M |
| 3ah | One shared session bridge for the in-process Python clients (finding 111) | simplify | M |
| 3ai | Split `tangl.prose` into the rendering substrate (below story) and the naming and portrait extensions (above it); state where prose, media, journal and presentation sit in the layer rule (findings 119, 120) | simplify, docs | S |
| 3ad | Presentation: remove or reserve fields with no producer or reader; one `emphasis` vocabulary; one hint carrier (findings 95, 96) | cleanup | S |
| 3ae | Presentation: split the design note into contract and per-client slice notes; state the three questions and the two advice tiers (P11) | docs | S |
| 4 | One shared clear-and-project helper for menu, sandbox and game hubs. It re-uses existing edges and assignments where they are still wanted and removes only the rest; this is what keeps resume valid on hubs | simplify | M |
| 5 | Name fan-out results as bound dependencies; reserve `Affordance` for the source-open edge | rename | S |
| 6 | Fan-in in VM; witnesses: site arrivals (site plus due-when) and "go home / call mom" | feature | L |
| 6a | Offer arbitration in hub projection: contended provider plus rank | feature | M |
| 6b | Read-set analysis in story: keys read and written, undeclared names, outcome merge by resolution. Stretch: a PlotEx-style explorer over the same keys (terminal classes, stuck states, block-an-action what-ifs); first use is the touring proof | feature | M |
| 6c | Calendar demo world with a short catalog codec (sandbox enumeration) | demo | M |
| 6d | Sandbox gaps a downstream world works around: clock namespace outside locations, scope creation at setup | fix | S |
| 7 | Lower sandbox contributions onto fan-in, then #556 | simplify | L |
| 8 | Split diagnosis and ancestor building out of the resolver (#450) | simplify | M |
| 9 | Write fan-out/fan-in and the determinism contract (P5) into AFFORDANCE_MODEL.md | docs | S |
| 10 | Delete core legacy aliases; retire story transitional seams | cleanup | M |
| 11 | Parity check for the TypeScript port, on equivalence classes (P3) | tooling | M |
| 12 | Downstream codec audit (done; see findings 36 to 43) | review | done |
| 13 | Replace #402 with a short ROADMAP; retitle stale issues; prune finished handoff docs | docs | S |
| 14 | Tutorial path for a new author | docs | M |
| 15 | Cold-process tests pass the source path explicitly | fix | S |
| 16 | devref: filter noisy pack headings; make the query test independent of a local issue snapshot (labelling was done in the 2026-11-10 board audit) | tooling | S |
| 17 | Small drift: Python version, `tangldev` URLs, eight world READMEs | cleanup | S |
| 18 | Service operation table as the single source: first a conformance test that remote client and REST routes match it; later an explicit loop that binds them | test, simplify | S then M |
| 19 | Promotion ledger for the calendar world, seeded with P6; cached YAML path loading from the gamebook ledger | docs, fix | S |

Demo ideas:

- Calendar world: sandbox enumeration from a schedule script, promoted from
  a downstream codec (item 6c).
- Touring witness: a proven complete tour of a calendar world, replayable in
  the CLI.
- Salon Season first playable (#669).
- Two-reader multi-lane witness (#346).
- Web attribution witness (#611).

## Open questions for Derek

1. Fan-in scope: exclude the "rest of graph" fallback?
2. A concept affording itself: is that an edge whose projection is a namespace
   entry?
3. Attached but inactive: shown disabled or hidden? (Looks like a presentation
   choice.)
4. Does step belong in an attachment's id?
5. Is the equivalence-class comparison the right parity basis for the port?
6. Answered: the seed is optional, for testing. See P5.
7. Answered in effect: patches are not worth more investment; raise the
   cadence only.
8. Answered: no. Shape-bearing chance is not recorded; see P5.
9. Tabled: at what scale is "tell them apart" judged?

## For the issues-board agent

Candidate issues, none filed yet. Existing issues to link are in brackets.

- Offer sources registered through dispatch (findings 1, 2). Topic:
  provisioning.
- Single stored binding on open edges (findings 3, 4). Topic: provisioning.
- Thumbprint ids, recorded seed, no random fallback (findings 11 to 15, 23,
  P1). Topic: provisioning, replay. [#548]
- Checkpoint cadence and per-hop snapshot cost (findings 25, 50 to 55, P7).
  Topic: replay, ledger. [#548]
- Large-graph timing guard test (finding 55).
- Ledger scalars as a fold; duplicate frame sync in service (finding 26).
  Topic: ledger.
- Shared hub projection helper and offer arbitration (findings 9, 38). Topic:
  provisioning, sandbox.
- VM fan-in with site arrivals as witness (findings 8, 37, P2). [#556, #527,
  #255]
- Read-set analysis and equivalence classes in story (findings 39, 40).
- Calendar demo world (P6).
- Sandbox clock namespace and scope creation (finding 41).
- Control-flow intent table; return at sink; resume versus refresh; meaning
  of visited (findings 56 to 64, P8). Topic: traversal, frame. [#556]
- Resolver split (finding 5). [#450]
- `ancestors` shape (finding 31); compose-journal context field (finding 34).
- Service operation table (finding 48).
- Legacy alias and transitional seam removal (findings 16, 17).
- Cold-process test source path (finding 20).
- Housekeeping: label the 36 unlabelled issues; retitle #611; replace #402 with
  a ROADMAP.

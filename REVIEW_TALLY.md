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

Not yet read in any depth (as of 2026-11-11): the story compile path
(`story/fabula` compiler and materializer), `tangl.media` beyond its
provisioners, `tangl.prose` and `tangl.lang`, `tangl.presentation`, mechanics
other than sandbox and game handlers (assemblies and components, progression,
demographics, credentials internals), the four apps (CLI, pygame, web,
server), the loaders, and the docs site as a whole. Core was read for
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

- **Several intros due at once.** Resuming at UPDATE would skip the remaining
  PREREQS edges; refreshing re-fires the one just played. "Once per visit"
  for a triggered call, as #556 proposes, is the same fix from the other side.
- **An outro before the choices.** The frame has already dropped the caller's
  choice fragments when POSTREQS redirected (finding 62), so a plain resume
  would return to a node with no menu shown.

This is documentation and a compiler table first. Frame changes follow only
where the table shows two intents that need different behaviour.

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
| 3j | Write the "intrinsic contribution, extrinsic assembly" pattern and the phase-manager recipe idea into VM_DESIGN.md | docs | S |
| 3o | Control-flow intent table in VM_DESIGN.md with one witness test per intent (P8) | docs, test | M |
| 3p | Decide and implement: return at sink, resume versus refresh, one meaning of visited (P8) | design, fix | M |
| 4 | One shared clear-and-project helper for menu, sandbox and game hubs | simplify | M |
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
| 16 | devref: label unlabelled issues; filter noisy pack headings | tooling | S |
| 17 | Small drift: Python version, `tangldev` URLs, eight world READMEs | cleanup | S |
| 18 | Service operation table drives the remote client and REST routes | simplify | M |
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

# StoryTangl review (November 2026), consolidated

A whole-project review, groomed on 2026-11-13. The chronological record, with
all 136 numbered findings, the experiments and two rounds of outside review,
is in [REVIEW_TALLY_FULL.md](REVIEW_TALLY_FULL.md). Finding numbers below
(F1 to F136) and proposal numbers (P1 to P14) refer to it. Probe scripts are in
`scratch/review_probes/`.

## 1. The lens

This is not a game engine. It follows ideas Derek had while working on
synthetic image generation and anatomic classification: apply the same logical
framework to story writing and understanding, or to any process that can be
generated and understood.

What matters, in his order:

- **The gestalt**: a coherent conceptual design.
- **Transfer**: what it implies for applying formal processes in other domains.
- **Story shape-and-appearance models** that are basically deterministic,
  unlike story writing by a language model.

What matters little: works, optimized, consistent, safe. Those are there so the
foundation does not undermine the exploration, and because a public repo should
not be riddled with errors.

Reproducibility is not hard and fast. The claim is: reproducible to a given
equivalence, when the engine is used in a specific way.

So this review ranks things by whether they make the design clearer, more
demonstrable or more transferable. Engineering quality is hygiene.

How to read it: statements attributed to Derek are intent. Items marked
measured or reproduced are evidence. Anything marked "mine" is a hypothesis.
The board and the design notes are views, not authorities; neither is the code.

## 2. The conceptual design in brief

Nine working laws, in Derek's words, are in review as PR 681 for
`docs/src/design/story/philosophy.md`. In one line each:

1. **Four orderings of one space.** World (rules, no order), story graph (one
   grounded configuration), episodic process (the walk, partial order), journal
   (what was told, total order).
2. **Concepts and episodes.** Any node is a concept; a traversable one is an
   episode; the rest are mostly a person, a place or a thing.
3. **Two readings of one rule.** Imperative (if this, go there) and declarative
   (this is reachable when that holds). Materialization assembles what was
   declared so it can be walked.
4. **Pull and push.** A dependency reaches for a provider; an affordance waits
   and offers itself. Fan-out and fan-in.
5. **Shape and state.** Shape changes in provisioning; state in update or
   finalize when possible; the telling may change state on what it is about.
6. **Scope and navigation.** A container is a scope first and a navigation
   unit second, with one source and one sink.
7. **What belongs to story.** Story is shape and path. Prose, media and
   mechanics are appearance and interactivity. Two states are the same when
   nothing downstream can tell them apart.
8. **Two kinds of similarity.** The same start reproduces; a different start
   with the same choices lands on essentially the same state.
9. **Whom the rules bind.** Firm for work on the engine, rules of thumb for
   authors and plugins, and changed by the smallest carve-out.

The connection to the imaging lineage, as this review reads it (mine):

| Imaging | Here |
|---|---|
| Shape model | story layer: structure and path |
| Appearance model | prose, media, mechanics |
| Fitting a model to an instance | provisioning: grounding declared rules against state |
| Synthesis | walking the graph and telling it |
| Classification | recovering structure from a told story (the compression work) |
| Modes of variation | the "parametric story space" in `philosophy.md`, not yet instrumented |
| Same shape, different texture | equivalence classes; the same state told in another voice |

## 3. What was examined

| Area | Depth | Verdict against the design |
|---|---|---|
| Core (entity, registry, graph, dispatch) | basics | sound; some probing and legacy aliases |
| VM: provisioning | read | pull side unified and re-used; offer sources hand-listed; diagnosis interleaved |
| VM: hubs (menu, sandbox, games) | read | one pattern, three implementations |
| VM: step, ledger, replay | read, measured | right split; bookkeeping is most of a turn |
| VM: namespace and journal fold | read | the strongest re-use in the code |
| VM: jumps, calls, redirects | read, reproduced | three settings carry ten intents; one return policy |
| Containers | read, measured | scope works; navigation contract stated but unused |
| Compile | outline | clean; many source forms meet at one intermediate form |
| Materialize | outline, targeted | eager and lazy are one pipeline; ids minted in one place |
| Story classes | outline | a thin translation of the VM into narrative names |
| Presentation | all fields, census | sound mission; split into two client dialects |
| Media | design notes, outline | the clearest contract in the repo |
| Prose and lang | outline, linking read | naming by knowledge works; no request, identity or selection step |
| Client apps | inventory, counts | no client covers the contract; a conformance kit exists unused |
| Service, persistence | outline | small; the service surface is stated three times |
| Demo worlds (23) | scripts parsed | one subsystem each; the push side has almost no witness |
| Two downstream worlds | read (private) | built the push side, arbitration and equivalence merging for themselves |
| Design documents | high-level notes read, all searched | the why and the what are written; the laws were not |

Not read: mechanics internals, the Twine codec, core in depth, most of
`design/story`.

## 4. Strengths relative to the design

- **The levels are real in the code.** Compile produces a world, materialize
  grounds it, the frame walks it, the journal records the telling
  (F81, F82, F130).
- **The base expresses narrative without changing.** A role is a dependency on
  an actor; a scene is a traversable container. The story vocabulary is under a
  thousand lines, and what each class adds is a namespace contract (F124, F125).
- **One dispatch mechanism carries real load**: 15 provision handlers, 14
  namespace, 10 update, 7 journal (F30).
- **The pull side is one mechanism, and media re-uses it** as "same offer
  protocol, different search spaces" (F101).
- **Media shows the whole pattern working**: authored and generated kept
  apart, identity as a hash of what determines the output, provenance kept but
  excluded, format negotiated with the client (F100, F102, F105).
- **Appearance already follows state in one place.** Text is written with
  proper names; a reference is realized as a name or a description according
  to what the narrator knows (F121). A dialog line's attitude fans out to a
  style tag and a portrait (F122).
- **The rendering contract frames prose and media as one family** without
  forcing one representation (F115).
- **Demo worlds work as instrumented probes.** Each exercises one subsystem,
  and the downstream worlds found what the engine lacked (F70, F36 to F40).
- **Three documents hold the basis at three levels**: the why
  (`philosophy.md`), the what (`SIMPLIFICATION_SPEC.md`), and the method
  (`CANON_AND_REALIZATION.md`) (F130).
- **Reskinning exists**: one world ships an alternate art pack over the same
  graph, prose and choices.

## 5. Weaknesses relative to the design

Ordered by how much they obscure the gestalt.

1. **"The same story state" has no instrument in the engine.** The claim is
   reproducibility up to an equivalence. The analysis that defines the
   equivalence (which keys anything reads; which outcomes merge) exists only in
   a downstream world (F39). Nothing in the engine can compare two walks.
2. **The declarative reading is not a VM operator and has no in-repo
   witness.** Fan-in is implemented three times in story and mechanics and
   again downstream (F8, F9, F37). No demo world script uses `return`, `once`,
   `effects`, a fan-out or a contribution (F73, F74). Agents copy what they
   see, so new worlds come out imperative.
3. **Identity is not determined by declaration.** Two stories from one world
   share no ids (F23); hubs rebuild edges with new ids (F12, F68). Two partial
   solutions exist: a hashed key for scheduled events (F91) and media's
   identity projection (F102). So re-assembling is not a no-op, and things
   that point at rebuilt edges break.
4. **The long-range idea has no code.** The parametric story space
   (similarity, interpolation, style transfer) is described and not
   instrumented.
5. **A container's navigation role is stated and unused.** Every
   cross-container edge in the demo worlds enters at a member; half leave from
   somewhere other than the sink (F77). A story has no end: nothing records
   that one finished (F80). Two February notes specify the intended design
   (F134).
6. **Control flow has one return policy.** Every return re-plans and
   re-renders the caller; a call frame can outlive its callee (F57, F58, F65,
   F66, F68). #560 owns the design.
7. **Presentation has drifted into client dialects.** A pygame set and a web
   set of fields over a CLI floor; some fields have no producer or reader; four
   overlapping hint carriers (F93 to F96). The kit that would hold clients to
   one floor is not run against them (F112).
8. **Prose stops short of media's pattern.** No request object, no identity
   for a realization, no selection step; the rewriting kit is not on the path
   (F117, F118). Attitude is read only from the line, not from the speaker
   (F122).
9. **The laws were not written down.** Of ten themes this review reached, two
   appear in no design file and four in three or fewer (F132). One section,
   on determinism, contradicted both the code and the intent (F133).
10. **Accidental weight.** Replay bookkeeping is about 85% of a turn (F50).
    Diagnosis is interleaved with mechanism in three places (F5, F88, F127).
    The service surface is written three times (F48), the session bridge three
    times (F111), the hub pattern three times (F9).

## 6. Recommendations

By the seven verbs asked for. Each is sized S, M or L and marked by what it
serves: **G** gestalt, **T** transfer, **H** hygiene.

### Build out: what the design needs and does not have

| # | What | Serves | Size |
|---|---|---|---|
| 1 | **An equivalence instrument.** Promote read-set analysis into story: keys read and written, outcomes that merge, a comparison of two story states restricted to what anything reads. Then a small explorer over it: reachable classes, stuck states, what-if with one episode blocked (F39, F40; PlotEx) | G, T | M |
| 2 | **Fan-in as a VM operator**, with site arrivals as the first witness, so the declarative reading is as much a mechanism as the imperative one (P2, F37; #556) | G | L |
| 3 | **Identity by declaration**, stated as generalizing the two schemes already in the repo, starting at story creation (P1, F85, F91, F102) | G | M |
| 4 | **A story's end, and a container's exit.** Sinks as intended endings, distinct from running out of choices; the story as the outermost container (F80, F134, P10). Report-only validator first | G | M |
| 5 | **Resume beside re-enter** for calls (F68; #560) | H | S |
| 6 | **Attitude from the speaker when the line gives none** (F122) | G | S |

Item 1 is the one that turns "reproducible to a given equivalence" from a
sentence into something that runs. It is also the most portable idea here: any
rule-based process has states that differ only in ways nothing reads.

### Ornament: small things that show the design

| # | What | Shows |
|---|---|---|
| 1 | **One story, both readings.** A declarative calendar world beside the existing imperative schedule world (F75, P6) | law 3 |
| 2 | **Same shape, another telling.** One walk journaled in two voices or two languages, ending in the same state; the existing art-pack swap is the media half | laws 7, 8 |
| 3 | **The four levels as a picture.** A projection that reassembles world, graph, episodes and fragment leaves from a ledger (F130 note) | law 1 |
| 4 | **An equivalence-class graph of a small world**, in the manner of PlotEx | law 7 |
| 5 | **Witness worlds for the push side**: go home and call someone; a shared intro and outro; a companion who speaks before the choices; one world whose effects are all in script (P9) | laws 3, 4 |
| 6 | **Two readers, one graph**: a duel in the simultaneous-move gamebook tradition (#346) | laws 1, 8 |

Each is a few dozen lines of script and doubles as the example an agent copies
from.

### Expand: the research direction

| # | What | Serves |
|---|---|---|
| 1 | **Instrument the parametric story space.** Start small: a signature for a walk built from its sequence of equivalence classes, and a distance between two walks | G, T |
| 2 | **One witness from another domain.** The repo already has computation by topology, a queue simulation and document inspection. Add one process that is plainly not a story, written in the same vocabulary of requirements, roles and affordances | T |
| 3 | **Classification, the other direction.** The compression work: recover shape from a told story, with the language kit as its substrate | G, T |
| 4 | **A clean reimplementation as a test of the laws.** If the nine laws and `SIMPLIFICATION_SPEC.md` are enough to rebuild from, they are complete (#468) | G |

### Bolster: keep strong what the design rests on

| # | What | Size |
|---|---|---|
| 1 | The law layer in the documents: PR 681, then glossary entries and the two February notes on sinks brought forward (P14) | S |
| 2 | A few tests that pin laws, for engine development only: assembling twice changes nothing (A9); reading a committed journal changes nothing (A13); no ad hoc serialization in core, vm, story (A11) | S |
| 3 | The client floor: run the portable conformance fixtures in each client; content, choices and inputs are rendered or refused, hints may be ignored (A12, F112) | M |
| 4 | Media's contract as the model for prose and for presentation profiles (F105, P11, P13) | n/a |
| 5 | The practice of small witness worlds and downstream promotion ledgers (F44) | n/a |

### Trim: reduce without losing a concept

| # | What | Size |
|---|---|---|
| 1 | Per-hop step tracing: on a cadence or opt-in. It is about 3.2 s of a 4.7 s turn on a large graph, and it serves a promise the project no longer makes strictly (F50, P7) | S |
| 2 | Diagnosis out of the resolver, the compiler and the choice projection (F5, F88, F127; #450) | M |
| 3 | The service surface to one source: finish the conformance check; a generating loop only if hosts multiply (F48, A7) | S |
| 4 | One session bridge for the in-process Python clients (F111) | M |
| 5 | Slice logs out of the contracts in the presentation and media notes; a short roadmap in place of the #402 stack (F99, F107, F19) | S |
| 6 | This review: once its conclusions land, retire both files | S |

### Shave: small inconsistencies

- One meaning for the singular `predicate` key, lowered to a condition (F72).
- One shape for `ancestors` (F31).
- One `emphasis` vocabulary and one hint vocabulary (F96).
- The scheduled-event key built with the engine's hasher (F91).
- The wiring pass list written once (F83).
- `set_successor` delegating to `set_provider` (A4).
- Protocols in place of `getattr` probing in dialog, roles and media hooks
  (F122, F129, F107).
- Hubs re-using what is still wanted, on the model of scheduled events (F9).

### Discard

| What | Why |
|---|---|
| The claim of strict event-sourced replay, and the "choice list is the save" idea (P4) | Derek: patches are a hand-wave; reproducibility is up to an equivalence |
| Any runtime guard on what authors or plugins do | rules bind engine work only |
| Presentation fields with no producer or reader (F95); the one-line raster forge (F106) | dead |
| Core legacy aliases and story transitional seams (F16, F17) | residue; `git` remembers |
| Historical and migration notes from the canonical design index | move to an archive section; two of them held the better design, so read before archiving |
| Further performance work beyond tracing (trusted `structure`, identity equality) | not needed for exploration yet |
| Chasing the remaining dependency alerts in the web toolchain | not blocking; the Python side is done |
| Polishing mechanics | non-load-bearing by definition |

## 7. Order of work under this lens

1. Land the laws (PR 681), the glossary terms and the sinks notes.
2. The equivalence instrument.
3. Two ornaments that make laws 3 and 7 visible: one story in both readings;
   one walk in two tellings.
4. Fan-in in the VM.
5. Identity by declaration.
6. Story end and container exit; resume.
7. Client floor.
8. Trim tracing and diagnosis.
9. A first measurement in the parametric space.
10. A witness from another domain.

Hygiene items ride along where they are cheap. None of them should lead.

## 8. Status

### Landed since the review began

| PR | What |
|---|---|
| 676 | Python dependencies; Pillow 13; web job pinned to Ubuntu 24.04 |
| 677 | Journal diagnostic hashes only under debug logging (A2) |
| 678 | Cold-process and devref tests isolated (A5, A6) |
| 679 | Checkpoint every ten completed choices, with rollback witnesses (A1) |
| 680 | Remote preflight through the service API; operation-to-route inventory (part of A7) |

In review: PR 681, the working laws.

Timing on `main` on 2026-11-13, same large graph, five choices, one run: 4.73 s
per choice; 3.65 s with checkpoints off; 0.42 s with per-hop tracing also off.

### Open handoff items

Small and decided:

| # | Work |
|---|---|
| A3 | Large-graph timing guard, with a generous threshold |
| A4 | Optional: `set_successor` delegates to `set_provider`; one parametrized test over both edge classes |
| A7 | Extend the route conformance check to every operation |
| A8 | Report-only validator for edges that bypass a container's source or sink |
| A9 | Invariant: planning a node twice changes nothing; expected to fail on hubs for now |
| A11 | Guard: no ad hoc serialization in `core`, `vm`, `story` outside an allow-list |
| A12 | Clients run the portable conformance fixtures |
| A13 | Witness: reading a committed journal changes nothing |

Documentation still to write: authoring vocabulary (B7), the story
translation table (B9), the two traversal notes (B12), glossary entries.

Evidence for existing issues: the call and resume reproductions to #560; the
profile to #548 and #472; the arrival witness to #556; the demo gap to #438
and #461.

### Not stable; do not implement from this review

Fan-in (P2), identity by declaration (P1), routing edges through source and
sink (P10), the story as root container, multi-lane, the parity basis (P3),
a prose request (P13), presentation profiles (P11). Each is a direction with
an owner issue or none yet. Both clean-slate sketches are hypotheses.

## 9. What the review got wrong, and what that taught

- It rediscovered #560 from the code without reading it. Independent arrival
  is confirmation that the issue is not stale, but the issue should have been
  compared afterwards.
- It rediscovered the method in `CANON_AND_REALIZATION.md`, and broke its rule
  against keeping a second encyclopedia.
- It twice mis-weighted a rule: first treating "the journal does not change
  state" as absolute, then proposing a guard for it. The rule has a known,
  narrow exception and binds engine work only.
- It claimed all hub edges are rebuilt; scheduled events already keep theirs.
- It described a visit counter as counting rendered visits; it counts executed
  ones.
- Its first draft of the week's plan coupled too much and led with hygiene.

The pattern in these: what Derek states about how it is supposed to work
outranks what the code currently does, and the documents often already say it.

# Curation Design

**Status:** DESIGN, nothing landed; revised against review 2026-09-20  
**Scope:** a standing gardener over the repository's own record — developer
docs, the issue board, and authored world content — driven by deterministic
checks plus a local reader model, producing prioritized nominations that a
higher-tier agent triages  
**Background sources:** `docs/src/design/CANON_AND_REALIZATION.md` (registers,
mismatch classes, review rhythm — this note defers to it), `tangl.devref`
(index, topics, issues), `#282` (governing context on PRs; "no second issue/PR
indexer"), `#286` (authoring/runtime validation), `#396` (formal narrative
analysis contract), `scripts/comfy_batch.py` (job-runner-with-receipts)

## Why This Note Exists

Three jobs keep recurring and keep being paid for in expensive tokens:

1. **Canon and realization drifting apart.** 172 markdown files, ~2MB of prose,
   1021 Python modules. Documented claims and the code that realizes them move
   independently, and nothing notices until someone reads both. Which of the two
   is wrong is a separate question, and not the gardener's to answer.
2. **Post-merge board grooming.** After every merge: close, consolidate, narrow,
   update. Today this is done by re-reading the diff and the board from cold.
3. **Content proofing.** Authored worlds compile, materialize, and pass every
   structural check while telling an incoherent story.

All three share a retrieval shape — *take a unit, take what it connects to, ask
whether they still agree* — and the expensive half of that shape, computing what
connects to what, already exists in this repo. The cheap half, asking the
question, is what a small local model on local hardware is good for. Sharing a
shape is not the same as being one program; see **Three Programs, One
Substrate**.

This note is about not rebuilding the expensive part, and about being precise
concerning what the cheap part can and cannot do.

## The Load-Bearing Distinction: Facts vs Nominations

`AuthoringDiagnostic` plus world/service preflight already exist and are, per
`#286`, "built". They carry explicit placement, severity, and stable codes.
Everything in that channel is **true**: a reference resolves or it does not.

A local model saying "this transition feels unmotivated" is **not** a
diagnostic. It is probabilistic, advisory, sometimes wrong, and concerns
authorial intent rather than a fact of the bundle. Pushing it through
`AuthoringDiagnostic` would destroy the one property that makes that channel
worth reading.

Therefore:

- **`AuthoringDiagnostic` holds facts.** Structural, deterministic, build-path.
- **The curation ledger holds nominations.** Advisory, model-sourced or
  heuristic, never build-path, triaged by a human or a higher-tier agent.

They cross-reference by code and stay separate surfaces. This does not violate
`#286`'s "no second validation registry" non-goal, because the ledger validates
nothing — it is a triage queue whose entries are only ever *promoted*.

`#286` already set the precedent for where an expensive optional tier sits:

> Structural finishability should begin bounded and engine-native; optional
> solver work remains #396.

**The reader tier is to content what #396's solver is to structure**: optional,
out-of-core, never a dependency of the basic checks, never in the build path.

## The Authority Boundary

Settled before Phase 0, because it is the property that has to survive every
later convenience.

**Everything the reader reads is untrusted input.** Repository prose, PR bodies,
issue text, world content, and commit messages are *data*. Text inside them that
addresses the gardener — asking it to ignore a rule, approve a change, or treat
something as already authorized — carries no authority and is quoted to a human
rather than acted on.

**The reader has no write credentials and no tool authority.** It receives a
rendered unit and returns a typed nomination. It cannot edit files, call `gh`,
push, comment, or label. A separate adjudicator — human or higher-tier agent,
with its own credentials — is the only thing that opens a branch or a PR.

**There are no "mechanically safe" edits.** Annotation stubs were previously
listed as a plausible exception; they are not. An annotation changes which topic
a symbol joins and therefore what future retrieval returns, which is a semantic
change to the index the whole system reasons over. The gardener proposes
annotations like anything else.

The always-on worker stays an observer and proposer. It does not accumulate
repository authority by increments.

## Three Programs, One Substrate

The earlier framing — "one system, three entry points" — overclaimed. These are
three programs at very different maturities that **share receipts, budgeting,
scheduling, and adjudication**, and nothing else:

| program | unit | neighborhood | question |
|---|---|---|---|
| **doc register audit** | canon / realization claim | linked symbols | which register, and which mismatch class? |
| **merge-event grooming** | one merge on `main` | topics of changed paths | what did this invalidate; what should close? |
| **content continuity** | block / passage | declared edges, both directions | could the reader plausibly have arrived here? |

Only the first two are near-term. The content program is a larger research
effort that happens to reuse the substrate; it is written up here so the
substrate is not designed too narrowly, not because it ships alongside.

### The first deployable contract

One line, and nothing in Phase 0 or 1 may exceed it:

```
pinned main revision
  -> deterministic candidate generation
  -> read-only local classification
  -> durable nominations
  -> reviewed PR
```

Pinned, because a sweep must be attributable to a revision. Deterministic
generation, because the model never chooses what to look at. Read-only, per the
authority boundary. Durable nominations, so adjudication is not repeated.
Reviewed PR, because a human merges.

### Program 1 — doc register audit

**This is not a yes/no correspondence test, and framing it as one would do
damage.** `CANON_AND_REALIZATION.md` is the governing method note and this
program implements a piece of it rather than competing with it.

It separates three registers — **portable canon** (names no symbols, does not
rot), **realization** (where this codebase currently makes canon true; rots
constantly and *should be generated*), and **residue** (transitional, scheduled
for deletion, and explicitly *not citable*). It then names three mismatch
classes:

| signal | direction | resolution |
|---|---|---|
| canon names a symbol that does not exist | canon decayed | mechanical — fix canon |
| a public symbol or behaviour canon never mentions | realization pressing up | apply the promotion gate |
| both exist and disagree on meaning | genuine negotiation | judgment; expensive and rare |

**The first two are mechanizable and are this program's entire target.** The
third is not automated; the point of mechanizing the first two is to
*concentrate* human review on the third.

Two consequences bind the design:

1. **Unchanged prose next to moved code is not evidence of staleness.** Canon
   moving toward realization is normative; realization pressing up into canon is
   evidential; *both directions are legitimate*. A curator that treats every
   mismatch as stale prose would quietly make canon follow implementation, which
   is the specific failure this program exists to prevent. The nomination
   therefore carries a **register and mismatch class**, never a repair.
2. **Residue must stay unreachable from a canon read**, so the classifier has to
   recognize residue as a register rather than reporting it as contradiction.

`CANON_AND_REALIZATION.md` already names the intended vehicle — the proposed
`devref audit`, in `#282` lineage — and records that no such command exists yet.
This program is that command's nomination half, not a new parallel proposal.

The index makes it feasible: `artifacts(content, source_hash, kind, facet,
relation, line, anchor)`, `symbols(qualified_name, source_hash, signature,
summary)`, and `artifact_topics(...)` over 35 curated topics. The curator never
reads the codebase; it hands the model one paragraph plus one signature — 2–4k
tokens inside a 16k window. What the index does *not* hold is history: "changed
N times since" comes from **git**, not from devref, which stores only a current
hash.

### Program 2 — merge-event grooming

**Correction from review: there is no PR indexer, and this note does not propose
one.** `#282` lists "no second issue/PR indexer" and "no PR indexing merely for
symmetry" as explicit non-goals, and prefers a static changed-path -> governing
topic mapping. An earlier draft of this note proposed `ArtifactKind +=
"pull_request"`, a `sync_prs()` snapshot, and writing mention edges into
`artifact_links`. All three are withdrawn:

- `artifact_links` is rebuilt wholesale by `compute_artifact_link_rows()` on
  every build and holds document/symbol reference links derived from artifact
  metadata. Anything written there is erased on the next build, and issue
  extraction deliberately avoids deriving cross-artifact links.
- `sync_issues()` indexes **open** issues only by default, with a documented
  reason — indexing closed work "would present finished business as
  outstanding". So a post-merge index cannot see the issue a merge just closed.
- A current-state index cannot recover deleted symbols or per-symbol change
  counts at all.

The merge event is therefore an **ephemeral input, not an indexed artifact**:
base/head from the merge plus GitHub metadata fetched at sweep time, joined
against the index at a pinned revision, and discarded. Nothing about PRs is
retained in the index; only the resulting nominations are durable.

```
merge on main -> changed paths -> topics (static map, #282) -> at pinned rev:
  +- issues on those topics ......... close / consolidate / narrow candidates
  +- docs on those topics unchanged while the code moved (git) ... register audit
  +- tests on those topics that did not move .................... coverage gap
```

This stays inside `#282`'s stated shape. If the static mapping proves
inadequate, `#282` already says what to do next, and that conversation happens
there rather than being pre-empted here.

Run **post-merge on `main`**, not on the PR. Pre-merge is CodeRabbit's turf and
the diff is not yet final.

### Program 3 — world and narrative content

Unlike docs, the neighborhood here is *declared*, not inferred: `successor`,
`links.out.target`, `start_at`, `plates`, `kind`, `media.name`. The loader
already resolves every one. The chunking problem — the hard part of doc
curation — is solved for free. The unit is the block; the bundle is the block
plus the tails of its predecessors and the heads of its successors. 600–1500
tokens. Small worlds fit whole.

Two distinct corpora share this program: in-repo demo worlds (`worlds/`), and
imported material such as the CarWars gamebook anthology, where the content
arrived via OCR and carries a different, harder error profile.

## What Already Exists — Do Not Rebuild

| need | existing mechanism |
|---|---|
| doc/symbol/topic joins | `tangl.devref` index + FTS5 |
| issue -> topic join | `devref:<topic>` label convention; 44 of 62 open issues carry one (open only, by design) |
| changed-path -> governing topic | `#282`'s static mapping — **not** a PR indexer |
| per-symbol change history | git, not devref (the index holds one current hash) |
| register / mismatch vocabulary | `docs/src/design/CANON_AND_REALIZATION.md` |
| review cadence | that note's Change / Topic / Layer / Coarse rhythm |
| structural world validators | `#286` (entry/reference, reachability, media-link, materializability, finishability) |
| structural findings channel | `AuthoringDiagnostic` + preflight |
| mechanical prose checks | `lang/apis/language_tool.py`, `lang/helpers/spell_check.py`, `[lang.apis.languagetool]` in defaults |
| local model endpoint | `[content.apis.ollama]` in `defaults.toml`, resolved the way `comfy_batch.py` resolves the render node |
| job-runner + receipts pattern | `scripts/comfy_batch.py` |
| query surface for a findings *projection* | the `devref` MCP server |

**The deterministic world tier is `#286`, not new work.** It lands there and the
curator consumes it. Mechanical prose checks (spelling, locale variants,
terminology) go to LanguageTool, never to the reader model.

That leaves the reader model a deliberately narrow remit: register and
mismatch-class classification, entity co-reference, transition continuity, and
mention-edge classification. Four classification tasks. Nothing else, and none
of them a repair.

## The Deterministic Tier

Free, high-confidence, runs nightly over everything.

**Docs**
- doc names a symbol absent from `symbols` -> dangling reference
- doc unchanged while linked symbols moved N times (**history from git**, not
  from the index) -> register-audit candidate, *not* a staleness verdict
- code fence does not parse, or its imports do not resolve
- `source_path` no longer exists -> dead artifact
- symbol or module with no `artifact_topics` row -> coverage gap
- topic with `defines` but no `tests` / `documents` facet -> facet hole
- unresolvable file path, issue number, or PR number -> broken pointer

**PRs**
- topic touched by the merge whose doc sections did not move -> **register-audit candidate**
- `#N` mentioned in a merged PR body with no closing reference -> unlinked grooming candidate
- issue whose topics were all superseded by merged work -> close candidate
- milestone whose children are all closed -> narrow candidate

**Content**
- reachability, sinks, dangling targets, media resolution, template-variable
  supply (all `#286`)
- plate/region staleness: region coordinates edited at rev A, plate image
  rebuilt at rev B > A. `worlds/red_paperclip/script.yaml` documents this hazard
  in a comment — "Re-render the plate and these move" — which is the
  `source_hash` staleness check verbatim
- declared `location_name` never appearing in prose; capitalized noun phrases in
  prose absent from the roster
- locale and spelling variants **within a namespace** (see below)

### Namespace-aware naming checks

`red_paperclip` has British prose (`"Sandpoint Harbour"`, "the harbourmaster's
office") against American identifiers (`harbor:`, `district:harbor`,
`harbor_bg.png`, `rp_harbor`). That split is deliberate and disciplined —
ASCII-safe keys, British voice — and it holds even where the two sit close
together: `README.md` writes "the harbour and airfield boxes" in prose and
`harbor, market, garage, ...` inside a fenced list of hub identifiers.

A cross-namespace checker flags that whole cluster. **Every one of those flags
is a false positive**, which is the point: the corpus is consistent, and a check
that cannot see namespaces reports a clean world as broken.

**Drift is only drift within a namespace.** Identifier space and prose space are
checked separately or not at all.

## The Reader Tier

### Why a reader is required at all

A transition from a bar in Texas to the middle of a car battle in New York,
where the target should have been a different passage, is a transcription error
that **defeats every deterministic check by construction**:

- it compiles; the target is a real passage
- it materializes; the reference resolves
- nothing missing, nothing extra; reachability is fine
- LanguageTool has nothing to say; both passages are impeccably written

It is a perfectly valid graph telling an incoherent story. There is no
structural fact to check it against. The only instrument that finds it is
something that reads both ends and notices.

Two pre-filters were proposed and **both were measured and rejected** — see
*Measured Evidence*. There is no trick that avoids reading.

### Scoping the question

Ask about **continuity**, never quality. "Could the reader plausibly have
arrived here?" — same place, same people, same situation. Not "is this
well-motivated?", which is an authorial judgment a small model gets confidently
wrong, and under which deliberate non-sequitur reads as a defect.

Guards:

1. **Quote or drop.** The verdict must cite the span justifying it. No span, no
   finding.
2. **Never judge an edge whose requirement is hidden.** An open
   requirement-bearing edge is the primitive; a gated transition shown without
   its gate reads as a non-sequitur. The unit carries the requirement or is
   marked un-judgeable.
3. **Abstention is cheap.** `unclear` accumulates silently; only confident
   negatives with spans reach the digest.

### Two evidence streams, neither authoritative

Imported content arrives with two independent streams, each prone to error:

- **Position** — where unit boundaries fall. Linear, inferred from unit size and
  from things that look like unit headers, and **self-propagating**: an early
  off-by-one shifts everything after it.
- **Links** — what each unit points at. Non-local, and with no correction
  available beyond *in range* and *narratively continuous*.

The cross-product is the real state space:

| link | unit at that id | diagnosis |
|---|---|---|
| right | wrong | segmentation slipped; the edge is innocent |
| wrong | coincidentally right | **worst case** — locally invisible |
| wrong | wrong | compounded; usually appears as a run |
| right | right | the goal, and mid-reconciliation the minority case |

Range-validity is the only automatic check either stream gets, and in a dense id
space it is vacuous. **Narrative continuity is the sole corrective available to
the link stream** — which is why the reader tier is load-bearing here rather
than a refinement on top of working checks.

### The bidirectional neighborhood pass

For each passage, one bundle: the passage, the tails of everything that links
**to** it, and the heads of everything it links **from**. Two questions per
bundle — *does everything that arrives here belong here*, and *does everything I
send the reader to follow from here*. Reading each passage once amortizes it
across its neighbors.

This pass distinguishes two failure modes for free, by the *shape* of the
failure:

- **one** predecessor fails, others fit -> a bad edge (misread target)
- **all** predecessors fail -> a bad unit (mis-split or misassigned body)

And clustering flagged edges **by position** separates two more:

- a **run** of consecutive passages failing -> a boundary slipped in that
  neighborhood; one fix, not twelve
- an **isolated** failure among well-fitting neighbors -> a misread link

Segmentation errors are local and correlated; link errors are isolated and
uncorrelated. That asymmetry is the signal, and it is unavailable to either
stream alone.

### Repair is retrieval, not edit distance

In a dense id space every misread lands on a real passage, so constraint-based
repair is dead (measured: 95.5% of edges have four or more plausible
OCR-neighbours that are all real passages). Instead, a flagged edge is answered
by **retrieval**: rank all candidate units in the book by continuity with the
flagged source and propose the top few. Cheaper than generation, and it catches
errors that are not single-character at all — including renumbering slips.

### The graph as checksum

Grooming the nodes and links makes the rendered graph less chaotic; that
"settling" is itself an integrity signal over the whole story. Community
structure, hubs, linear progression between communities, dead starts and dead
ends are a coarse checksum that a per-edge pass cannot provide, and vice versa.
The two are complementary and both belong in the digest.

Because settling is a trend rather than a threshold, the metrics are **recorded
per run** — community count and modularity, false roots, false termini, hub
distribution, longest unanchored stretch — so a corpus can be compared against
its own history and against its siblings. That one book groomed clean while
others did not should be a number the digest states, not something anyone has to
remember.

### Global reconciliation is a solver problem

Link constraints over-determine unit boundaries — roughly 680 constraints over
~400 boundary positions in a single CarWars book, 4,081 over the anthology. The
leverage is less in the ratio than in the coupling: a single bad boundary breaks
*every* inbound link to the units it shifts, so one error shows up many times.

The right global framing is therefore not "check each edge" but "find the
segmentation maximizing total continuity across all links at once" — an
optimization where **the reader supplies the cost function** and a solver does
the reconciliation. This is a cleaner motivation for `#396` than that issue
currently carries.

**The optimization has a degenerate attractor, and anchors are not optional.**
A globally shifted segmentation can be locally consistent nearly everywhere:
start one unit off, "correct" each subsequent boundary to match the expectation,
and arrive at a solution that satisfies almost every local continuity check
while being wrong almost everywhere. In the limit only the first and last units
are right. A solver maximizing total continuity will happily land there, and
report confidence.

The corrective is an **anchor set drawn from an independent evidence stream** —
in the CarWars pass, units whose true page number could be looked up and
thereafter held fixed, cutting the book into stretches that reconcile without
inheriting an upstream shift. Anchors cannot come from the links; if they did
they would share the failure mode. Any `#396` solver backend therefore takes the
anchor set as a **required input**, and the digest reports **anchor density**
per corpus, because a long unanchored stretch is precisely where a confident,
self-consistent, wrong answer hides.

## The Ledger

Idempotence is the difference between a gardener and a spam machine.

### Two dimensions, not one state machine

A reader verdict and a human decision are different facts about a finding and
are stored separately:

| dimension | values | owner |
|---|---|---|
| **verdict** | `yes` / `no` / `unclear` | the reader, per evaluation |
| **adjudication** | `open` / `accepted` / `rejected` / `wontfix` | a person, per finding |

Collapsing them loses two things. `unclear` must be **stored**, or the daemon
re-spends calls on the same unit every sweep and abstention rate — the main
calibration signal — becomes unmeasurable. And an adjudication has to outlive
the verdict that prompted it.

### Identity includes the evaluator

```
(check_contract_version, unit_key, anchor_hash, counterpart_hash)
```

with `model`, `prompt_digest`, `harness_version`, and `input_revision` recorded
alongside. A rejection suppresses a finding only while the *question* is
unchanged; swapping the model or editing the prompt yields a materially
different check, and old rejections must not silently suppress it.

### Storage: durable, and outside the index

**The ledger cannot live in `tmp/devref/devref.sqlite3`.** `tmp*` is gitignored
and the index is explicitly disposable and rebuilt wholesale — adjudications,
coverage history, and calibration data are exactly the opposite. They go in a
separate persistent store (or a replayable append-only log), and the index may
carry a **disposable projection** of currently-open findings so the existing
MCP surface can serve them.

This also answers a constraint `CANON_AND_REALIZATION.md` sets on any review
process — *"dossiers are disposable ... do not accumulate a second encyclopedia
that itself needs maintenance."* The reconciliation is that **findings are
regenerable and adjudications are not**. What persists is small: what a person
decided, what has been swept, and with which evaluator. Findings themselves can
be thrown away and recomputed from a pinned revision.

### Coverage is part of the record

The human-scale failure in the CarWars pass was not the checking — it was losing
track of what had been checked. Whether a given book's graph was ever considered
*done* is not recoverable after the fact.

The ledger therefore tracks sweep state per corpus alongside findings:

- which units have been read, at which content hash, by which check, and when
- share of the corpus swept at the current revision
- findings outstanding by state, and how long they have been open
- the graph-metric trend above, and anchor density

This makes "is this done?" an answerable query rather than a memory, and makes a
partial sweep visibly partial instead of silently so.

**Non-determinism at the edge, determinism in the record.** The CarWars
`ripper/config.py` is the proof of this pattern: hundreds of hardcoded
corrections making a noisy pipeline *replayable* against fresh scans. A
model-driven pipeline needs the same artifact, sourced differently. A judgment
is allowed to be probabilistic precisely because it lands somewhere replayable
and reviewable.

## Receipts

Every finding carries a deterministic locator — `file:line`,
`qualified_name`, git rev range — **resolved by Python before the finding is
written**. Findings whose receipt does not resolve are dropped by the harness
and never reach a digest.

The model *nominates*; Python *verifies the nomination is coherent*; a
higher-tier agent *adjudicates*. Model prose never becomes the finding: it is
quoted beside the receipt and labelled as the model's opinion. This exists so
that acting on the digest costs one `grep`, not a re-read.

## Budget and Ranking

Cadence is not invented here. `CANON_AND_REALIZATION.md` already defines the
rhythm, and the gardener attaches to it rather than running an unmotivated
nightly sweep:

| scale | trigger | what the gardener contributes |
|---|---|---|
| **change** | every substantial merge | the merge-event nominations (Program 2) |
| **topic** | routine | one topic's register audit, as a disposable dossier |
| **layer** | periodic | census-shaped deterministic checks only |
| **coarse** | triggered by a canon-level change | nothing automatic; a person decides |

Deterministic checks are free and run at whatever scale fires. The reader pass
works a ranked queue against a fixed call budget, so a topic sweep completes in
bounded time rather than the whole corpus contending at once. A coarse pass is
*triggered*, never scheduled — "running one against a canon that has not moved
is relaxing against a reference that is not changing.

The one ranking heuristic that survived measurement: **exclude hubs.** In-degree
is median 1, p90 3, max 43–63. High-in-degree units are generic funnels — "you
are hit, turn to X" — where continuity judgment is meaningless. Excluding the
top few percent removes a large slice of edges at zero risk.

## Measured Evidence (2026-09-17)

Recorded because two designs were killed by measurement and should not be
revived without new evidence.

**Board signal exists and is unread.** Of the last 30 merged PRs, **26 mention an
issue number in the body; 6 carry a real `closingIssuesReferences`.** The
PR<->issue graph is written by hand in prose and GitHub captures a fifth of it.
44 of 62 open issues carry a `devref:` label.

**CodeRabbit supplies nothing on this axis.** PRs #479 and #481 contain no
"Linked Issues", "Possibly related PRs", or "Assessment against linked issues"
section — only Changes, pre-merge checks, finishing touches. Nothing in the repo
consumes its output. `review_details: false` in `.coderabbit.yaml` is a
candidate cause, unconfirmed. Not worth building on regardless: it is an
ephemeral per-PR comment, sees only the diff, and does not know the topic
vocabulary.

**REJECTED — constraint-based repair.** Across 6 CarWars books: ids 1–400 all
present, **zero gaps in every book**. Over 4,081 numeric edges, the
OCR-confusion neighbourhood of the target contains real passages at:

| plausible real OCR-neighbours | edges |
|---|---|
| 1 | 12 (0.3%) |
| 2 | 100 (2.5%) |
| 3 | 73 (1.8%) |
| 4+ | 3,896 (95.5%) |

The candidate set is effectively the whole id space. Note that this density is
partly **enforced** — sequential numbering was used as a splitting constraint
during transcription — which also means a forced-dense numbering can *absorb* an
error rather than reveal it, producing misassigned bodies as well as misread
targets.

**REJECTED — proper-noun continuity fingerprint as a pre-filter.** Over 3,907
edges, **53.7% share zero proper nouns with their target.** That is the
baseline, not an anomaly. As a filter it flags half the corpus.

**Worst case is narrower than it feels.** Median in-degree is 1, so for a large
share of units the only way in is a single link; misdirecting it orphans the
true target, which surfaces as a false root in existing graph analysis. The
genuinely invisible residual is links misdirected to a unit that *also* has
other predecessors, where the wrong target happens to read acceptably.

**Bug found in existing tooling.** `scratch/ripper/graph_passages.py` builds the
graph from `label_num` but reports false roots via `passages[r-1]` — list
position. Config explicitly assigns `-1` to unparseable labels, so any such
passage shifts the alignment and the report prints **the wrong passage body**.
Real findings would have looked like noise. Fixing the lookup and re-running the
false-root report across all six books is a cheap, model-free check with real
yield.

## Validation Discipline

No model tier is trusted before it is measured on injected error.

Take a corpus, rewire N known-good transitions to random targets, run the
checker, and compute catch rate and false-positive rate against ground truth
known by construction. If it catches ~70% at a tolerable false-positive rate,
build the pipeline. If it catches 20%, the design is wrong and the cost was one
evening.

Sabotage the mechanism to prove the test screams. This applies equally to the
deterministic checks: each one ships with a fixture that breaks it.

## Shape

Mirroring the render-node trio, which is the closest existing analogue:

- `engine/src/tangl/devref/curate.py` — checks, findings table, ledger state
- `scripts/devref_curate.py` — local-model batch driver, receipts, digest render
- `scripts/devref_curate.md` — the helper contract
- `.claude/skills/devref-curate/SKILL.md` — thin: run a sweep, read the digest,
  adjudicate, and the traps

Deterministic checks live in the engine, where they are testable against
fixtures alongside `engine/tests/devref/`. The model driver lives in `scripts/`
next to `comfy_batch.py`, because it is a job runner against a local worker, not
engine behavior. The endpoint resolves from `[content.apis.ollama]` the way the
render node resolves from settings — never a hardcoded host.

## Phases

**Phase 0 — ledger and digest, no new checks, no model.**
Durable store, dedup keying with evaluator provenance, the two dimensions above,
receipt resolution, digest renderer.

**It composes existing facts; it does not copy them.** An earlier draft said the
digest would be "fed by" `AuthoringDiagnostic` records, which would have built
precisely the second diagnostic registry this note rejects — with a second copy
of each record and a second place to adjudicate it. Instead the digest
**references and joins** the factual surface at render time: diagnostics stay
owned by preflight, and the ledger holds only nominations and adjudications.
Proves the digest is worth reading before anything is spent generating
findings.

**Phase 1 — two deterministic indicators as proof of concept.**
Chosen to serve the post-merge grooming ritual that is performed by hand today:

1. **touched-topic / untouched-doc** — a register-audit candidate, reported as
   "these claims and this code moved apart", never as "this doc is stale"
2. **mention-without-closing-ref** — `#N` parsed from a merged PR body, held as
   an ephemeral merge-event input and emitted as a nomination

Both are deterministic: a pinned revision, a git diff, a `gh` fetch at sweep
time, and index queries. Neither writes to the index, neither adds an artifact
kind, and both produce output on the very next merge.

*Independent and parallel:* fix the `passages[r-1]` lookup in the CarWars ripper
and re-read the false-root report. Model-free, and blocked on nothing above.

**Phase 2 — first reader pass: content.**
Worlds before docs: the units are smallest, the neighborhood is declared rather
than inferred, and claims are testable against an actual playthrough.
Bidirectional bundle, continuity-only verdict, hub exclusion, injected-error
measurement first.

**Phase 3 — PR mention-edge classification.**
`closes | advances | supersedes | depends-on | context-only` over an existing
edge. Five-way, checkable at a glance.

**Phase 4 — doc claim extraction and pairwise verdicts.**
Hardest and most inferential; last.

**Phase 5 — cron on the local box**, findings landing in the DB.

## Non-Goals

- No replacement for, or extension of, `AuthoringDiagnostic`. Facts and
  nominations stay separate, and the digest joins rather than copies.
- No second validation registry, and no second diagnostic registry.
- **No PR or issue indexer.** `#282`'s non-goal stands; merge events are
  ephemeral inputs.
- **No write credentials or tool authority for the reader.** Ever, and including
  annotation stubs.
- **No ledger inside the disposable index.** Adjudications outlive rebuilds.
- **No staleness verdicts on docs.** Register and mismatch class only; direction
  is a human decision.
- No repair policy. The gardener proposes; it does not edit prose.
- No model in the build path.
- No reader-model spend on checks LanguageTool or SQL already performs.
- No generic drift-detection framework. Three named programs, four named model
  tasks.

## Open Questions

*Resolved by this revision:* whether the curator ever writes (no — see **The
Authority Boundary**), and whether the ledger can share the index (no — see
**Storage**).

1. **What form does the durable store take?** A SQLite file outside `tmp*`, or
   an append-only log replayed into one. The log is friendlier to review and to
   git; the database is friendlier to query. Either way the index carries only a
   disposable projection.
2. **Should it nag upstream?** Flagging a merged PR that mentions `#N` without a
   closing keyword is the cheapest possible intervention and would make GitHub's
   own linkage worth reading. It is also the first thing that could become
   annoying.
3. **How does a topic dossier stay disposable?** `CANON_AND_REALIZATION.md`
   requires it. The split proposed here — regenerable findings, durable
   adjudications — needs proving against one real topic sweep before it is
   trusted.
4. **What plays the role of anchors for authored worlds?** Imported corpora have
   page numbers as an independent stream. Authored worlds have no equivalent and
   may not need one — their boundaries are declared rather than inferred — but
   that asymmetry is untested, and the solver framing assumes anchors exist.
5. **Do the CarWars LanguageTool rules generalize?** `ripper/config.py` encodes
   real OCR failure modes (dominantly `rn` -> `m`) for that corpus. Whether that
   rule set is worth porting, or is scan-specific, is unmeasured.

# Curation Design

**Status:** DESIGN, nothing landed (2026-09-19)  
**Scope:** a standing gardener over the repository's own record — developer
docs, the issue board, and authored world content — driven by deterministic
checks plus a local reader model, producing prioritized nominations that a
higher-tier agent triages  
**Background sources:** `tangl.devref` (index, topics, issues), `#286`
(authoring/runtime validation), `#396` (formal narrative analysis contract),
`scripts/comfy_batch.py` (the job-runner-with-receipts pattern)

## Why This Note Exists

Three jobs keep recurring and keep being paid for in expensive tokens:

1. **Doc drift.** 172 markdown files, ~2MB of prose, 1021 Python modules. Docs
   claim things the code stopped doing, and nothing notices until someone reads
   both.
2. **Post-PR board grooming.** After every merge: close, consolidate, narrow,
   update. Today this is done by re-reading the diff and the board from cold.
3. **Content proofing.** Authored worlds compile, materialize, and pass every
   structural check while telling an incoherent story.

All three are the same shape: *take a unit, take what it connects to, ask
whether they still agree.* The expensive part of that shape — computing what
connects to what — already exists in this repo. The cheap part — asking the
question — is exactly what a small local model on local hardware is good for.

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

## One Harness, Three Seeds

| seed | unit | neighborhood | verdict question |
|---|---|---|---|
| **docs** | `doc_section` artifact | linked symbols via `artifact_topics` | does the prose still describe this code? |
| **PRs** | merged PR | topic siblings of touched symbols | what did this invalidate; what should close? |
| **content** | block / passage | declared edges, both directions | could the reader plausibly have arrived here? |

Same ledger, same receipt rule, same `yes / no / unclear`, same budgeted queue.
This is one system with three entry points, not three systems.

### Seed 1 — docs

`devref` already stores `artifacts(content, source_hash, kind, facet, relation,
line, anchor)`, `symbols(qualified_name, source_hash, signature, summary)`, and
`artifact_topics(...)` with `evidence_source` and `weight`, over 35 curated
topics with FTS5 and incremental build. The curator never reads the codebase;
it queries pre-computed pairs and hands the model one paragraph plus one
symbol's signature and docstring — 2–4k tokens, comfortably inside a 16k window.

### Seed 2 — PRs and issues

`issues.py` already pulls a `gh` snapshot to `tmp/devref/issues.json` and joins
on the `devref:<topic>` label convention. Its own docstring names the structure:
"the issues <-> design-docs <-> code triangle." A PR is the fourth corner, and
reaches the index the same way — an offline, deterministic, disposable snapshot.

```
PR -> changed files -> symbols (source_path) -> topics (artifact_topics)
                                                  |
  +- issues on those topics ......... close / consolidate / narrow candidates
  +- doc_sections on those topics whose source_hash did NOT move ... stale docs
  +- test_modules on those topics that did NOT move ................ coverage gap
```

The middle row is the pre-emptive refresh, and it needs no model at all.

Required additions, all small and mostly reusing existing shapes:

- `ArtifactKind += "pull_request"`
- `sync_prs()` mirroring `sync_issues()` -> `tmp/devref/prs.json`
- mention parsing (`#\d+` from PR bodies) into the **existing**
  `artifact_links(source_artifact_id, target_artifact_id, link_kind)` table
- topic projection from changed files, not from labels

Run **post-merge on `main`**, not on the PR. Pre-merge is CodeRabbit's turf and
the diff is not yet final.

### Seed 3 — world and narrative content

Unlike docs, the neighborhood here is *declared*, not inferred: `successor`,
`links.out.target`, `start_at`, `plates`, `kind`, `media.name`. The loader
already resolves every one. The chunking problem — the hard part of doc
curation — is solved for free. The unit is the block; the bundle is the block
plus the tails of its predecessors and the heads of its successors. 600–1500
tokens. Small worlds fit whole.

Two distinct corpora share this seed: in-repo demo worlds (`worlds/`), and
imported material such as the CarWars gamebook anthology, where the content
arrived via OCR and carries a different, harder error profile.

## What Already Exists — Do Not Rebuild

| need | existing mechanism |
|---|---|
| doc/symbol/topic joins | `tangl.devref` index + FTS5 |
| issue -> topic join | `devref:<topic>` label convention; 44 of 62 open issues carry one |
| PR -> issue edges | `artifact_links` table |
| structural world validators | `#286` (entry/reference, reachability, media-link, materializability, finishability) |
| structural findings channel | `AuthoringDiagnostic` + preflight |
| mechanical prose checks | `lang/apis/language_tool.py`, `lang/helpers/spell_check.py`, `[lang.apis.languagetool]` in defaults |
| local model endpoint | `[content.apis.ollama]` in `defaults.toml`, resolved the way `comfy_batch.py` resolves the render node |
| job-runner + receipts pattern | `scripts/comfy_batch.py` |
| query surface for the ledger | the `devref` MCP server |

**The deterministic world tier is `#286`, not new work.** It lands there and the
curator consumes it. Mechanical prose checks (spelling, locale variants,
terminology) go to LanguageTool, never to the reader model.

That leaves the reader model a deliberately narrow remit across all three seeds:
entity co-reference, transition continuity, mention-edge classification, and
doc-claim verdicts. Four classification tasks. Nothing else.

## The Deterministic Tier

Free, high-confidence, runs nightly over everything.

**Docs**
- doc names a symbol absent from `symbols` -> dangling reference
- doc `source_hash` static while linked symbols' hashes moved N times -> stale pressure
- code fence does not parse, or its imports do not resolve
- `source_path` no longer exists -> dead artifact
- symbol or module with no `artifact_topics` row -> coverage gap
- topic with `defines` but no `tests` / `documents` facet -> facet hole
- unresolvable file path, issue number, or PR number -> broken pointer

**PRs**
- topic touched by the diff whose doc sections did not move -> **pre-emptive refresh**
- `#N` mentioned in a PR body with no closing reference -> unlinked grooming candidate
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

- key: `(check_id, unit_key, anchor_hash, counterpart_hash)`
- state: `open | accepted | rejected | wontfix`
- a rejection **persists** until one of the hashes moves
- the rejected pile is a free few-shot corpus, and for content a de-facto style
  profile for that world

Storage: a `curation_findings` table in the same SQLite as the index, so the
existing `devref` MCP server can serve the queue. The rendered digest is a
projection, not the truth.

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

Deterministic checks run over everything, nightly, free. The reader pass works a
ranked queue against a fixed call budget (~300/night), so the corpus is swept
over roughly a week rather than choking on night one.

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
`curation_findings` table, dedup keying, state machine, receipt resolution,
digest renderer. Fed initially by findings that already exist
(`AuthoringDiagnostic`, preflight, graph analysis). Proves the digest is worth
reading before anything is spent generating findings.

**Phase 1 — two deterministic indicators as proof of concept.**
Chosen to serve the post-merge grooming ritual that is performed by hand today:

1. **touched-topic / untouched-doc** — the pre-emptive refresh
2. **mention-without-closing-ref** — PR body `#N` parsing into `artifact_links`

Both are pure SQL plus `gh` snapshot. Both produce output on the very next merge.

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
  nominations stay separate.
- No second validation registry. The ledger validates nothing.
- No repair policy. The gardener proposes; it does not edit prose.
- No model in the build path, ever.
- No reader-model spend on checks LanguageTool or SQL already performs.
- No generic drift-detection framework. Three named seeds, four named model
  tasks.

## Open Questions

1. **Does the curator ever write?** Current position: no — it proposes
   annotations and never edits prose. Annotation stubs are the one plausible
   exception, being mechanical.
2. **Should it nag upstream?** Flagging a PR that mentions `#N` without a
   closing keyword is the cheapest possible intervention and would make GitHub's
   own linkage worth reading. It is also the first thing that could become
   annoying.
3. **Digest as file, DB, or both?** DB is truth and MCP-queryable; a rendered
   in-repo digest is diffable, greppable, and survives a rebuild.
4. **What plays the role of anchors for authored worlds?** Imported corpora have
   page numbers as an independent stream. Authored worlds have no equivalent and
   may not need one — their boundaries are declared rather than inferred — but
   that asymmetry is untested, and the solver framing assumes anchors exist.
5. **Do the CarWars LanguageTool rules generalize?** `ripper/config.py` encodes
   real OCR failure modes (dominantly `rn` -> `m`) for that corpus. Whether that
   rule set is worth porting, or is scan-specific, is unmeasured.

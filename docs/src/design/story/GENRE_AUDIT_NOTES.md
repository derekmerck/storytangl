# Genre Audit Notes — v1.5

**Companion to:** `STORYTANGL_WIDGET_VOCAB.md` v1.5
**Bundles audited:** carwars, credentials, training, elefant_hunt
**Status:** v0.1
**Purpose:** consolidate findings from extending the vocabulary to four
distinct gameplay paradigms. Identify what worked, what was awkward,
what was genuinely missing, and what cross-paradigm patterns emerged.

---

## TL;DR

**The vocabulary held.** All four paradigms — vehicle outfitting,
inspection / verification, scheduled training, graph-traversal board
game — map cleanly to v1.5 with no new top-level fragment types, no
new `accepts.kind` values, no new `value_type`s. Two small additions
to the vocabulary itself (`§0.8` journal-as-narrative sidebar; §1.5 per-cursor
projection paragraph) were enough to formalize patterns the paradigms
exercised in common.

The strongest finding is positive: the §0.3 backend-authority stance
and §0.6 narrative-authoring stance — both lifted to spec text in
v1.5 — handle a remarkable range of design surfaces. Backend-private
engine pools, lazily-authored hidden state, generative outcomes,
authored-on-demand junctions — all fall out of the framing rather
than requiring new contract surfaces.

The §7.4 `predicate_ref` registration protocol remains the
highest-leverage open item. Every paradigm exercises it; none can
be fully implemented without it.

---

## §A — Where the vocabulary works (per paradigm)

### carwars

Vehicle outfitting maps to `zone_role="slot"` zones with
`constraints.capacity` and `accepts.kind="place"` choices. Per-piece
weight/power summed by the backend, projected as `KvRow.value`/`max`
bars. The original `tokens → pieces` and `cost_preview → cost_previews`
renames in v1.2/v1.3 trace directly to carwars-driven friction.

`ui_hints.stat_check` and `ui_hints.drag` ship as carwars-specific
Tier P3 hints; both leave click-pick paths reachable per §5.3 Input
Parity. Drag is presentation enhancement, never required.

### credentials

Maps cleanly to existing surfaces with **zero genre-specific
extensions to UIHints or section value_types**. Findings are `KvRow`
with `emphasis` plus `extra="allow"` for `code` / `target` / `state`.
Disposition severity uses `ui_hints.emphasis` (primary / warning /
danger). Mediation moves are typed choices. Restriction map is an
annotated `kv_list`.

The verbatim usability test: an experienced StoryTangl bundle author
could write a credentials bundle by reading only the main spec plus
`bundles/credentials/EXTENSIONS.md` and a worked fixture. No
hand-waving required.

### training (`worlds/coronate_the_regent`)

Maps cleanly. Mood-as-tag-modulator is a `ProjectedState` scalar
plus `cost_previews.delta` on study choices reflecting the modulated
gain. Skill checks reuse `RollFragment(kind="dice")` with `against:
{piece_id, property}`. Inventory unlocks (the dragonslayer sword)
use `PieceFragment.realized` lifecycle.

The demo is intentionally minimal vs. full LLtQ — four weeks, two
skills. The vocabulary handled both the demo's current size and
forward direction (skill trees, calendar widgets, per-skill XP
curves) without needing extension.

### elefant_hunt

Maps cleanly via `ZoneLayoutHints.graph` for the board topology.
Backend-private engine `TokenPool` validates §0.3 — the client never sees
pool state, only `RollFragment.inputs.drawn` outcomes. Hunt
resolution is a single `RollFragment(kind="custom")` with structured
inputs/outcome.

**Predicted gap (hex movement) did not materialize.** Pre-audit
analysis assumed Elefant Hunt would force a `target_position` field
on `PlaceAccepts`. The actual Wham game is graph-based, not hex —
so `target_zone_ref` (locations) and `edge_ref` (the Tier P2
proposal-fixture for first-class edges) suffice. Worth recording
because it overrode a confident pre-audit guess.

---

## §B — Where the vocabulary is awkward but workable

These are patterns the vocabulary supports but where convention
does work the contract leaves unspecified. None warrant spec
changes today.

### Time pressure (credentials, optional)

Per §0.3 / §0.6, time pressure is backend territory: the bundle
emits periodic envelopes decrementing a visible counter via
`update` control fragments. When time reaches zero, dispositions
become `available=false`.

This is awkward because every credentials bundle reinvents the
clock-tick pattern. A Tier P3 `ui_hints.tick: TickHint` sub-shape
could formalize "this counter is backend-driven; expect periodic
updates," but no genre actually *requires* one — manual `update`
control fragments work. Defer until a bundle author asks.

### Cell-as-zone for spatial games

If a future bundle wants a true hex grid (Catan-style, *Photosynthesis*,
hex-wargame), `ZoneLayoutHints.hex={orientation, radius}` exists
as Tier P2 fixture. The cell-as-zone convention (each hex as its
own sub-zone of the board) is contract-compatible but verbose at
typical board sizes (~50+ zones). A `PlaceAccepts.target_position:
dict` field would be more direct.

**This is the single most likely future spec extension.** Held
back today because no shipped or in-design bundle exercises a
true hex grid. Elefant Hunt is graph-based; coronate_the_regent
is non-spatial. The decision waits for an MVP author.

### Composite outcome rituals

`RollFragment(kind="custom")` accommodates Elefant Hunt's hunt
resolution (multi-animal, multi-hunter, mixed outcome) by leaning
on `inputs` and `outcome` being open-typed. This works but pushes
structure into a `dict[str, Any]` field. If composite resolutions
become common, a typed `CompositeOutcome` model on `RollFragment`
might be worth promoting. Today: convention covers it.

### Hot-seat as multi-cursor stand-in

Elefant Hunt and any future multi-player bundle must hot-seat
through one cursor until §1.5 graduates from Tier P1. The
convention: emit "Pass the keyboard to Player Red" `content`
fragments between turns; project all players' scores in a single
`kv_list`.

This is rendering-clean but UX-awkward. Multi-cursor graduation
(per §1.5) closes it. Pending.

### `cost_previews` naming for gains

`CostPreview.delta` is signed; positive = gain, negative = cost.
The field name "cost" misleads when previewing a +2 skill gain.
v1.5 keeps explicit documentation in §0.5 rename history; no
field rename needed. Bundles render the user-facing text as
"+2 combat" while the contract field stays `cost_previews`.

This is a documentation-level rough edge, not a vocabulary
problem.

---

## §C — Where the vocabulary genuinely doesn't reach

**Nothing genuinely out of reach across the four paradigms.** The
findings worth recording:

### §7.4 predicate_ref registration — confirmed highest-leverage open item

All four paradigms exercise `predicate_ref`:

- carwars: slot eligibility ("can I mount a vulcan here")
- credentials: complex restriction matching ("is this candidate's
  origin under embargo *with the prince's visit suspending the rule*")
- training: scheduled-event prerequisite ("does the player have
  enough charm AND the proper invitation")
- elefant_hunt: junction parity, hazard probabilities, hunter
  assignment legality

None can fully ship without a settled predicate registration
protocol. v1.5 spec §7.4 marks this as the highest-leverage open
item; this audit confirms it.

### Multi-cursor projection (Tier P1 §1.5 elaboration)

v1.5 includes the per-cursor projection paragraph naming the recipe
(shared world / per-cursor visibility / control fragments to all
affected channels). The recipe is right; what's missing is engine
implementation. This is a Tier P1 → Tier S graduation question, not
a vocabulary gap.

### Closed drafting / sealed-bid (re-confirmed out of scope)

Per the prior BGG audit, mechanics requiring simultaneous concealed
commit across multiple cursors remain out of scope by §0.3 (backend
single-cursor authority). The four paradigms here don't exercise it;
the audit just reaffirms the boundary.

---

## §D — Cross-paradigm patterns

Patterns that emerged from drafting all four EXTENSIONS docs and
were considered for promotion to a shared `bundles/_common/EXTENSIONS.md`.
**`_common` was not created.** All cross-paradigm patterns turned out
to already be covered by main-spec conventions; lifting them to a
shared doc would have duplicated rather than consolidated.

| Pattern | Decision | Rationale |
|---|---|---|
| Severity emphasis (carwars hazards, credentials findings, training stat-warns, elefant_hunt threat exits) | **No shared doc.** Already covered by `ui_hints.emphasis` and `KvRow.emphasis` in main spec. | The four genres reach for the same field with consistent semantics. No abstraction needed. |
| Gate-check previews (carwars `stat_check`, training reused `stat_check`, credentials `validity_check`, elefant_hunt `encounter_check`) | **No shared doc.** Each genre keeps its own typed `ui_hints` sub-key. | Considered a unified `gate_check` hint; the genres' difficulty rendering, callout text, and modifier breakdowns are similar but the per-genre framing matters for legibility. Forcing a single shape obscures intent. The underlying shape pattern is documented in the EXTENSIONS-doc cross-references. |
| Owner-bound state-bearing pieces (carwars hunters, training inventory, elefant_hunt hunters) | **No shared doc.** `PieceFragment` with `owner` and `properties` is the main-spec answer. | No genre invented its own piece subtype. The convention is exercised, not extended. |
| Drag/click parity for `place` (carwars drag-mount, hypothetical elefant_hunt move-by-drag) | **No shared doc.** Per §5.3 Input Parity, the floor rule lives in the main spec. | Every genre with drag honors click-pick fallback. Documented once in the main spec. |
| Backend-private state with rendered outcomes (elefant_hunt engine `TokenPool`, credentials hidden-rules-not-yet-decided, training hidden-difficulty-targets) | **No shared doc.** Per §0.3 and §0.6, backend-authoritative state with contract-invisible mechanisms is the framing. | This is the strongest cross-paradigm validation in v1.5. The framing handles it. Lifting it to a shared genre doc would weaken the main-spec authority of the principle. |

**Conclusion:** the absence of `bundles/_common/EXTENSIONS.md` is
itself the finding. Four diverse paradigms reach for a small,
consistent set of main-spec conventions. The vocabulary is doing
what compact vocabularies are supposed to do.

---

## §E — Validation: the journal-as-story claim

Per §0.8 / §10.4, the elefant_hunt EXTENSIONS doc includes a worked
CLI transcript (see `bundles/elefant_hunt/EXTENSIONS.md` §10). The
transcript reads as a naturalist's field notes / pulp-adventure log
without any prose beyond per-location flavor and outcome narratives.

This is the concrete validation of the StoryTangl thesis claim.
The vocabulary is doing what it was designed to do: produce
legible narrative as a consequence of structured traversal, not as
authored prose.

**The other three paradigms produce legible transcripts too**, but
their genres are narrative-bound (credentials and training are
already prose-rich; carwars is prose-light but narrowly scenic).
Elefant Hunt is the strongest test because its prose is *thinnest*
and its mechanics *densest* — and it still produces a story.

The conformance harness should grow exemplar transcripts per
paradigm. Suggested set:

```
engine/contrib/conformance/transcripts/
  carwars_garage_to_combat.txt
  credentials_day1_morning.txt
  training_coronate_full_session.txt
  elefant_hunt_one_expedition.txt
```

These serve as both regression baselines and authoring references.

---

## §F — Recommended next steps

Ranked by leverage:

1. **Land §7.4 predicate registration.** Affects all four paradigms.
   Even a minimal protocol (per-bundle string-keyed callables) closes
   most of the open gaps.
2. **Wireframe the four genre demos.** Each EXTENSIONS doc has a
   worked example; the design agent's job is to produce visual
   reference renderings + CLI parity panes. Single prompt, four
   demos.
3. **Grow exemplar transcripts.** Capture CLI output from
   coronate_the_regent and any future bundle runs into
   `engine/contrib/conformance/transcripts/`. Use as regression
   baselines.
4. **Defer hex-grid spatial extension.** No current bundle needs
   it. The proposal-fixture is ready when an MVP author appears.
5. **Defer `_common/EXTENSIONS.md`.** Don't create until a fourth
   cross-paradigm pattern emerges that genuinely warrants
   consolidation.
6. **Engine PR sequencing follows
   `WIDGET_CONTRACT_RECONCILIATION.md` §I** as planned.

---

*End of audit notes v0.1.*

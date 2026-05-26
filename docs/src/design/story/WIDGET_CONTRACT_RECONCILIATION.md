# Widget Contract Reconciliation

**Status:** living document · updated alongside each spec / engine / UI release
**Companion to:** `STORYTANGL_WIDGET_VOCAB.md` v1.5
**Companion to:** `bundles/<name>/EXTENSIONS.md` (Tier P3 genre layers)

This document tracks **implementation status** across the three layers
named in spec §0.7:

| Layer | Document | Role |
|---|---|---|
| **L1 — UI Vocabulary** | `STORYTANGL_WIDGET_VOCAB.md` + `bundles/<name>/EXTENSIONS.md` | Target-truth. What data shapes the player-facing client needs. The spec evolves here; everything else chases. |
| **L2 — API Transport** | `API_SPEC.md` (forthcoming; derived from this doc) | REST endpoints (and other wire transport) routing L1 needs to L3 capabilities. Optional layer — CLI ports skip it. |
| **L3 — Engine Capabilities** | `ENGINE_CAPABILITIES.md` (forthcoming; derived from this doc) | Python callables that produce the data L1 wants. The current engine's actual surface. |

**The spec is target-truth.** This document is the honest reality
check. The two are intentionally allowed to disagree during a
settling phase — that's how the inversion (UI-led design, backend
chases) works.

---

## How to read this doc

Each surface in the spec gets a row in one of the §-numbered tables
below. The four status columns per row:

| Column | What it tracks |
|---|---|
| **Spec tier (L1)** | `Tier S` / `Tier P1` / `Tier P2` / `Tier P3` per the vocab spec. The contract commitment. |
| **Reference clients** | What `apps/web/` and the reference CLI/Tk ports ship today. Values: `done`, `partial`, `not_started`, `n/a`. |
| **Engine backend (L3)** | What `engine/` ships today. Values: same as L2, plus `untyped` (works but with `dict[str, Any]` rather than typed Pydantic). |
| **Plan** | One-line forward direction. Empty when the row is settled across columns. |

A row is **settled** when all three implementation columns match the
spec's tier commitment. A row with mismatched columns is in
**negotiation** — that's fine; the doc just makes the gap visible.

**Sequence of work, per the inversion strategy.** UI vocabulary
leads (commit the target shape in the spec), the reference UI
catches up next (against fixtures, even with dummy data), then the
engine + API expose capabilities that match. The CLI port skips L2
entirely and consumes L3 directly via an in-process shim.

---

## §A — Tier S surfaces (core contract)

These are the surfaces v1.5 marks Tier S — committed as stable target
contract. Most are already shipping in the reference UI and engine;
the negotiation is mostly about typed-shape graduations.

| Surface | Spec tier | Reference UI | Engine backend | Plan |
|---|---|---|---|---|
| `ContentFragment` shape | S | done | done | — |
| `AttributedFragment` shape | S | done | done | — |
| `MediaFragment` shape | S | done | done | — |
| `GroupFragment` shape (`scene`, `dialog`, `overlay`, `status_sidecar`) | S | done | done | — |
| `KvFragment` shape | S | done (`KvRow[]`) | done (`list[KvRow]`) | tuple-row fixtures migrated in typed accepts / KvRow PR |
| `ChoiceFragment` shape (frame only) | S | done | done | — |
| `ControlFragment` (`update` / `delete`) | S | done | done | — |
| `UserEventFragment` | S | done | done | — |
| `ProjectedState.sections` with five `value_type`s | S | done | done | — |
| `PresentationHints` (style_name, style_tags, style_dict, icon) | S | partial (basic style/icon fields) | done | audit aliases and long-tail hints before treating complete |
| Bundle customization / presentation profiles | S target | partial (docs + older world `ui_config`) | not_started | keep advisory; requires world-info catalog before conformance |
| §5.1 Decision Legibility Contract | S | partial (JSON harness covers fixtures/sequences) | n/a (contract; not a capability) | expand field coverage as new decision surfaces promote |
| §5.2 Time Parity Rule (visual ritual skip, media advance) | S | partial (skip available, not enforced) | n/a | webapp conformance harness |
| §5.3 Input Parity Rule (drag fallback, hotkey numbers) | S | partial (positional hotkeys done; drag-fallback in carwars) | n/a | webapp conformance harness |
| §0.2 CLI Floor Rule | S | n/a | n/a (gating rule on PRs) | wire into CI for Tier S graduations |

---

## §B — Tier P1 surfaces (target for next engine epoch)

These are committed target contract but require additive engine
work. Each row should land as a single PR-shaped change unless the
surface is small enough to settle with its immediate neighbors.

| Surface | Spec tier | Reference UI | Engine backend | Plan |
|---|---|---|---|---|
| Typed `PiecesAccepts` (was `tokens`) | P1 | done (kind `pieces` + typed TS shape) | done (`Accepts` union) | expand conformance cases only as new widgets land |
| Typed `PickAccepts`, `TextAccepts`, `QuantityAccepts`, `RawCommandAccepts` | P1 | done | done (`Accepts` union) | keep legacy web `payload_type` path as local UI compatibility until fixtures stop using it |
| Typed `PlaceAccepts` (including optional `edge_ref`) | P1 | partial (`edge_ref` not rendered) | done (`Accepts` union) | add `edge_ref` fixture when route/network MVP lands |
| Typed `ComposeAccepts` | P1 | partial (web nested renderer + CLI/Tk inspection fixture) | done (`Accepts` union) | harden layout and add broader part combinations as worlds emit them |
| Typed `UIHints` | P1 | partial (documented + ad-hoc keys) | done (`UIHints`, extra-allow) | tighten named fields when more worlds use them |
| Typed `Blocker` (replaces dict blockers) | P1 | done (typed + rendered) | untyped | engine PR |
| Typed `InterpretationFragment` | P1 | done (renders `result` / `text` / `message`) | untyped | engine PR |
| `cost_previews: list[CostPreview]` (plural) | P1 | done (choice display) | not_started | engine PR |
| `metadata.grammar` typed sub-key | P1 | done | partial (string-keyed dict) | engine PR for `GrammarHint` Pydantic model |
| `metadata.info_affordances: list[InfoAffordance]` | P1 | done (with `query` descriptor) | partial (emits in some bundles, untyped) | engine PR: typed `InfoAffordance` model |
| `InfoAffordance.query` optional dict (opaque descriptor) | P1 | done | partial | engine PR: declare the field; bundles populate as needed |
| `metadata.info_state: InfoState` typed | P1 | done (nested type + dirty-kind cache hints) | not_started | engine PR: emit nested `info_state` |
| `/story/info` accepts `kind` + `query` params | P1 | done client-side | partial (basic endpoint exists; no query routing) | API + engine PR (see §E) |
| HTTP body field `edge_id` | P1 | done | done | — |
| §1.5 Cursors and journal channels (per-channel envelopes) | P1 | n/a (single cursor) | n/a (single cursor) | wait for MVP author needing multi-cursor (Discord-bot bundle, Lost Worlds gamebook) |
| §1.6 Info channels graduation to Tier S | P1 | done | partial | gated on CLI reference port implementing the `?`/slash fallback |

**Block on Tier P1 graduation to Tier S:** the CLI reference port
(`engine/contrib/conformance/cli_reference_port.py`) must implement
each surface before its row can promote. Until then they stay P1.

---

## §C — Tier P2 surfaces (interactive surface vocabulary)

These are committed target contract but larger, and several depend
on the §7.4 predicate-registration protocol (an explicit open
question in the spec).

| Surface | Spec tier | Reference UI | Engine backend | Plan |
|---|---|---|---|---|
| `PieceFragment` (core shape) | P2 | partial (basic web widget + carwars wireframes) | partial (untyped equivalent) | engine PR: typed `PieceFragment` with required `hints.label_text` |
| `PieceFragment.realized` + `cost` (offers) | P2 | done in carwars catalog fixtures | not_started | engine PR for typed lifecycle; bundle MVP needed for shop semantics |
| `PieceFragment.owner` | P2 (proposal fixture) | not_started | not_started | wait for multi-cursor MVP |
| `PieceFragment.position` | P2 (proposal fixture) | not_started | not_started | wait for grid/hex bundle MVP (Patchwork, Carcassonne) |
| `PieceFragment.available` + `unavailable_reason` | P2 | done | not_started | engine PR with `PieceFragment` graduation |
| `group_type="zone"` with `ZoneConstraints` | P2 | partial (basic web widget + carwars wireframes) | not_started | engine PR: typed `GroupFragment.constraints`; bundle MVP for capacity |
| `ZoneLayoutHints` (orientation, fan, grid, hex, graph, floorplan) | P2 | partial (orientation/grid/fan) | not_started | engine PR; render-port catches up as needed |
| `GraphLayout.edges` (first-class adjacencies with UIDs) | P2 (proposal fixture) | not_started | not_started | wait for network/route bundle MVP (Ticket-to-Ride-shaped) |
| `PlaceAccepts.edge_ref` fixture coverage | P2 pressure fixture | not_started | not_started | P1 typed field exists in the target; graph-route fixture remains gated on a route/network MVP |
| `RollFragment` (typed) | P2 | partial (basic rendering in carwars) | not_started | engine PR; CLI reference port renders outcome word + narrative |
| `RitualHints` (skip_label, auto_skip_after_seen, allow_replay, duration_ms) | P2 | partial | not_started | engine PR with `RollFragment` graduation |
| `predicate_ref` registration protocol | §7.4 OPEN | n/a | n/a | **highest-leverage open question**; awaiting MVP author |
| `visibility="hidden" \| "owner_only" \| "public"` | P2 | partial | not_started | engine PR — single-cursor today, audience-list extension when multi-cursor lands |
| `visibility: list[ParticipantId]` (audience lists) | P2 (proposal fixture) | not_started | not_started | wait for team-game MVP |

---

## §D — Tier P3 genre extension surfaces

These are advisory genre conventions layered on top of v1.5. They do
not create new core fragment types, accepts kinds, or value types. A
generic client remains conforming when it renders the underlying v1.5
surfaces and ignores these enrichments.

| Surface | Spec tier | Reference UI | Engine backend | Plan |
|---|---|---|---|---|
| `bundles/carwars/EXTENSIONS.md` | P3 | docs + v1.5 wireframe | n/a | keep drag optional; no garage-specific core widgets |
| `bundles/credentials/EXTENSIONS.md` | P3 | docs + v1.5 wireframe | n/a | packet / finding / disposition treatments remain genre enrichments |
| `bundles/training/EXTENSIONS.md` | P3 | docs + v1.5 wireframe | n/a | study previews, stat checks, and inventory unlocks remain genre enrichments |
| `bundles/elefant_hunt/EXTENSIONS.md` | P3 | docs + v1.5 wireframe | n/a | journal-as-story transcript proof; no new surface beyond graph zones / rolls |
| `ui_hints.stat_check` | P3 | docs + v1.5 wireframe | bundle-specific | optional badge or CLI suffix; backend remains authoritative |
| `ui_hints.validity_check` | P3 | docs + v1.5 wireframe | bundle-specific | optional preview over mediation choices; fallback to ordinary choice text |
| `ui_hints.encounter_check` | P3 | docs + v1.5 wireframe | bundle-specific | optional risk badge / suffix; fallback to `ui_hints.emphasis` + prose |
| `ui_hints.drag` | P3 | docs + v1.5 wireframe | n/a | optional enrichment; click-pick fallback remains required by §5.3 |
| Genre transcript examples | P3 diagnostic | v1.5 wireframe samples | n/a | add executable transcripts when demo worlds stabilize; diagnostic, not gating |
| `_common/EXTENSIONS.md` | deferred | n/a | n/a | do not create until a fourth cross-genre pattern is not already covered by core v1.5 |

---

## §E — API transport (Layer 2)

The API surface is intentionally underspecified at the contract
level — the spec commits to the data shapes (L1), and the API
chooses how to route them. This table is what the engine team
implements.

| Endpoint | Method | Spec target | Current engine | Plan |
|---|---|---|---|---|
| `/story/do` | POST | accepts `ChoiceRequest{edge_id, payload}`; returns `RuntimeEnvelope` | accepts `{edge_id, payload}` | type response |
| `/story/update` | GET | returns `RuntimeEnvelope` typed | partial | type response |
| `/story/info` | GET | accepts `kind?` and `query?` params (JSON-encoded descriptor); returns `ProjectedState` | basic endpoint exists | add `query` param routing; document descriptor semantics |
| `/system/info` | GET | public; rate-limited | done | — |
| `/auth/whoami` | GET | returns current `Principal` | not_started | see auth thread |
| `/auth/keys` (CRUD) | various | API key lifecycle | not_started | see auth thread |
| `/auth/revoke` | POST | revoke a key | not_started | see auth thread |

**CLI port and L2.** The CLI port does not call any of these
endpoints. It consumes `engine/`'s Python surface directly via an
in-process shim — typically a thin wrapper around
`ServiceManager.do_action()` / `get_envelope()` / `get_projected_state()`.
The L2 column is therefore not blocking for CLI conformance.

---

## §F — Conformance harness

These tests verify spec contracts against the reference
implementations. They serve as the gating mechanism for tier
graduations and as the regression suite for cross-port parity.

| Harness | What it checks | Status | Plan |
|---|---|---|---|
| `engine/contrib/conformance/cli_reference_port.py` | Tier S CLI rendering for every fragment / value_type | partial (Tier S + current P1 widgets) | extend coverage as Tier P1 → S graduations happen |
| `engine/contrib/conformance/legibility.py` | §5.1 — referenced UIDs are rendered | initial | covers fixture and sequence choices; expand as new P1/P2 fields promote |
| `engine/contrib/conformance/parity.py` | §5.2 time parity, §5.3 input parity | not_started | second harness |
| `engine/contrib/conformance/test_conformance.py` | pytest harness binding fixtures + ports | not_started | wire into CI |
| `engine/contrib/conformance/fixtures/*.json` | canonical envelopes per surface | partial (Tier S + current P1 fixtures) | keep promoting proposal fixtures as implementation lands |
| `engine/contrib/conformance/proposals/*.json` | forward-compatible proposal envelopes | partial | current set covers carwars garage, piece realization, place accepts, record KvRow, roll fragment, and one UUID-shaped v1.5 wireframe interpretation sample; CLI/Tk can inspect them without promotion |
| webapp Vitest conformance suite | webapp DOM matches expected for each fixture | not_started | written from fixtures; webapp regression mechanism |

---

## §G — Recent reconciliation events

A short log of what changed across recent spec / UI / engine releases.
Each entry names which layer moved and what the consequence is for the
others.

### 2026-05 — spec v1.5 (L1 update only)

- Adopted the v1.4 genre-audit additions: journal-as-narrative,
  per-cursor projection of shared state, and the genre extension index.
  **Impact:** no new top-level vocabulary surfaces; improves authoring
  discipline and cross-demo traceability.
- Reconciled v1.4 language with repo-current implementation status.
  **Impact:** typed `Accepts` and `UIHints` are described as implemented;
  `Blocker`, `InterpretationFragment`, typed info metadata, and Tier P2
  widgets remain pending or partial.
- Updated the fixture inventory to match the current repository,
  including `compose_payload.json` and the existing proposal fixture set.
- Imported and vetted Tier P3 extension docs for CarWars, credentials,
  training, and elefant_hunt, plus `GENRE_AUDIT_NOTES.md`.
  **Impact:** genre enrichments are advisory over core v1.5; no
  `_common/EXTENSIONS.md` until a repeated cross-genre pattern is not
  already covered by the core vocabulary.
- Archived the v1.5 wireframe package under
  `docs/src/design/story/wireframes/v1_5/`. **Impact:** visual coverage
  now matches the reconciled v1.5 vocabulary and Tier P3 extension docs;
  most wireframe fixtures remain design fixtures until their symbolic ids
  are translated for engine conformance.
- Translated one v1.5 wireframe interpretation sample into
  `engine/contrib/conformance/proposals/` with UUID-shaped ids. **Impact:**
  future ports have a concrete command-feedback fixture without promoting the
  whole wireframe bundle to gating conformance.

### 2026-05 — spec v1.3 (L1 update only)

- Reverted `accepts.kind="select"` rename → `pieces`. **Impact:** L2/L3
  may continue using `pieces`; no migration needed.
- Demoted §1.5 cursors and §1.6 info channels to Tier P1. **Impact:**
  none on L2/L3 directly; clarifies that current single-cursor behavior
  is settled, multi-cursor is target.
- Replaced `GET /story/info/{kind}` with query-descriptor model.
  **Impact:** L2 evolves the `/story/info` endpoint; no L1 break since
  the v1.2 URL form was never shipped.
- Added §0.7 three-layer architecture. **Impact:** this document
  exists.
- EXTENSIONS.md swept `tokens → pieces`. **Impact:** carwars Tier P3
  conventions now consistent with main spec.

### 2026-05 — webapp v1.3 reference UI update

- Reference webapp uses `accepts.kind="pieces"` throughout (15+ call
  sites).
- Reference webapp implements `InfoAffordance.query` as an opaque JSON
  descriptor on `/story/info?kind=...&query=...`.
- Reference webapp accepts nested `metadata.info_state`. This row is
  superseded by the v1.5 update, where `dirty_kinds` became an implemented
  cache hint in the reference client.
- Reference webapp ships `place` accepts kind without `edge_ref`
  (proposal fixture not yet exercised).

### 2026-05 — webapp v1.5 reference UI reconciliation

- Reference webapp renders `InterpretationFragment` with the spec's
  `result`, `text`, `message`, `blocked_reason`, `hint`, and `candidates`
  fields. **Impact:** command-resolution feedback no longer falls through
  to the unknown-fragment fallback.
- Reference webapp renders typed `blockers[]` and plural
  `cost_previews[]` as choice decision details. **Impact:** locked choices
  expose more of the decision-legibility contract in the current shell.
- Reference webapp posts `edge_id` to `/story/do`. **Impact:** client and
  endpoint server now use the same choice-edge identifier name.
- Reference webapp treats `metadata.info_state.dirty_kinds` as cache hints for
  `/story/info`. **Impact:** the sidebar keeps old refresh behavior when no
  hint is provided, but skips clean side-channel refreshes when the backend
  sends explicit dirty-kind metadata. The tests cover both default status and
  selected affordance kinds.
- Reference CLI/Tk ports render or inspect blockers, cost previews, typed
  accepts prompts, and v1.5 interpretation fields. **Impact:** new client
  ports can compare against portable JSON fixtures and proposal fixtures
  instead of copying the Vue shell.

### 2026-05 — engine current (L3 baseline)

- Engine emits typed `Accepts` and `UIHints` models from
  `tangl.journal.intent`; blockers remain dictionary-shaped pending the
  next intent pass.
- Engine HTTP body uses `edge_id`.
- Engine `KvFragment.content`, projected `kv_list` values, web fixtures,
  and conformance fixtures use the unified `KvRow` record shape.
- Engine has no `/story/info/{kind}` (consistent with v1.5 spec).

---

## §H — How to use this doc

- **Spec authors.** When you commit a vocabulary change, update the
  appropriate row's "Spec tier" column and add a one-paragraph entry
  to §G. The implementation columns lag deliberately.
- **Reference UI authors.** When the webapp implements a surface,
  update the "Reference UI" column to `done` or `partial`. If you're
  implementing against a fixture (not against a live engine), use
  `partial` and note the fixture in the Plan column.
- **Engine authors.** When the engine ships a typed shape or endpoint,
  update the "Engine backend" column. If you're shipping the engine
  capability but not the API endpoint, that's still progress — the
  capabilities table in `ENGINE_CAPABILITIES.md` (forthcoming) tracks
  Python surface separately.
- **CLI port authors.** Watch §A and §B; you don't care about §E.
  Your conformance is against `cli_reference_port.py` and the §F
  harness.

A row becomes a candidate for the §G log when any column moves.
A surface becomes a candidate for Tier S graduation when all three
implementation columns read `done` and the CLI reference port
renders it.

---

## §I — Forward-looking sequence

This is the **inversion plan** the project committed to: UI leads,
API + engine chase. Each step's deliverable is a single PR-shaped
change to the named layer.

**Phase 1 — Stabilize spec (current).**

- ✅ Spec v1.5 with the v1.4 genre-audit additions reconciled to repo state.
- ✅ EXTENSIONS.md swept to `pieces`.
- ✅ Tier P3 extension docs imported and vetted for current demo genres.
- ✅ This reconciliation doc as the three-layer spine.

**Phase 2 — Reference UI catches up.** Wireframes and webapp align
to v1.5.

- ✅ Wireframes resync: v1.5 bundle is archived under
  `docs/src/design/story/wireframes/v1_5/`, with v1.2/v1.3 treated as
  visual precedent rather than contract truth.
- ✅ The v1.5 wireframe annotates core vocabulary separately from Tier P3
  enrichments (`stat_check`, `drag`, `validity_check`, `encounter_check`),
  keeping contract conformance and genre flavor separable.
- Webapp PR sequence:
  1. ✅ `compose` accepts rendering as nested ChoiceInputView.
  2. ✅ `InterpretationFragment` renderer with the spec's `result` /
     `text` field names.
  3. ✅ `metadata.info_state` behavior pass: use nested `dirty_kinds` /
     `available_kinds` as cache hints once the backend emits them.
  4. Keep `info_affordances` opaque; clients pass `query` descriptors through
     rather than parsing bundle-specific fields.

**Phase 3 — Engine + API catch up.** Backend declares capabilities,
API maps them.

- Engine PR sequence:
  1. Typed `Blocker` model in `tangl/journal/intent.py`.
  2. Typed `InterpretationFragment` with `result` / `text` fields.
  3. Typed `metadata.grammar` and `metadata.info_affordances`.
  4. HTTP API: type responses on `/story/do` / `/story/update`; add `query`
     param routing on `/story/info`.
  5. Conformance harness: ✅ initial `legibility.py`; next write
     `parity.py` and extend `cli_reference_port.py` for new Tier P1 surfaces.

**Phase 4 — Tier P1 → S graduation.** Surfaces in §B promote one
at a time, gated on the CLI reference port and the conformance
harness having coverage for each.

**Phase 5 — Tier P2 surfaces gate on bundle MVPs.** Each Tier P2
surface (multi-cursor, pieces with position, edge_ref, predicate
registration) waits for a real bundle author who needs it. We do
not pre-build these.

---

*End of v0.2.*

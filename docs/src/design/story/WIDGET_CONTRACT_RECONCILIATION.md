# Widget Contract Reconciliation

**Status:** living document · updated alongside each spec / engine / UI release
**Companion to:** `STORYTANGL_WIDGET_VOCAB.md` v1.3
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

These are the surfaces v1.3 marks Tier S — committed as stable target
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
| §5.1 Decision Legibility Contract | S | partial (no automated check) | n/a (contract; not a capability) | webapp conformance harness (see §E) |
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
| Typed `Blocker` (replaces dict blockers) | P1 | partial | untyped | engine PR |
| Typed `InterpretationFragment` | P1 | partial (custom shape mid-cycle) | untyped | engine PR; webapp aligns on `result`/`text` field names |
| `cost_previews: list[CostPreview]` (plural) | P1 | partial | not_started | engine PR; webapp follows |
| `metadata.grammar` typed sub-key | P1 | done | partial (string-keyed dict) | engine PR for `GrammarHint` Pydantic model |
| `metadata.info_affordances: list[InfoAffordance]` | P1 | done (with `query` descriptor) | partial (emits in some bundles, untyped) | engine PR: typed `InfoAffordance` model |
| `InfoAffordance.query` optional dict (opaque descriptor) | P1 | done | partial | engine PR: declare the field; bundles populate as needed |
| `metadata.info_state: InfoState` typed | P1 | partial (nested type + fixture; refresh still unconditional) | not_started | engine PR: emit nested `info_state`; webapp can later use it for cache hints |
| `/story/info` accepts `kind` + `query` params | P1 | done client-side | partial (basic endpoint exists; no query routing) | API + engine PR (see §D) |
| HTTP body field `edge_id` (rename of `choice_id`) | P1 | uses `choice_id` | uses `choice_id` | engine + webapp PR with one-version deprecation shim |
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

## §D — API transport (Layer 2)

The API surface is intentionally underspecified at the contract
level — the spec commits to the data shapes (L1), and the API
chooses how to route them. This table is what the engine team
implements.

| Endpoint | Method | Spec target | Current engine | Plan |
|---|---|---|---|---|
| `/story/do` | POST | accepts `ChoiceRequest{edge_id, payload}`; returns `RuntimeEnvelope` | accepts `{choice_id, payload}`; untyped response | rename body field; type response; ship deprecation shim |
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

## §E — Conformance harness

These tests verify spec contracts against the reference
implementations. They serve as the gating mechanism for tier
graduations and as the regression suite for cross-port parity.

| Harness | What it checks | Status | Plan |
|---|---|---|---|
| `engine/contrib/conformance/cli_reference_port.py` | Tier S CLI rendering for every fragment / value_type | partial (Tier S widgets only) | extend coverage as Tier P1 → S graduations happen |
| `engine/contrib/conformance/legibility.py` | §5.1 — referenced UIDs are rendered | not_started | first conformance harness to write |
| `engine/contrib/conformance/parity.py` | §5.2 time parity, §5.3 input parity | not_started | second harness |
| `engine/contrib/conformance/test_conformance.py` | pytest harness binding fixtures + ports | not_started | wire into CI |
| `engine/contrib/conformance/fixtures/*.json` | canonical envelopes per surface | partial (Tier S fixtures only) | add P1 proposal fixtures: `place_on_edge.json`, `multi_cursor_visibility.json`, `roll_outcomes.json` |
| webapp Vitest conformance suite | webapp DOM matches expected for each fixture | not_started | written from fixtures; webapp regression mechanism |

---

## §F — Recent reconciliation events

A short log of what changed across recent spec / UI / engine releases.
Each entry names which layer moved and what the consequence is for the
others.

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
- Reference webapp accepts nested `metadata.info_state`, but still refreshes
  `/story/info` on every story update until backend dirty-kind support lands.
- Reference webapp ships `place` accepts kind without `edge_ref`
  (proposal fixture not yet exercised).

### 2026-05 — engine current (L3 baseline)

- Engine emits typed `Accepts` and `UIHints` models from
  `tangl.journal.intent`; blockers remain dictionary-shaped pending the
  next intent pass.
- Engine HTTP body uses `choice_id` (pre-rename).
- Engine `KvFragment.content`, projected `kv_list` values, web fixtures,
  and conformance fixtures use the unified `KvRow` record shape.
- Engine has no `/story/info/{kind}` (consistent with v1.3 spec).

---

## §G — How to use this doc

- **Spec authors.** When you commit a vocabulary change, update the
  appropriate row's "Spec tier" column and add a one-paragraph entry
  to §F. The implementation columns lag deliberately.
- **Reference UI authors.** When the webapp implements a surface,
  update the "Reference UI" column to `done` or `partial`. If you're
  implementing against a fixture (not against a live engine), use
  `partial` and note the fixture in the Plan column.
- **Engine authors.** When the engine ships a typed shape or endpoint,
  update the "Engine backend" column. If you're shipping the engine
  capability but not the API endpoint, that's still progress — the
  capabilities table in `ENGINE_CAPABILITIES.md` (forthcoming) tracks
  Python surface separately.
- **CLI port authors.** Watch §A and §B; you don't care about §D.
  Your conformance is against `cli_reference_port.py` and the §E
  harness.

A row becomes a candidate for the §F log when any column moves.
A surface becomes a candidate for Tier S graduation when all three
implementation columns read `done` and the CLI reference port
renders it.

---

## §H — Forward-looking sequence

This is the **inversion plan** the project committed to: UI leads,
API + engine chase. Each step's deliverable is a single PR-shaped
change to the named layer.

**Phase 1 — Stabilize spec (current).**

- ✅ Spec v1.3 with the six v1.2.1 patches.
- ✅ EXTENSIONS.md swept to `pieces`.
- ✅ This reconciliation doc as the three-layer spine.

**Phase 2 — Reference UI catches up.** Wireframes and webapp align
to v1.3.

- Wireframes resync: v1.3 bundle is archived under
  `docs/src/design/story/wireframes/v1_3/`; keep future wireframes labeled
  by tier and avoid treating P2/P3 sketches as reference-client status.
- Webapp PR sequence:
  1. ✅ `compose` accepts rendering as nested ChoiceInputView.
  2. `InterpretationFragment` renderer with the spec's `result` /
     `text` field names.
  3. `metadata.info_state` behavior pass: use nested `dirty_kinds` /
     `available_kinds` as cache hints once the backend emits them.
  4. Keep `info_affordances` opaque; clients pass `query` descriptors through
     rather than parsing bundle-specific fields.

**Phase 3 — Engine + API catch up.** Backend declares capabilities,
API maps them.

- Engine PR sequence:
  1. Typed `Blocker` model in `tangl/journal/intent.py`.
  2. Typed `InterpretationFragment` with `result` / `text` fields.
  3. Typed `metadata.grammar` and `metadata.info_affordances`.
  4. HTTP API: rename `choice_id` → `edge_id` with deprecation; type
     responses on `/story/do` / `/story/update`; add `query` param
     routing on `/story/info`.
  6. Conformance harness: write `legibility.py`, `parity.py`, extend
     `cli_reference_port.py` for new Tier P1 surfaces.

**Phase 4 — Tier P1 → S graduation.** Surfaces in §B promote one
at a time, gated on the CLI reference port and the conformance
harness having coverage for each.

**Phase 5 — Tier P2 surfaces gate on bundle MVPs.** Each Tier P2
surface (multi-cursor, pieces with position, edge_ref, predicate
registration) waits for a real bundle author who needs it. We do
not pre-build these.

---

*End of v0.1.*

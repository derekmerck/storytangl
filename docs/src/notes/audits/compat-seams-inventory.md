# Compatibility Seam Inventory (annealing #268, item E)

## Scope

- Objective: catalog the in-repo compatibility seams flagged by the v38
  annealing synthesis (GitHub issue #268, approved item E), each with an
  **actionable sunset condition**, so a follow-up cleanup PR can act immediately.
- Non-goal: **no removals in this pass.** This is a cleanup shopping list, not a
  deprecation schedule.

## Repo policy (durable, owner-set)

Tests and apps in *this* repo are the **only** legacy consumers: no external
clients, no version skew, no long-lived saves. So a seam is "sunsettable" the
moment the named in-repo readers are updated — there is no migration window to
honor and no external contract to preserve. Each entry below is written as
"update `<named in-repo readers>` and delete."

---

## Seam 1 — legacy `payload_type` / `input` accepts

**What it bridges.** The pre-typed choice-input shape, where an accept was keyed
by a bare `input` string plus an optional `payload_type`, instead of the typed
`accepts.kind` discriminator (`pick` / `text` / `quantity` / `pieces` / `place`
/ `compose`). It survives only in the web client as `LegacyPayloadAccepts`, a
member of the `Accepts` union.

**Backend status.** Dead on the backend. The engine `Accepts` union
(`engine/src/tangl/journal/intent.py`) emits only the six typed kinds; no engine
or server path produces `payload_type` or an `input`-keyed accept (the
`payload_kind` / `has_payload_kind` symbols in `core` are unrelated template
machinery).

**In-repo readers.**
- `apps/web/src/types/tangl_typedefs.ts` — `LegacyPayloadAccepts` interface
  (≈ line 420) and its membership in the `Accepts` union (≈ line 449).
- `apps/web/src/components/story/ChoiceInputView.vue` — reads
  `accepts.value.input` (≈ line 71) and `accepts.value.payload_type` →
  `payloadKey` (≈ lines 109–110, 272–307).
- `apps/web/src/components/story/StoryAction.test.ts` — two cases exercising
  `payload_type: 'offer_silver'` (≈ lines 197, 263).

**Sunset condition.** Remove `LegacyPayloadAccepts` from the `Accepts` union and
its interface in `tangl_typedefs.ts`; remove the `input` / `payload_type` /
`payloadKey` branches in `ChoiceInputView.vue`; delete the two legacy cases in
`StoryAction.test.ts`. No backend change required (already typed-only).

---

## Seam 2 — `_normalize_choice_labels_in_fragments`

**What it bridges.** Choice fragments that lack an explicit `label`. The REST
serializer backfills `label` from `source_label`, then `text`, then `content`,
for both top-level `choice` fragments and `choice`s embedded in `block`
fragments.

**In-repo readers / mirrors.**
- `apps/server/src/tangl/rest/routers/story_router.py` — definition
  (≈ line 136) and its single call site in the `/story` response assembly
  (≈ line 240).
- `apps/server/tests/helpers_server/json_fragment_helpers.py` —
  `extract_choices_from_fragments` carries its **own copy** of the same
  `source_label`/`text`/`content` → `label` normalization (≈ line 9), so server
  tests do not actually depend on the router's pass.
- The web renderer reads `choice.text` for display
  (`apps/web/src/components/story/StoryAction.vue`), not the normalized `label`.

**Sunset condition.** Confirm the canonical `ChoiceFragment` projection (the
#271 DTO) always populates `label` at projection time — or that every reader
falls back on its own (the web client already renders `text`). Then delete
`_normalize_choice_labels_in_fragments` (def + call at `story_router.py:240`)
and drop the `_normalize` wrapper inside `extract_choices_from_fragments`.

**#275 note.** PR #275 (typed blocker contract) also touches `story_router.py`
and `ui_hints` (`cost_previews`). This inventory does not modify the router; if
#275 lands first, this entry's line numbers shift but the seam is unchanged.

---

## Seam 3 — `edge_id` as the wire field (**keep — do not rename**)

**What it is.** The backend-issued interaction id on every choice; clients
submit `{edge_id, payload}` to `/story/do`. The synthesis names the *conceptual*
shape "interaction request" but explicitly **defers any rename** (no concrete
client/compat need; renaming would churn fixtures for no functional payoff).
Inventoried here only to record the blast radius for a future rename PR.

**In-repo readers (blast radius if ever renamed).**
- Web: `apps/web/src/types/tangl_typedefs.ts`,
  `components/story/StoryFlow.vue`, `StoryAction.vue`, `ChoiceInputView.vue`,
  and the `StoryFlow.test.ts` / `StoryAction.test.ts` / `StoryBlock.test.ts`
  fixtures.
- Engine/service: `engine/src/tangl/service/response.py`,
  `service/service_manager.py`, `story/system_handlers.py`, `story/analysis.py`.

**Sunset condition.** **None this iteration — keep `edge_id`.** A rename is a
deferred item (per the synthesis "Deferred findings" table), promoted only by a
concrete client/compat need, not by doc aesthetics. The "interaction request"
name stays docs-only vocabulary.

---

## Seam 4 — dynamic-action cleanup tag conventions

**What it is.** The discriminator tag sets that scope each `_clear_dynamic_*`
helper's GC sweep — the compound-key cleanup contract (`{dynamic, fanout, menu}`,
`{dynamic, fanout, game}`, `{dynamic, sandbox, <kind>}` ×9, `{dynamic, sandbox,
incremental}`, world-owned `{dynamic, sandbox, adventure}`). These are **not a
removable compat seam** — they are the load-bearing cleanup mechanism, pinned by
the non-subsumption / exactly-one-family invariant (PR #274). Inventoried per the
synthesis because the *drift* in the convention is sunsettable, the contract is
not.

**In-repo readers asserting exact tag sets.**
- `engine/tests/mechanics/test_projection_characterization.py` — per-family
  exact tag assertions (the executable form of the audit table).
- `engine/tests/mechanics/test_sandbox_architecture.py` — the non-subsumption /
  exactly-one-family invariant.
- `engine/tests/mechanics/test_sandbox.py`,
  `engine/tests/mechanics/test_sandbox_adventure_slice.py`,
  `engine/tests/loaders/test_adventure_sandbox_world.py`,
  `engine/tests/story/test_menu_fanout.py`,
  `engine/tests/mechanics/games/test_game_handlers.py`,
  `engine/tests/vm/test_provision_pipeline.py` — golden tag-set behavior.

**Sunset condition.** The *contract* does not sunset. The only sunsettable item
is the recorded **drift**: game self-loop moves wear `fanout` without touching
`Resolver.resolve_fanout` (the tag vocabulary lies). Resolving it means an
intentional, characterized migration that (a) drops `fanout` from
`_build_game_actions`' tag set and the `_clear_dynamic_game_actions`
discriminator, and (b) updates the matching `test_projection_characterization.py`
and `test_game_handlers.py` assertions and the AFFORDANCE_MODEL.md audit table
together — never as a drive-by. Until then the `fanout` tag is preserved exactly
(item D added a `source: "game_self_loop"` *hint* alongside it precisely to avoid
echoing the lie in a second place).

---

## Cross-references

- Approved plan: GitHub issue #268, "Architecture synthesis: v38 Aardvark
  annealing direction" (item E).
- Audit table + cleanup-ownership contract:
  `docs/src/design/planning/AFFORDANCE_MODEL.md` ("The audit table (filled)").
- Related: PR #274 (cleanup-discriminator invariant), PR #276 (projection
  characterization tests), PR #277 (doc reconciliation), PR #275 (typed blocker
  contract, open).

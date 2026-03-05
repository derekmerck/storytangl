# V38 Parity Matrix (Phase 1)

## Status
- Date: 2026-03-04
- Phase: 1 + secondary-scope execution recipe validated (non-retiring blast run green, including full-v38 toggle lane)
- Scope lock: `engine/tests/core`, `engine/tests/vm`, `engine/tests/story`, `engine/tests/service`
- Explicitly out of first-pass classification scope: `engine/tests/integration`, `engine/tests/loaders`, `engine/tests/ir` (now tracked as secondary execution scope)

## Purpose
This matrix classifies each in-scope legacy test module exactly once and maps it to either:
- `PORT_*`: move test intent into v38 behavior/contracts.
- `RETIRE_*`: remove from parity gate because behavior is gone, moved, or irrelevant.

This document tracks both mapping decisions and current parity execution status for mapped `PORT_*` targets.

## Phase 1.5 Execution Recipe (Validated)
This experiment is now the active migration recipe:
1. Normalize non-retiring imports to top-level surfaces (`tangl.core`, `tangl.vm`, `tangl.story`, `tangl.service`) so blast radius is measurable.
2. Add/keep thin compatibility bridges only where needed (selector/caller aliasing, record-like acceptance, type aliases).
3. Pin explicit legacy semantics only where behavior is still intentionally legacy (for example `LegacyStoryGraph` in selected tests).
4. Convert eager legacy imports in loader/service entrypoints to lazy imports so v38 flows do not pull legacy internals by accident.
5. Re-run the non-retiring blast gate and only keep bridges still required by passing behavior.

## Secondary Scope Bridge Matrix (Integration/Loaders/IR)
| concern | temporary bridge (now) | end-state target | test policy |
|---|---|---|---|
| Deep import drift bypassing shims | Replace deep imports with top-level package imports in non-retiring modules/tests | Remove legacy package shims entirely; import `core38`/`vm38`/`story38`/`service38` directly | Keep tests if they validate externally observable behavior |
| Legacy story-graph semantics still required by some tests | Use `LegacyStoryGraph` explicitly in tests that still require legacy runtime behavior | Port those tests to v38 semantics or retire if no external behavior is covered | Retire tests that only assert legacy graph internals |
| Legacy matcher syntax (`matches(**criteria)` / filter helpers) | Translate to selector-first matching where low-risk (`Selector(...).matches(entity)`) | Remove compatibility aliases once callsites are migrated | Keep only behavior-focused assertions, not matcher implementation details |
| Loader/service eager legacy imports | Convert to lazy imports in runtime37-only paths | Remove runtime37 code paths when fully retired | Keep loader tests that validate world discovery/compile outputs |
| Legacy-internal assertions in secondary suites | Explicitly classify as retirement candidates | Drop from parity gate unless tied to missing public behavior | If no external consumer-facing gap exists, retire |

## Secondary Scope Test Retirement Policy
- Keep tests that validate observable contracts: API outputs, journal/choice behavior, loader/compiler outputs, replay/provision invariants.
- Retire tests that only inspect legacy internal classes, private fields, or historical execution mechanics with no v38 contract value.
- Keep or reintroduce a retired test only when it demonstrates a legitimately missing feature relied on by another non-retiring area.
- For media while v37/v38 mechanics are in transition, keep only stable contracts (resource indexing and RIT/URL dereference shape); retire legacy phase-runner/media-dependency internal assertions.

## Secondary Scope File Matrix (Integration/Loaders/IR, 2026-03-05 pass 3)
| path | disposition | rationale | status |
|---|---|---|---|
| `engine/tests/integration/test_choice_availability_e2e.py` | `RETIRE_LEGACY_INTERNAL` | Hard-coupled to `LegacyStoryGraph` + legacy phase runner internals; no longer a v38 contract gate. | retired (module skipped) |
| `engine/tests/integration/test_media_e2e.py` | `RETIRE_LEGACY_INTERNAL` | Depends on legacy v37 phase-runner/media-dependency mechanics that are not vm38 contract assertions. | retired (module skipped) |
| `engine/tests/integration/test_service_layer.py` | `PORT_ADAPT` | Integration smoke flow now runs through `create_story38`/`resolve_choice38`/`get_story_update38` on service-layer orchestrator wiring. | ported to runtime38 |
| `engine/tests/integration/test_system_media_e2e.py` | `KEEP_DIRECT` | Validates system-media URL dereference contract; runtime-version agnostic. | kept |
| `engine/tests/loaders/test_world_loader.py::test_compile_anthology_shares_domain_and_media` | `RETIRE_LEGACY_INTERNAL` | Asserts runtime37-only world internals (`domain_manager`/`resource_manager`) with no added v38 signal. | retired (test skipped) |
| `engine/tests/loaders/test_world_loader.py::test_loader_creates_runtime38_world_with_media_registry` | `PORT_ADAPT` | Same intent as legacy media-registry smoke test, now asserted against runtime38 world facets (`resources`, `bundle`). | ported to runtime38 |
| `engine/tests/loaders/test_world_loader.py::test_compiler_adds_bundle_root_for_domain_imports` | `PORT_ADAPT` | Preserves domain import-path contract while asserting runtime38 world domain facet wiring. | ported to runtime38 |
| `engine/tests/loaders/test_round_tripping.py` | `RETIRE_LEGACY_INTERNAL` | Relied on legacy ScriptManager template-shape assumptions that do not map 1:1 to story38 template bundle/runtime representation. | retired (module skipped) |
| `engine/tests/loaders/test_world_bundle.py` | `KEEP_DIRECT` | Bundle manifest/path normalization contract is runtime-neutral and still required. | kept |
| `engine/tests/loaders/test_world_manifest.py` | `KEEP_DIRECT` | Manifest schema/normalization contract is runtime-neutral and still required. | kept |
| `engine/tests/ir/test_base_script_item_path.py` | `RETIRE_LEGACY_INTERNAL` | Asserts live parent-chain path semantics from legacy `HierarchicalTemplate`; v38 scope parity is covered by core38 `admission_scope` tests. | retired (module skipped) |
| `engine/tests/ir/test_base_script_item_selectable.py` | `RETIRE_LEGACY_INTERNAL` | Depends on legacy `Entity.matches` selector internals and `ancestor_tags` scope gates; those contracts are retired for v38 parity. | retired (module skipped) |
| `engine/tests/ir/test_script_item_selection.py` | `RETIRE_LEGACY_INTERNAL` | Validates legacy criteria shape (`has_path` + `has_ancestor_tags`) rather than v38 template admission behavior. | retired (module skipped) |
| `engine/tests/ir/test_template_field_conversion.py` | `RETIRE_MOVED` | Front-end tree conversion (`visit_field` + implicit path inference) belongs to codec/compiler migration track, not core template parity. | retired (module skipped) |
| `engine/tests/ir/test_round_trip.py` | `RETIRE_MOVED` | YAML IR round-trip asserts legacy script shape; equivalent parity is already covered by core38 template compile/decompile/roundtrip tests. | retired (module skipped) |
| `engine/tests/ir/test_script_round_trip.py` | `RETIRE_REMOVED` | `ancestor_tags` serialization is no longer a v38 template feature; scope matching now maps to admission-scope semantics. | retired (module skipped) |
| `engine/tests/ir/{test_base_script_item.py,test_block_media_script.py,test_ir.py,test_role_setting_scripts.py,test_role_setting_shorthands.py,test_scene_block_templates.py}` | `KEEP_ADAPT` | These still validate active IR schema/shorthand/reference/media parsing contracts not duplicated by core38 template unit coverage. | kept |

### IR Coverage Hand-Off to `core38.template`
- Scope admission behavior (`path_pattern` parity lane) is covered by:
  - `engine/tests/core38/template/test_template.py::test_admitted_to_matches_scope_prefix`
  - `engine/tests/core38/template/test_template.py::test_admitted_to_non_wildcard_scope_requires_leaf_segment`
  - `engine/tests/core38/template/test_template.py::test_selector_can_filter_with_admitted_to`
- Template compile/decompile and round-trip behavior is covered by:
  - `engine/tests/core38/template/test_template.py::test_unstructure_structure_roundtrip`
  - `engine/tests/core38/template/test_template.py::test_template_group_decompile_roundtrip`
  - `engine/tests/core38/template/test_template.py::test_template_group_compile_yields_depth_first`

## IR Legacy-Only Triage Snapshot (2026-03-05 pass 4)
- Module-level skips added for legacy IR mechanics now covered by `core38.template` or moved to compiler/codec migration:
  - `engine/tests/ir/test_base_script_item_path.py`
  - `engine/tests/ir/test_base_script_item_selectable.py`
  - `engine/tests/ir/test_script_item_selection.py`
  - `engine/tests/ir/test_template_field_conversion.py`
  - `engine/tests/ir/test_round_trip.py`
  - `engine/tests/ir/test_script_round_trip.py`
- Validation runs:
  - Command: `poetry run pytest -q engine/tests/ir`
  - Result: `22 passed, 17 skipped, 1 xfailed`
  - Command: `poetry run pytest -q engine/tests --ignore=engine/tests/core --ignore=engine/tests/service --ignore=engine/tests/vm --ignore=engine/tests/story --maxfail=200`
  - Result: `1621 passed, 68 skipped, 9 xfailed`
  - Command: `TANGL_SHIM_CORE_DEFAULT=v38 TANGL_SHIM_VM_DEFAULT=v38 TANGL_SHIM_STORY_DEFAULT=v38 poetry run pytest -q engine/tests --ignore=engine/tests/core --ignore=engine/tests/service --ignore=engine/tests/vm --ignore=engine/tests/story --maxfail=200`
  - Result: `1621 passed, 68 skipped, 9 xfailed`

## Deferred Track: Media Planning (2026-03-04)
- Status: deferred by design for a dedicated follow-up track.
- Why deferred: loader/codec and IR ingestion are still evolving, and legacy media planning internals are not a stable parity target.
- Diagnostic policy now: keep skip-based diagnostics on legacy-coupled media integration tests (`engine/tests/integration/test_media_e2e.py`) while preserving stable system-media contracts (`engine/tests/integration/test_system_media_e2e.py`).
- Exit criteria for this deferred track:
  - vm38-native media planning/provision hook for media dependencies,
  - parity coverage for world-vs-system media resolution behavior,
  - service-layer dereference contract coverage for media URLs/content.

## Non-Retiring Blast Snapshot (2026-03-04)
- Validation run:
  - Command: `poetry run pytest -q engine/tests --ignore=engine/tests/core --ignore=engine/tests/service --ignore=engine/tests/vm --ignore=engine/tests/story --maxfail=200`
  - Result: `1640 passed, 48 skipped, 10 xfailed`
- Full-v38 toggle validation run (updated):
  - Command: `TANGL_SHIM_CORE_DEFAULT=v38 TANGL_SHIM_VM_DEFAULT=v38 TANGL_SHIM_STORY_DEFAULT=v38 poetry run pytest -q engine/tests --ignore=engine/tests/core --ignore=engine/tests/service --ignore=engine/tests/vm --ignore=engine/tests/story --maxfail=200`
  - Result: `1636 passed, 52 skipped, 10 xfailed`
- Additional bridge reductions validated in this run:
  - `engine/tests/persistence/test_ledger_persistence.py` exercises `tangl.vm38.Ledger` + `CheckpointRecord` directly.
  - `tangl.core.record.base_fragment.BaseFragment` now derives from `tangl.core38.Record` while keeping alias/serialization compatibility (`fragment_type`, `content`, `has_channel`).

## Vocabulary Migration Snapshot (2026-03-04 pass 3)
- `obj_cls -> kind` migration is now mechanically adopted in non-retiring mechanics/media callsites via compat wrappers (`kind` first, fallback to `obj_cls` where needed for mixed lanes).
- Persistence structuring now accepts `kind` (preferred) and legacy `obj_cls`, and emits both keys for cross-lane compatibility.
- Coverage added: `engine/tests/persistence/test_structuring_handler.py` validates `kind`/`obj_cls` dual support.
- Focused validation run:
  - Command: `TANGL_SHIM_CORE_DEFAULT=v38 TANGL_SHIM_VM_DEFAULT=v38 TANGL_SHIM_STORY_DEFAULT=v38 poetry run pytest -q engine/tests/mechanics/games/test_has_game.py engine/tests/mechanics/games/test_game_handlers.py engine/tests/mechanics/games/test_rps_integration.py engine/tests/media/test_system_media_integration.py engine/tests/persistence/test_structuring_handler.py`
  - Result: `25 passed, 2 skipped`

## VM Constructor Migration Snapshot (2026-03-04 pass 4)
- Active mechanics game callsites now use explicit capability checks instead of exception-driven compatibility branches.
  - Updated source/test adapters:
    - `engine/src/tangl/mechanics/games/has_game.py`
    - `engine/tests/mechanics/games/test_has_game.py`
    - `engine/tests/mechanics/games/test_game_handlers.py`
    - `engine/tests/mechanics/games/test_rps_integration.py`
- Focused validation run:
  - Command: `TANGL_SHIM_CORE_DEFAULT=v38 TANGL_SHIM_VM_DEFAULT=v38 TANGL_SHIM_STORY_DEFAULT=v38 poetry run pytest -q engine/tests/mechanics/games/test_has_game.py engine/tests/mechanics/games/test_game_handlers.py engine/tests/mechanics/games/test_rps_integration.py engine/tests/mechanics/games/test_step_turn_round.py`
  - Result: `33 passed`
- Full non-retiring lane remained stable:
  - Command: `TANGL_SHIM_CORE_DEFAULT=v38 TANGL_SHIM_VM_DEFAULT=v38 TANGL_SHIM_STORY_DEFAULT=v38 poetry run pytest -q engine/tests --ignore=engine/tests/core --ignore=engine/tests/service --ignore=engine/tests/vm --ignore=engine/tests/story --maxfail=200`
  - Result: `1636 passed, 52 skipped, 10 xfailed`
- Skip inventory check:
  - deferred/retired skip reasons are unchanged; no new trivial feature-gap regressions were introduced in this pass.

## Domain Registration + Persistence Snapshot (2026-03-04 pass 5)
- Domain class registration now accepts explicit core38 entity inheritance (recorded before shim package defaults were later flipped to v38):
  - `tangl.story.fabula.domain_manager._is_entity_subclass(...)` includes `tangl.core38.Entity`.
  - `load_domain_module(...)` excludes `Entity38` base types from registration.
- Domain facet now explicitly exposes dispatch authorities for runtime38 world authority cascades:
  - `tangl.story.fabula.domain_manager.DomainManager.get_authorities()` returns the domain `dispatch_registry`.
- Runtime38 loader coverage now authors domain classes against `tangl.core38.Entity` in active tests:
  - `engine/tests/loaders/test_world_loader.py::test_compile_anthology_runtime38_shares_world_facets`
  - `engine/tests/loaders/test_world_loader.py::test_compiler_adds_bundle_root_for_domain_imports`
  - `engine/tests/story38/test_story38_init.py::test_loader_compiler_runtime_38_path`
- Persistence vm38 vocabulary cleanup:
  - `engine/tests/persistence/test_ledger_persistence.py` now uses `Ledger.from_graph(...)` and `output_stream` assertions.
- Focused validation runs:
  - Command: `TANGL_SHIM_CORE_DEFAULT=v38 TANGL_SHIM_VM_DEFAULT=v38 TANGL_SHIM_STORY_DEFAULT=v38 poetry run pytest -q engine/tests/loaders/test_world_loader.py::test_compile_anthology_runtime38_shares_world_facets engine/tests/loaders/test_world_loader.py::test_compiler_adds_bundle_root_for_domain_imports`
  - Result: `2 passed`
  - Command: `poetry run pytest -q engine/tests/loaders/test_world_loader.py::test_compile_anthology_runtime38_shares_world_facets engine/tests/loaders/test_world_loader.py::test_compiler_adds_bundle_root_for_domain_imports`
  - Result: `2 passed` (verifies runtime38 domain registration without shim env overrides)
  - Coverage expansion:
    - loader runtime38 assertions now verify world authority exposure includes domain dispatch registry.
  - Command: `TANGL_SHIM_CORE_DEFAULT=v38 TANGL_SHIM_VM_DEFAULT=v38 TANGL_SHIM_STORY_DEFAULT=v38 poetry run pytest -q engine/tests/persistence/test_ledger_persistence.py`
  - Result: `14 passed, 8 skipped`
  - Command: `poetry run pytest -q engine/tests/story38/test_story38_init.py::test_loader_compiler_runtime_38_path`
  - Result: `1 passed`
- Full non-retiring lane remained stable:
  - Command: `TANGL_SHIM_CORE_DEFAULT=v38 TANGL_SHIM_VM_DEFAULT=v38 TANGL_SHIM_STORY_DEFAULT=v38 poetry run pytest -q engine/tests --ignore=engine/tests/core --ignore=engine/tests/service --ignore=engine/tests/vm --ignore=engine/tests/story --maxfail=200`
  - Result: `1636 passed, 52 skipped, 10 xfailed`

## VM/Story Surface Cleanup Snapshot (2026-03-04 pass 6)
- Mechanics game tests now run v38-native surfaces directly (core38/vm38/story38) with constructor-vocabulary compatibility branches removed:
  - `engine/tests/mechanics/games/test_has_game.py`
  - `engine/tests/mechanics/games/test_game_handlers.py`
  - `engine/tests/mechanics/games/test_rps_integration.py`
  - `engine/tests/mechanics/games/test_step_turn_round.py`
- Mechanics runtime sources aligned to v38 edge/action classes to avoid mixed-lane edge objects:
  - `engine/src/tangl/mechanics/games/has_game.py` uses `vm38.TraversableEdge`/`ResolutionPhase` in game-block edge wiring.
  - `engine/src/tangl/mechanics/games/handlers.py` provisions `story38.Action` edges.
- Runtime38 loader parity assertion expanded:
  - `engine/tests/story38/test_story38_init.py::test_loader_compiler_runtime_38_path` now asserts domain dispatch registry presence in `compiled.get_authorities()`.
- Deferred media planning now uses explicit module skip in `engine/tests/media/test_system_media_integration.py` (consistent with deferred-track policy).
- Focused validation run:
  - Command: `poetry run pytest -q engine/tests/mechanics/games/test_has_game.py engine/tests/mechanics/games/test_game_handlers.py engine/tests/mechanics/games/test_rps_integration.py engine/tests/mechanics/games/test_step_turn_round.py`
  - Result: `33 passed`
- Non-retiring blast validation:
  - Default lane: `1640 passed, 48 skipped, 10 xfailed`
  - Full-v38 lane: `1636 passed, 52 skipped, 10 xfailed`
- Remaining callsite inventory (current):
  - VM constructor/vocabulary: `2` active helper callsites (`frame._make_ctx()` in mechanics tests), `16` legacy callsites in skipped/deferred modules (`integration/*`, `media/*`, `test_game_journal_content.py`).
  - Domain registration/authority: `0` active blockers; `1` remaining legacy entity import callsite in skipped runtime37 loader fixture.
  - IR/template authoring: `1` core bridge file (`tangl.ir.core_ir.base_script_model` -> `HierarchicalTemplate`) plus associated IR tests; this remains the architectural migration tail.

## Remaining Shim Work (Primary)
- `core.factory` remains active in IR authoring models:
  - `engine/src/tangl/ir/core_ir/base_script_model.py` still subclasses legacy `HierarchicalTemplate`.
  - This is the largest remaining conceptual bridge until IR/template authoring migrates to `core38.template`/`TemplateRegistry`.
- Legacy matcher semantics still appear in retired/legacy-coupled tests:
  - `engine/tests/ir/test_base_script_item_selectable.py` continues to assert `matches(...)` internals (already classified retirement candidate).
- `core.domain` retirement status is on track:
  - no active non-retiring imports from `tangl.core.domain`;
  - `tangl.story.fabula.domain_manager` remains the intentional world-specific class/dispatch registry seam.

## Shim Switchboard (2026-03-04)
- Added env-driven symbol switches to compatibility shims:
  - `tangl.core`:
    - package default: `TANGL_SHIM_CORE_DEFAULT`
    - per symbol: `TANGL_SHIM_CORE_ENTITY|REGISTRY|GRAPHITEM|GRAPH|EDGE|SUBGRAPH|RECORD|SNAPSHOT|NODE`
  - `tangl.vm`:
    - package default: `TANGL_SHIM_VM_DEFAULT`
    - per symbol: `TANGL_SHIM_VM_BUILDRECEIPT|CHOICEEDGE|CONTEXT|FRAME|LEDGER|PLANNINGRECEIPT|RESOLUTIONPHASE`
  - `tangl.story`:
    - package default: `TANGL_SHIM_STORY_DEFAULT`
    - per symbol: `TANGL_SHIM_STORY_ACTION|BLOCK|SCENE|STORYGRAPH`
  - `tangl.service`:
    - package default: `TANGL_SHIM_SERVICE_DEFAULT`
    - per symbol: `TANGL_SHIM_SERVICE_APIENDPOINT|ORCHESTRATOR`
- Value semantics:
  - legacy: `legacy/old/0/false/off`
  - v38: `v38/new/1/true/on`
- Initial switchboard rollout kept package defaults unchanged; later cutover to v38 defaults is tracked under
  `Shim Default Cutover (2026-03-05)`.
- First canary cut:
  - Command: `TANGL_SHIM_STORY_BLOCK=v38 poetry run pytest ... --maxfail=20`
  - Result: `10 failed, 1629 passed, 46 skipped, 10 xfailed`
  - Signal: expected mixed-runtime breakage in mechanics/media paths that combine legacy story graph/runtime with a v38 block type.

### Service Switchboard Validation (2026-03-05)
- Added service switchboard in `tangl.service` for `ApiEndpoint` and `Orchestrator`.
- Active integration service smoke now imports v38 orchestrator directly (`engine/tests/integration/test_service_layer.py`),
  retiring dependence on shim-selected legacy service behavior.
- Retired `engine/tests/mechanics/games/test_game_journal_content.py` from parity gate as legacy story-dispatch internals.
- Non-retiring gate with service forced to v38:
  - Command: `TANGL_SHIM_SERVICE_DEFAULT=v38 poetry run pytest -q engine/tests --ignore=engine/tests/core --ignore=engine/tests/service --ignore=engine/tests/vm --ignore=engine/tests/story --maxfail=200`
  - Result: `1621 passed, 68 skipped, 9 xfailed`
- Full-v38 gate with service forced to v38:
  - Command: `TANGL_SHIM_CORE_DEFAULT=v38 TANGL_SHIM_VM_DEFAULT=v38 TANGL_SHIM_STORY_DEFAULT=v38 TANGL_SHIM_SERVICE_DEFAULT=v38 poetry run pytest -q engine/tests --ignore=engine/tests/core --ignore=engine/tests/service --ignore=engine/tests/vm --ignore=engine/tests/story --maxfail=200`
  - Result: `1621 passed, 68 skipped, 9 xfailed`
- Legacy canary (service default legacy):
  - Command: `TANGL_SHIM_SERVICE_DEFAULT=legacy poetry run pytest -q engine/tests --ignore=engine/tests/core --ignore=engine/tests/service --ignore=engine/tests/vm --ignore=engine/tests/story --maxfail=200`
  - Result: `1621 passed, 68 skipped, 9 xfailed`
  - Signal: no remaining non-retiring dependence on legacy `tangl.service.Orchestrator`.
- Per-symbol canaries (service default v38):
  - Command: `TANGL_SHIM_SERVICE_DEFAULT=v38 TANGL_SHIM_SERVICE_ORCHESTRATOR=legacy poetry run pytest -q engine/tests --ignore=engine/tests/core --ignore=engine/tests/service --ignore=engine/tests/vm --ignore=engine/tests/story --maxfail=200`
  - Result: `1621 passed, 68 skipped, 9 xfailed`
  - Command: `TANGL_SHIM_SERVICE_DEFAULT=v38 TANGL_SHIM_SERVICE_APIENDPOINT=legacy poetry run pytest -q engine/tests --ignore=engine/tests/core --ignore=engine/tests/service --ignore=engine/tests/vm --ignore=engine/tests/story --maxfail=200`
  - Result: `1621 passed, 68 skipped, 9 xfailed`

### Shim Default Cutover (2026-03-05)
- Compatibility package defaults now prefer v38 while preserving env overrides:
  - `tangl.core`: `_pick(..., default="v38")`
  - `tangl.vm`: `_pick(..., default="v38")`
  - `tangl.story`: `_pick(..., default="v38")`
- Validation:
  - Command: `poetry run pytest -q engine/tests --ignore=engine/tests/core --ignore=engine/tests/service --ignore=engine/tests/vm --ignore=engine/tests/story --maxfail=200`
  - Result: `1621 passed, 68 skipped, 9 xfailed`
  - Command: `TANGL_SHIM_CORE_DEFAULT=legacy TANGL_SHIM_VM_DEFAULT=legacy TANGL_SHIM_STORY_DEFAULT=legacy TANGL_SHIM_SERVICE_DEFAULT=legacy poetry run pytest -q engine/tests --ignore=engine/tests/core --ignore=engine/tests/service --ignore=engine/tests/vm --ignore=engine/tests/story --maxfail=200`
  - Result: `1621 passed, 68 skipped, 9 xfailed`

### Switchboard Deep-Dive (2026-03-04)
- Toggle matrix against the same non-retiring gate:
  - `TANGL_SHIM_CORE_DEFAULT=v38 TANGL_SHIM_VM_DEFAULT=legacy TANGL_SHIM_STORY_DEFAULT=legacy`
    - Result: `23 failed, 1616 passed, 46 skipped, 10 xfailed`
    - Fail clusters: `ir` (`6`), `loaders` (`2`), `story38` (`15`)
  - `TANGL_SHIM_CORE_DEFAULT=legacy TANGL_SHIM_VM_DEFAULT=v38 TANGL_SHIM_STORY_DEFAULT=legacy`
    - Result: `35 failed, 1604 passed, 46 skipped, 10 xfailed`
    - Fail clusters: `mechanics/games` (`33`), `media` (`2`)
  - `TANGL_SHIM_CORE_DEFAULT=v38 TANGL_SHIM_VM_DEFAULT=legacy TANGL_SHIM_STORY_DEFAULT=v38`
    - Result: `34 failed, 1605 passed, 46 skipped, 10 xfailed`
    - Fail clusters: core-only set + mixed story/runtime mechanics/media (`11`)
  - `TANGL_SHIM_CORE_DEFAULT=v38 TANGL_SHIM_VM_DEFAULT=v38 TANGL_SHIM_STORY_DEFAULT=v38`
    - Result: `58 failed, 1581 passed, 46 skipped, 10 xfailed`

- First-cause signatures:
  - Core-v38 only:
    - Legacy type anchoring in template/fabula stack:
      - `tangl.core.factory.template` validates `obj_cls` against legacy `tangl.core.entity.Entity`.
      - `tangl.story.fabula.domain_manager` registers only subclasses of legacy `Entity`.
    - Strict selector typing in legacy `Selectable.matches(selector=...)` rejects core38 graph items.
  - VM-v38 only:
    - Constructor/shape drift:
      - `Frame(graph=..., cursor_id=...)` (legacy) vs vm38 expects `Frame(graph=..., cursor=...)`.
      - `Ledger(..., records=StreamRegistry())` (legacy) vs vm38 expects core38-shaped graph/output stream.
  - Core+Story mixed with legacy VM:
    - Mixed-runtime dispatch drift (legacy VM planning/journal phases with v38 story/core call sites) causes handler non-selection and empty/None journal/update outputs.

- Classification outcome for current failing set:
  - `MECHANICAL_ADAPT` (majority):
    - Update call sites/helpers to vm38 constructor and payload vocabulary.
    - Replace legacy hard imports (`tangl.core.entity`, `tangl.core.graph.*`) in bridging layers with shim-safe imports.
    - Relax/translate legacy selector typing to accept core38 entities or translate to `core38.Selector`.
  - `REQUIRED_BRIDGE_FIX`:
    - Domain class/module loading in runtime38 paths must accept classes deriving from shimmed/v38 entity types.
  - `RETIRE_CANDIDATE`:
    - Any remaining assertions that require exact legacy `obj_cls` export strings or legacy internal MRO shape (not observable in v38 contracts).

## Inventory Snapshot
- Total in-scope legacy modules: `128`
- By feature area:
  - `core`: 15
  - `vm`: 41
  - `story`: 56
  - `service`: 16
- By disposition:
  - `PORT_DIRECT`: 16
  - `PORT_ADAPT`: 72
  - `RETIRE_REMOVED`: 24
  - `RETIRE_MOVED`: 12
  - `RETIRE_IRRELEVANT`: 4
- By risk level:
  - `low`: 20
  - `medium`: 57
  - `high`: 51

## Disposition Legend
- `PORT_DIRECT`: same behavior intent, mostly namespace/type rename.
- `PORT_ADAPT`: behavior intent retained, assertions must be rewritten for v38 contracts.
- `RETIRE_REMOVED`: intentionally removed from v38 behavior.
- `RETIRE_MOVED`: concern moved out of this in-scope parity effort.
- `RETIRE_IRRELEVANT`: no meaningful mapping to v38 architecture.

## Target Resolution Status (PORT rows)
- `PORT_*` rows: `88`
- Missing `target_v38_test_path`: `0`
- Unique target modules: `36`
  - Existing targets: `36`
  - Planned targets: `0`

Planned target modules referenced by `PORT_*` rows:
- None.

## Current Port Coverage Snapshot (2026-03-03)
- `PORT_*` rows with existing target tests: `88 / 88` (`100.0%`)
- By feature area:
  - `core`: `13 / 13`
  - `vm`: `30 / 30`
  - `story`: `33 / 33`
  - `service`: `12 / 12`
- Remaining `PORT_*` gaps:
  - None.
- Validation run:
  - Command: `poetry run pytest -q engine/tests/core38 engine/tests/vm38 engine/tests/story38 engine/tests/service38`
  - Result: `909 passed, 11 warnings`

## Legacy vs V38 Surface Audit (2026-03-03)
- Scope-completeness check:
  - In-scope legacy test modules discovered under scope lock: `128`
  - Matrix rows: `128` (unique legacy paths: `128`)
  - Missing rows: `0`; duplicate rows: `0`
- Surface comparison snapshot (package/module level, implementation-facing):
  - `core` modules: `36` → `core38` modules: `15` (name-overlap modules: `8`)
  - `vm` modules: `40` → `vm38` modules: `25` (name-overlap modules: `11`)
  - `story` modules: `38` → `story38` modules: `23` (name-overlap modules: `12`)
  - `service` modules: `25` → `service38` modules: `14` (name-overlap modules: `6`)
- Interpretation:
  - Lower direct module-name overlap is expected from v38 consolidation/refactoring (trait split, phase-driven VM runtime, service gateway/adapter model).
  - Parity remains test-intent based; non-overlap modules are represented through `PORT_ADAPT`/`RETIRE_*` dispositions rather than 1:1 module renames.
- Audit delta found during this pass:
  - Added previously missing in-scope service rows (all `PORT_DIRECT`): `test_auth38.py`, `test_operations38.py`, `test_rest_adapter38.py`.

## Classification Matrix
| legacy_test_path | feature_area | disposition | target_v38_test_path | v38_feature_anchor | rationale | risk_level | status |
|---|---|---|---|---|---|---|---|
| engine/tests/core/behavior/test_behavior.py | core | PORT_ADAPT | engine/tests/core38/behavior/test_behavior.py | tangl.core38.behavior.BehaviorRegistry.chain_execute | Behavior chaining remains core functionality but aggregation and naming contracts changed in core38. | low | mapped |
| engine/tests/core/dispatch/test_hooked_reg.py | core | RETIRE_REMOVED |  | tangl.core38.dispatch.dispatch | v38 removed HookedRegistry-specific behavior wrappers and consolidated lifecycle hooks into the core38 dispatch registry. | medium | mapped |
| engine/tests/core/entity/test_entity.py | core | PORT_ADAPT | engine/tests/core38/entity/test_entity.py | tangl.core38.entity.Entity.structure | Entity identity and structuring behavior is retained with core38 trait composition and updated dispatch context semantics. | low | mapped |
| engine/tests/core/entity/test_structuring.py | core | PORT_ADAPT | engine/tests/core38/entity/test_entity.py | tangl.core38.entity.Entity.structure | Entity identity and structuring behavior is retained with core38 trait composition and updated dispatch context semantics. | low | mapped |
| engine/tests/core/factory/test_templates.py | core | PORT_ADAPT | engine/tests/core38/template/test_template.py | tangl.core38.template.TemplateRegistry | Legacy template factory concerns map to core38 template registry/materialization contracts with renamed APIs. | medium | mapped |
| engine/tests/core/factory/test_token_factory.py | core | PORT_ADAPT | engine/tests/core38/token/test_token.py | tangl.core38.token.TokenFactory | Token factory coverage remains relevant but should assert core38 wrapper behavior and singleton delegation semantics. | medium | mapped |
| engine/tests/core/graph/test_edge.py | core | PORT_ADAPT | engine/tests/core38/graph/test_graph.py | tangl.core38.graph.Graph | Graph topology behavior persists in v38 with consolidated graph item types and updated endpoint naming. | low | mapped |
| engine/tests/core/graph/test_graph.py | core | PORT_ADAPT | engine/tests/core38/graph/test_graph.py | tangl.core38.graph.Graph | Graph topology behavior persists in v38 with consolidated graph item types and updated endpoint naming. | low | mapped |
| engine/tests/core/graph/test_node.py | core | PORT_ADAPT | engine/tests/core38/graph/test_graph.py | tangl.core38.graph.Graph | Graph topology behavior persists in v38 with consolidated graph item types and updated endpoint naming. | low | mapped |
| engine/tests/core/graph/test_token_37.py | core | PORT_ADAPT | engine/tests/core38/token/test_token.py | tangl.core38.token.Token | Graph token behavior is still needed but should follow the v38 token wrapper model instead of v37 token-node conventions. | medium | mapped |
| engine/tests/core/record/test_content_addressable.py | core | RETIRE_REMOVED |  | tangl.core38.record.Record.get_hashable_content | v38 no longer carries a standalone ContentAddressable model and folds content hashing semantics into core38 record/entity traits. | low | mapped |
| engine/tests/core/record/test_record_stream.py | core | PORT_ADAPT | engine/tests/core38/record/test_record.py | tangl.core38.record.OrderedRegistry | Record stream behaviors continue via core38 ordered registry with different naming and slice/query helpers. | low | mapped |
| engine/tests/core/registry/test_registry.py | core | PORT_DIRECT | engine/tests/core38/registry/test_registry.py | tangl.core38.registry.Registry | Registry CRUD and selection semantics remain first-class in core38 with directly comparable contracts. | low | mapped |
| engine/tests/core/registry/test_selection.py | core | PORT_ADAPT | engine/tests/core38/selector/test_selector.py | tangl.core38.selector.Selector.matches | Selection remains in scope but moved to explicit Selector-driven matching rather than legacy inline matcher assumptions. | low | mapped |
| engine/tests/core/singleton/test_singleton.py | core | PORT_DIRECT | engine/tests/core38/singleton/test_singleton.py | tangl.core38.singleton.Singleton | Singleton uniqueness and inheritance semantics still exist in core38 and should remain gated directly. | low | mapped |
| engine/tests/service/controllers/test_runtime_controller.py | service | PORT_ADAPT | engine/tests/service38/controllers/test_runtime_controller.py | tangl.service.controllers.runtime_controller.RuntimeController.create_story38 | Runtime controller lifecycle checks remain needed but should target the v38 runtime endpoint set only. | high | mapped |
| engine/tests/service/controllers/test_runtime_controller38.py | service | PORT_DIRECT | engine/tests/service/controllers/test_runtime_controller38.py | tangl.service.controllers.runtime_controller.RuntimeController.resolve_choice38 | This suite already validates v38 runtime-controller flows and should be retained as direct parity coverage. | low | mapped |
| engine/tests/service/controllers/test_runtime_controller_media.py | service | RETIRE_MOVED |  | tangl.story38.fragments.MediaFragment | Runtime media controller behavior is outside the in-scope service38/story38 parity gate and remains demoted for a later media-focused track. | medium | mapped |
| engine/tests/service/controllers/test_user_controller.py | service | PORT_ADAPT | engine/tests/service38/controllers/test_user_controller.py | tangl.service.controllers.user_controller.UserController | User endpoint behavior stays in scope but should be asserted through the service38 gateway/orchestrator flow. | medium | mapped |
| engine/tests/service/response/test_exports.py | service | PORT_ADAPT | engine/tests/service38/response/test_exports.py | tangl.service38.__all__ | Export contract checks should move to service38 package exports and operation/gateway surface. | medium | mapped |
| engine/tests/service/response/test_info_models.py | service | RETIRE_REMOVED |  | tangl.service38.gateway.ServiceGateway38.execute | Legacy native response/info model contracts are superseded by service38 gateway operation and runtime-envelope contracts. | high | mapped |
| engine/tests/service/response/test_native_response.py | service | RETIRE_REMOVED |  | tangl.service38.gateway.ServiceGateway38.execute | Legacy native response/info model contracts are superseded by service38 gateway operation and runtime-envelope contracts. | high | mapped |
| engine/tests/service/response/test_runtime38_response.py | service | PORT_DIRECT | engine/tests/service/response/test_runtime38_response.py | tangl.service.response.RuntimeEnvelope38 | RuntimeEnvelope38 is already v38-specific and should remain as direct transport contract coverage. | low | mapped |
| engine/tests/service/test_api_endpoints.py | service | PORT_ADAPT | engine/tests/service38/test_api_endpoint.py | tangl.service38.api_endpoint.ApiEndpoint38.annotate | Endpoint annotation metadata remains required but should validate service38 policy-aware endpoint wrappers. | medium | mapped |
| engine/tests/service/test_auth38.py | service | PORT_DIRECT | engine/tests/service/test_auth38.py | tangl.service38.auth.user_id_by_key | API-key auth resolution and access-level mapping are already v38-specific and should remain direct parity coverage. | medium | mapped |
| engine/tests/service/test_operations38.py | service | PORT_DIRECT | engine/tests/service/test_operations38.py | tangl.service38.operations.endpoint_for_operation | Operation-to-endpoint routing and bootstrap registration are already encoded as service38 contracts and should stay directly gated. | low | mapped |
| engine/tests/service/test_orchestrator.py | service | PORT_ADAPT | engine/tests/service38/test_orchestrator.py | tangl.service38.orchestrator.Orchestrator38.execute | Orchestrator behavior remains core but should be validated against service38 hydration, policy, and writeback semantics. | high | mapped |
| engine/tests/service/test_orchestrator38.py | service | PORT_DIRECT | engine/tests/service/test_orchestrator38.py | tangl.service38.orchestrator.Orchestrator38 | This suite already targets service38 orchestrator behavior and should stay as direct parity evidence. | low | mapped |
| engine/tests/service/test_orchestrator_basic.py | service | PORT_ADAPT | engine/tests/service38/test_orchestrator.py | tangl.service38.orchestrator.Orchestrator38.execute | Orchestrator behavior remains core but should be validated against service38 hydration, policy, and writeback semantics. | high | mapped |
| engine/tests/service/test_response_contract.py | service | RETIRE_REMOVED |  | tangl.service38.gateway.ServiceGateway38.execute | Legacy native response/info model contracts are superseded by service38 gateway operation and runtime-envelope contracts. | high | mapped |
| engine/tests/service/test_rest_adapter38.py | service | PORT_DIRECT | engine/tests/service/test_rest_adapter38.py | tangl.service38.rest_adapter.GatewayRestAdapter38.execute_operation | Transport adapter request/auth forwarding is already service38-native behavior and should remain direct parity coverage. | medium | mapped |
| engine/tests/story/asset/test_asset_bag.py | story | RETIRE_MOVED |  | tangl.story38.fabula.StoryMaterializer38 | Legacy story-level asset workflows are demoted from in-scope v38 parity and moved outside the core refactor gate. | medium | mapped |
| engine/tests/story/asset/test_asset_manager2.py | story | RETIRE_MOVED |  | tangl.story38.fabula.StoryMaterializer38 | Legacy story-level asset workflows are demoted from in-scope v38 parity and moved outside the core refactor gate. | medium | mapped |
| engine/tests/story/asset/test_asset_wallet.py | story | RETIRE_MOVED |  | tangl.story38.fabula.StoryMaterializer38 | Legacy story-level asset workflows are demoted from in-scope v38 parity and moved outside the core refactor gate. | medium | mapped |
| engine/tests/story/asset/test_countable_asset.py | story | RETIRE_MOVED |  | tangl.story38.fabula.StoryMaterializer38 | Legacy story-level asset workflows are demoted from in-scope v38 parity and moved outside the core refactor gate. | medium | mapped |
| engine/tests/story/asset/test_discrete_asset.py | story | RETIRE_MOVED |  | tangl.story38.fabula.StoryMaterializer38 | Legacy story-level asset workflows are demoted from in-scope v38 parity and moved outside the core refactor gate. | medium | mapped |
| engine/tests/story/concepts/test_actor.py | story | PORT_ADAPT | engine/tests/story38/test_story38_init.py | tangl.story38.concepts.Actor | Concept entity coverage remains necessary but should validate story38 concept contracts and wiring semantics. | medium | mapped |
| engine/tests/story/concepts/test_concept.py | story | PORT_ADAPT | engine/tests/story38/test_story38_init.py | tangl.story38.concepts.Actor | Concept entity coverage remains necessary but should validate story38 concept contracts and wiring semantics. | medium | mapped |
| engine/tests/story/concepts/test_location.py | story | PORT_ADAPT | engine/tests/story38/test_story38_init.py | tangl.story38.concepts.Actor | Concept entity coverage remains necessary but should validate story38 concept contracts and wiring semantics. | medium | mapped |
| engine/tests/story/discourse/test_dialog_handler.py | story | RETIRE_MOVED |  | tangl.story38.system_handlers.render_block | Dialog microblock discourse parsing is currently out of scope and not part of the story38 core parity target. | medium | mapped |
| engine/tests/story/episode/test_action.py | story | PORT_ADAPT | engine/tests/story38/test_system_handlers.py | tangl.story38.episode.Action | Action choice rendering remains in scope with story38 choice fragment fields and vm38 trigger-phase semantics. | medium | mapped |
| engine/tests/story/episode/test_block.py | story | PORT_ADAPT | engine/tests/story38/test_system_handlers.py | tangl.story38.system_handlers.render_block | Block journaling behavior remains needed but is implemented via story38 journal handlers and fragment records. | high | mapped |
| engine/tests/story/episode/test_block_dialog.py | story | RETIRE_MOVED |  | tangl.story38.system_handlers.render_block | Dialog-specific block rendering is out of scope for the current v38 story/runtime parity effort. | medium | mapped |
| engine/tests/story/episode/test_block_journal_concepts.py | story | PORT_ADAPT | engine/tests/story38/test_system_handlers.py | tangl.story38.system_handlers.render_block | Block journaling behavior remains needed but is implemented via story38 journal handlers and fragment records. | high | mapped |
| engine/tests/story/episode/test_block_journal_order.py | story | PORT_ADAPT | engine/tests/story38/test_journal_order.py | tangl.story38.system_handlers.render_block | Fragment ordering guarantees should be retained with story38 handlers but require updated order assertions. | high | mapped |
| engine/tests/story/episode/test_block_journal_pipeline.py | story | PORT_ADAPT | engine/tests/story38/test_system_handlers.py | tangl.story38.system_handlers.render_block | Block journaling behavior remains needed but is implemented via story38 journal handlers and fragment records. | high | mapped |
| engine/tests/story/episode/test_block_media_dependencies.py | story | RETIRE_MOVED |  | tangl.story38.fragments.MediaFragment | Media dependency/journal wiring is demoted from this in-scope story38 parity phase. | medium | mapped |
| engine/tests/story/episode/test_block_media_journal.py | story | RETIRE_MOVED |  | tangl.story38.fragments.MediaFragment | Media dependency/journal wiring is demoted from this in-scope story38 parity phase. | medium | mapped |
| engine/tests/story/episode/test_block_post_process.py | story | RETIRE_REMOVED |  | tangl.story38.system_handlers.render_block | Legacy post-process content pipeline layers were removed in favor of direct story38 render handler output. | medium | mapped |
| engine/tests/story/episode/test_deps_in_ns.py | story | PORT_ADAPT | engine/tests/story38/test_system_handlers.py | tangl.vm38.system_handlers.contribute_satisfied_deps | Dependency projection into namespace remains relevant and should be verified through vm38/story38 handler integration. | high | mapped |
| engine/tests/story/episode/test_menu_block.py | story | RETIRE_REMOVED |  | tangl.story38.episode.Block | MenuBlock dynamic provisioning semantics were intentionally dropped from story38 node vocabulary. | high | mapped |
| engine/tests/story/episode/test_scene.py | story | PORT_ADAPT | engine/tests/story38/test_story38_init.py | tangl.story38.episode.Scene.finalize_container_contract | Scene container/source-sink behavior remains required and should align to story38 scene finalization contracts. | medium | mapped |
| engine/tests/story/fabula/test_asset_manager.py | story | RETIRE_MOVED |  | tangl.story38.fabula.StoryCompiler38 | Fabula asset manager behavior is out of the in-scope story38 parity set and will be handled separately if revived. | medium | mapped |
| engine/tests/story/fabula/test_custom_world_handlers.py | story | PORT_ADAPT | engine/tests/story38/test_story38_init.py | tangl.story38.story_graph.StoryGraph38.get_authorities | Custom world authority registration remains relevant via story38 graph authority composition. | medium | mapped |
| engine/tests/story/fabula/test_managers.py | story | RETIRE_REMOVED |  | tangl.story38.fabula.StoryCompiler38.compile | Script/domain manager orchestration was replaced by story38 compiler+materializer bundle flow. | high | mapped |
| engine/tests/story/fabula/test_materialize_dispatch.py | story | RETIRE_REMOVED |  | tangl.story38.fabula.StoryMaterializer38.create_story | Legacy materialize dispatch task buses were removed and replaced by explicit story38 materialization passes. | high | mapped |
| engine/tests/story/fabula/test_phase2_revision.py | story | RETIRE_IRRELEVANT |  | tangl.story38.fabula.InitMode | Legacy phased revision milestones no longer map to the story38 initialization model. | medium | mapped |
| engine/tests/story/fabula/test_role_resolution_integration.py | story | PORT_DIRECT | engine/tests/story38/test_story38_init.py | tangl.story38.fabula.StoryMaterializer38._wire_dependencies_for_specs | Role/setting dependency wiring is a direct story38 materializer responsibility and should stay gated. | medium | mapped |
| engine/tests/story/fabula/test_role_setting_wiring.py | story | PORT_DIRECT | engine/tests/story38/test_story38_init.py | tangl.story38.fabula.StoryMaterializer38._wire_dependencies_for_specs | Role/setting dependency wiring is a direct story38 materializer responsibility and should stay gated. | medium | mapped |
| engine/tests/story/fabula/test_role_wiring_modes.py | story | PORT_DIRECT | engine/tests/story38/test_story38_init.py | tangl.story38.fabula.StoryMaterializer38._wire_dependencies_for_specs | Role/setting dependency wiring is a direct story38 materializer responsibility and should stay gated. | medium | mapped |
| engine/tests/story/fabula/test_script_manager.py | story | RETIRE_REMOVED |  | tangl.story38.fabula.StoryCompiler38.compile | ScriptManager APIs were retired in story38 and replaced by compiler normalization over StoryScript payloads. | high | mapped |
| engine/tests/story/fabula/test_script_manager_anchored_lookup.py | story | RETIRE_REMOVED |  | tangl.story38.fabula.StoryCompiler38.compile | ScriptManager APIs were retired in story38 and replaced by compiler normalization over StoryScript payloads. | high | mapped |
| engine/tests/story/fabula/test_script_manager_helpers.py | story | RETIRE_REMOVED |  | tangl.story38.fabula.StoryCompiler38.compile | ScriptManager APIs were retired in story38 and replaced by compiler normalization over StoryScript payloads. | high | mapped |
| engine/tests/story/fabula/test_script_manager_scope_rank.py | story | RETIRE_REMOVED |  | tangl.story38.fabula.StoryCompiler38.compile | ScriptManager APIs were retired in story38 and replaced by compiler normalization over StoryScript payloads. | high | mapped |
| engine/tests/story/fabula/test_story_graph.py | story | PORT_ADAPT | engine/tests/story38/test_story38_init.py | tangl.story38.story_graph.StoryGraph38 | Story graph contracts remain relevant with updated authority/template scope helpers in story38. | medium | mapped |
| engine/tests/story/fabula/test_story_script_model_rebuild.py | story | PORT_ADAPT | engine/tests/story38/test_story38_init.py | tangl.story38.fabula.StoryCompiler38.compile | Script model rebuild intent remains useful but should assert story38 compiler model validation and bundle output. | medium | mapped |
| engine/tests/story/fabula/test_template_factory_integration.py | story | PORT_ADAPT | engine/tests/story38/test_story38_init.py | tangl.story38.fabula.StoryTemplateBundle.template_registry | Template registry integration remains needed with story38 template bundles and materializer lineage mapping. | medium | mapped |
| engine/tests/story/fabula/test_template_registry.py | story | PORT_ADAPT | engine/tests/story38/test_story38_init.py | tangl.story38.fabula.StoryTemplateBundle.template_registry | Template registry integration remains needed with story38 template bundles and materializer lineage mapping. | medium | mapped |
| engine/tests/story/fabula/test_world_ensure_scope.py | story | PORT_ADAPT | engine/tests/story38/test_story38_init.py | tangl.story38.fabula.StoryMaterializer38.create_story | World initialization/materialization boundaries remain essential and should be asserted against story38 world entrypoints. | high | mapped |
| engine/tests/story/fabula/test_world_materialization.py | story | PORT_ADAPT | engine/tests/story38/test_story38_init.py | tangl.story38.fabula.StoryMaterializer38.create_story | World initialization/materialization boundaries remain essential and should be asserted against story38 world entrypoints. | high | mapped |
| engine/tests/story/fabula/test_world_vm_boundary.py | story | PORT_ADAPT | engine/tests/story38/test_story38_init.py | tangl.story38.fabula.StoryMaterializer38.create_story | World initialization/materialization boundaries remain essential and should be asserted against story38 world entrypoints. | high | mapped |
| engine/tests/story/test_branching_playthrough.py | story | PORT_ADAPT | engine/tests/story38/test_traversal_playthrough.py | tangl.vm38.runtime.ledger.Ledger.resolve_choice | Playthrough behavior is still required but must run through story38 world + vm38 ledger traversal. | high | mapped |
| engine/tests/story/test_complex_conditions.py | story | PORT_ADAPT | engine/tests/story38/test_choice_availability.py | tangl.story38.system_handlers._choice_unavailable_reason | Condition and gating assertions remain important but should target story38 choice availability and blocker diagnostics. | high | mapped |
| engine/tests/story/test_concept_gating.py | story | PORT_ADAPT | engine/tests/story38/test_choice_availability.py | tangl.story38.system_handlers._choice_unavailable_reason | Condition and gating assertions remain important but should target story38 choice availability and blocker diagnostics. | high | mapped |
| engine/tests/story/test_demo_script.py | story | PORT_ADAPT | engine/tests/story38/test_story38_init.py | tangl.story38.fabula.World38.from_script_data | Script-to-world compilation remains relevant and should validate story38 bundle/compiler/materializer flow. | medium | mapped |
| engine/tests/story/test_full_world_factory.py | story | PORT_ADAPT | engine/tests/story38/test_story38_init.py | tangl.story38.fabula.World38.from_script_data | Script-to-world compilation remains relevant and should validate story38 bundle/compiler/materializer flow. | medium | mapped |
| engine/tests/story/test_lazy_provisioning_integration.py | story | RETIRE_REMOVED |  | tangl.story38.fabula.InitMode | Legacy lazy world/provisioning mode is intentionally absent from story38 initialization modes. | high | mapped |
| engine/tests/story/test_lazy_world.py | story | RETIRE_REMOVED |  | tangl.story38.fabula.InitMode | Legacy lazy world/provisioning mode is intentionally absent from story38 initialization modes. | high | mapped |
| engine/tests/story/test_phase4_integration.py | story | RETIRE_IRRELEVANT |  | tangl.story38.fabula.StoryInitResult | Legacy phase-tier milestone tests do not align with the simplified story38 initialization/reporting model. | medium | mapped |
| engine/tests/story/test_role_provisioning.py | story | PORT_ADAPT | engine/tests/story38/test_story38_init.py | tangl.story38.fabula.StoryMaterializer38._prelink_all_dependencies | Role provisioning behavior remains in scope but should assert story38 dependency prelinking outcomes. | medium | mapped |
| engine/tests/story/test_role_provisioning2.py | story | PORT_ADAPT | engine/tests/story38/test_story38_init.py | tangl.story38.fabula.StoryMaterializer38._prelink_all_dependencies | Role provisioning behavior remains in scope but should assert story38 dependency prelinking outcomes. | medium | mapped |
| engine/tests/story/test_script_to_graph_integration.py | story | PORT_ADAPT | engine/tests/story38/test_story38_init.py | tangl.story38.fabula.World38.from_script_data | Script-to-world compilation remains relevant and should validate story38 bundle/compiler/materializer flow. | medium | mapped |
| engine/tests/story/test_simple_story.py | story | PORT_ADAPT | engine/tests/story38/test_traversal_playthrough.py | tangl.vm38.runtime.ledger.Ledger.resolve_choice | Playthrough behavior is still required but must run through story38 world + vm38 ledger traversal. | high | mapped |
| engine/tests/story/test_story_state_conditions.py | story | PORT_ADAPT | engine/tests/story38/test_choice_availability.py | tangl.story38.system_handlers._choice_unavailable_reason | Condition and gating assertions remain important but should target story38 choice availability and blocker diagnostics. | high | mapped |
| engine/tests/story/test_template_provisioner_scope.py | story | PORT_ADAPT | engine/tests/story38/test_compiler_scope_resolution.py | tangl.story38.story_graph.StoryGraph38.get_template_scope_groups | Template scope ranking remains relevant but now depends on story38 template lineage and scope group APIs. | high | mapped |
| engine/tests/story/test_tier2_integration.py | story | RETIRE_IRRELEVANT |  | tangl.story38.fabula.StoryInitResult | Legacy phase-tier milestone tests do not align with the simplified story38 initialization/reporting model. | medium | mapped |
| engine/tests/story/test_world_template_registry.py | story | PORT_ADAPT | engine/tests/story38/test_compiler_scope_resolution.py | tangl.story38.story_graph.StoryGraph38.get_template_scope_groups | Template scope ranking remains relevant but now depends on story38 template lineage and scope group APIs. | high | mapped |
| engine/tests/vm/context/test_materialization_context.py | vm | RETIRE_REMOVED |  | tangl.story38.fabula.StoryMaterializer38.create_story | Legacy MaterializationContext was removed and story initialization now uses story38 compiler/materializer orchestration. | high | mapped |
| engine/tests/vm/dispatch/test_materialize_task.py | vm | RETIRE_REMOVED |  | tangl.story38.fabula.StoryMaterializer38._materialize_one | MaterializeTask phase bus hooks were removed in favor of direct story38 materializer passes. | high | mapped |
| engine/tests/vm/dispatch/test_namespace_concepts.py | vm | PORT_ADAPT | engine/tests/vm38/test_system_handlers.py | tangl.vm38.system_handlers.contribute_satisfied_deps | Namespace concept projection still matters but is now provided by vm38 gather_ns handlers and phase context. | medium | mapped |
| engine/tests/vm/events/test_event_canonicalize.py | vm | RETIRE_REMOVED |  | tangl.vm38.replay.DiffReplayEngine.build_delta | Event canonicalization from the legacy watcher stack is intentionally removed from the vm38 diff-replay MVP architecture. | medium | mapped |
| engine/tests/vm/events/test_events.py | vm | PORT_ADAPT | engine/tests/vm38/test_replay_mvp.py | tangl.vm38.replay.Event.apply | Replay event CRUD remains in scope but should target vm38 patch/event contracts instead of watcher-backed streams. | medium | mapped |
| engine/tests/vm/events/test_snapshot.py | vm | PORT_ADAPT | engine/tests/vm38/test_ledger.py | tangl.vm38.runtime.ledger.Ledger.save_snapshot | Snapshot/restore behavior persists in vm38 through ledger checkpoints rather than legacy snapshot stream conventions. | medium | mapped |
| engine/tests/vm/events/test_watched.py | vm | RETIRE_REMOVED |  | tangl.vm38.replay.DiffReplayEngine | Watched proxy/observer event sourcing was explicitly deprecated by vm38 in favor of simpler incremental graph diff deltas. | high | mapped |
| engine/tests/vm/planning/test_offer_pipeline.py | vm | PORT_ADAPT | engine/tests/vm38/test_provision_pipeline.py | tangl.vm38.dispatch.do_provision | Planning pipeline behavior remains required but vm38 uses side-effect provisioning hooks with updated offer/resolver contracts. | high | mapped |
| engine/tests/vm/planning/test_planning_flow.py | vm | PORT_ADAPT | engine/tests/vm38/test_provision_pipeline.py | tangl.vm38.dispatch.do_provision | Planning pipeline behavior remains required but vm38 uses side-effect provisioning hooks with updated offer/resolver contracts. | high | mapped |
| engine/tests/vm/planning/test_planning_integration.py | vm | PORT_ADAPT | engine/tests/vm38/test_provision_pipeline.py | tangl.vm38.dispatch.do_provision | Planning pipeline behavior remains required but vm38 uses side-effect provisioning hooks with updated offer/resolver contracts. | high | mapped |
| engine/tests/vm/planning/test_planning_receipt.py | vm | RETIRE_REMOVED |  | tangl.vm38.resolution_phase.ResolutionPhase.PLANNING | Planning receipt aggregation was removed because vm38 planning handlers are side-effect-only and return no aggregated receipt. | medium | mapped |
| engine/tests/vm/planning/test_planning_refactored.py | vm | PORT_ADAPT | engine/tests/vm38/test_provision_pipeline.py | tangl.vm38.dispatch.do_provision | Planning pipeline behavior remains required but vm38 uses side-effect provisioning hooks with updated offer/resolver contracts. | high | mapped |
| engine/tests/vm/planning/test_reqs_in_ns.py | vm | PORT_ADAPT | engine/tests/vm38/test_system_handlers.py | tangl.vm38.system_handlers.contribute_satisfied_deps | Requirement-to-namespace visibility is still needed and should be asserted through vm38 namespace contributor handlers. | medium | mapped |
| engine/tests/vm/provision/test_asset_provisioner.py | vm | RETIRE_MOVED |  | tangl.story38.system_handlers.render_block | Asset/media-specific provisioners are out of current scope and demoted from the v38 parity gate. | medium | mapped |
| engine/tests/vm/provision/test_build_receipt_provenance.py | vm | RETIRE_REMOVED |  | tangl.vm38.provision.Resolver.resolve_dependency | Build/provenance receipts were removed from vm38 provisioning in favor of direct resolver decisions and replay deltas. | high | mapped |
| engine/tests/vm/provision/test_provision_int1.py | vm | PORT_ADAPT | engine/tests/vm38/test_provision_pipeline.py | tangl.vm38.provision.Resolver.resolve_dependency | Provision integration coverage remains critical but must target vm38 resolver/policy behavior and new provisioning entry points. | high | mapped |
| engine/tests/vm/provision/test_provision_int2.py | vm | PORT_ADAPT | engine/tests/vm38/test_provision_pipeline.py | tangl.vm38.provision.Resolver.resolve_dependency | Provision integration coverage remains critical but must target vm38 resolver/policy behavior and new provisioning entry points. | high | mapped |
| engine/tests/vm/provision/test_provision_pure.py | vm | PORT_ADAPT | engine/tests/vm38/test_provision_pipeline.py | tangl.vm38.provision.Resolver.resolve_dependency | Provision integration coverage remains critical but must target vm38 resolver/policy behavior and new provisioning entry points. | high | mapped |
| engine/tests/vm/provision/test_provisioner1.py | vm | PORT_ADAPT | engine/tests/vm38/test_provision_pipeline.py | tangl.vm38.provision.Resolver.resolve_dependency | Provision integration coverage remains critical but must target vm38 resolver/policy behavior and new provisioning entry points. | high | mapped |
| engine/tests/vm/provision/test_provisioner2.py | vm | PORT_ADAPT | engine/tests/vm38/test_provision_pipeline.py | tangl.vm38.provision.Resolver.resolve_dependency | Provision integration coverage remains critical but must target vm38 resolver/policy behavior and new provisioning entry points. | high | mapped |
| engine/tests/vm/provision/test_requirement_token_ref.py | vm | PORT_ADAPT | engine/tests/vm38/test_requirement.py | tangl.vm38.provision.Requirement | Requirement identifier semantics remain relevant but are expressed through vm38 requirement fields and resolver matching rules. | medium | mapped |
| engine/tests/vm/provision/test_template_provisioner.py | vm | PORT_ADAPT | engine/tests/vm38/test_resolver.py | tangl.vm38.provision.TemplateProvisioner | Template-based provisioning still exists but is now exercised through vm38 resolver/template scope APIs. | high | mapped |
| engine/tests/vm/provision/test_template_provisioner_delegation.py | vm | PORT_ADAPT | engine/tests/vm38/test_resolver.py | tangl.vm38.provision.TemplateProvisioner | Template-based provisioning still exists but is now exercised through vm38 resolver/template scope APIs. | high | mapped |
| engine/tests/vm/provision/test_template_provisioner_scope.py | vm | PORT_ADAPT | engine/tests/vm38/test_resolver.py | tangl.vm38.provision.TemplateProvisioner | Template-based provisioning still exists but is now exercised through vm38 resolver/template scope APIs. | high | mapped |
| engine/tests/vm/provision/test_token_provisioner.py | vm | RETIRE_REMOVED |  | tangl.vm38.provision.InlineTemplateProvisioner | Dedicated token provisioner paths were removed and replaced by generic resolver/template provisioners in vm38. | medium | mapped |
| engine/tests/vm/test_call_return_integration.py | vm | PORT_ADAPT | engine/tests/vm38/test_call_stack.py | tangl.vm38.runtime.ledger.Ledger.push_call | Call/return stack behavior remains required but should be ported to vm38 frame+ledger stack semantics. | high | mapped |
| engine/tests/vm/test_call_stack.py | vm | PORT_ADAPT | engine/tests/vm38/test_call_stack.py | tangl.vm38.runtime.ledger.Ledger.push_call | Call/return stack behavior remains required but should be ported to vm38 frame+ledger stack semantics. | high | mapped |
| engine/tests/vm/test_call_stack_persistence.py | vm | PORT_ADAPT | engine/tests/vm38/test_call_stack.py | tangl.vm38.runtime.ledger.Ledger.push_call | Call/return stack behavior remains required but should be ported to vm38 frame+ledger stack semantics. | high | mapped |
| engine/tests/vm/test_context.py | vm | PORT_ADAPT | engine/tests/vm38/test_frame.py | tangl.vm38.runtime.frame.PhaseCtx.get_ns | Legacy VM context responsibilities were refactored into vm38 PhaseCtx and should be asserted against the new accessors. | medium | mapped |
| engine/tests/vm/test_context_journal_state.py | vm | PORT_ADAPT | engine/tests/vm38/test_system_handlers.py | tangl.vm38.runtime.frame.Frame.follow_edge | Journal-time state expectations remain valid but should be tested through vm38 phase sequencing and system handlers. | medium | mapped |
| engine/tests/vm/test_cost_model.py | vm | RETIRE_IRRELEVANT |  | tangl.vm38.provision.ProvisionPolicy | Legacy cost model heuristics are not part of vm38 MVP provisioning policy semantics. | medium | mapped |
| engine/tests/vm/test_cursor_history.py | vm | PORT_DIRECT | engine/tests/vm38/test_traversal.py | tangl.vm38.traversal.get_visit_count | Cursor history and visit counting are directly represented in vm38 traversal query helpers. | low | mapped |
| engine/tests/vm/test_cursor_history_integration.py | vm | PORT_DIRECT | engine/tests/vm38/test_traversal.py | tangl.vm38.traversal.get_visit_count | Cursor history and visit counting are directly represented in vm38 traversal query helpers. | low | mapped |
| engine/tests/vm/test_frame.py | vm | PORT_DIRECT | engine/tests/vm38/test_frame.py | tangl.vm38.runtime.frame.Frame.resolve_choice | Frame-driven phase execution remains core runtime behavior and has a direct vm38 counterpart. | low | mapped |
| engine/tests/vm/test_integration.py | vm | PORT_ADAPT | engine/tests/vm38/test_phase_integration.py | tangl.vm38.runtime.frame.Frame.follow_edge | End-to-end VM integration is still required but should align to vm38 phase names, redirect traces, and replay records. | high | mapped |
| engine/tests/vm/test_ledger.py | vm | PORT_DIRECT | engine/tests/vm38/test_ledger.py | tangl.vm38.runtime.ledger.Ledger.resolve_choice | Ledger lifecycle behavior is still central and has a direct vm38 runtime ledger implementation. | low | mapped |
| engine/tests/vm/test_ledger_structures.py | vm | PORT_ADAPT | engine/tests/vm38/test_ledger.py | tangl.vm38.runtime.ledger.Ledger.structure | Ledger structuring contracts remain relevant but now serialize vm38 graph/output_stream/replay fields. | medium | mapped |
| engine/tests/vm/test_ns.py | vm | PORT_ADAPT | engine/tests/vm38/test_system_handlers.py | tangl.vm38.dispatch.do_gather_ns | Namespace assembly remains required but now flows through vm38 gather_ns dispatch and PhaseCtx caching. | medium | mapped |
| engine/tests/vm/test_stack_event_sourcing.py | vm | RETIRE_REMOVED |  | tangl.vm38.replay.DiffReplayEngine | Legacy stack event-sourcing infrastructure is deprecated by vm38 in favor of simpler diff patches and step records. | high | mapped |
| engine/tests/vm/test_traversal_utilities.py | vm | PORT_DIRECT | engine/tests/vm38/test_traversal.py | tangl.vm38.traversal.steps_since_last_visit | Traversal utility behavior is directly represented by vm38 traversal query functions. | low | mapped |
| engine/tests/vm/test_update_markers.py | vm | RETIRE_REMOVED |  | tangl.vm38.runtime.ledger.Ledger.get_journal | Marker-channel update slicing was replaced by step-based fragment retrieval in vm38 output streams. | medium | mapped |

# V38 Phase 1 Review Memo

## Status
- Date: 2026-02-19
- Scope: inventory + classification only
- Phase gate: stop after review package (no Phase 2 execution, no cutover work)

## Deliverable Coverage
- Matrix delivered: `docs/src/contrib/v38-parity-matrix.md`
- In-scope module inventory classified: `125 / 125`
- Secondary-reference inventory captured (not first-pass classified):
  - `engine/tests/integration`: 4
  - `engine/tests/loaders`: 4
  - `engine/tests/ir`: 12

## Acceptance Check Results
1. Every legacy module in scope present exactly once: **PASS** (`125` rows for `125` modules).
2. No `PORT_*` row without `target_v38_test_path`: **PASS** (`0` missing of `85` port rows).
3. Every `RETIRE_*` row includes architecture rationale: **PASS** (all retire rows include one-sentence rationale tied to v38 design choices).
4. Risk-ranked gap list + recommended Phase 2 entry slice included: **PASS** (see sections below).
5. No cutover tasks included in Phase 1 output: **PASS**.

## Coverage and Mapping Summary
- In-scope legacy modules: `125`
- Ported intent (`PORT_DIRECT` + `PORT_ADAPT`): `85`
- Retired intent (`RETIRE_*`): `40`
- Direct ports already backed by existing v38 tests: `13`
- Planned target modules required for `PORT_ADAPT` backlog: `12`

## Top 5 High-Risk Unmapped Capability Clusters

### 1. VM Provisioning/Planning Pipeline Rewrite
- Evidence: 23 mapped modules in this cluster; 15 high-risk; majority `PORT_ADAPT`.
- Why high risk: legacy planning receipts and provisioner classes were reshaped into vm38 resolver + side-effect planning semantics.
- Typical impacted tests: `engine/tests/vm/planning/*`, `engine/tests/vm/provision/*`, and vm integration tests that depended on old planning object graphs.
- Primary v38 anchors:
  - `tangl.vm.dispatch.do_provision`
  - `tangl.vm.provision.Resolver.resolve_dependency`
  - `tangl.vm.provision.Requirement`

### 2. Story Fabula Compiler/Materializer Migration
- Evidence: 28 modules; 13 high-risk; many script-manager and world-materialization tests require remapping.
- Why high risk: legacy `ScriptManager`/manager stack is replaced by `StoryCompiler` + `StoryMaterializer` and init-mode reports.
- Typical impacted tests: `engine/tests/story/fabula/test_script_manager*.py`, `test_world_*`, `test_template_*`.
- Primary v38 anchors:
  - `tangl.story.fabula.StoryCompiler.compile`
  - `tangl.story.fabula.StoryMaterializer.create_story`
  - `tangl.story.fabula.World.from_script_data`

### 3. Story Episode Journaling and Choice Availability Semantics
- Evidence: 17 modules; 11 high-risk; heavy `PORT_ADAPT` around block pipeline/order/conditions.
- Why high risk: story38 centralizes output through journal handlers and vm38 phase contracts; legacy dialog/post-process/menu behavior does not map 1:1.
- Typical impacted tests: `engine/tests/story/episode/test_block*.py`, `test_menu_block.py`, `test_complex_conditions.py`.
- Primary v38 anchors:
  - `tangl.story.system_handlers.render_block`
  - `tangl.story.system_handlers._choice_unavailable_reason`
  - `tangl.vm.system_handlers.contribute_satisfied_deps`

### 4. Service Contract Consolidation onto Service38 Gateway/Orchestrator
- Evidence: 13 modules; 6 high-risk; legacy response-model tests include retired contract assumptions.
- Why high risk: endpoint/orchestrator behavior survives, but response/info-model contract focus shifts toward service38 operation + runtime-envelope patterns.
- Typical impacted tests: `engine/tests/service/test_orchestrator*.py`, `test_api_endpoints.py`, response contract tests.
- Primary v38 anchors:
  - `tangl.service.orchestrator.Orchestrator.execute`
  - `tangl.service.api_endpoint.ApiEndpoint.annotate`
  - `tangl.service.gateway.ServiceGateway.execute`

### 5. VM Replay Simplification (Watcher/Observer Model Retirement)
- Evidence: 6 replay/event-model modules; 4 retired; remaining 2 require adaptation to diff-patch MVP.
- Why high risk: legacy event-sourcing watcher assumptions are intentionally deprecated; replay confidence now depends on patch/checkpoint invariants.
- Typical impacted tests: `engine/tests/vm/events/test_watched.py`, `test_event_canonicalize.py`, `test_stack_event_sourcing.py`.
- Primary v38 anchors:
  - `tangl.vm.replay.DiffReplayEngine.build_delta`
  - `tangl.vm.replay.Event.apply`
  - `tangl.vm.runtime.ledger.Ledger.save_snapshot`

## Proposed Phase 2 Candidate Scope (Proposal Only)
No lock or execution implied; this is a review-time recommendation for the first implementation slice.

### Candidate slice: “Runtime correctness spine”
1. VM replay and planning baseline:
   - Cover diff replay/patch/checkpoint invariants.
   - Port high-value provisioning/planning integration intent into vm38 tests.
2. Story episode correctness:
   - Port block/choice/availability/journal-order behavior into story38 tests.
   - Retire menu-block and legacy post-process/dialog couplings explicitly.
3. Service38 backbone:
   - Port orchestrator/api-endpoint/user/runtime controller core tests into service38-targeted modules.
   - Retire legacy response-contract assumptions not used by service38 gateway/runtime envelope.

Suggested first Phase 2 output target modules:
- `engine/tests/vm38/test_provision_pipeline.py` (planned)
- `engine/tests/vm38/test_call_stack.py` (planned)
- `engine/tests/story38/test_choice_availability.py` (planned)
- `engine/tests/story38/test_journal_order.py` (planned)
- `engine/tests/service38/test_orchestrator.py` (planned)
- `engine/tests/service38/test_api_endpoint.py` (planned)

## Explicit Stop Gate
Phase 1 package is complete at this point. Work should pause here for review approval before any Phase 2 implementation activity.

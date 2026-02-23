# Story38 / VM38 Action And Testing Plan

Status: In Progress (updated 2026-02-21)

## Interim Constraint (2026-02-20)

- Until container provisioning rules for unresolved scene/block links are finalized,
  treat story38 runtime support as:
- `EAGER` stories, or
- effectively flat/minimally-scoped stories that do not depend on deferred container creation.
- `LAZY` stories where unresolved dependencies are expected to resolve at runtime.

## Decision Locks

- Feature parity with legacy is required; syntax parity is not required.
- `on_get_ns` stays as a temporary bridge until scoped-dispatch returns.
- Renderer is pluggable; Jinja2 is the default implementation.
- `core.ctx` and `vm.ctx` protocol contracts are firmed up together.
- Runtime audit detail should prefer structured logging sinks over many new record types.

## Priority Sequence (Now)

### Phase 0 - Stabilize Current Regressions

- [x] Restore CLI/server endpoint compatibility after service endpoint updates.
- [x] Reconfirm story creation/choose flows include required metadata (`ledger_id`, envelope shape).
- [x] Reconfirm selector usage paths (`matches` migration) in branching/linear endpoint tests.

Tests:
- [x] `apps/cli/tests/test_story_cli_integration.py`
- [x] `apps/server/tests/test_story38_endpoints.py`
- [x] `apps/server/tests/test_story_branching_endpoints.py`
- [x] `apps/server/tests/test_story_linear_endpoints.py`
- [x] `apps/server/tests/test_multi_world_switching.py`

### Phase 1 - Context Contracts (Core + VM + Story)

- [x] Define protocol-first `CoreCtx` + `VmCtx` surface (correlation, logging/audit, metadata, namespace access).
- [x] Keep story runtime context thin: locals, scope groups, provisioning view, world access.
- [x] Ensure resolver/journal/provision code depends on protocol methods, not concrete classes.

Target code:
- `engine/src/tangl/core38/ctx.py`
- `engine/src/tangl/vm38/ctx.py`
- `engine/src/tangl/story38/story_graph.py`
- `engine/src/tangl/story38/fabula/materializer.py`

Tests:
- [x] `engine/tests/vm38/test_dispatch.py`
- [x] `engine/tests/vm38/test_frame.py`
- [x] `engine/tests/vm38/test_resolver.py`

### Phase 2 - Namespace Publication

- [x] Add concept namespace publishers (`Actor`, `Location`, `Role`, `Setting`) through `on_get_ns`.
- [x] Document temporary nature of `on_get_ns` in code and docs.
- [x] Enforce deterministic ancestor merge order and cache behavior.

Target code:
- `engine/src/tangl/story38/concepts/actor.py`
- `engine/src/tangl/story38/concepts/location.py`
- `engine/src/tangl/story38/concepts/role.py`
- `engine/src/tangl/story38/concepts/setting.py`
- `engine/src/tangl/vm38/runtime/frame.py`

Tests:
- [x] New `engine/tests/story38/test_concept_namespace.py`
- [x] Extend `engine/tests/vm38/test_dispatch.py`
- [x] Extend `engine/tests/vm38/test_frame.py`

### Phase 3 - Journal Handler Decomposition

- [x] Split `render_block` into composable handlers: content, choices, media.
- [x] Preserve current endpoint response shape while migrating.
- [x] Enable concept/mechanic handler injection into JOURNAL phase.

Target code:
- `engine/src/tangl/story38/system_handlers.py`
- `engine/src/tangl/story38/dispatch.py`

Tests:
- [x] Extend `engine/tests/story38/test_system_handlers.py`
- [x] Add handler-order and custom-injection tests

### Phase 4 - Runtime Template Lookup + World Contributions

- [x] Add ScriptManager-lite facade for provisioning-time template lookup.
- [x] Allow world-authoritative template groups to participate in provisioning.
- [x] Keep lookup API protocol-driven so story runtime and VM can share it.

Target code:
- `engine/src/tangl/story38/fabula/script_manager38.py` (new)
- `engine/src/tangl/story38/fabula/world.py`
- `engine/src/tangl/story38/fabula/materializer.py`

Tests:
- [x] Extend `engine/tests/story38/test_story38_init.py`
- [x] Extend `engine/tests/vm38/test_resolver.py`

### Phase 5 - World Facets (Lightweight Interfaces)

- [x] Add lightweight world facets:
- [x] `domain`: custom classes + dispatch hooks exposed to VM.
- [x] `templates`: template factory/definitions.
- [x] `assets`: token/platonic object factory.
- [x] `resources`: script/media/binary inventory.
- [x] Thread facets through bundle compile/load and world creation path.

Target code:
- `engine/src/tangl/story38/fabula/world.py`
- `engine/src/tangl/story38/fabula/compiler.py`
- `engine/src/tangl/story38/fabula/types.py`
- `engine/src/tangl/loaders/`

Tests:
- [x] Extend `engine/tests/loaders/test_world_loader.py`
- [x] Extend `engine/tests/loaders/test_world_bundle.py`
- [x] Extend `engine/tests/story38/test_story38_init.py`

### Phase 5.5 - Gateway Transport Adapter Alignment

- [x] Add a transport-facing adapter around `ServiceGateway38` for auth resolution + operation execution.
- [x] Make `apps/server` use adapter dependencies rather than direct gateway/auth plumbing in routers.
- [x] Keep CLI gateway-first by removing legacy orchestrator/controller bootstrap from default app wiring.
- [x] Register service38-owned controller wrappers in bootstrap so operation endpoints no longer bind directly to legacy controller classes.

Target code:
- `engine/src/tangl/service38/rest_adapter.py` (new)
- `apps/server/src/tangl/rest/dependencies38.py`
- `apps/server/src/tangl/rest/routers/`
- `apps/cli/src/tangl/cli/app.py`

Tests:
- [x] New `engine/tests/service/test_rest_adapter38.py`
- [x] Extend `apps/server/tests/test_rest_dependencies38.py`

### Phase 6 - Materialization Modes + Provisioning Semantics

- [x] Keep `LAZY` and `EAGER`.
- [x] Remove `HYBRID` mode from story38 initialization.
- [ ] Define container provisioning rules for unresolved scene/block links in `LAZY`.
- [x] Document resolver behavior for update/clone policy offers (deferred execution, rank/filter first, strict fallback).

Target code:
- `engine/src/tangl/story38/fabula/types.py`
- `engine/src/tangl/story38/fabula/materializer.py`
- `engine/src/tangl/vm38/provision/`

Tests:
- [x] Add/extend `engine/tests/story38/test_story38_init.py` for `LAZY`/`EAGER` behavior
- [x] Extend `engine/tests/vm38/test_resolver.py` for clone/update offer orchestration

## Testing Plan (Per Phase)

- [x] Unit gate for each phase (target package tests only).
- [x] Integration gate after Phases 3, 5, and 6:
- [x] `apps/server/tests/test_story38_endpoints.py`
- [x] `apps/server/tests/test_story_branching_endpoints.py`
- [x] `apps/server/tests/test_story_linear_endpoints.py`
- [x] `apps/cli/tests/test_story_cli_integration.py`
- [x] `apps/server/tests/test_multi_world_switching.py`
- [x] Replay/determinism checks after provisioning changes:
- [x] `engine/tests/vm38/test_replay_mvp.py`
- [x] `engine/tests/vm38/test_ledger.py`

Validation snapshot (2026-02-21):
- [x] `engine/tests/vm38/test_replay_mvp.py`
- [x] `engine/tests/vm38/test_ledger.py`
- [x] `engine/tests/loaders/test_world_bundle.py`
- [x] `engine/tests/story38/test_story38_init.py`
- [x] `engine/tests/vm38/test_resolver.py`

## Definition Of Done

- [ ] No legacy response primitive imports from v38 service/story code paths.
- [x] Context protocol contracts documented and used in VM/story runtime surfaces.
- [x] `on_get_ns` behavior documented as temporary and covered by tests.
- [x] Journal composition is modular and externally extensible.
- [x] World facets are available through `World38` and loader path.
- [x] End-to-end CLI + REST story flows green on the full regression gate.

## Later Track (Deferred)

- [ ] Scoped-dispatch resurrection to replace temporary `on_get_ns` pattern.
- [ ] Extended provisioners (token/asset/update/clone variants) as workload needs harden.
- [ ] Adapter tooling for legacy-script migration where operationally needed.

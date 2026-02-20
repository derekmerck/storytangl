# Story38 / VM38 Action And Testing Plan

Status: Draft (updated 2026-02-20)

## Decision Locks

- Feature parity with legacy is required; syntax parity is not required.
- `on_get_ns` stays as a temporary bridge until scoped-dispatch returns.
- Renderer is pluggable; Jinja2 is the default implementation.
- `core.ctx` and `vm.ctx` protocol contracts are firmed up together.
- Runtime audit detail should prefer structured logging sinks over many new record types.

## Priority Sequence (Now)

### Phase 0 - Stabilize Current Regressions

- [ ] Restore CLI/server endpoint compatibility after service endpoint updates.
- [ ] Reconfirm story creation/choose flows include required metadata (`ledger_id`, envelope shape).
- [ ] Reconfirm selector usage paths (`matches` migration) in branching/linear endpoint tests.

Tests:
- [ ] `apps/cli/tests/test_story_cli_integration.py`
- [ ] `apps/server/tests/test_story38_endpoints.py`
- [ ] `apps/server/tests/test_story_branching_endpoints.py`
- [ ] `apps/server/tests/test_story_linear_endpoints.py`
- [ ] `apps/server/tests/test_multi_world_switching.py`

### Phase 1 - Context Contracts (Core + VM + Story)

- [ ] Define protocol-first `CoreCtx` + `VmCtx` surface (correlation, logging/audit, metadata, namespace access).
- [ ] Keep story runtime context thin: locals, scope groups, provisioning view, world access.
- [ ] Ensure resolver/journal/provision code depends on protocol methods, not concrete classes.

Target code:
- `engine/src/tangl/core38/ctx.py`
- `engine/src/tangl/vm38/ctx.py`
- `engine/src/tangl/story38/story_graph.py`
- `engine/src/tangl/story38/fabula/materializer.py`

Tests:
- [ ] `engine/tests/vm38/test_dispatch.py`
- [ ] `engine/tests/vm38/test_frame.py`
- [ ] `engine/tests/vm38/test_resolver.py`

### Phase 2 - Namespace Publication

- [ ] Add concept namespace publishers (`Actor`, `Location`, `Role`, `Setting`) through `on_get_ns`.
- [ ] Document temporary nature of `on_get_ns` in code and docs.
- [ ] Enforce deterministic ancestor merge order and cache behavior.

Target code:
- `engine/src/tangl/story38/concepts/actor.py`
- `engine/src/tangl/story38/concepts/location.py`
- `engine/src/tangl/story38/concepts/role.py`
- `engine/src/tangl/story38/concepts/setting.py`
- `engine/src/tangl/vm38/runtime/frame.py`

Tests:
- [ ] New `engine/tests/story38/test_concept_namespace.py`
- [ ] Extend `engine/tests/vm38/test_dispatch.py`
- [ ] Extend `engine/tests/vm38/test_frame.py`

### Phase 3 - Journal Handler Decomposition

- [ ] Split `render_block` into composable handlers: content, choices, media.
- [ ] Preserve current endpoint response shape while migrating.
- [ ] Enable concept/mechanic handler injection into JOURNAL phase.

Target code:
- `engine/src/tangl/story38/system_handlers.py`
- `engine/src/tangl/story38/dispatch.py`

Tests:
- [ ] Extend `engine/tests/story38/test_system_handlers.py`
- [ ] Add handler-order and custom-injection tests

### Phase 4 - Runtime Template Lookup + World Contributions

- [ ] Add ScriptManager-lite facade for provisioning-time template lookup.
- [ ] Allow world-authoritative template groups to participate in provisioning.
- [ ] Keep lookup API protocol-driven so story runtime and VM can share it.

Target code:
- `engine/src/tangl/story38/fabula/script_manager38.py` (new)
- `engine/src/tangl/story38/fabula/world.py`
- `engine/src/tangl/story38/fabula/materializer.py`

Tests:
- [ ] Extend `engine/tests/story38/test_story38_init.py`
- [ ] Extend `engine/tests/vm38/test_resolver.py`

### Phase 5 - World Facets (Lightweight Interfaces)

- [ ] Add lightweight world facets:
- [ ] `domain`: custom classes + dispatch hooks exposed to VM.
- [ ] `templates`: template factory/definitions.
- [ ] `assets`: token/platonic object factory.
- [ ] `resources`: script/media/binary inventory.
- [ ] Thread facets through bundle compile/load and world creation path.

Target code:
- `engine/src/tangl/story38/fabula/world.py`
- `engine/src/tangl/story38/fabula/compiler.py`
- `engine/src/tangl/story38/fabula/types.py`
- `engine/src/tangl/loaders/`

Tests:
- [ ] Extend `engine/tests/loaders/test_world_loader.py`
- [ ] Extend `engine/tests/loaders/test_world_bundle.py`
- [ ] Extend `engine/tests/story38/test_story38_init.py`

### Phase 6 - Materialization Modes + Provisioning Semantics

- [ ] Keep `MINIMAL` and `FULLY_SPECIFIED`.
- [ ] Reintroduce `HYBRID` semantics as: instantiate containers/groups, defer resident members.
- [ ] Define container provisioning rules for unresolved scene/block links.
- [ ] Document resolver behavior for update/clone policy offers (deferred execution, rank/filter first, strict fallback).

Target code:
- `engine/src/tangl/story38/fabula/types.py`
- `engine/src/tangl/story38/fabula/materializer.py`
- `engine/src/tangl/vm38/provision/`

Tests:
- [ ] Add/extend `engine/tests/story38/test_story38_init.py` for hybrid behavior
- [ ] Extend `engine/tests/vm38/test_resolver.py` for clone/update offer orchestration

## Testing Plan (Per Phase)

- [ ] Unit gate for each phase (target package tests only).
- [ ] Integration gate after Phases 3, 5, and 6:
- [ ] `apps/server/tests/test_story38_endpoints.py`
- [ ] `apps/server/tests/test_story_branching_endpoints.py`
- [ ] `apps/server/tests/test_story_linear_endpoints.py`
- [ ] `apps/cli/tests/test_story_cli_integration.py`
- [ ] `apps/server/tests/test_multi_world_switching.py`
- [ ] Replay/determinism checks after provisioning changes:
- [ ] `engine/tests/vm38/test_replay_engine.py`
- [ ] `engine/tests/vm38/test_ledger.py`

## Definition Of Done

- [ ] No legacy response primitive imports from v38 service/story code paths.
- [ ] Context protocol contracts documented and used in VM/story runtime surfaces.
- [ ] `on_get_ns` behavior documented as temporary and covered by tests.
- [ ] Journal composition is modular and externally extensible.
- [ ] World facets are available through `World38` and loader path.
- [ ] End-to-end CLI + REST story flows green on the full regression gate.

## Later Track (Deferred)

- [ ] Scoped-dispatch resurrection to replace temporary `on_get_ns` pattern.
- [ ] Extended provisioners (token/asset/update/clone variants) as workload needs harden.
- [ ] Adapter tooling for legacy-script migration where operationally needed.

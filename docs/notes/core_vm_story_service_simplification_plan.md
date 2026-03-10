# Core / VM / Story / Service Simplification Tracker

Status: Waves 0-3 Complete, Wave 4 In Progress (updated 2026-03-10)

## Goal

Reduce cognitive overhead in `tangl.core`, `tangl.vm`, `tangl.story`, and
`tangl.service` while preserving the current feature set, deterministic behavior,
and strict layer separation.

This tracker replaces the earlier draft plan with implementation status, hard
gates, and measured checkpoints.

## Guardrails

- Keep layer flow one-way: `core -> vm -> service/app/presentation`, with story
  remaining a VM-domain layer.
- Keep auth, persistence, and transport policy in service only.
- Do not unify endpoints with core behavior entities in this pass.
- Remove compatibility bridges in the same wave that replaces them.
- Prefer explicit failures over silent compatibility fallbacks.

## Interface Decisions

- `ApiEndpoint` is the only public endpoint type.
- `LegacyApiEndpoint` is removed from code, tests, and exports.
- `Orchestrator.execute(...)`, `ApiEndpoint.annotate(...)`,
  `BehaviorRegistry.execute_all(...)`, `Resolver` public methods, and
  `Frame.follow_edge(...)` / `Frame.resolve_choice(...)` keep their public
  signatures.
- Canonical context contract names are:
  `get_authorities()`, `get_location_entity_groups()`,
  `get_template_scope_groups()`.
- Story no longer owns controller bridge modules; controller implementations now
  live under `tangl.service.controllers`.

## Wave Status

### Wave 0: Baseline and execution lock

Status: Complete

Completed:

- Converted this note into an execution tracker with explicit wave status.
- Recorded baseline hotspot metrics for line count, exported symbols, public
  classes, and public methods.
- Added or updated contract tests around endpoint policy extraction, layering
  guards, and canonical context method usage before continuing refactors.

Acceptance gates:

- Service/core/VM/story hotspot suites green before structural follow-up work.

### Wave 1: Service boundary cleanup

Status: Complete

Completed:

- Refactored `service/orchestrator.py` into explicit private stages for binding,
  policy resolution, hydration, invocation, normalization, persistence, cleanup,
  and service-error mapping.
- Centralized endpoint metadata and policy defaults in `service/api_endpoint.py`.
- Removed `LegacyApiEndpoint` entirely.
- Tightened runtime result normalization so runtime endpoints must return
  `RuntimeInfo`-compatible payloads or raise `TypeError`.

Acceptance gates:

- `engine/tests/service38/test_api_endpoint.py`
- `engine/tests/service38/test_orchestrator.py`
- `engine/tests/service38/controllers/test_runtime_controller.py`
- `engine/tests/service38/controllers/test_user_controller.py`
- `engine/tests/integration/test_service_layer.py`

### Wave 2: Story/service decoupling and handler cleanup

Status: Complete

Completed:

- Moved runtime and world controller implementations under
  `tangl.service.controllers`.
- Deleted `tangl.story.story_controller` and
  `tangl.story.fabula.world_controller`.
- Extracted shared provider-collection helpers into
  `story/provider_collection.py`.
- Reused those helpers from `story/system_handlers.py`.
- Restored canonical journal media handling so authored media keeps
  `fragment_type="media"` and unresolved inventory entries emit a placeholder
  media fragment plus diagnostics instead of disappearing from runtime
  envelopes.
- Tightened the layering import guard so `tangl.story` no longer imports the
  service layer directly.

Acceptance gates:

- `engine/tests/story38/test_system_handlers.py`
- `engine/tests/integration/test_layering_import_guards.py`
- `engine/tests/integration/test_service_layer.py`

### Wave 3: Core/VM contract canon

Status: Complete

Completed:

- Removed `get_registries()`, `get_entity_groups()`, and `get_template_groups()`
  from runtime protocols, contexts, resolver compatibility paths, materializer
  helper contexts, and tests.
- Updated `CORE_DESIGN.md` and `VM_DESIGN.md` to reflect canonical context
  vocabulary.
- Confirmed VM dispatch ordering already routes through `Behavior.sort_key`.
- Deduplicated graph typed-query narrowing through shared private helpers in
  `core/graph.py`.
- Replaced the media-specific `on_index` bootstrap with a generic
  `resolve_ctx(..., authorities=...)` overlay path so objects can opt specific
  local `BehaviorRegistry` instances into selected dispatch calls without
  reviving automatic ambient per-instance local-behavior discovery.

Acceptance gates:

- `engine/tests/core38/behavior/test_behavior.py`
- `engine/tests/core38/test_ctx.py`
- `engine/tests/core38/entity/test_entity.py`
- `engine/tests/core38/dispatch/test_dispatch.py`
- `engine/tests/core38/graph/test_graph_dispatch.py`
- `engine/tests/vm38/test_dispatch.py`
- `engine/tests/vm38/test_frame.py`
- `engine/tests/vm38/test_resolver.py`

### Wave 4: Resolver and materialization decomposition

Status: In Progress

Completed in this checkpoint:

- Extracted shared template materialization helpers into
  `vm/provision/materialization.py`.
- Reused the shared helper from both `Resolver` and `StoryMaterializer`.
- Removed the story-layer dependency on `Resolver._materialize_node`.

Remaining:

- Split resolver internals further into discovery/ranking, build-chain
  execution, dependency binding, and preview/blocker helpers.
- Decompose `StoryMaterializer.create_story()` into explicit passes rather than
  one long control path.

Acceptance gates reached for this checkpoint:

- `engine/tests/vm38/test_resolver.py`
- `engine/tests/vm38/test_provision_pipeline.py`
- `engine/tests/vm38/test_scope_path_provisioning.py`
- `engine/tests/story38/test_story_init.py`
- `engine/tests/story38/test_compiler_scope_resolution.py`

### Wave 5: Frame and traversal simplification

Status: Pending

Not started:

- `Frame.follow_edge()` / `Frame.resolve_choice()` reducer extraction.
- Removal of `Frame.local_behaviors`, `Ledger.local_behaviors`, and numeric
  task-name translation.
- Traversable helper narrowing.

### Wave 6: Final cleanup and measurement

Status: Pending

Exit criteria:

- Remove only compatibility code with no remaining internal references.
- Update design docs in the same changes that finalize implementation.
- Achieve at least two roughly 20% metric improvements per touched package, or
  document the accepted shortfall explicitly.

## Baseline Metrics

Recorded before structural cleanup:

| Hotspot | Lines | Exports | Public Classes | Public Methods |
| --- | ---: | ---: | ---: | ---: |
| `engine/src/tangl/service/orchestrator.py` | 687 | 3 | 2 | 4 |
| `engine/src/tangl/service/api_endpoint.py` | 315 | 11 | 11 | 9 |
| `engine/src/tangl/core/behavior.py` | 502 | 0 | 7 | 20 |
| `engine/src/tangl/vm/dispatch.py` | 584 | 26 | 0 | 0 |
| `engine/src/tangl/vm/provision/resolver.py` | 1319 | 0 | 1 | 9 |
| `engine/src/tangl/vm/runtime/frame.py` | 878 | 2 | 3 | 21 |
| `engine/src/tangl/vm/traversable.py` | 933 | 11 | 6 | 17 |
| `engine/src/tangl/story/fabula/materializer.py` | 813 | 0 | 1 | 1 |
| `engine/src/tangl/story/fabula/compiler.py` | 520 | 0 | 2 | 2 |
| `engine/src/tangl/story/system_handlers.py` | 732 | 0 | 0 | 0 |
| `engine/src/tangl/core/registry.py` | 597 | 0 | 4 | 31 |
| `engine/src/tangl/core/graph.py` | 564 | 0 | 6 | 48 |

## Checkpoint Metrics

Measured after Waves 0-3 and the first Wave 4 extraction:

| Hotspot | Baseline Lines | Current Lines | Delta |
| --- | ---: | ---: | ---: |
| `engine/src/tangl/service/orchestrator.py` | 687 | 741 | +54 |
| `engine/src/tangl/service/api_endpoint.py` | 315 | 280 | -35 |
| `engine/src/tangl/core/behavior.py` | 502 | 496 | -6 |
| `engine/src/tangl/vm/dispatch.py` | 584 | 581 | -3 |
| `engine/src/tangl/vm/provision/resolver.py` | 1319 | 1260 | -59 |
| `engine/src/tangl/vm/runtime/frame.py` | 878 | 866 | -12 |
| `engine/src/tangl/vm/traversable.py` | 933 | 933 | 0 |
| `engine/src/tangl/story/fabula/materializer.py` | 813 | 794 | -19 |
| `engine/src/tangl/story/fabula/compiler.py` | 520 | 520 | 0 |
| `engine/src/tangl/story/system_handlers.py` | 732 | 567 | -165 |
| `engine/src/tangl/core/registry.py` | 597 | 597 | 0 |
| `engine/src/tangl/core/graph.py` | 564 | 580 | +16 |

Notable wins already visible:

- `story/system_handlers.py` is down by 22.5%.
- `service/api_endpoint.py` is down by 11.1%.
- `vm/provision/resolver.py` is down by 4.5% before the larger split.
- `story/fabula/materializer.py` is down by 2.3% before the explicit-pass
  decomposition.

## Verified Test Checkpoints

Green targeted runs after the refactors in this tracker:

- `95 passed`:
  `engine/tests/service38/test_api_endpoint.py`
  `engine/tests/service38/test_orchestrator.py`
  `engine/tests/service38/controllers/test_runtime_controller.py`
  `engine/tests/service38/controllers/test_user_controller.py`
  `engine/tests/integration/test_layering_import_guards.py`
  `engine/tests/story38/test_system_handlers.py`
- `253 passed`:
  `engine/tests/core38/behavior/test_behavior.py`
  `engine/tests/core38/test_ctx.py`
  `engine/tests/core38/entity/test_entity.py`
  `engine/tests/core38/dispatch/test_dispatch.py`
  `engine/tests/core38/graph/test_graph_dispatch.py`
  `engine/tests/vm38/test_dispatch.py`
  `engine/tests/vm38/test_frame.py`
  `engine/tests/vm38/test_resolver.py`
  `engine/tests/vm38/test_provision_pipeline.py`
  `engine/tests/vm38/test_scope_path_provisioning.py`
  `engine/tests/vm38/test_system_handlers.py`
- `148 passed`:
  `engine/tests/core38/graph/test_graph_dispatch.py`
  `engine/tests/vm38/test_resolver.py`
  `engine/tests/vm38/test_provision_pipeline.py`
  `engine/tests/vm38/test_scope_path_provisioning.py`
  `engine/tests/story38/test_story_init.py`
  `engine/tests/story38/test_compiler_scope_resolution.py`
- `1707 passed`, `68 skipped`, `9 xfailed`:
  full `poetry run pytest engine/tests -q` regression after the media fragment,
  logger-noise, registry-binding, media index-handler, and authority-overlay
  fixes landed.

## Next Execution Slice

1. Split `Resolver` internals into smaller offer-discovery, chain-execution,
   dependency-binding, and preview helpers.
2. Break `StoryMaterializer.create_story()` into explicit passes while preserving
   `LAZY` and `EAGER` behavior.
3. Refactor `Frame.follow_edge()` / `Frame.resolve_choice()` into reducer phases.
4. Use the now-green full `engine/tests` regression as the next Wave 4/5
   checkpoint baseline while continuing structural splits.

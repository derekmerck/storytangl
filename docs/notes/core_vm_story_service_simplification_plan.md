# Core / VM / Story / Service Simplification Tracker

Status: Waves 0-5 Complete, Wave 6 Pending (updated 2026-03-10)

## Goal

Reduce cognitive overhead in `tangl.core`, `tangl.vm`, `tangl.story`, and
`tangl.service` while preserving the current feature set, deterministic behavior,
and strict layer separation.

This tracker is the canonical execution record for the simplification effort.
The external draft plan remains directionally correct, but this note should
reflect what is actually implemented in the repo today.

## Guardrails

- Keep layer flow one-way: `core -> vm -> service/app/presentation`, with story
  remaining a VM-domain layer.
- Keep auth, persistence, and transport policy in service only.
- Do not unify endpoints with core behavior entities in this pass.
- Remove compatibility bridges in the same wave that replaces them.
- Prefer explicit failures over silent compatibility fallbacks.
- Optimize primarily for cognitive overhead reduction. Line count remains a
  tracking signal, but not the primary definition of success.

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
- `InitMode.LAZY` and `InitMode.EAGER` remain the only story materialization
  modes in this cleanup effort.

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
  policy resolution, hydration, invocation, normalization, persistence,
  cleanup, and service-error mapping.
- Centralized endpoint metadata and policy defaults in
  `service/api_endpoint.py`.
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

Status: Complete

#### Checkpoint A complete

Completed:

- Extracted shared template materialization helpers into
  `vm/provision/materialization.py`.
- Reused the shared helper from both `Resolver` and `StoryMaterializer`.
- Removed the story-layer dependency on `Resolver._materialize_node`.
- Split `StoryMaterializer.create_story()` into explicit initialization,
  materialization, topology, prelink, and result-assembly passes.
- Extracted `Resolver` helper seams for raw offer discovery, resolve overrides,
  policy filtering, sorting, and fanout deduplication so `gather_offers()` and
  `gather_fanout_offers()` are orchestration wrappers rather than monoliths.

Checkpoint A gates reached:

- `engine/tests/vm38/test_resolver.py`
- `engine/tests/vm38/test_provision_pipeline.py`
- `engine/tests/vm38/test_scope_path_provisioning.py`
- `engine/tests/story38/test_story_init.py`
- `engine/tests/story38/test_compiler_scope_resolution.py`

#### Checkpoint B complete: resolver decomposition

Completed:

- Split preview viability into smaller helpers for viable-offer detection,
  blocker-diagnosis entry, shared blocker-context construction, and
  per-blocker-family diagnosis.
- Split structural chain work into smaller helpers for target-path resolution,
  structural plan construction, existing-path lookup, chain viability
  checking, and chain materialization/execution.
- Removed repeated target-path and chain-resolution logic from preview and
  structural dependency execution while keeping blocker reasons and metadata
  shapes stable.

Checkpoint B acceptance:

- `engine/tests/vm38/test_resolver.py`
- `engine/tests/vm38/test_scope_path_provisioning.py`
- `engine/tests/vm38/test_provision_pipeline.py`

#### Checkpoint C complete: materializer decomposition

Completed:

- Split topology wiring into explicit scene-contract, role/setting dependency,
  menu fanout, action, and media-dependency passes.
- Split eager prelink into explicit dependency prelink, action successor
  projection, fanout prelink, menu action projection, traversal-contract
  verification, and hard-error promotion passes.
- Extracted repeated `_PrelinkCtx` construction into one helper.
- Kept `LAZY` and `EAGER` as the only init modes.

Checkpoint C acceptance:

- `engine/tests/story38/test_story_init.py`
- `engine/tests/story38/test_compiler_scope_resolution.py`
- `engine/tests/media/test_media_provisioning.py`
- `engine/tests/integration/test_media_e2e.py`
- `engine/tests/integration/test_system_media_e2e.py`

#### Wave 4 closeout

Reached:

- Refreshed hotspot metrics after the Wave 4 refactors landed.
- Ran `pytest engine/tests`.
- Ran app/server story endpoint suites.
- Accepted the metric tradeoff that `resolver.py` and `materializer.py` grew in
  line count while their control flow became more explicit and locally readable.

### Wave 5: Frame and traversal simplification

Status: Complete

Completed:

- Simplified frame/ledger local behavior support so `Frame.local_behaviors` and
  `Ledger.local_behaviors` participate as explicit `PhaseCtx` authorities when
  populated, instead of being wrapped as inline behaviors.
- Removed the numeric task-name translation bridge from `Frame`; local
  registries now use the canonical vm dispatch task names directly.
- Kept the phase bus explicit rather than reintroducing a generic phase-spec
  loop, while splitting `follow_edge()` into hop preparation, redirect-phase,
  terminal-phase, and completion helpers.
- Split `resolve_choice()` into a small loop coordinator around depth guard,
  per-hop execution, return-edge continuation, and step-trace emission.
- Split the ledger/frame handshake into smaller metadata, validation, sync, and
  commit helpers so `Ledger.resolve_choice()` reads as orchestration rather than
  one mixed state-update block.
- Reused the explicit local-authority path in ledger provisioning contexts so
  selection-time dependency resolution can opt into populated ledger-local
  registries without reviving ambient discovery.
- Keep `Frame.local_behaviors` and `Ledger.local_behaviors` as explicit opt-in
  local authority registries. Do not revive ambient per-instance discovery.
- Keep `TraversableNode` and `TraversableEdge` in VM. Limit this wave to helper
  extraction and state-flow simplification rather than moving concepts between
  layers.

Acceptance gates:

- `engine/tests/vm38/test_frame.py`
- `engine/tests/vm38/test_phase_integration.py`
- `engine/tests/vm38/test_call_stack.py`
- `engine/tests/vm38/test_ledger.py`
- `engine/tests/vm38/test_traversable.py`

Wave 5 closeout:

- Reran the Wave 5 acceptance slice after the explicit bus/helper refactor.
- Reran full `pytest engine/tests`.
- Reran the app/server story endpoint suites to confirm the runtime refactor did
  not change transport behavior.

### Wave 6: Final cleanup and measurement

Status: Pending

Exit criteria:

- Remove only compatibility code with no remaining internal references.
- Refresh metrics one final time and document any category that did not reach
  the target reduction.
- Update design docs and this tracker in the same changes that finalize
  implementation.
- Run final regression:
  `pytest engine/tests`, app/server story endpoint suites, and media
  integration suites.

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

## Current Metrics

Measured after Waves 0-5, including the completed Wave 5 runtime
simplification, and the latest maintenance hardening:

| Hotspot | Baseline Lines | Current Lines | Delta |
| --- | ---: | ---: | ---: |
| `engine/src/tangl/service/orchestrator.py` | 687 | 740 | +53 |
| `engine/src/tangl/service/api_endpoint.py` | 315 | 294 | -21 |
| `engine/src/tangl/core/behavior.py` | 502 | 495 | -7 |
| `engine/src/tangl/vm/dispatch.py` | 584 | 580 | -4 |
| `engine/src/tangl/vm/provision/resolver.py` | 1319 | 1509 | +190 |
| `engine/src/tangl/vm/runtime/frame.py` | 878 | 966 | +88 |
| `engine/src/tangl/vm/traversable.py` | 933 | 932 | -1 |
| `engine/src/tangl/story/fabula/materializer.py` | 813 | 951 | +138 |
| `engine/src/tangl/story/fabula/compiler.py` | 520 | 519 | -1 |
| `engine/src/tangl/story/system_handlers.py` | 732 | 613 | -119 |
| `engine/src/tangl/core/registry.py` | 597 | 603 | +6 |
| `engine/src/tangl/core/graph.py` | 564 | 598 | +34 |

Notes:

- `story/system_handlers.py` remains materially smaller than baseline.
- `service/api_endpoint.py` remains smaller than baseline while exposing
  clearer seams.
- `vm/provision/resolver.py` and `story/fabula/materializer.py` are both above
  baseline after the Wave 4 helper extraction. This checkpoint improved local
  readability and responsibility boundaries first, at the cost of additional
  internal scaffolding.
- `vm/runtime/frame.py` is further above baseline after completing Wave 5 with
  an explicit bus plus named coordinators. The tradeoff remains the same:
  clearer runtime seams first, with line count still a secondary metric.
- These metrics are descriptive only. The primary success criterion remains
  lower cognitive overhead.

## Verified Test Checkpoints

Green checkpoints currently on record:

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
- `106 passed`:
  Wave 4 Checkpoint B acceptance covering
  `engine/tests/vm38/test_resolver.py`,
  `engine/tests/vm38/test_scope_path_provisioning.py`,
  and `engine/tests/vm38/test_provision_pipeline.py`.
- `42 passed`, `1 skipped`:
  Wave 4 Checkpoint C acceptance covering
  `engine/tests/story38/test_story_init.py`,
  `engine/tests/story38/test_compiler_scope_resolution.py`,
  `engine/tests/media/test_media_provisioning.py`,
  `engine/tests/integration/test_media_e2e.py`,
  and `engine/tests/integration/test_system_media_e2e.py`.
- `83 passed`, `1 skipped`:
  targeted service/core/media/server hardening slice covering
  `engine/tests/service38/test_api_endpoint.py`,
  `engine/tests/service38/controllers/test_runtime_controller.py`,
  `engine/tests/core38/graph/test_graph.py`,
  `engine/tests/media/test_resource_manager.py`,
  `engine/tests/media/test_media_fragment.py`,
  `engine/tests/story38/test_provider_collection.py`,
  and the affected app/server story endpoint suites.
- `14 passed`, `1 skipped`:
  story REST/router slice covering
  `apps/server/tests/test_story_linear_endpoints.py`,
  `apps/server/tests/test_story_branching_endpoints.py`,
  `apps/server/tests/test_story_runtime_endpoints.py`,
  and `apps/server/tests/test_multi_world_switching.py`.
- `154 passed`:
  Wave 5 acceptance slice covering
  `engine/tests/vm38/test_frame.py`,
  `engine/tests/vm38/test_phase_integration.py`,
  `engine/tests/vm38/test_call_stack.py`,
  `engine/tests/vm38/test_ledger.py`,
  and `engine/tests/vm38/test_traversable.py`.
- `1719 passed`, `68 skipped`, `9 xfailed`:
  full `poetry run pytest engine/tests -q` regression after the completed Wave 5
  runtime simplification slice.

## Non-wave Stability Maintenance

The following recent changes improved correctness and CI stability, but are not
counted as Wave 4 completion work:

- media path-hardening and CodeQL-oriented story-media safety checks
- media fragment serialization and journal media-type normalization fixes
- provider-collection dedupe and resource-manager alias hardening
- REST choice payload migration to `choice_id` in app/server tests
- small service/core compatibility fixes discovered during CI and targeted test
  runs

## Next Execution Slice

1. Start Wave 6 by identifying remaining compatibility helpers with no internal
   references and remove only the ones that are now truly dead.
2. Refresh the hotspot metrics one more time and document where cognitive
   overhead improved even if line count did not.
3. Update the design docs and this tracker together as Wave 6 changes land so
   the architectural record stays current.
4. Rerun the full engine, media integration, and app/server story endpoint
   regressions for the Wave 6 closeout checkpoint.

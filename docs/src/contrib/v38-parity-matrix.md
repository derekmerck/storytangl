# V38 Parity Matrix (Phase 1)

## Status
- Date: 2026-02-19
- Phase: 1 (inventory and classification only)
- Scope lock: `engine/tests/core`, `engine/tests/vm`, `engine/tests/story`, `engine/tests/service`
- Explicitly out of first-pass classification scope: `engine/tests/integration`, `engine/tests/loaders`, `engine/tests/ir` (tracked as secondary references only)

## Purpose
This matrix classifies each in-scope legacy test module exactly once and maps it to either:
- `PORT_*`: move test intent into v38 behavior/contracts.
- `RETIRE_*`: remove from parity gate because behavior is gone, moved, or irrelevant.

This document is analysis-only and does not execute cutover work.

## Inventory Snapshot
- Total in-scope legacy modules: `125`
- By feature area:
  - `core`: 15
  - `vm`: 41
  - `story`: 56
  - `service`: 13
- By disposition:
  - `PORT_DIRECT`: 13
  - `PORT_ADAPT`: 72
  - `RETIRE_REMOVED`: 24
  - `RETIRE_MOVED`: 12
  - `RETIRE_IRRELEVANT`: 4
- By risk level:
  - `low`: 19
  - `medium`: 55
  - `high`: 51

## Disposition Legend
- `PORT_DIRECT`: same behavior intent, mostly namespace/type rename.
- `PORT_ADAPT`: behavior intent retained, assertions must be rewritten for v38 contracts.
- `RETIRE_REMOVED`: intentionally removed from v38 behavior.
- `RETIRE_MOVED`: concern moved out of this in-scope parity effort.
- `RETIRE_IRRELEVANT`: no meaningful mapping to v38 architecture.

## Target Resolution Status (PORT rows)
- `PORT_*` rows: `85`
- Missing `target_v38_test_path`: `0`
- Unique target modules: `33`
  - Existing targets: `21`
  - Planned targets: `12`

Planned target modules referenced by `PORT_*` rows:
- `engine/tests/service38/controllers/test_runtime_controller.py`
- `engine/tests/service38/controllers/test_user_controller.py`
- `engine/tests/service38/response/test_exports.py`
- `engine/tests/service38/test_api_endpoint.py`
- `engine/tests/service38/test_orchestrator.py`
- `engine/tests/story38/test_choice_availability.py`
- `engine/tests/story38/test_compiler_scope_resolution.py`
- `engine/tests/story38/test_journal_order.py`
- `engine/tests/story38/test_traversal_playthrough.py`
- `engine/tests/vm38/test_call_stack.py`
- `engine/tests/vm38/test_phase_integration.py`
- `engine/tests/vm38/test_provision_pipeline.py`

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
| engine/tests/core/record/test_content_addressable.py | core | RETIRE_REMOVED |  | tangl.core38.record.Record.hashable_content | v38 no longer carries a standalone ContentAddressable model and folds content hashing semantics into core38 record/entity traits. | low | mapped |
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
| engine/tests/service/test_orchestrator.py | service | PORT_ADAPT | engine/tests/service38/test_orchestrator.py | tangl.service38.orchestrator.Orchestrator38.execute | Orchestrator behavior remains core but should be validated against service38 hydration, policy, and writeback semantics. | high | mapped |
| engine/tests/service/test_orchestrator38.py | service | PORT_DIRECT | engine/tests/service/test_orchestrator38.py | tangl.service38.orchestrator.Orchestrator38 | This suite already targets service38 orchestrator behavior and should stay as direct parity evidence. | low | mapped |
| engine/tests/service/test_orchestrator_basic.py | service | PORT_ADAPT | engine/tests/service38/test_orchestrator.py | tangl.service38.orchestrator.Orchestrator38.execute | Orchestrator behavior remains core but should be validated against service38 hydration, policy, and writeback semantics. | high | mapped |
| engine/tests/service/test_response_contract.py | service | RETIRE_REMOVED |  | tangl.service38.gateway.ServiceGateway38.execute | Legacy native response/info model contracts are superseded by service38 gateway operation and runtime-envelope contracts. | high | mapped |
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
| engine/tests/vm/test_call_return_integration.py | vm | PORT_ADAPT | engine/tests/vm38/test_call_stack.py | tangl.vm38.runtime.ledger.push_call | Call/return stack behavior remains required but should be ported to vm38 frame+ledger stack semantics. | high | mapped |
| engine/tests/vm/test_call_stack.py | vm | PORT_ADAPT | engine/tests/vm38/test_call_stack.py | tangl.vm38.runtime.ledger.push_call | Call/return stack behavior remains required but should be ported to vm38 frame+ledger stack semantics. | high | mapped |
| engine/tests/vm/test_call_stack_persistence.py | vm | PORT_ADAPT | engine/tests/vm38/test_call_stack.py | tangl.vm38.runtime.ledger.push_call | Call/return stack behavior remains required but should be ported to vm38 frame+ledger stack semantics. | high | mapped |
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
| engine/tests/vm/test_update_markers.py | vm | RETIRE_REMOVED |  | tangl.vm38.runtime.ledger.get_journal | Marker-channel update slicing was replaced by step-based fragment retrieval in vm38 output streams. | medium | mapped |

# engine/tests skip/xfail triage

## Legend
- **Priority – High**: Blocks or risks core runtime behavior and should be addressed soon.
- **Priority – Medium**: Important guardrails or developer feedback; fix or rewrite when the owning area is next touched.
- **Priority – Low**: Legacy expectations or features no longer planned; keep skipped/xfail or replace with updated coverage only if the area is revived.
- **Priority – External**: Depends on optional services or credentials; keep guarded and document expectations.

## Core infrastructure

### Registry & Entity
- **`test_registry_prevent_duplicate`** – `xfail`
  - *Observation*: The test expects `Registry.add` to reject re-adding the same entity, but the current implementation simply overwrites the entry (no `allow_overwrite` hook).【F:engine/tests/core/test_registry.py†L36-L42】【F:engine/src/tangl/core/registry.py†L54-L58】
  - *Priority – Medium*: Silent overwrites make debugging harder in some domains; consider adding an explicit overwrite flag and updating the registry API when we next tighten persistence semantics. Until then, keep the xfail to remind us of the desired safeguard.
- **`test_predicate_satisfied`** – `xfail`
  - *Observation*: This instantiates `Entity(predicate=...)`, but `Entity` no longer exposes a `predicate` field; predicate gating moved to the `Conditional`/`Selectable` mixins.【F:engine/tests/core/test_entity.py†L27-L31】【F:engine/src/tangl/core/entity.py†L58-L101】【F:engine/src/tangl/core/entity.py†L226-L265】
  - *Priority – Low*: Replace the test with coverage for `Conditional.available` or remove it entirely; the current shape is incompatible with the model and not part of the target behavior.

### Dispatch handlers
- **`test_handler_satisfied_with_predicate_and_criteria`** – `skip`
  - *Observation*: The test relies on `Handler` supporting `caller_criteria`/`predicate` attributes that no longer exist; handlers now lean on `Selectable` semantics instead.【F:engine/tests/core/test_handlers.py†L120-L151】【F:engine/src/tangl/core/dispatch/handler.py†L58-L133】
  - *Priority – Medium*: Rewrite the test to exercise the current selection path (e.g., via `selection_criteria` on custom handler subclasses) when dispatch matching is revisited; until then the skip is appropriate.

### Structuring & persistence
- **`test_persistence_cold_load`** – `xfail`
  - *Observation*: The first half asserts that cold-loading with `StructuringHandler` should fail without a registered class. The pipeline now resolves by looking up `obj_cls` in `obj_cls_map`, which still raises `KeyError` when absent; the second half demonstrates the supported path via `Entity.structure` fallback.【F:engine/tests/core/test_structuring.py†L42-L60】【F:engine/src/tangl/persistence/manager.py†L19-L66】【F:engine/src/tangl/persistence/structuring.py†L39-L67】
  - *Priority – Medium*: Decide whether we want strict failures (then unmark xfail after confirming) or documented cold-loading. Clarify expected behavior and adjust the test to assert it.

### Graph & scope
- **`test_graph_prevents_duplicates` / `test_graph_missing_node_raises_key_err`** – module `skip`
  - *Observation*: These expect legacy constraints (re-adding nodes raises, `Graph.get` returning `None` raises `KeyError`). Current `Graph` permits re-add and `get` defers to `find_one`, so the legacy behavior is intentionally retired.【F:engine/tests/core/graph/test_graph_2.py†L24-L40】【F:engine/src/tangl/core/graph/graph.py†L68-L115】
  - *Priority – Low*: Keep skipped; document the new semantics in graph docs instead of reviving deprecated behavior.
- **`test_find_nodes`** – `xfail`
  - *Observation*: Expects `find_all(tags={"red"})` to treat tags as a subset match; `Entity.matches` compares equality unless the caller uses the `has_tags` predicate field.【F:engine/tests/core/graph/test_graph_2.py†L87-L109】【F:engine/src/tangl/core/entity.py†L77-L139】
  - *Priority – Medium*: Update the test (and any calling code) to query `has_tags` instead of `tags` if subset semantics are desired, then drop the xfail.
- **`test_subgraph_reparent_member_updates_parent_chain`** – `xfail`
  - *Observation*: Adding a member to a second subgraph leaves the first membership in place; `Subgraph.add_member` never removes the old parent, so `parent` still resolves via cached membership list.【F:engine/tests/core/graph/test_graph.py†L66-L75】【F:engine/src/tangl/core/graph/subgraph.py†L26-L48】
  - *Priority – High*: Reparenting is fundamental for editors; implement a `move_member`/automatic removal (or document multi-membership) and convert this to a passing test.
- **`test_domain_gating_via_predicate_excludes_unavailable_domain`** – `xfail`
  - *Observation*: Relies on helper factories (`make_domain`, `attach_domain_to_graph`, `build_scope`) that are no longer present, and assumes domains expose mutable `conditional` or `available` gates at runtime.【F:engine/tests/core/test_scope_and_domain.py†L62-L102】
  - *Priority – Medium*: Redesign gating tests around the current domain API once the gating story is reintroduced; for now, leave xfailed and track the missing helpers.

## Fragment & media resources
- **`test_group_creation_and_membership`** – `xfail`
  - *Observation*: The test expects `ContentFragment` instances to auto-populate `group_id`/role metadata, but fragments now only expose `member_ids` on the `GroupFragment` root; individual fragments do not carry group identifiers.【F:engine/tests/core/fragment/test_group_fragment.py†L10-L63】【F:engine/src/tangl/core/fragment/group_fragment.py†L12-L21】【F:engine/src/tangl/core/fragment/content_fragment.py†L11-L19】
  - *Priority – Medium*: Decide whether grouping should be encoded in child fragments (reinstating `group_id`) or whether clients should infer via the registry; update the API and test accordingly.
- **`test_resource_inventory_tag_get_aliases`** – `xfail`
  - *Observation*: `MediaResourceInventoryTag` exposes `content_hash` via `has_identifier`, but there is no `alias` attribute to satisfy `matches(alias=...)` as the test expects.【F:engine/tests/media/media_resource/test_media_rit_2.py†L32-L37】【F:engine/src/tangl/media/media_resource/media_resource_inv_tag.py†L21-L78】
  - *Priority – Medium*: Either add an `aliases`/`identifier_map` concept or rewrite the test to stick with `has_identifier`.
- **`test_compute_hash_caching`** – `xfail`
  - *Observation*: The caching decorator on `_from_path` is never triggered when constructing `MediaRIT(path=...)`, so cache counters stay at zero and the assertions fail.【F:engine/tests/media/media_resource/test_media_rit_2.py†L40-L54】【F:engine/src/tangl/media/media_resource/media_resource_inv_tag.py†L49-L74】【F:engine/src/tangl/utils/shelved2.py†L24-L117】
  - *Priority – Medium*: Either call `MediaRIT.from_source()` in the test or implement caching within the primary constructor.
- **SVG / image handler suites** – module `skip`
  - *Observation*: Tests under `svg_forge` and `svg_image_handler` point at deprecated APIs or known-broken image handlers.【F:engine/tests/media/media_creators/svg_forge/test_svg_forge.py†L1-L35】【F:engine/tests/media/media_creators/svg_forge/test_svg_image_handler.py†L1-L34】
  - *Priority – Low*: Leave skipped until the media tooling is refreshed or removed.
- **`test_elevenlabs`** – `skipif`
  - *Observation*: Requires ElevenLabs credentials; the skip guards against missing configuration.【F:engine/tests/media/media_creators/tts_forge/test_elevenlabs.py†L7-L36】
  - *Priority – External*: Keep the skip; document credential handling for environments that can run it.

## Mechanics
- **`test_ornament_details`** – `xfail`
  - *Observation*: Placeholder asserting `NotImplementedError` for richer ornament descriptions.【F:engine/tests/mechanics/look/test_ornament.py†L52-L56】
  - *Priority – Low*: Leave as a feature backlog note.
- **Game suites (`test_trivial_game.py`, `test_token_games.py`, `test_twentyone.py`)** – module `skip`
  - *Observation*: The entire modules are skipped pending refactors; individual tests still describe desired flows (e.g., scoring strategies, story context interaction).【F:engine/tests/mechanics/games/test_trivial_game.py†L1-L150】【F:engine/tests/mechanics/games/test_token_games.py†L1-L52】【F:engine/tests/mechanics/games/test_twentyone.py†L1-L37】
  - *Priority – Low*: These games are auxiliary; keep skipped until the mechanics roadmap prioritizes them.
- **`test_player_advantage` / `test_story_context_interaction`** – `xfail`
  - *Observation*: Depend on `TrivialGame` difficulty/graph hooks that no longer behave as written (e.g., handler using undefined `game` variable in scoring strategies).【F:engine/tests/mechanics/games/test_trivial_game.py†L125-L150】【F:engine/src/tangl/mechanics/games/trivial_game.py†L87-L144】
  - *Priority – Low*: Fix when the trivial game is brought back; otherwise leave documented as future work.
- **`test_name_sampler_variations`** – `xfail`
  - *Observation*: Our demographic dataset lacks consistent subtype coverage, so sampling by every country can raise `KeyError`.【F:engine/tests/mechanics/demographics/test_demographics_builtins.py†L42-L51】
  - *Priority – Medium*: When we enrich demographic data, revisit the sampler to either guard missing combos or ensure the fixtures cover them.

## Language integrations
- **LanguageTool / Reverso / Verbix tests** – `skipif` + `xfail`
  - *Observation*: All require external APIs; xfails mark expected `RemoteApiUnavailable` errors when services are offline.【F:engine/tests/lang/test_languagetool.py†L28-L45】【F:engine/tests/lang/test_lang_apis.py†L14-L82】
  - *Priority – External*: Keep guarded; ensure documentation covers enabling these tests in integration environments.
- **`test_thesaurus_loading` / `test_no_repeated_synonyms`** – `skip`
  - *Observation*: Depend on resource files/logic that are not packaged yet.【F:engine/tests/lang/test_thesaurus.py†L25-L38】
  - *Priority – Low*: Leave skipped until the reference lexicon ships.

## Virtual machine / planning
- **Provisioning pipeline xfails** – `test_provisioner_runs_offers_with_ns_and_returns_job_receipts`, `test_provisioner_blame_tuple_when_requirement_present`, `test_selector_prefers_lowest_priority_and_stable_ordering`, `test_equivalent_offers_are_deduplicated`, `test_affordance_creates_or_finds_source` – `xfail`
  - *Observation*: These encode the intended provisioning contract (namespaces passed through, blame tuples, priority selection, deduping offers, affordances materializing sources). Current implementation stubs or partially implements these paths, so the assertions fail.【F:engine/tests/vm/test_provisioning.py†L92-L137】【F:engine/tests/vm/test_provisioning.py†L217-L295】【F:engine/tests/vm/test_provisioning.py†L393-L406】
  - *Priority – High*: Provisioning is central to story runtime; schedule dedicated work to satisfy these tests and convert them into true regressions.
- **`test_preview_graph_is_copy`** – `xfail`
  - *Observation*: `Session.get_preview_graph` was removed for the MVP; the test still describes the desirable isolation semantics for watched graphs.【F:engine/tests/vm/test_events.py†L23-L33】
  - *Priority – Medium*: Either restore the preview helper or remove the test if the feature is out of scope.
- **`test_resource_inventory_tag_hash caching` interplay with provisioning** – already covered above under media.

## Utilities & diagnostics
- **`test_shelve_performance`** – `skip`
  - *Observation*: Benchmark-only workload guarded behind a skip to avoid long-running loops during CI.【F:engine/tests/utils/test_shelved2.py†L97-L115】
  - *Priority – Low*: Leave skipped; optional microbenchmark.
- **`test_resource_inventory_tag` xfails** – covered above.


## Overall recommendations
1. **Provisioning & graph reparenting** are the only high-priority items—they affect story planning fidelity. Schedule implementation work and flip those tests to required coverage.
2. **Medium-priority items** mostly need tests rewritten to match modern APIs (registry duplicates, handler selection, tagging queries, structuring expectations, media aliasing/caching, domain gating). Address them opportunistically during feature work to avoid stale expectations.
3. **Low-priority and external tests** document aspirational or integration-specific behavior. Leave their skip/xfail markers in place and update documentation so contributors understand the status quo.

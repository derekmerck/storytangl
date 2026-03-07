# `obj_cls` Inventory

## Status

- Last reviewed: March 6, 2026
- Migration status: active

## Summary

As of this review, `obj_cls` appears 144 times in the live tree:

- `engine/src`: 72
- `engine/tests`: 37
- `docs/src`: 34
- `worlds`: 1
- `apps`: 0

This count excludes `scratch/` and other legacy-only debris.

The main conclusion is that `obj_cls` is no longer the preferred runtime
vocabulary, but it still exists in three distinct roles:

1. Compatibility seams that accept or emit legacy payloads.
2. IR/schema helpers whose internal naming never got updated after the
   `kind` migration.
3. Historical docs, tests, and sample data that still describe the old term.

## Keep For Now: Compatibility Seams

These references still serve a migration purpose and should not be removed
blindly.

### Graph API aliasing

- `engine/src/tangl/core/graph.py`

`Graph.add_node`, `Graph.add_edge`, and `Graph.add_subgraph` still accept
`obj_cls` as a fallback alias when `kind` is not provided. This is a narrow
compatibility shim and matches the current cutover story.

**Recommendation:** keep until authored data and helper call sites stop passing
`obj_cls`.

### Persistence read/write compatibility

- `engine/src/tangl/persistence/structuring.py`
- `engine/src/tangl/persistence/manager.py`

The persistence layer currently:

- prefers `kind` on read,
- accepts legacy `obj_cls` on read,
- and emits both `kind` and `obj_cls` on write.

That is the clearest active compatibility seam in the runtime today.

**Recommendation:** eventually move to `kind`-only writes while preserving
`obj_cls` as a read alias for one deprecation window.

### Story-script ingestion compatibility

- `engine/src/tangl/story/fabula/compiler.py`

The story compiler still reads authored `obj_cls` values from script payloads
when resolving concrete kinds for scenes, blocks, actors, locations, and other
templated items.

**Recommendation:** keep until story/world fixtures and incoming authored
content have been normalized to `kind`.

### IR field aliasing

- `engine/src/tangl/ir/core_ir/base_script_model.py`

The IR base model still uses `obj_cls` as the serialized field alias, with an
internal `obj_cls_` attribute and `obj_cls` property.

**Recommendation:** this should survive until the story-script schema migrates,
but it is the canonical place where the old term is still embedded in public
serialized form.

## Rename Soon: Internal Helpers And Stale Names

These are mostly internal names that can be renamed with little or no wire
format impact.

### IR default-kind helpers

- `engine/src/tangl/ir/story_ir/actor_script_models.py`
- `engine/src/tangl/ir/story_ir/location_script_models.py`
- `engine/src/tangl/ir/story_ir/scene_script_models.py`
- `engine/src/tangl/ir/story_ir/story_script_models.py`

The helper name `get_default_obj_cls()` is stale. In v38 vocabulary this should
be `get_default_kind()`.

**Recommendation:** safe next-pass rename, provided callers are updated in the
same change.

### Dispatch placeholder naming

- `engine/src/tangl/ir/dispatch.py`

The placeholder `_update_obj_cls` name is stale even if the handler body is not
implemented yet.

**Recommendation:** rename to `_update_kind`.

### Utility naming

- `engine/src/tangl/utils/dereference_obj_cls.py`

This utility still describes the old vocabulary directly.

**Recommendation:** rename to a `kind`-based helper or fold it into the current
class-resolution utility surface if one already exists.

### Persistence variable naming

- `engine/src/tangl/persistence/manager.py`

`obj_cls_map` is an internal variable name that no longer matches the preferred
term.

**Recommendation:** rename to `kind_map` once the structuring API is updated.

### Type-hint/comment residue

- `engine/src/tangl/type_hints.py`
- `engine/src/tangl/media/media_creators/svg_forge/vector_spec.py`

These appear to be comment/example residue rather than active runtime API.

**Recommendation:** safe cleanup whenever the surrounding files are next
touched.

## High-Value Cleanup Targets

These are the best immediate targets because they either create confusion or
generate visible warning noise.

### Asset script field naming

- `engine/src/tangl/ir/story_ir/asset_script_models.py`

`AssetsScript` currently declares a field literally named `obj_cls` with
`alias="asset_cls"`. That is confusing on its own and also triggers the
Pydantic warning that shows up during the Sphinx build.

**Recommendation:** rename the internal field to something like `kind` or
`asset_kind`, keep `asset_cls` only if it is still needed as an external alias,
and avoid introducing new `obj_cls`-named schema fields.

### Mechanics compatibility wrapper

- `engine/src/tangl/mechanics/games/has_game.py`

This file still falls back to `graph.add_node(obj_cls=kind, ...)` when the graph
surface does not advertise `kind=`.

**Recommendation:** remove once all supported graph implementations are known to
accept `kind`.

## Fixtures, Tests, And Docs

These references are not runtime blockers, but they do obscure whether the
migration is really done.

### Tests

- `engine/tests/persistence/test_structuring_handler.py`
- `engine/tests/story38/test_story_init.py`
- `engine/tests/ir/*`

Most remaining test references are intentionally verifying compatibility. Those
should stay until the matching compatibility seam is retired.

### Sample/story data

- `worlds/reference/script.yaml`
- `engine/tests/resources/*.yaml`

Some sample authored data still uses `obj_cls`.

**Recommendation:** convert these to `kind` before removing compiler aliases so
fixtures model the intended vocabulary.

### Published docs and notes

- `docs/src/design/*`
- `docs/src/notes/migration/*`

Design and migration notes still refer to `obj_cls` where they discuss older
formats or transitional behavior.

**Recommendation:** keep historical mentions in migration notes, but update
stable design docs to prefer `kind` unless they are intentionally documenting a
legacy lane.

## Proposed Cleanup Order

### Phase 1: Safe internal renames

- Rename helper/function/variable names like `get_default_obj_cls`,
  `_update_obj_cls`, and `obj_cls_map`.
- Update comments and examples that are clearly stale.

### Phase 2: Clean the IR surface

- Rename `AssetsScript.obj_cls`.
- Decide whether `BaseScriptItem` should move to `kind` as the primary field
  with `obj_cls` preserved only as an input alias.

### Phase 3: Normalize fixtures and authored inputs

- Convert reference YAML and test fixtures from `obj_cls` to `kind`.
- Update story compiler tests so `kind` is the canonical authored form.

### Phase 4: Retire compatibility writes

- Change persistence unstructuring to emit `kind` only.
- Keep `obj_cls` accepted on read for one deprecation window if needed.

### Phase 5: Retire compatibility reads

- Remove `obj_cls` fallback handling from graph creation helpers and story
  compilation once fixtures and consumers are off the legacy term.

## Working Rule

Going forward, the intended model is:

- `kind` means the active Python class in memory.
- serialized data may use a string form temporarily, but it should hydrate to a
  class on read.
- `obj_cls` is legacy compatibility vocabulary and should not be introduced into
  new runtime APIs or schema fields.

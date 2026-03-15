# Media resurrection plan (`tangl.media`)

## Goal

Re-establish `tangl.media` as a first-class end-to-end pipeline that covers:

1. script-level media notation,
2. compile-time provisioning for static assets,
3. runtime journal fragment emission,
4. service-layer transformation into client-consumable resources,
5. optional adapter-driven generated media recipes (avatars, voice-over, etc.).

## Status

- March 9, 2026: Milestone 1 static-media plumbing is now wired through the v38 resolver path on `codex/v38-media`.
- March 14, 2026: Milestone 2 sync inline-spec generation is now wired through story materialization and the resolver path for story-scoped generated media.
- March 14, 2026: Milestone 3 server-side async lifecycle is now wired through story-scoped `MediaRIT` status transitions, guarded `@on_provision` reconcile/dispatch hooks, a `WorkerDispatcher` protocol, and fallback-first service rendering for pending or failed generated media.
- Implemented: authority-chain media inventory discovery, resolver offer generation for static media, story/world/sys inventory layering, canonical journal media fragments, shared service-layer dereference, `/media/story/{story_id}/...` serving, story-media cleanup on drop, inline `media.spec` loading for sync and async generation, story-scoped generated `MediaRIT` provenance, deterministic adapted-spec hashing and dedupe, typed render profiles, and server-side pending/fallback handling.
- Deferred: concrete worker backends, named `MediaSpecRegistry` templates, `GenerationHints` and richer authoring surfaces, the `get_media_registries` rename / dispatch-generalized media resolution, anticipatory affordance quota policy, and broader client capability negotiation beyond the current compatibility profiles.

## Current hooks and what they already provide

### Script and compile surfaces

- `MediaItemScript` already supports exactly-one-of declarations (`url`, `data`, `name`, `spec`) and a `media_role`. This is a strong contract to keep.  
- `StoryCompiler` still normalizes raw `media` lists onto blocks, while `StoryMaterializer` now translates static `name` media and supported inline `spec` media into `MediaDep` edges.
- `MediaCompiler` can index `world/media/**` into a `ResourceManager` and supports organization hints.

### Runtime and journal surfaces

- `Block.media` is currently `list[dict[str, Any]]` and remains payload-oriented.
- `render_block_media` now emits canonical `MediaFragment` payloads for resolved static media, sync-generated media, and bound async-generated providers (`content_format="rit"`, typed `MediaRIT` content, deterministic scope). Fallback text for pending/failed generated media is carried through to the service layer; malformed or unsupported specs still use the placeholder/fallback path.

### Service and transport surfaces

- Runtime controller compatibility path can dereference `MediaRIT` content into stable URLs (`/media/world/{world_id}/...`, `/media/sys/...`, `/media/story/{story_id}/...`) and now applies fallback-first behavior for pending or failed story-scoped generated media.
- Gateway hooks can still append URL placeholders for media fragments under a `media_url` render profile, but this path is intentionally generic and should remain the final compatibility fallback, not the primary resolver.

## Design principles for the resurrection

- Keep layer boundaries explicit:
  - **story/compile** decides intent and references,
  - **vm/journal** emits typed fragments,
  - **service** resolves transport resources.
- Preserve determinism:
  - static assets should resolve reproducibly,
  - generated assets should use auditable recipe + seed records.
- Prefer typed records/entities over free-form dicts in cross-layer handoff.

## Proposed target model

### 1) Script notation model

Keep `MediaItemScript` as canonical input shape with two categories:

- **Static declarations**
  - `name` (registry alias / filename)
  - `url` (external pass-through)
  - `data` (embedded literal media payload)
- **Potential declarations**
  - `spec` (recipe template to be adapted for story context)

Add a small typed discriminator at compile output (e.g., `media_source_kind: static|potential`) to avoid repeated string heuristics downstream.

### 2) Compile-time provisioning model

At world compile/load:

- Index static media directories into `ResourceManager` inventory.
- Translate static `name` declarations into requirements that bind deterministically to `MediaRIT`.
- Keep unresolved `spec` declarations as recipe templates (not generated yet unless policy says eager).

Suggested policy options:

- `static_only` (default): index files; do not generate.
- `eager_generate`: realize selected recipes at compile and register resulting `MediaRIT`.
- `lazy_generate`: defer recipe realization to runtime first use.

### 3) Story/runtime representation model

Represent block media as typed dependency descriptors rather than opaque dicts:

- static descriptor -> points to existing `MediaRIT` requirement,
- potential descriptor -> carries `MediaSpec` template + adaptation context.

Provisioning step should produce either:

- bound `MediaRIT` for static/past-generated media,
- or realized `MediaRIT` by invoking an adapter pipeline for potential media.

### 4) Journal fragment contract

Emit a normalized `MediaFragment` contract from story handlers:

- `fragment_type="media"`
- `media_role`
- `scope` (`world` / `sys` / external)
- one canonical content path:
  - `content_format="rit"` + `content=<MediaRIT>` for engine-internal pipeline,
  - `content_format="url"` for pass-through external references.
- optional caption/text metadata.

This makes service transforms simpler and allows profile-specific output (`raw`, `html`, `cli_ascii`) without shape drift.

### 5) Service-layer client resource model

Primary resolver behavior:

- resolve `content_format="rit"` via world/system resource manager into client URL plus `media_type`.
- preserve pass-through external URLs as-is.
- output flattened JSON transport fragments.

Fallback compatibility behavior:

- keep gateway `media_url` transform for non-normalized payloads while migration is active.

## Layered media inventories and capability matrix

Media resolution should follow three explicit inventory layers, mirroring dispatch-style layering:

1. **System inventory (`sys`)**
   - Public/shared static assets (branding, UI chrome, install-level banners).
   - Loaded once per backend and reused across worlds/stories.

2. **World inventory (`world`)**
   - Static assets and optional compile-time generated assets for a world.
   - Shared by all stories instantiated from that world.

3. **Story inventory (`story`)**
   - Dynamic media created or assembled for one story instance and current context.
   - Scoped to ledger/story lifecycle and safe to evict when story is dropped.

Resolution order for media requests should be `story -> world -> sys` unless a scope is explicitly pinned.

### Availability and policy matrix

The same media declaration may be constrained by both backend capabilities and client render profiles.

- **Backend capability examples**
  - supports dynamic image generation
  - supports text-to-speech audio generation
  - supports vector composition only

- **Client profile examples**
  - accepts raster images
  - accepts audio playback
  - text-only / cli-ascii mode

Policy evaluation should therefore gate media realization on the cross-product:

- `inventory scope` × `media data type` × `backend capability` × `client profile policy`.

When unavailable:

- emit deterministic diagnostics to journal/service metadata,
- fall back to permitted alternatives (e.g., text caption, placeholder token),
- avoid silent failure.

## Static vs potential media lifecycle

### Static media (compile-indexed)

1. bundle load indexes media files,
2. script `name` resolves by alias/hash/path,
3. provisioning binds requirement -> `MediaRIT`,
4. journal emits `MediaFragment(content=rit, content_format="rit")`,
5. service dereferences into URL.

### Potential media (adapter recipe)

1. script provides `spec` template,
2. adapter selection uses concept + role + world policy,
3. adapter materializes output and returns `(realized_spec, media_data|path)`,
4. output registered as `MediaRIT` with deterministic identifiers,
5. journal and service follow same `rit` flow as static media.

Persist recipe metadata (adapter id, model/version, seed, prompt/context hash) so reruns are reproducible/auditable.

## Phased implementation plan

### Phase 0 — Pin current contracts (now)

- Add/keep tests for:
  - media compiler indexing with organization hints,
  - gateway media URL compatibility transform behavior,
  - runtime dereference URL conventions for world/sys scopes.

### Phase 1 — Typed media declaration handoff

- Introduce typed block-level media declaration model (compile output type).
- Update `render_block_media` to emit canonical `MediaFragment` shape for static declarations.
- Maintain backward compatibility for legacy dict payloads.

### Phase 2 — Provisioning integration

- Status: landed for static media plus inline `media.spec` sync generation and server-side async lifecycle records.
- Route typed declarations through `MediaProvisioner` policies.
- Bind static requirements and emit unresolved diagnostics for missing aliases.
- Record reuse vs creation via spec-hash-based dedupe and generated-media provenance.

### Phase 3 — Adapter recipe pipeline

- Status: protocol/orchestration slice landed; concrete workers remain next.
- Define adapter interface for potential media generation.
- Implement reference adapters (avatar image recipe, voice-over recipe) behind `WorkerDispatcher`.
- Add lazy/eager generation policies and deterministic seed strategy.

### Phase 4 — Service resource unification

- Status: largely landed for the runtime controller path; compatibility gateway path remains.
- Consolidate media dereference logic behind one service helper used by runtime controller and gateway hook path.
- Deprecate URL placeholder transform except as explicit fallback mode.

### Phase 5 — Docs and migration

- Publish media script authoring guide and client fragment contract.
- Mark legacy dict payload media path deprecated with timeline.

## Risks and mitigations

- **Risk:** shape drift between journal and service transforms.  
  **Mitigation:** snapshot tests over serialized fragment payloads.

- **Risk:** nondeterministic generated media.  
  **Mitigation:** require recipe metadata + seed persistence and hash-based IDs.

- **Risk:** adapter coupling leaking into core/vm.  
  **Mitigation:** keep adapters in service/media layer and pass only typed records into lower layers.

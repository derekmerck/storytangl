# tangl.media — Design Notes

> Status: Current contract
> Authority: Canonical journal fragment types live in `tangl.journal.fragments`; `tangl.journal.media` remains a compatibility re-export surface.
>
> Architectural intent, design decisions, and rationale for the canonical media
> package of the StoryTangl narrative engine.
> This document describes the current v3.8 framework. The source packages are
> `tangl.core`, `tangl.vm`, `tangl.story`, `tangl.service`, and `tangl.media`
> (no version suffix).
>
> The static media pipeline (file-based assets through to service-layer payload
> resolution) is wired and tested. The generative creator pipeline now has real
> sync/async lifecycle infrastructure plus a deterministic in-process checker
> harness, but external worker-backed forges are still provisional. This note
> describes the implemented architecture and the design commitments for the
> still-evolving creator layer.
>
> The package-level architecture is canonical here. Broader design documents
> under `docs/src/design/` remain useful for subsystem history, rationale, and
> roadmap details, even where some older terminology survives.

---

## Position in the Architecture

Media is a satellite package that provides resource inventory, provisioning, and
creator infrastructure for non-textual narrative content, images, audio, video,
vectors. It sits alongside the core→vm→story→service stack rather than inside it:

```text
Service  → Dereferences MediaRIT → client-facing URLs/data  (service/media.py)
Story    → Declares media deps, emits MediaFragment in journal  (story/system_handlers.py)
VM       → Resolves MediaDep edges during PLANNING  (vm provisioning)
Media    → Inventory, provisioning offers, creator pipeline  ← this document
Core     → Entity, Registry, Record primitives used by media types
```

Media types are imported by story (for dependency wiring) and by service (for
dereferencing). Media does not import from story or service. The
`tangl.journal.fragments` module defines `MediaFragment` and `StagingHints` as
cross-cutting output types that both story and service consume; the
`tangl.journal.media` package remains a compatibility re-export.

### Litmus Test

| Question                                                    | Layer             |
|-------------------------------------------------------------|-------------------|
| Does it track, index, or inventory media resources?         | Media             |
| Does it define how a media resource becomes a URL or data?  | Service           |
| Does it declare which block needs which media?              | Story             |
| Does it generate media from specs (images, audio, SVG)?     | Media (creators)  |
| Does it emit media references into the journal stream?      | Story             |

### Media's Defining Characteristic

Media provides **resource indirection**. Authored scripts reference media by
name, path, inline data, or generative spec. The media package inventories those
references, wraps them in content-addressed `MediaRIT` entities, and resolves
them through the same dependency/provisioning machinery that the VM uses for
concepts. The service layer dereferences the final `MediaRIT` into a
transport-appropriate format (URL, inline data, passthrough path) — media
itself never decides how content reaches the client.

---

## Media Module Map

```text
tangl.media
├── Types          → media_data_type.py    (MediaDataType enum: IMAGE, VECTOR, AUDIO, etc.)
│                  → media_role.py         (MediaRole enum: narrative_im, dialog_im, etc.)
│                  → type_hints.py         (Media type aliases)
├── Resource       → media_resource/
│                  → media_resource/media_resource_inv_tag.py  (MediaRIT: content-addressed entity)
│                  → media_resource/media_resource_registry.py (MediaResourceRegistry)
│                  → media_resource/media_inventory.py         (MediaInventory: provisioner-facing adapter)
│                  → media_resource/media_dependency.py        (MediaDep: dependency edge for media)
│                  → media_resource/media_provisioning.py      (MediaProvisioner, MediaInventoryProvisioner, MediaSpecProvisioner)
│                  → media_resource/resource_manager.py        (ResourceManager: directory indexing + lookup)
├── Creators       → media_creators/
│                  → media_creators/media_spec.py             (MediaSpec, MediaResolutionClass, on_adapt_media_spec, on_create_media)
│                  → media_creators/checker_forge/            (deterministic in-process harness)
│                  → media_creators/svg_forge/                (SVG composition, partial)
│                  → media_creators/stable_forge/             (Stable Diffusion adapters, partial)
│                  → media_creators/tts_forge/                (text-to-speech adapters, stub/partial)
│                  → media_creators/raster_forge/             (raster assembly, stub)
├── Runtime hooks  → phase_hooks.py                           (pending-job reconcile/dispatch once per planning pass)
│                  → worker_dispatcher.py                     (async submit/poll result protocol)
├── Dispatch       → dispatch.py                              (media_dispatch registry, MediaTask)
│                  → dispatch_handlers.py                     (system resource manager provider)
├── Scoping        → story_media.py                           (story-scoped ResourceManager factory)
│                  → system_media.py                          (system-scoped ResourceManager singleton)
└── Journal (separate package)
                   → tangl.journal.media/media_fragment.py    (MediaFragment: journal output type)
                   → tangl.journal.media/staging_hints.py     (StagingHints: client presentation metadata)
```

---

## How Media Dependencies Differ from Concept Dependencies

Media provisioning reuses the VM's dependency/offer/resolver machinery but differs
from concept provisioning in several important ways. Understanding these
differences is key to understanding the media package.

### Same Pattern

Both media and concept dependencies follow the same structural lifecycle:

1. **Script declares** intent (a block needs an image; a scene needs an actor)
2. **Compiler creates** a dependency edge with an open destination
3. **Planning resolves** the dependency by finding or creating a provider
4. **Journal emits** a fragment referencing the resolved provider
5. **Service dereferences** the provider for client delivery

Both use `Dependency` edges, `Requirement` specifications, `ProvisionOffer`
objects, and the resolver's offer-selection pipeline. `MediaDep` extends
`Dependency[MediaRIT]` just as `Role` extends `Dependency[Actor]`.

### Key Differences

**Media dependencies are typically soft.** Missing an actor for a role is usually
a hard failure; the scene cannot render without its villain. Missing a background
image is usually a soft failure; the prose still works, the client shows a
placeholder or nothing. This is reflected in `MediaDep` defaulting
`hard_requirement=False`.

**Media has specialized provisioners.** Concept provisioning uses the VM's
`FindProvisioner`, `TemplateProvisioner`, and `TokenProvisioner` through
standard dispatch hooks. Media provisioning uses:

- `MediaProvisioner` for direct registry/path/data-backed matches
- `MediaInventoryProvisioner` for authority-chain inventory matches
- `MediaSpecProvisioner` for dependency-carried inline `MediaSpec` objects

The offer interface is the same (`ProvisionOffer`), but the search spaces are
different.

**Media inventories are scoped by deployment, not by graph hierarchy.**
Concept templates live in the story's `TemplateRegistry` and are scoped by the
graph hierarchy. Media inventories are scoped by deployment topology:

| Scope     | Source                           | Lifecycle          |
|-----------|----------------------------------|--------------------|
| `sys`     | System media directory           | Process lifetime   |
| `world`   | World bundle media directories   | World load lifetime|
| `story`   | Story-instance media directory   | Story session      |

Resolution order is `story → world → sys` unless scope is explicitly pinned.
This mirrors the dispatch authority chain but operates on registries of media
files, not on behavior registries.

**Media has a creator pipeline that concepts do not.** Concepts are found or
created from templates; both are graph-native operations. Media can additionally
be *generated* from specs via external services or local forges (image
generation, TTS, SVG composition, deterministic test harnesses). The creator
pipeline (`MediaSpec` → adapt → create/register) has no concept-side equivalent
because concept creation is always structural.

**MediaRIT is content-addressed; concepts are identity-addressed.** A `MediaRIT`
is identified primarily by content hash or adapted-spec hash; two identical files
are the same resource regardless of filename. Actors and locations are identified
by `uid`; two actors with identical fields are still different entities.
Content-addressing enables deduplication and caching across stories and sessions.

---

## Component Design

### MediaResourceInventoryTag (MediaRIT)

The indirection entity that decouples narrative references from actual media
storage. A `MediaRIT` wraps one media resource (an image, an audio clip, an SVG
document) and provides:

- **Content hash** for content-addressed deduplication and caching
- **Data type** classification (`IMAGE`, `VECTOR`, `AUDIO`, etc.)
- **Source reference** — one of file path, in-memory data, or generated-spec provenance
- **Lifecycle metadata** — status, worker/job info, timestamps, persistence policy
- **Spec provenance** — adapted/executed spec payloads and hashes for generated media

`MediaRIT` extends `RegistryAware` and `ContentAddressable`. It does *not*
extend `GraphItem`; RITs can live in registries outside any graph. When a media
dependency is resolved, the accepted RIT may be copied into the story graph as a
graph-local entity, but inventory-scoped registries remain the authoritative
source for static assets.

**What a MediaRIT does NOT carry:** client-relative URLs, transport format
decisions, or presentation hints. Those belong on `MediaFragment` (journal layer)
and the service dereferencing pipeline.


### MediaDep (`media_dependency.py`)

Dependency edge linking a structural node to a media resource.
`MediaDep(Dependency[MediaRIT])` with a `model_validator` that constructs a
standard `Requirement` from authored media declaration fields (`media_id`,
`media_path`, `media_data`, `media_spec`).

**Dual representation.** `MediaDep` carries both the structured declaration
fields (`media_id`, `scope`, `media_role`, `script_spec`, `realized_spec`,
`final_spec`) and the derived `Requirement` that the provisioning pipeline
consumes. The declaration fields are authoring provenance; the requirement is
the live provisioning contract.

**Three resolution paths based on authored input:**

1. **`media_id` or `media_path`** → identifier-based lookup in media registries.
   The requirement carries `has_identifier` and `authored_path`.
2. **`media_data`** → inline data. The requirement carries a fallback template
   `MediaRIT` for direct use.
3. **`media_spec`** → generative recipe. The spec is stored on the dependency and
   fed into the spec provisioner at planning time.


### Provisioners (`media_provisioning.py`)

Three provisioner types generate offers for media dependencies:

**`MediaProvisioner`** operates on directly attached `MediaResourceRegistry`
instances. It searches by identifier, and if CREATE policy is allowed and a
template with inline data exists, creates a new RIT and registers it.

**`MediaInventoryProvisioner`** operates on authority-chain-discovered
`MediaInventory` instances. It searches all inventories with a selector derived
from the requirement and offers EXISTING matches. The accept callback produces a
graph-local copy of the candidate RIT when needed.

**`MediaSpecProvisioner`** operates on dependency-carried inline `MediaSpec`
objects. It adapts the spec against runtime context, uses the adapted-spec
fingerprint as the identifier, reuses an existing story-scoped RIT when present,
or offers CREATE through `materialize_rit_from_spec`.

All three yield standard `ProvisionOffer` objects that the resolver's selection
pipeline ranks and accepts.


### ResourceManager (`resource_manager.py`)

Directory indexing and lookup utilities for one inventory scope. A `ResourceManager`
wraps a `MediaResourceRegistry` with:

- **`index_directory(subdir)`** — scans a folder, creates `MediaRIT` entries,
  applies default tags and optional index handlers
- **`register_file(path)`** — indexes one newly created file into the registry
- **`get_rit(alias)`** — lookup by label, identifier, hash, or relative filename
- **`get_url(rit)`** — deterministic URL-style path derivation from content hash

Two factory functions create scoped managers:

- **`get_system_resource_manager()`** — cached singleton for the system media
  directory. Loaded once per process.
- **`get_story_resource_manager(story_id)`** — per-story directory. Created on
  demand and removed when a story is dropped.

World-scoped managers are created by loader/compiler infrastructure during world
loading and attached to world facets.


### MediaFragment and StagingHints (`tangl.journal.fragments`)

These live in `tangl.journal.fragments`, not in `tangl.media`, because they are
cross-cutting output types consumed by both story (emission) and service
(dereferencing). `tangl.journal.media` remains a compatibility import path.

**`MediaFragment(ContentFragment)`** carries:

- `content` — a `MediaRIT`, URL string, raw data, or dict payload
- `content_format` — `"rit"`, `"url"`, `"data"`, `"json"`, `"xml"`
- `content_type` — `MediaDataType` classification
- `media_role` — narrative intent (for example `"narrative_im"`, `"dialog_im"`)
- `scope` — inventory scope for service-layer resolution
- `staging_hints` — optional `StagingHints` for client presentation

**`StagingHints`** carries client-facing suggestions: shape, size, position,
transition, duration, timing. These are hints, not commands; the client decides
how to interpret them based on its capabilities.

**The RIT-to-client boundary.** Story journal handlers emit
`MediaFragment(content=rit, content_format="rit")`. The service layer's
`media_fragment_to_payload` translates RIT content into client-appropriate URLs,
inline data, passthrough paths, poll directives, or fallback content. This is
the one place where media indirection is resolved; story code never constructs
client-facing media payloads.


### Creator Pipeline (`media_creators/`)

Infrastructure for generating media from declarative specs. This is the least
mature part of the media package, but it is no longer just scaffolding: the
dispatch registries, spec base class, sync/async lifecycle hooks, and a
deterministic checker harness are all active.

**`MediaSpec(Entity)`** is the base class for generation specifications. It
provides two dispatch-backed methods:

- `adapt_spec(ref, ctx)` → dispatches through `on_adapt_media_spec` to inject
  context-specific details (for example character appearance into an image prompt)
- `create_media(ref, ctx)` → dispatches through `on_create_media` to invoke the
  appropriate forge, returning `(media_data, realized_spec)`

**`on_adapt_media_spec`** uses pipeline aggregation; each handler can refine the
spec progressively. **`on_create_media`** uses first-result aggregation; the
first forge that handles the spec type wins.

**Creator implementations currently present:**

| Forge | Media type | Status |
|-------|------------|--------|
| `checker_forge` | IMAGE | Active deterministic harness used to prove sync/async pipeline slices |
| `svg_forge` | VECTOR | Partial — group/transform/viewbox infrastructure exists |
| `stable_forge` | IMAGE | Partial — API client and spec model exist |
| `tts_forge` | AUDIO | Partial/stub — API clients exist, worker-backed flow deferred |
| `raster_forge` | IMAGE | Stub |

The creator pipeline will continue to change as worker-backed forges take final
shape. The stable commitments are the dispatch pattern, the two-phase
adapt→create contract, and the use of story-scoped generated RITs as the
topological satisfaction point for media deps.


### Dispatch and Phase Hooks (`dispatch.py`, `dispatch_handlers.py`, `phase_hooks.py`)

`media_dispatch` is a standalone `BehaviorRegistry` for media-specific tasks.
Today it has one concrete task: `GET_SYSTEM_RESOURCE_MANAGER`, which returns the
cached system-level `ResourceManager`. This exists so the system media manager
can be overridden or extended without import-time coupling.

The package also installs VM `on_provision` hooks in `phase_hooks.py`:

- **`reconcile_media_jobs`** polls async worker jobs once per planning pass and
  updates story-scoped pending/running RITs
- **`dispatch_media_jobs`** submits newly accepted pending RITs once per
  planning pass

These hooks make the async creator lifecycle part of ordinary planning rather
than a separate sidecar pipeline.

---

## Cross-Cutting Design Decisions

### Media as a Symmetric Partner to Prose

The media package handles the *non-textual* output dimension of narrative:
images, audio, video, vectors. A future or expanding prose system handles the
*textual* output dimension: narrator voice, character speech, focalization,
epistemic state.

These are symmetric concerns:

| Dimension | Input | Adaptation | Output |
|-----------|-------|------------|--------|
| **Media** | `MediaSpec` | `on_adapt_media_spec` (context → refined spec) | `MediaRIT` → `MediaFragment` |
| **Prose** | intent/template | discourse context → refined text | prose fragments |

Both follow the same pattern: authored intent is adapted to runtime context,
then materialized into a concrete artifact. Both produce journal fragments that
the service layer transforms for client delivery. The media package establishes
the dispatch-backed adapt/create pattern that prose-adjacent systems can reuse.

### Indirection Through Content-Addressed Inventory

The `MediaRIT` layer exists so that narrative structure never carries raw media
bytes or transport URLs. Scripts reference media by name or spec; the inventory
resolves names to content-addressed entities; the service layer resolves entities
to client formats. This three-step indirection enables:

- **Deduplication** — same image used in ten scenes is stored once
- **Caching** — content hash is a natural cache key
- **Transport independence** — same RIT becomes a URL, inline blob, or path
  depending on client
- **Reproducibility** — content hash or adapted-spec hash in the patch log proves
  exactly which media was selected or generated

### Scoped Inventories Mirror Dispatch Authorities

The three inventory scopes (`sys`, `world`, `story`) mirror the three dispatch
authority tiers (global, application, local). This is not accidental; media
resources have the same scoping semantics as behavior registries:

- System media are available everywhere (like global dispatch handlers)
- World media are available to all stories from that world (like application
  handlers)
- Story media are available only to one story instance (like local handlers)

Resolution order (`story → world → sys`) ensures the most specific scope wins,
just as local dispatch handlers override application handlers.

### Soft Dependencies by Default

Media declarations default to `hard_requirement=False`. A story should still be
playable, still produce coherent prose and choices, when media is unavailable.
This is both a practical concern (generated media may be slow or fail) and a
philosophical one: the journal's textual content is the primary narrative
artifact; media enriches it but does not replace it.

Authors can override with `hard_requirement=True` for cases where media is
structurally necessary (for example a puzzle that requires examining an image).

---

## Architectural Principles at the Media Layer

### Inventory, Not Generation

The core media pipeline is about *tracking and resolving references*, not about
*creating content*. The creator pipeline is an optional extension. A fully
functional media system can run entirely on pre-authored static assets. This
keeps the critical path simple and testable.

### Same Offer Protocol, Different Search Spaces

Media provisioners yield the same `ProvisionOffer` objects as concept
provisioners. The resolver does not need to know whether it is selecting an
actor or an image; it sees offers with policies, priorities, and callbacks. The
search spaces are different (media registries vs. entity groups), but the
selection mechanics are identical. This reuse is deliberate and should be
preserved.

### Creator Pipeline Is a Deferred-But-Real Concern

The adapt/create dispatch infrastructure exists, the pending-RIT lifecycle is
wired into planning, and the checker harness proves the sync and async code
paths. But worker-backed external forges, named spec registries, richer authoring,
and anticipatory affordances are still in motion. Current decisions (spec base
class, two-phase dispatch, pending RIT as topological satisfaction, first-result
aggregation for creation) are commitments; specific forge backends are not.

---

## Related Documents

| Document | Location | Status |
|----------|----------|--------|
| Detailed media subsystem design | `docs/src/design/MEDIA_DESIGN.md` | Current detailed design, but some older terminology is historical |
| Generative media design | `docs/src/design/GENERATIVE_MEDIA_DESIGN.md` | Current active implementation/design note |
| Media resurrection plan | `docs/notes/media_resurrection_plan.md` | Current execution plan |
| Media client contract | `docs/notes/media_client.md` | Current (JSON fragment examples) |
| Media creator notes | `engine/src/tangl/media/media_creators/notes.md` | Stub (forge vocabulary) |
| Presence/prose contract | `docs/src/design/story/PRESENCE_PROSE_CONTRACT.md` | Active spike (symmetric to media) |
| Story design | `engine/src/tangl/story/STORY_DESIGN.md` | Current |
| VM design (provisioning) | `engine/src/tangl/vm/VM_DESIGN.md` | Current |
| Service design | `engine/src/tangl/service/SERVICE_DESIGN.md` | Current |

---

*See `STORY_DESIGN.md` for how story declares and emits media dependencies.
See `VM_DESIGN.md` for the provisioning mechanics that media provisioners
participate in. See `SERVICE_DESIGN.md` for how the service layer dereferences
`MediaRIT` into client-facing formats.*

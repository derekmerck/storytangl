# Generative Media Design

**Status:** DESIGN + PARTIAL IMPLEMENTATION — extends [`MEDIA_DESIGN.md`](MEDIA_DESIGN.md)
and [`media_resurrection_plan.md`](../notes/media_resurrection_plan.md)  
**Scope:** Async generative pipeline, pending-RIT lifecycle, spec registry and provisioner,
phase-bus integration, and service-layer response profiles.  
**Prerequisite:** Media resurrection plan Phase 1–2 (static RIT plumbing) must be complete.  
**Implementation order:** Sync-first (§3.5–3.6 prove the architecture without workers),
then server-side async lifecycle, then concrete worker backends, then anticipatory affordances.

---

## Implementation Status

- **March 14, 2026:** The sync-first slice is now implemented for inline `media.spec`
  declarations. Story materialization creates real `MediaDep` edges for supported inline
  specs, sync generation writes deterministic story-scoped files, generated `MediaRIT`s
  carry provenance plus a spec fingerprint for dedupe, and the existing journal/service
  path now emits canonical story media URLs for those generated resources.
- **March 14, 2026:** The server-side async lifecycle is now implemented on the same
  inline-spec path. Story-scoped generated `MediaRIT`s can be `PENDING | RUNNING |
  RESOLVED | FAILED`, guarded `@on_provision` hooks reconcile and dispatch worker jobs
  once per planning pass, deterministic adapted-spec hashing commits seeds for dedupe,
  and service dereference now applies fallback-first handling with typed resolve
  results.
- **Still deferred:** concrete worker backends, named `MediaSpecRegistry` templates,
  `GenerationHints`, `get_media_registries` / dispatch-generalized media resolution,
  and anticipatory affordance quotas.

---

## Context and Motivation

The resurrection plan establishes the static media pipeline: compile-time indexing, inventory
lookup, RIT-backed `MediaFragment` emission, and service-layer deref. That pipeline is
synchronous end-to-end — by the time a fragment is emitted the RIT is fully resolved.

Generative media (Stable Diffusion portraits, TTS voice-overs, assembled paperdolls) does not
fit that model cleanly. Some creation is fast enough to block on (SVG paperdoll assembly), some
is acceptable as a planning-time synchronous call, and some is too slow to block on in any
real-time context (SD image generation, 5–30s). A pure "block until ready" model either makes
the engine unusably slow or forecloses fast generative media entirely.

This document defines the design that allows all three regimes to coexist under a single
provisioning model, with no special-case logic in the fabula, VM, or journal layers.

---

## Design Summary

The central insight is: **a pending RIT is topologically satisfying**. Once a dep's `provider_id`
is set, that dep is claimed — no reprovisioning, no re-dispatch. Whether the RIT holds resolved
data or is still waiting on a remote job is a render-time concern, not a graph concern. The only
code that needs to care is service-layer media resolution at the boundary.

Supporting structures:

- `MediaRITStatus` enum — `PENDING | RUNNING | RESOLVED | FAILED` (four states; `job_id` is evidence, not state)
- `MediaPersistencePolicy` enum — `EPHEMERAL | CACHEABLE | STORY_CANONICAL | EXTERNAL_REFERENCE`
- `MediaResolutionClass` enum — `INLINE | FAST_SYNC | ASYNC | EXTERNAL` (replaces `sync_ok: bool`)
- Three-phase RIT identity — `adapted_spec_hash` (planning-time dedupe key), `execution_spec_hash` (post-completion reproduction key), and `content_hash` (output bytes)
- Deterministic `adapt_spec()` / `spec_fingerprint()` behavior — normalized payloads omit transient identity fields and commit a seed before hashing when the spec supports one
- `MediaSpecProvisioner` — implemented today for dependency-carried inline specs; named `MediaSpecRegistry` templates remain the next authoring-layer extension
- Two thin phase-bus hooks — implemented as guarded `@on_provision` reconciliation and dispatch passes that run once per `PhaseCtx`
- `MediaRenderProfile` + typed resolve-result objects at the service boundary; extracting a formal `resolve_media_data` dispatch task is still future work

---

## Part 1: Pending-RIT Lifecycle

### 1.1 RIT Identity Is Simpler Than It Looks

The apparent problem — "catalog RIT UUIDs are ephemeral, story RIT paths aren't portable" —
dissolves under the final model. `provider_id` stays UUID throughout, no type change required.

**Catalog RITs** (indexed from disk into world/sys `MediaResourceRegistry`): these are not
story graph nodes. The dep's `has_identifier` carries the *content hash* — the durable
cross-session key. The provisioner's EXISTING search through `get_media_inventories` finds
the freshly-indexed RIT by content hash each session. UUID only matters at runtime within
one session; content hash is the durable identity.

**Story RITs** (generated): full graph nodes, UUID stable for the story lifetime. `path`
points to the story media directory. If the path is stale on restore (storage moved, server
migrated), `resolve_media_data` rebinds it lazily at serve time by scanning the story
media directory for a file matching the content hash — using the same `ResourceManager` /
`from_source` / `@shelved` machinery. No startup scan, no `_init_media` validator needed.

**Files stay human-readable.** Backing files use authored names or convention-based names
(`avatar-mary-happy.png`, `cassie-portrait-neutral-v3.png`). The RIT's content hash is the
lookup key; the filename is a human-readable label. This is exactly what the `ResourceManager`
was built to solve: scan a directory, hash the contents, make files findable by hash without
requiring hash-based filenames.

### 1.2 RIT Lifecycle State

Four states. `job_id` is evidence that a job exists; it is not the state carrier.

```python
class MediaRITStatus(str, Enum):
    PENDING  = "pending"   # accepted by provisioner; job not yet dispatched
    RUNNING  = "running"   # job dispatched; worker has acknowledged
    RESOLVED = "resolved"  # path or data present, content_hash valid
    FAILED   = "failed"    # terminal; fallback policy applies
```

State transitions:
```
CREATE offer accepted → PENDING
post-PLANNING hook dispatches job → RUNNING  (job_id set)
pre-PLANNING poll: success → RESOLVED        (path set, content_hash valid)
pre-PLANNING poll: failure → FAILED          (derivation_spec retained for re-dispatch)
```

`PENDING` with no `job_id` = accepted but not yet dispatched (end of this PLANNING pass).
`RUNNING` with `job_id` = dispatched and acknowledged.
Both states block rendering; the distinction aids debugging and observability.

A PENDING or RUNNING RIT may have no `path`, `data`, or `preset_content_hash`.
Guard `_validate_required_source`: require at least one only when `status == RESOLVED`.

### 1.3 Persistence Policy

Generated media needs an explicit persistence policy for replay and audit correctness.
Without it the system works operationally but is philosophically half-integrated with
StoryTangl's event-sourced model.

```python
class MediaPersistencePolicy(str, Enum):
    EPHEMERAL          = "ephemeral"          # may be discarded/regenerated freely
    CACHEABLE          = "cacheable"          # regenerable from derivation metadata
    STORY_CANONICAL    = "story_canonical"    # this exact result is part of story history
    EXTERNAL_REFERENCE = "external_reference" # source of truth is elsewhere (CMS, CDN)
```

`STORY_CANONICAL` means replay must reproduce the same bytes or fail explicitly —
re-generation is not a silent substitute. `CACHEABLE` means re-generation from
`derivation_spec` is acceptable if the file is missing.

`persistence_policy` is an authoring annotation on `MediaSpec`, not computed at runtime.
Default is `CACHEABLE`. Authors mark portrait slots `STORY_CANONICAL` when the specific
generated result is part of the narrative record (e.g. a character's appearance is now
established for this story).

### 1.4 Three-Phase RIT Identity

A story-scoped RIT acquires identifiers progressively over its lifecycle. They answer
different questions and coexist on the same record:

| Phase | Field | Hash of | Answers |
|---|---|---|---|
| PLANNING | `adapted_spec_hash` | Adapted spec (fully rendered, seed committed) | "Would this namespace state produce this asset?" |
| RESOLVED | `execution_spec_hash` | Executed spec (worker's accounting of what ran) | "Can I exactly reproduce this output?" |
| RESOLVED | `content_hash` | Output file bytes | "Do I already have this file?" |

`adapted_spec_hash` is set when the RIT is created, including for `PENDING` RITs. It is the
dedup key for EXISTING searches and the compatibility successor to `spec_fingerprint`.
`execution_spec_hash` is set when the worker returns and captures the exact realized run.
`content_hash` remains the output-identity hash already provided by `ContentAddressable`.

### 1.5 Provenance Fields on MediaRIT

For cacheable and story-canonical generated media, provenance needs to preserve author
intent, the rendered request, and the worker's final accounting separately:

```python
class MediaResourceInventoryTag(RegistryAware, ContentAddressable):
    # ... existing fields ...
    status: MediaRITStatus = MediaRITStatus.RESOLVED
    job_id: str | None = None
    persistence_policy: MediaPersistencePolicy = MediaPersistencePolicy.CACHEABLE

    # Set at creation / dispatch time
    adapted_spec: dict | None = None
    adapted_spec_hash: str | None = None

    # Set at completion
    execution_spec: dict | None = None
    execution_spec_hash: str | None = None

    # Audit fields
    derivation_spec: dict | None = None
    worker_id: str | None = None
    generated_at: datetime | None = None
    source_step_id: UUID | None = None
```

`derivation_spec` is the authored template or inline authored payload. `adapted_spec` is the
fully rendered request that gets sent to the worker. `execution_spec` is what the worker
actually used. Flattening those three layers would lose either author intent or reproducibility.

### 1.6 Seed Assignment During Adaptation — Determinism Contract

`adapt_spec()` remains pure and deterministic. It renders against the namespace, resolves
references, and does not call workers. The apparent random element — seed selection — is
resolved inside the normalized fingerprinting path:

```python
adapted = media_spec.adapt_spec(ref=parent, ctx=ctx.get_ns(parent))
adapted.commit_deterministic_seed()
adapted_hash = adapted.spec_fingerprint()
```

`spec_fingerprint()` normalizes the spec payload, excludes transient identity fields such as
`uid` and `templ_hash`, and commits a deterministic seed when the spec supports one and no
seed has been authored. Two planning passes over the same namespace state therefore produce
the same seed and the same `adapted_spec_hash`.

If a worker cannot honor that exact seed, the worker reports the actual seed and other runtime
details back in `execution_spec`. The planning-time identity still stays stable because it is
derived before dispatch.

### 1.7 Spec Hash as EXISTING Search Key

`MediaDep` requirements use the adapted spec fingerprint as their identifier:

```python
adapted = media_spec.model_copy(deep=True).adapt_spec(ref=parent, ctx=ctx.get_ns(parent))
adapted_hash = adapted.spec_fingerprint()
payload["adapted_spec"] = adapted.normalized_spec_payload()
payload["adapted_spec_hash"] = adapted_hash
requirement_kwargs["has_identifier"] = adapted_hash
```

Same namespace state → same adapted spec → same committed seed → same `adapted_spec_hash`.
That is the core dedupe invariant for both sync-generated and async-pending story media.

### 1.8 render_ready Property on MediaDep

Journal handlers should not interpret `status` directly. Expose a single predicate:

```python
class MediaDep(Dependency[MediaRIT]):
    @property
    def render_ready(self) -> bool:
        """True iff dependency is satisfied AND the RIT has resolved content."""
        if not self.satisfied:
            return False
        rit = self.provider
        return (rit is not None and
                getattr(rit, 'status', MediaRITStatus.RESOLVED) == MediaRITStatus.RESOLVED)
```

Journal handlers use `dep.render_ready` only if they need to decide whether to suppress a
fragment. In general they should **not** suppress — the service layer handles pending policy.

---

## Part 2: Media Authority Chain — Dispatch, Not Hierarchy

### 2.1 The Authoritative Question

When the provisioner asks "is there an EXISTING RIT matching this requirement?", and when
the response manager asks "how do I resolve this RIT to bytes or a URL?", both questions go
through dispatch hooks — not a fixed authority chain baked into the provisioner or service layer.

Two resolver seams govern the current media pipeline:

- **`get_media_inventories`** — the live hook today, returning ordered `MediaInventory`
  adapters for EXISTING-offer search across story, world, and sys scope.
- **Typed service-side resolution helpers** — `media_fragment_to_payload()` now routes
  through typed `PendingMediaResult`, `ResolvedMediaResult`, and `FailedMediaResult`
  objects behind one internal helper.

This means the authority chain is a *policy* evaluated at dispatch time, not a static list.
Swapping a style registry, adding a story-arc-specific asset set, or routing to a different
backend for a user preference are all handler registrations, not architectural changes.

**Staging note:** `get_media_registries` plus dispatch-based `resolve_media_data` remain the
intended long-term generalization, but do not rename or split these surfaces yet. The current
Phase 2 slice deliberately keeps `get_media_inventories`, `graph.story_resources`, and the
internal service helper path until graph-backed story search and inventory-backed world/sys
search have both been proven together.

The examples in the rest of Part 2 use those generalized future names on purpose. Read them
as target-shape pseudocode, not as the literal symbols shipped in the current slice.

### 2.2 Story Scope: Graph Is the Registry

Current implementation note: story scope still stages file writing, re-indexing, and serving
through `graph.story_resources` and the story media directory. The graph remains the provider
authority for story-scoped generated `MediaRIT` nodes; `story_resources` is the filesystem and
index facade that keeps `/media/story/{story_id}/...` stable.

For story-scoped RITs, the graph *is* the registry. `MediaRIT` nodes are full graph
entities. `content_hash` is already `@is_identifier`. `graph.find_all(Selector(has_kind=MediaRIT, **criteria))` is the complete story-scope EXISTING search — no adapter, no wrapper.

The `get_media_registries` dispatch handler for story scope simply returns the graph:

```python
@on_get_media_registries.register(priority=Priority.EARLY)
def story_media_registries(*, ctx: VmPhaseCtx, **_):
    """Story graph is the story-scope media authority."""
    return ctx.graph   # Graph implements Registry[RegistryAware]
```

`MediaInventoryProvisioner` (or any provisioner that consumes the registry chain)
calls `find_all` on whatever each handler returns. `Graph` already supports this.
No `GraphMediaInventory` wrapper needed.

### 2.3 World/Sys Scope: ResourceManager Registries

World and sys scoped media are not on the story graph. Their `MediaResourceRegistry`
objects, populated at world load by `ResourceManager.index_directory`, are returned by
their own `get_media_registries` handlers at lower priority:

```python
@on_get_media_registries.register(priority=Priority.NORMAL)
def world_media_registries(*, ctx: VmPhaseCtx, **_):
    return ctx.world.media_resource_manager.registry

@on_get_media_registries.register(priority=Priority.LATE)
def sys_media_registries(*, ctx: VmPhaseCtx, **_):
    return get_system_resource_manager().registry
```

These `MediaResourceRegistry` objects earn their keep: the `index()` pipeline with
`on_index` hooks, bulk dedup by content hash, and the `@shelved` cache on `from_source`
are all meaningful for world/sys scope where hundreds of static files are indexed at load.
None of that complexity belongs in the story graph.

### 2.4 Style Registries and Swappable Sets

Adding a style registry or story-arc-specific asset set is just another
`get_media_registries` handler, registered conditionally:

```python
@on_get_media_registries.register(priority=Priority.EARLY - 1)
def arc_media_registries(*, ctx: VmPhaseCtx, **_):
    arc = ctx.get_ns(ctx.cursor).get('active_arc')
    if arc and arc.has_tag('has_media_override'):
        return arc.media_registry   # swapped in for this arc
    return None  # skip
```

Priority ordering determines which registry wins for a given content hash match.
No architectural changes needed to support any of this.

### 2.5 Typed Result Objects and Resolve Media Data

`resolve_media_data` returns typed result objects — not ad hoc dicts. This keeps
`media_fragment_to_payload` from becoming a pile of nested conditionals.

```python
@dataclass
class PendingMediaResult:
    job_id: str | None
    status: MediaRITStatus   # PENDING or RUNNING

@dataclass
class ResolvedMediaResult:
    path: Path | None = None
    data: bytes | None = None
    data_type: MediaDataType | None = None
    url: str | None = None   # for EXTERNAL_REFERENCE

@dataclass
class FailedMediaResult:
    reason: str | None = None
    derivation_spec: dict | None = None  # for possible re-dispatch
```

Default `resolve_media_data` handlers:

```python
@on_resolve_media_data.register(priority=Priority.EARLY)
def resolve_not_ready(rit: MediaRIT, *, ctx, **_):
    if rit.status in (MediaRITStatus.PENDING, MediaRITStatus.RUNNING):
        return PendingMediaResult(job_id=rit.job_id, status=rit.status)
    if rit.status == MediaRITStatus.FAILED:
        return FailedMediaResult(reason="generation_failed", derivation_spec=rit.derivation_spec)
    return None

@on_resolve_media_data.register(priority=Priority.NORMAL)
def resolve_path(rit: MediaRIT, *, ctx, **_):
    if rit.path and rit.path.exists():
        return ResolvedMediaResult(path=rit.path, data_type=rit.data_type)
    if rit.path and not rit.path.exists() and rit.content_hash:
        # Lazy rebind: scan story media dir for matching content hash
        manager = get_story_resource_manager(ctx.story_id, create=False)
        if manager:
            disk_rit = manager.get_rit(rit.content_hash.hex())
            if disk_rit:
                rit.path = disk_rit.path
                return ResolvedMediaResult(path=rit.path, data_type=rit.data_type)
        rit.status = MediaRITStatus.FAILED
        return FailedMediaResult(reason="file_missing", derivation_spec=rit.derivation_spec)
    return None

@on_resolve_media_data.register(priority=Priority.NORMAL)
def resolve_inline(rit: MediaRIT, *, ctx, **_):
    if rit.data is not None:
        return ResolvedMediaResult(data=rit.data, data_type=rit.data_type)
    return None
```

The lazy path rebind in `resolve_path` is the only place disk is touched at serve time,
and only when a previously-known path is stale. The `@shelved` cache makes it cheap.

No `_init_media` on the Ledger. No startup disk scan. No `story_resource_manager` field.



---

## Part 3: Media Registries and Spec Templates

### 3.1 Summary

| Kind | Object | Serialization | Authority |
|---|---|---|---|
| Static world/sys | `MediaRIT` in `MediaResourceRegistry` | Not serialized — rebuilt at world load | Target: `get_media_registries` handler; current: `get_media_inventories` |
| Story-generated | `MediaRIT` in story graph | Full graph node | Target: graph-backed registry search; current: graph + `story_resources` through `get_media_inventories` |
| Spec template | `MediaSpec` in `MediaSpecRegistry` | By value, world config | `MediaSpecProvisioner` |

### 3.2 Static Catalog = MediaResourceRegistry (Already Exists)

`MediaResourceRegistry` populated by `ResourceManager` at world/sys load. Ephemeral RIT
objects rebuilt from filesystem every session. The `on_index` hook, bulk dedup, and
`@shelved` cache are the value-add over a plain registry. Nothing new needed here.

### 3.3 Spec Templates = MediaSpecRegistry (New)

Author-defined named spec templates — recipes declared in world config that any dep can
reference by label. Plain `Registry[MediaSpec]`, serializes by value in the world bundle.

Current implementation note: Phase 2 does **not** require this registry yet. The shipped path
still treats dependency-carried inline `media.spec` payloads as the only source of truth.
`MediaSpecRegistry` remains the next authoring-layer extension once the inline lifecycle is
fully proven.

```python
class MediaSpecRegistry(Registry[MediaSpec]):
    """Named spec template registry.

    Holds author-defined MediaSpec instances keyed by label
    (e.g. 'cassie.portrait.neutral'). Populated at world compile time.
    Searched by MediaSpecProvisioner during PLANNING.
    """
```

Two authoring fields added to `MediaSpec`:

```python
class MediaResolutionClass(str, Enum):
    INLINE     = "inline"     # zero-cost; data already available (embedded asset, URL)
    FAST_SYNC  = "fast_sync"  # sync generation acceptable; local forge, < ~200ms
    ASYNC      = "async"      # slow/remote generation; worker required
    EXTERNAL   = "external"   # source of truth is outside the engine (CMS, CDN, etc.)

class MediaSpec(Entity):
    # ... existing fields ...
    resolution_class: MediaResolutionClass = MediaResolutionClass.ASYNC
    persistence_policy: MediaPersistencePolicy = MediaPersistencePolicy.CACHEABLE
    fallback_ref: str | None = None
    # Label of fallback spec, or direct file path, for FALLBACK pending policy
```

`resolution_class` replaces the earlier `sync_ok: bool`. The extra granularity matters
once external references and zero-cost inline cases need distinguishing from local forges.
`FAST_SYNC` corresponds to the old `sync_ok=True`; `ASYNC` to `sync_ok=False`.

### 3.4 Per-Story Generated RITs

Full `MediaRIT` nodes in the story graph. `path` points to:
```
<media_root>/stories/<story_id>/<human-readable-name>.<ext>
```

Files stay human-readable — authored names or convention-based names. Content hash is the
lookup key; the `ResourceManager` / `from_source` / `@shelved` machinery indexes them by
hash without requiring hash-based filenames. Served at `/media/story/{story_id}/...`.
Cleaned up by `remove_story_media` when the story is dropped.

Current implementation note: Phase 1–2 filenames are deterministic and readable but still
simple: `<base-label>-<fingerprint[:12]>.<ext>`. `uid_template`-style filename authoring
remains deferred with the larger template-registry pass.

### 3.5 materialize_rit_from_spec

```python
def materialize_rit_from_spec(
    spec: MediaSpec,
    *,
    requirement: Requirement,
    derivation_spec: MediaSpec | None = None,
    _ctx: Any = None,
) -> MediaRIT:
    """Produce a story-scoped RIT from one already-adapted spec.

    INLINE / FAST_SYNC → create_media() inline → RESOLVED RIT with path
    ASYNC / EXTERNAL   → PENDING RIT with adapted_spec; job dispatched post-PLANNING
    """
    parent = _resolve_media_parent(requirement, _ctx=_ctx)
    ctx_ns = _resolve_media_namespace(parent, _ctx=_ctx)
    story_manager = _story_media_manager(_ctx=_ctx)
    fingerprint = requirement.has_identifier or spec.spec_fingerprint()

    if spec.resolution_class in (MediaResolutionClass.INLINE, MediaResolutionClass.FAST_SYNC):
        media_data, realized_spec = spec.create_media(ref=parent, ctx=ctx_ns)
        path = _write_to_story_media(media_data, story_manager, realized_spec)
        return MediaRIT(
            path=path,
            data_type=realized_spec.media_type,
            status=MediaRITStatus.RESOLVED,
            persistence_policy=spec.persistence_policy,
            derivation_spec=_spec_payload(derivation_spec),
            adapted_spec=_spec_payload(spec),
            adapted_spec_hash=fingerprint,
            execution_spec=_spec_payload(realized_spec),
            execution_spec_hash=realized_spec.spec_fingerprint(),
        )
    return MediaRIT(
        status=MediaRITStatus.PENDING,
        data_type=spec.media_type,
        persistence_policy=spec.persistence_policy,
        derivation_spec=_spec_payload(derivation_spec),
        adapted_spec=_spec_payload(spec),
        adapted_spec_hash=fingerprint,
        # execution_spec and execution_spec_hash are set by the reconcile hook on completion
    )
```

The returned RIT is added to the story graph by the provisioner's callback, making it
findable by future EXISTING searches without any extra wiring.



### 3.6 MediaSpecProvisioner

The CREATE-side provisioner. `MediaInventoryProvisioner` handles EXISTING offers via the
`get_media_inventories` authority chain. The shipped `MediaSpecProvisioner` currently reads
dependency-carried inline specs, adapts them during PLANNING, and emits either an EXISTING
offer for a matching story RIT or a CREATE offer for sync/async materialization. Registry-
backed named templates remain future work.

```python
@dataclass
class MediaSpecProvisioner:
    graph: Any | None = None

    def get_dependency_offers(
        self,
        requirement: Requirement,
        *,
        _ctx: Any = None,
    ) -> Iterator[ProvisionOffer]:
        base_spec = requirement.media_spec
        parent = _resolve_media_parent(requirement, _ctx=_ctx)
        ctx_ns = _resolve_media_namespace(parent, _ctx=_ctx)
        adapted_spec = base_spec.model_copy(deep=True).adapt_spec(ref=parent, ctx=ctx_ns)
        fingerprint = adapted_spec.spec_fingerprint()

        existing = _graph_media_by_identifier(self.graph or _ctx.graph, fingerprint)
        if existing is not None:
            yield ProvisionOffer(
                origin_id="MediaSpecProvisioner",
                policy=ProvisionPolicy.EXISTING,
                priority=Priority.NORMAL,
                distance_from_caller=0,
                candidate=existing,
                callback=lambda *_, _existing=existing, **__: _existing,
            )
            return

        if self._requirement_policy(requirement) & ProvisionPolicy.CREATE:
            is_fast = adapted_spec.resolution_class in (
                MediaResolutionClass.INLINE, MediaResolutionClass.FAST_SYNC
            )
            priority = Priority.NORMAL if is_fast else Priority.LATE
            yield ProvisionOffer(
                origin_id="MediaSpecProvisioner",
                policy=ProvisionPolicy.CREATE,
                priority=priority,
                distance_from_caller=1 if is_fast else 2,
                candidate=adapted_spec,
                callback=lambda *_, _spec=adapted_spec, _base=base_spec, _req=requirement, **kw: materialize_rit_from_spec(
                    _spec,
                    requirement=_req,
                    derivation_spec=_base,
                    _ctx=kw.get("_ctx"),
                ),
            )
```

| Resolution class | Policy | RIT state after accept |
|---|---|---|
| `INLINE` / `FAST_SYNC` | `CREATE` | `RESOLVED`, path in story media dir |
| `ASYNC` / `EXTERNAL` | `CREATE` | `PENDING`, provenance fields set, no `job_id` yet |

If a PENDING RIT for the same spec hash already exists in the graph (prior turn or
anticipatory affordance), the EXISTING offer from the graph wins. The CREATE offer is
generated but never accepted — no duplicate job.

---

## Part 4: Phase-Bus Reconciliation Hooks

These are **runtime reconciliation hooks**, not provisioning logic. Provisioning is
"gather offers, resolve dependencies, bind providers." Polling a worker queue and
dispatching jobs are different concerns — they happen to sit on the same PLANNING hook
infrastructure for convenience, but they should be understood and organized as a named
reconciliation policy module that could generalize to any async resource, not just media.

Two hooks, both side-effect-only (return `None` per the provision hook contract). In the
current VM, PLANNING/provision work runs for the cursor plus frontier nodes, so these hooks
must guard themselves to execute once per `PhaseCtx`.

### 4.1 Pre-PLANNING: Reconcile Completed Jobs

Runs at `Priority.EARLY` — before the resolver gathers offers. Upgrades RUNNING RITs
that have completed so they appear as EXISTING (cheaper) in this turn's provisioning pass.

```python
@on_provision(priority=Priority.EARLY)
def reconcile_media_jobs(caller: Any, *, ctx: Any, **_) -> None:
    """Check running jobs and upgrade completed RITs before provisioning runs."""
    _ = caller
    if not _run_once(ctx, "reconcile_media_jobs"):
        return

    dispatcher: WorkerDispatcher | None = ctx.meta.get("worker_dispatcher")
    if dispatcher is None:
        return

    for rit in ctx.graph.find_all(Selector(has_kind=MediaRIT)):
        if rit.status != MediaRITStatus.RUNNING or not rit.job_id:
            continue
        result = dispatcher.poll(rit.job_id)
        if result is None:
            continue  # still running
        if result.success:
            rit.path = result.path
            rit.execution_spec = result.execution_spec
            rit.execution_spec_hash = _hash_spec_dict(result.execution_spec)
            rit.worker_id = result.worker_id
            rit.generated_at = result.generated_at
            rit.status = MediaRITStatus.RESOLVED
            rit.job_id = None
        else:
            rit.status = MediaRITStatus.FAILED
            # derivation_spec retained; CACHEABLE policy can re-dispatch
```

### 4.2 Post-PLANNING: Dispatch Accepted Async Offers

Runs at `Priority.LATE` — after the resolver has settled all offers.

```python
@on_provision(priority=Priority.LATE)
def dispatch_pending_media(caller: Any, *, ctx: Any, **_) -> None:
    """Kick off worker jobs for RITs that were just created as PENDING.

    The hook walks the graph for PENDING story RITs with no job_id yet, submits the
    fully rendered adapted spec to the WorkerDispatcher, and stores the returned job_id.
    """
    _ = caller
    if not _run_once(ctx, "dispatch_media_jobs"):
        return

    dispatcher: WorkerDispatcher | None = ctx.meta.get("worker_dispatcher")
    if dispatcher is None:
        return

    for rit in ctx.graph.find_all(Selector(has_kind=MediaRIT)):
        if rit.status != MediaRITStatus.PENDING or rit.job_id:
            continue
        if rit.adapted_spec is None:
            continue
        job_id = dispatcher.submit(rit.adapted_spec)
        rit.job_id = job_id
        rit.status = MediaRITStatus.RUNNING
```

The `WorkerDispatcher` is injected into phase metadata from the service layer at story-creation
time. The media and vm packages never import from service. Worker selection, load balancing,
and backend-specific configuration remain entirely `WorkerDispatcher` concerns.

### 4.3 No New Phases Required

All of this is side-effect-only PLANNING work. The existing PLANNING contract (handlers return
None) is preserved. The phase bus needs no structural changes.

---

## Part 5: Anticipatory Media Affordances

A `MediaAffordance` is an `Affordance` edge whose provider is a (possibly pending) RIT that
a node pre-produces for a role it might soon need. The affordance pushes the RIT into scope
before any dep declares it.

**Why this works:** When a downstream dep searches for an EXISTING provider matching its
requirement (by spec hash), it finds the affordance's RIT — possibly already resolved, possibly
still pending. Either way it accepts it as EXISTING (cheap) and never spawns a new job.

**⚠️ Quota requirement:** Anticipatory affordances are a potential denial-of-service
mechanism. If every actor emits portraits for all probable emotional states, outfits, and
voice lines every turn, the graph and worker queue explode. **This feature must not ship
without a quota policy.** Required before production use:
- max speculative jobs per node per turn
- max speculative jobs per step globally
- LRU or priority-based cancellation when quota is exceeded
- author hint for confidence/urgency on each affordance
- no speculative generation for canonically unrepeatable branches unless explicitly marked

**Example use case:** An actor node with a `Look` component knows it will likely need portraits
in two or three emotional states in the coming turns. During PLANNING it attaches anticipatory
affordances for those states:

```python
# In an actor planning handler (soft affordances, non-blocking):
for state in actor.probable_states(ctx):
    spec = actor.portrait_spec(state)
    realized_spec = spec.adapt_spec(ref=actor, ctx=ctx.get_ns(actor))
    spec_hash = realized_spec.spec_fingerprint()

    # Only create affordance if RIT doesn't already exist
    existing = ctx.graph.find_one(Selector(has_kind=MediaRIT, has_identifier=spec_hash))
    if existing is not None:
        continue

    rit = MediaRIT(
        status=MediaRITStatus.PENDING,
        persistence_policy=spec.persistence_policy,
        derivation_spec=spec.normalized_spec_payload(),
        adapted_spec=realized_spec.normalized_spec_payload(),
        adapted_spec_hash=spec_hash,
    )
    ctx.graph.add(rit)

    affordance = Affordance(requirement=Requirement(
        has_kind=MediaRIT,
        has_identifier=spec_hash,
        hard_requirement=False,
    ))
    affordance.set_provider(rit)
    ctx.graph.add_edge(actor, affordance)
```

The post-PLANNING dispatch hook finds these new PENDING RITs (no `job_id` yet) and submits
their adapted specs to the dispatcher — exactly the same hook that handles dep-created
pending RITs. No affordance-specific logic.

**Affordances vs deps:** A dep must be satisfied for the node to be render-ready (if hard)
or is advisory (if soft). An affordance pushes availability outward without a local consumer.
Anticipatory affordances are always soft and always pre-scope the inventory for consumers
that haven't been instantiated yet.

---

## Part 6: Service Layer — MediaRenderProfile

### 6.1 Pending Policy

When `media_fragment_to_payload` encounters a RIT with `status=PENDING`, it needs a policy
decision. Three options:

```python
class MediaPendingPolicy(str, Enum):
    DISCARD   = "discard"           # drop fragment; client sees no media slot
    POLL      = "poll"              # emit a control directive; client polls
    FALLBACK  = "fallback"          # resolve fallback_ref from catalog; show placeholder
```

`FALLBACK` is the shipped default. The service layer reads `fallback_ref` from the stored
derivation/adapted spec payloads, resolves a matching static media record from the available
world/sys inventories when possible, then falls back to authored fragment text, and finally
discards the slot if neither is available. `POLL` remains a non-default client contract.

### 6.2 Content Profile

For resolved RITs, the content form depends on the client's render capabilities:

```python
class MediaContentProfile(str, Enum):
    INLINE_DATA  = "inline_data"   # always embed: base64 (raster) or raw text (SVG/JSON)
    MEDIA_SERVER = "media_server"  # always convert to /media/... URL
    PASSTHROUGH  = "passthrough"   # data→data, path→path, url→url; consumer maps it
```

SVG is a special case of `INLINE_DATA`: it is valid XML text and should be sent raw (not
base64-encoded) to clients that can inject it into the DOM directly. `MediaDataType.VECTOR`
with `INLINE_DATA` profile → serialize `content.data` as a UTF-8 string, not base64.

### 6.3 Combined Profile Object

```python
@dataclass
class MediaRenderProfile:
    pending_policy: MediaPendingPolicy = MediaPendingPolicy.FALLBACK
    content_profile: MediaContentProfile = MediaContentProfile.MEDIA_SERVER
    # Required for FALLBACK pending policy:
    static_inventories: tuple[MediaInventory, ...] = ()
```

The profile is a per-connection or per-render-target config object. The REST adapter
constructs it internally from the request context and existing compatibility render-profile
tokens, then passes it into `media_fragment_to_payload` without changing the external API.

### 6.4 Updated media_fragment_to_payload

```python
def media_fragment_to_payload(
    fragment: Any,
    *,
    render_profile: MediaRenderProfile = _DEFAULT_PROFILE,
    world_id: str | None = None,
    story_id: str | None = None,
    world_media_root: Path | None = None,
    story_media_root: Path | None = None,
    system_media_root: Path | None = None,
) -> dict | None:

    if not isinstance(fragment, MediaFragment):
        # existing fallback path unchanged
        ...

    rit = fragment.content if fragment.content_format == "rit" else None

    # ── Gate 1: unresolved lifecycle check ─────────────────────────────────────
    if rit is not None and getattr(rit, 'status', MediaRITStatus.RESOLVED) in {
        MediaRITStatus.PENDING,
        MediaRITStatus.RUNNING,
        MediaRITStatus.FAILED,
    }:
        policy = render_profile.pending_policy

        if policy == MediaPendingPolicy.DISCARD:
            return None

        if policy == MediaPendingPolicy.POLL:
            return {
                "fragment_type": "control",
                "directive":     "poll_media",
                "job_id":        rit.job_id,
                "media_role":    fragment.media_role,
                "retry_after_ms": 2000,
                "source_id":     str(fragment.source_id) if fragment.source_id else None,
            }

        if policy == MediaPendingPolicy.FALLBACK:
            rit = _resolve_fallback(rit, render_profile.static_inventories)
            if rit is None:
                fallback_text = _fallback_text(fragment)
                return (
                    _content_payload_from_text(fragment, fallback_text)
                    if fallback_text is not None
                    else None
                )
            # fall through with the fallback RIT

    # ── Gate 2: content profile dispatch (existing logic, now parameterized) ──
    return _deref_rit(
        rit, fragment,
        profile=render_profile.content_profile,
        world_id=world_id, story_id=story_id,
        world_media_root=world_media_root,
        story_media_root=story_media_root,
        system_media_root=system_media_root,
    )
```

`_deref_rit` replaces the existing inline RIT handling in `media_fragment_to_payload`:

```python
def _deref_rit(
    rit: MediaRIT,
    fragment: MediaFragment,
    *,
    profile: MediaContentProfile,
    **roots,
) -> dict:
    base_payload = {
        "fragment_type": "media",
        "media_role":    fragment.media_role,
        "source_id":     str(fragment.source_id) if fragment.source_id else None,
        "scope":         getattr(fragment, 'scope', 'world'),
        "media_type":    rit.data_type.value if rit.data_type else None,
    }

    is_svg = rit.data_type == MediaDataType.VECTOR

    if profile == MediaContentProfile.MEDIA_SERVER or (
        profile == MediaContentProfile.PASSTHROUGH and rit.path
    ):
        url = _build_url(rit, **roots)
        return {**base_payload, "content_format": "url", "url": url}

    if profile == MediaContentProfile.INLINE_DATA or (
        profile == MediaContentProfile.PASSTHROUGH and rit.data is not None
    ):
        if is_svg and isinstance(rit.data, (str, bytes)):
            data = rit.data if isinstance(rit.data, str) else rit.data.decode('utf-8')
            return {**base_payload, "content_format": "xml", "data": data}
        if isinstance(rit.data, bytes):
            return {**base_payload, "content_format": "data", "data": b64encode(rit.data).decode()}
        return {**base_payload, "content_format": "data", "data": str(rit.data)}

    # Passthrough with path
    if rit.path:
        return {**base_payload, "content_format": "path", "path": str(rit.path)}

    # Should not reach here for a RESOLVED RIT
    raise ValueError(f"Cannot deref MediaRIT {rit!r} with profile {profile}")
```

---

## Part 7: WorkerDispatcher Interface

The media package defines the interface. The service layer provides the implementation.

```python
# tangl/media/worker_dispatcher.py

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

@dataclass
class WorkerResult:
    success: bool
    path: Path | None = None
    data: bytes | str | None = None
    data_type: MediaDataType | None = None
    error: str | None = None
    execution_spec: dict | None = None
    worker_id: str | None = None
    generated_at: datetime | None = None


class WorkerDispatcher(Protocol):
    """Submit and poll async media generation jobs.

    Injected into phase metadata at the service layer. Never imported by vm or media packages.
    """

    def submit(self, spec: dict[str, Any]) -> str:
        """Submit the fully rendered adapted spec and return a job id."""
        ...

    def poll(self, job_id: str) -> WorkerResult | None:
        """Check job status. Returns None if still pending, WorkerResult if done."""
        ...

    def cancel(self, job_id: str) -> None:
        """Cancel a pending job (best effort)."""
        ...
```

The concrete implementation (`StableForgeDispatcher`, `ComfyDispatcher`, etc.) lives in
the service layer and is responsible for worker selection, queuing, load balancing, and the
backend-specific configuration. None of that leaks into the engine.

---

## Part 8: Scope of Changes (Implementation Checklist)

This section now distinguishes what is already landed from the next actionable work that
still remains after the server-side Phase 2 slice.

### `tangl/media/media_resource/media_resource_inv_tag.py`
- [x] Add `MediaRITStatus` enum (4 states: PENDING, RUNNING, RESOLVED, FAILED)
- [x] Add `MediaPersistencePolicy` enum
- [x] Add `status`, `job_id`, `persistence_policy`, `adapted_spec`, `adapted_spec_hash`,
  `execution_spec`, `execution_spec_hash`, `derivation_spec`, `worker_id`, `generated_at`,
  and `source_step_id` fields to `MediaResourceInventoryTag`
- [x] Guard source validation so only `RESOLVED` RITs require path/data/content data

### `tangl/media/media_creators/media_spec.py`
- [x] Add `MediaResolutionClass` enum (INLINE, FAST_SYNC, ASYNC, EXTERNAL)
- [x] Replace `sync_ok: bool` with `resolution_class: MediaResolutionClass`
- [x] Add `persistence_policy: MediaPersistencePolicy` and `fallback_ref: str | None`
- [x] Add normalized fingerprinting that excludes transient identity fields and commits
  deterministic seeds before hashing
- [ ] Add named-template authoring surfaces such as `GenerationHints` and richer prompt /
  uid templating only after the inline lifecycle is stable

### `tangl/media/media_resource/media_dependency.py`
- [x] Add `render_ready` property
- [x] Wire adapted spec fingerprint as `has_identifier` when inline `media_spec` is present

### `tangl/media/media_resource/media_provisioning.py`
- [x] Keep `get_media_inventories` as the live EXISTING-offer authority chain
- [x] Extend `MediaSpecProvisioner` so dependency-carried inline specs can produce either
  resolved sync RITs or pending async RITs
- [x] Reuse existing story RITs by `adapted_spec_hash` instead of creating duplicate jobs
- [ ] Generalize the authority chain to `get_media_registries` only after graph-backed
  story search and inventory-backed world/sys search are both proven on the same path

### `tangl/media/media_resource/media_spec_registry.py` (future)
- [ ] Introduce `MediaSpecRegistry(Registry[MediaSpec])` for named templates after the
  inline lifecycle is stable
- [ ] Add registry-backed CREATE offers without regressing the dependency-carried path

### `tangl/media/worker_dispatcher.py` (new)
- [x] `WorkerResult` dataclass (with provenance fields)
- [x] `WorkerDispatcher` Protocol
- [ ] Concrete worker implementations (`StableForgeDispatcher`, `ComfyDispatcher`, etc.)

### `tangl/media/phase_hooks.py` (new)
- [x] `reconcile_media_jobs` — `Priority.EARLY` `@on_provision`; polls RUNNING RITs
- [x] `dispatch_media_jobs` — `Priority.LATE` `@on_provision`; dispatches PENDING→RUNNING
- [x] Guard both hooks so they run once per `PhaseCtx`

### `tangl/service/media.py`
- [x] `MediaPendingPolicy`, `MediaContentProfile`, `MediaRenderProfile`
- [x] Refactor `media_fragment_to_payload` behind typed resolve-result objects and one
  internal resolved-RIT helper
- [x] Keep the external request/gateway `render_profile` string surface compatible
- [ ] Extract `resolve_media_data` into a formal dispatch task only if a second resolver
  implementation actually needs that extension point

### `tangl/service/` (REST adapter / runtime controller)
- [x] Construct `MediaRenderProfile` from request context / connection config
- [x] Inject `WorkerDispatcher` into phase metadata at story creation
- [x] Apply fallback-first handling for pending/failed story media via static fallback
  media, fallback text, or discard

### Deferred
- [ ] `StableForgeDispatcher` — async wrapper over `StableForge.create_media`
- [ ] `ComfyDispatcher` — stub / future
- [ ] `GenerationHints` and richer namespace-driven prompt assembly
- [ ] `MediaSpecRegistry` named template authoring
- [ ] `get_media_registries` / dispatch-generalized media resolution
- [ ] Anticipatory affordance quota policy (must be designed before shipping)

---

## Invariants

**Three-phase identity; each hash answers a different question.**
`adapted_spec_hash` answers "would this namespace state produce this asset?" and is the
planning-time dedupe key. `execution_spec_hash` answers "can I exactly reproduce what the
worker ran?" `content_hash` answers "do I already have these bytes?"

**`adapt_spec()` is deterministic; seed commitment is part of fingerprinting.**
No worker call, no external availability check, no ambient RNG. The same namespace state
must yield the same committed seed and the same `adapted_spec_hash`.

**`derivation_spec`, `adapted_spec`, and `execution_spec` are distinct on purpose.**
Author intent, rendered request, and worker accounting answer different debugging and replay
questions. Do not collapse them.

**Four-state lifecycle; `job_id` is evidence, not state.**
PENDING = accepted, not dispatched. RUNNING = dispatched, acknowledged. RESOLVED = content
available. FAILED = terminal.

**Story-scope media lives in the graph.**
Story RITs are full graph entities. The graph is the story-scope authority, while
`graph.story_resources` remains the filesystem/index facade for writing and serving files.

**Authority chain is a dispatch policy.**
Today that policy is expressed through `get_media_inventories`. Rename or split it only after
the graph-backed and inventory-backed paths are both proven on the same code path.

**`provider_id` is always UUID; disk resolution is lazy.**
Rebind happens only at serve time, only when a path is stale. `@shelved` makes it cheap.

**Files stay human-readable.**
Current generated filenames use a readable base label plus a fingerprint slice. Content hash
and spec hashes do the dedupe work; filenames stay legible.

**RIT is topologically inert once claimed.**
A pending RIT satisfies its dep. The resolver never revisits it.

**Spec hash is the deduplication key.**
Same adapted spec + same context → same committed seed → same `adapted_spec_hash` →
same RIT as EXISTING. No duplicate jobs.

**Journal is unaware of pending state.**
Journal emits `MediaFragment(content=rit, content_format="rit")` unconditionally.
Service-layer media resolution is the only place `status` matters.

**WorkerDispatcher is service-layer-only.**
Nothing below `tangl/service/` imports a concrete worker backend. Phase hooks receive a
`WorkerDispatcher` via phase metadata.

**Affordances and deps are symmetric.**
`dispatch_media_jobs` walks `ctx.graph` for all PENDING RITs with no `job_id`. Does not
distinguish affordance-produced from dep-produced — both get dispatched.

**Anticipatory affordances require quota policy before shipping.**
No speculative generation should reach production without max-jobs-per-node,
max-jobs-per-step, and cancellation/eviction policy implemented and tested.

**Sync-first implementation order.**
Prove the architecture with `resolution_class=FAST_SYNC` before async workers.
Async is an extension of a working sync system, not a prerequisite.

---

## Open Questions (Deferred)

**Replay and canonicality semantics.** `STORY_CANONICAL` marks a specific result as
narrative history. The full replay implication is undesigned: if a canonical asset is
missing, does replay fail, regenerate, or substitute? What constitutes "same result" —
exact bytes or spec hash match? Needs explicit policy before `STORY_CANONICAL` is used.

**`get_media_inventories` → `get_media_registries` migration timing.** Current code uses
`MediaInventory` adapters. The generalization to any `Registry[MediaRIT]` is correct long-
term. When to rename and retire `MediaInventory` is a sequencing decision; do not force it
before graph-as-registry is proven stable alongside the existing inventory chain.

**Anticipatory affordance quota policy.** Mechanism is correct; limits are not yet specified.
Required: max speculative jobs per node, per step, per story; cancellation strategy;
author-facing confidence/priority annotation; policy for canonically-unrepeatable branches.

**Re-dispatch policy for FAILED + CACHEABLE RITs.** If a CACHEABLE RIT fails and its dep
is still active, should the post-PLANNING hook re-dispatch on the next turn? How many
retries? Does `fallback_ref` kick in after N failures? Needs explicit policy before workers
are in production.

---

## Future: Generative Prose as a Sibling System

The abstraction underlying generative media is not "binary asset generation" — it is:

> authored dependency → pending/resolved artifact → fragment referencing artifact →
> service presents pending/resolved output

Generative prose follows the same pattern, with the artifact being rendered text.
The provisioner, phase-bus hooks, and service-layer pending policy all apply.

**Prose is not media.** Define a sibling system with parallel types:
- `GeneratedText` (analog to `MediaRIT`)
- `TextSpec` (analog to `MediaSpec`) — prompt, style, constraints
- `TextSpecRegistry`, `TextSpecProvisioner`
- `TextFragment` or extend `BlockFragment`

**Prose-specific policies not needed for media:**
- **Canonicality** — generated prose is usually directly player-facing; more load-bearing
- **Revision policy** — can a pending placeholder be replaced in-place, or is it a new
  fragment? In-place replacement has causal implications
- **Narrator authority** — does this prose introduce new facts, or only describe already-
  bound world state? LLM prose can accidentally smuggle canon into the story. Specs should
  declare constraints: `descriptive_only`, `no_new_entities`, `summarize_bound_facts`

The shared infrastructure can be extracted into a `GeneratedArtifact` base once both
systems exist and the common pattern is proven. Do not abstract before both concrete
instances are working.

---

## Relationship to Existing Design Documents

- **[`MEDIA_DESIGN.md`](MEDIA_DESIGN.md)** — Authoritative for layers, roles, static lifecycle, fragment
  contract. This document extends it for the generative pipeline.
- **[`media_resurrection_plan.md`](../notes/media_resurrection_plan.md)** — This design
  now documents the landed inline Phase 1–2 work plus the server-side async lifecycle.
- **[`PLANNING_DESIGN.md`](planning/PLANNING_DESIGN.md)** — `MediaSpecProvisioner` follows the same offer/accept protocol
  as `TokenProvisioner` and `TemplateProvisioner`.

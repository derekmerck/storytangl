# Generative Media Design

**Status:** DESIGN + PARTIAL IMPLEMENTATION — extends [`MEDIA_DESIGN.md`](MEDIA_DESIGN.md)
and [`media_resurrection_plan.md`](../../notes/media_resurrection_plan.md)  
**Scope:** Async generative pipeline, pending-RIT lifecycle, spec registry and provisioner,
phase-bus integration, and service-layer response profiles.  
**Prerequisite:** Media resurrection plan Phase 1–2 (static RIT plumbing) must be complete.  
**Implementation order:** Sync-first (§3.5–3.6 prove the architecture without workers),
then async pending RITs, then worker dispatch hooks, then anticipatory affordances.

---

## Implementation Status

- **March 14, 2026:** The sync-first slice is now implemented for inline `media.spec`
  declarations. Story materialization creates real `MediaDep` edges for supported inline
  specs, sync generation writes deterministic story-scoped files, generated `MediaRIT`s
  carry provenance plus a spec fingerprint for dedupe, and the existing journal/service
  path now emits canonical story media URLs for those generated resources.
- **Still deferred:** pending-RIT lifecycle states, worker dispatch hooks, named
  `MediaSpecRegistry` templates, render-profile pending policies, and anticipatory
  affordance quotas.

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
code that needs to care is the `resolve_media_data` dispatch at the service boundary.

Supporting structures:

- `MediaRITStatus` enum — `PENDING | RUNNING | RESOLVED | FAILED` (four states; `job_id` is evidence, not state)
- `MediaPersistencePolicy` enum — `EPHEMERAL | CACHEABLE | STORY_CANONICAL | EXTERNAL_REFERENCE`
- `MediaResolutionClass` enum — `INLINE | FAST_SYNC | ASYNC | EXTERNAL` (replaces `sync_ok: bool`)
- `MediaSpecRegistry` — named `MediaSpec` templates (world config, serializes by value)
- `MediaSpecProvisioner` — CREATE-side provisioner reading spec templates
- Two thin phase-bus hooks — pre-PLANNING reconciliation pass, post-PLANNING dispatch
- `MediaRenderProfile` + typed result objects at the service boundary

---

## Part 1: Pending-RIT Lifecycle

### 1.1 RIT Identity Is Simpler Than It Looks

The apparent problem — "catalog RIT UUIDs are ephemeral, story RIT paths aren't portable" —
dissolves under the final model. `provider_id` stays UUID throughout, no type change required.

**Catalog RITs** (indexed from disk into world/sys `MediaResourceRegistry`): these are not
story graph nodes. The dep's `has_identifier` carries the *content hash* — the durable
cross-session key. The provisioner's EXISTING search through `get_media_registries` finds
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

### 1.4 Provenance Fields on MediaRIT

For story-canonical and cacheable RITs, provenance must be complete enough to reproduce
or audit the result:

```python
class MediaResourceInventoryTag(RegistryAware, ContentAddressable):
    # ... existing fields ...
    status: MediaRITStatus = MediaRITStatus.RESOLVED
    job_id: str | None = None
    persistence_policy: MediaPersistencePolicy = MediaPersistencePolicy.CACHEABLE

    # Provenance — stored on RESOLVED story-scoped RITs
    derivation_spec: dict | None = None      # authored template spec (what was requested)
    execution_spec: dict | None = None       # realized execution spec: model, seed, prompt, LoRA, dims
    worker_id: str | None = None             # which worker/adapter produced this
    generated_at: datetime | None = None     # execution timestamp
    source_step_id: UUID | None = None       # which story step triggered generation
```

`derivation_spec` is the authored template — "Cassie neutral portrait."
`execution_spec` is the realized execution — "SDXL model X, seed 4172, prompt Y, 1024×1024."
These must stay distinct. Flattening them loses the ability to re-run with updated styles
while preserving the original intent.

### 1.5 Spec Hash as Cache Key

A spec in a `MediaDep` maps to a unique RIT via the normalized spec hash. The hash is computed
from the *realized* spec (after `adapt_spec()` has been applied) — this is `realized_spec` on
`MediaDep`, already present. It becomes the `has_identifier` on the requirement, so
`MediaInventoryProvisioner`'s existing EXISTING search finds previously-generated (or
previously-pending) RITs without any changes.

```python
# In MediaDep._pre_resolve, when media_spec is provided:
realized_hash = media_spec.adapt_spec(ref=parent).content_hash().hex()
requirement_kwargs["has_identifier"] = realized_hash
```

Same spec + same context → same hash → same RIT found as EXISTING, regardless of whether
it was produced sync or async, this session or a prior one.

### 1.6 render_ready Property on MediaDep

Journal handlers should not interpret `status` directly. Expose a single predicate:

```python
class MediaDep(Dependency[MediaRIT]):
    @property
    def render_ready(self) -> bool:
        """True iff dependency is satisfied AND the RIT has resolved content."""
        if not self.satisfied:
            return False
        rit = self.provider
        return rit is not None and getattr(rit, 'status', MediaRITStatus.RESOLVED) == MediaRITStatus.RESOLVED
```

Journal handlers use `dep.render_ready` only if they need to decide whether to suppress a
fragment. In general they should **not** suppress — the service layer handles pending policy.

---

## Part 2: Media Authority Chain — Dispatch, Not Hierarchy

### 2.1 The Authoritative Question

When the provisioner asks "is there an EXISTING RIT matching this requirement?", and when
the response manager asks "how do I resolve this RIT to bytes or a URL?", both questions go
through dispatch hooks — not a fixed authority chain baked into the provisioner or service layer.

Two dispatch tasks govern the media pipeline:

- **`get_media_registries`** — returns the ordered list of `Registry[MediaRIT]` to search
  for EXISTING offers. Handlers registered at different priorities compose the chain.
- **`resolve_media_data`** — given a `MediaRIT`, returns a typed result object (see §2.5).

This means the authority chain is a *policy* evaluated at dispatch time, not a static list.
Swapping a style registry, adding a story-arc-specific asset set, or routing to a different
backend for a user preference are all handler registrations, not architectural changes.

**Staging note:** The current code uses `get_media_inventories` returning `MediaInventory`
adapter objects. `get_media_registries` is the intended long-term name, but do not rename
the dispatch task until `GraphMediaInventory` (or direct graph search) is proven working
alongside the existing `MediaInventory` chain. Keep `MediaInventory` as a compatibility
adapter during the transition; only generalize the abstraction once both paths are verified.

### 2.2 Story Scope: Graph Is the Registry

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
| Static world/sys | `MediaRIT` in `MediaResourceRegistry` | Not serialized — rebuilt at world load | `get_media_registries` handler |
| Story-generated | `MediaRIT` in story graph | Full graph node | `get_media_registries` handler (graph) |
| Spec template | `MediaSpec` in `MediaSpecRegistry` | By value, world config | `MediaSpecProvisioner` |

### 3.2 Static Catalog = MediaResourceRegistry (Already Exists)

`MediaResourceRegistry` populated by `ResourceManager` at world/sys load. Ephemeral RIT
objects rebuilt from filesystem every session. The `on_index` hook, bulk dedup, and
`@shelved` cache are the value-add over a plain registry. Nothing new needed here.

### 3.3 Spec Templates = MediaSpecRegistry (New)

Author-defined named spec templates — recipes declared in world config that any dep can
reference by label. Plain `Registry[MediaSpec]`, serializes by value in the world bundle.

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

### 3.5 materialize_rit_from_spec

```python
def materialize_rit_from_spec(
    spec: MediaSpec,
    *,
    story_id: str,
    _ctx: Any = None,
) -> MediaRIT:
    """Produce a RIT from a spec and add it to the story graph.

    INLINE / FAST_SYNC → create_media() inline → RESOLVED RIT with path
    ASYNC / EXTERNAL   → PENDING RIT with derivation_spec; job dispatched post-PLANNING
    """
    if spec.resolution_class in (MediaResolutionClass.INLINE, MediaResolutionClass.FAST_SYNC):
        media_data, realized_spec = spec.create_media(_ctx=_ctx)
        path = _write_to_story_media(media_data, story_id, realized_spec)
        return MediaRIT(
            path=path,
            data_type=realized_spec.media_type,
            status=MediaRITStatus.RESOLVED,
            persistence_policy=spec.persistence_policy,
            derivation_spec=spec.model_dump(),
            execution_spec=realized_spec.model_dump(),
        )
    return MediaRIT(
        status=MediaRITStatus.PENDING,
        data_type=spec.media_type,
        persistence_policy=spec.persistence_policy,
        derivation_spec=spec.model_dump(),
        # execution_spec and worker_id set by post-PLANNING dispatch hook on completion
    )
```

The returned RIT is added to the story graph by the provisioner's callback, making it
findable by future EXISTING searches without any extra wiring.



### 3.6 MediaSpecProvisioner

The CREATE-side provisioner. `MediaInventoryProvisioner` handles EXISTING offers via the
`get_media_registries` dispatch chain. `MediaSpecProvisioner` handles CREATE offers from
named spec templates.

```python
@dataclass
class MediaSpecProvisioner:
    spec_registries: Iterable[MediaSpecRegistry]
    story_id: str

    def get_dependency_offers(self, requirement: Requirement) -> Iterator[ProvisionOffer]:
        selector = Selector(predicate=requirement.satisfied_by)
        for spec in MediaSpecRegistry.chain_find_all(*self.spec_registries, selector=selector):
            is_fast = spec.resolution_class in (
                MediaResolutionClass.INLINE, MediaResolutionClass.FAST_SYNC
            )
            priority = Priority.NORMAL if is_fast else Priority.LATE
            yield ProvisionOffer(
                origin_id=f"MediaSpecProvisioner:{spec.get_label()}",
                policy=ProvisionPolicy.CREATE,
                priority=priority,
                distance_from_caller=1 if is_fast else 2,
                candidate=spec,
                callback=lambda *_, _s=spec, **kw: materialize_rit_from_spec(
                    _s, story_id=self.story_id, _ctx=kw.get('_ctx'),
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

Two hooks, both side-effect-only (return None per PLANNING contract).

### 4.1 Pre-PLANNING: Reconcile Completed Jobs

Runs at `Priority.EARLY` — before the resolver gathers offers. Upgrades RUNNING RITs
that have completed so they appear as EXISTING (cheaper) in this turn's provisioning pass.

```python
@on_planning.register(task="planning", priority=Priority.EARLY)
def reconcile_media_jobs(*, ctx: VmPhaseCtx, **_) -> None:
    """Check running jobs and upgrade completed RITs before provisioning runs."""
    dispatcher: WorkerDispatcher | None = getattr(ctx, 'worker_dispatcher', None)
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
            rit.execution_spec = result.execution_spec  # model, seed, etc.
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
@on_planning.register(task="planning", priority=Priority.LATE)
def dispatch_pending_media(*, ctx: VmPhaseCtx, **_) -> None:
    """Kick off worker jobs for RITs that were just created as PENDING.

    Walks deps (and affordance edges) on the current node and frontier that have
    a PENDING provider with no job_id yet. Submits each to the WorkerDispatcher
    and stores the returned job_id on the RIT.

    This fires after provisioning, so deps are already claimed. The dispatcher
    call is non-blocking: it submits and returns a job_id immediately.
    Transitions status PENDING → RUNNING on successful submission.
    """
    dispatcher: WorkerDispatcher | None = getattr(ctx, 'worker_dispatcher', None)
    if dispatcher is None:
        return

    for rit in ctx.graph.find_all(Selector(has_kind=MediaRIT)):
        if rit.status != MediaRITStatus.PENDING or rit.job_id:
            continue
        if rit.derivation_spec is None:
            continue
        job_id = dispatcher.submit(rit.derivation_spec)
        rit.job_id = job_id
        rit.status = MediaRITStatus.RUNNING
```

The `WorkerDispatcher` is injected into `VmPhaseCtx` from the service layer at story-creation
time. The media and vm packages never import from service. Worker selection, load balancing,
and the `auto111_workers` / `comfy_workers` config are entirely `WorkerDispatcher` concerns.

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
    spec_hash = realized_spec.content_hash().hex()

    # Only create affordance if RIT doesn't already exist
    existing = ctx.graph.find_one(Selector(has_kind=MediaRIT, has_identifier=spec_hash))
    if existing is not None:
        continue

    rit = MediaRIT(
        status=MediaRITStatus.PENDING,
        persistence_policy=spec.persistence_policy,
        derivation_spec=realized_spec.model_dump(),
    )
    ctx.graph.add(rit)

    affordance = Affordance(requirement=Requirement(
        has_kind=MediaRIT,
        has_identifier=spec_hash,
        hard_requirement=False,
    ))
    affordance.set_provider(rit)
    ctx.graph.add_edge(actor, affordance)
    
    affordance.set_provider(rit)
    graph.add_edge(actor, affordance)
```

The post-PLANNING dispatch hook finds these new PENDING RITs (no `job_id` yet) and submits
their derivation specs to the dispatcher — exactly the same hook that handles dep-created
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

`FALLBACK` requires the response manager to have access to the `MediaSpecRegistry` — specifically
the `fallback_ref` on the spec that produced the pending RIT. This is available via
`rit.derivation_spec` (which contains the serialized spec, including `fallback_ref`). The
fallback is resolved synchronously: it is either a named static RIT (looked up in
`MediaResourceRegistry`) or a direct file path — never itself async.

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
    pending_policy: MediaPendingPolicy = MediaPendingPolicy.DISCARD
    content_profile: MediaContentProfile = MediaContentProfile.MEDIA_SERVER
    # Required for FALLBACK pending policy:
    static_inventory: MediaInventory | None = None  # searched for fallback_ref targets
```

The profile is a per-connection or per-render-target config object. The REST adapter
constructs it from the request context (client capabilities header, connection config, or
world config defaults) and passes it into `media_fragment_to_payload`.

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

    # ── Gate 1: pending check ──────────────────────────────────────────────────
    if rit is not None and getattr(rit, 'status', MediaRITStatus.RESOLVED) == MediaRITStatus.PENDING:
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
            rit = _resolve_fallback(rit, render_profile.catalog)
            if rit is None:
                return None     # no fallback available; discard
            # fall through with the fallback RIT

    # ── Gate 2: FAILED check ──────────────────────────────────────────────────
    if rit is not None and getattr(rit, 'status', None) == MediaRITStatus.FAILED:
        # Always discard failed RITs (fallback was the author's responsibility)
        return None

    # ── Gate 3: content profile dispatch (existing logic, now parameterized) ──
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

from typing import Protocol

class WorkerResult:
    success: bool
    path: Path | None = None      # if worker wrote a file
    data: bytes | None = None     # if worker returned inline data
    error: str | None = None


class WorkerDispatcher(Protocol):
    """Submit and poll async media generation jobs.

    Injected into VmPhaseCtx at the service layer. Never imported by vm or media packages.
    """

    def submit(self, spec: dict) -> str:
        """Submit a generation job. Returns job_id immediately (non-blocking)."""
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
`auto111_workers` / `comfy_workers` config. None of that leaks into the engine.

`WorkerResult` also carries provenance fields stored on the RIT at completion:

```python
@dataclass
class WorkerResult:
    success: bool
    path: Path | None = None
    data: bytes | None = None
    error: str | None = None
    execution_spec: dict | None = None  # model, seed, prompt, LoRA, dims, etc.
    worker_id: str | None = None
    generated_at: datetime | None = None
```

---

## Part 8: Scope of Changes (Implementation Checklist)

Recommended order: implement sync-generated RITs first (§3.3–3.6), prove end-to-end,
then add async PENDING state, then worker dispatch hooks, then anticipatory affordances
(only after quota policy is designed).

### `tangl/media/media_resource/media_resource_inv_tag.py`
- [ ] Add `MediaRITStatus` enum (4 states: PENDING, RUNNING, RESOLVED, FAILED)
- [ ] Add `MediaPersistencePolicy` enum
- [ ] Add `status`, `job_id`, `persistence_policy`, `derivation_spec`, `execution_spec`,
  `worker_id`, `generated_at`, `source_step_id` fields to `MediaResourceInventoryTag`
- [ ] Guard `_validate_required_source`: require path/data/hash only when `status == RESOLVED`

### `tangl/media/media_creators/media_spec.py`
- [ ] Add `MediaResolutionClass` enum (INLINE, FAST_SYNC, ASYNC, EXTERNAL)
- [ ] Replace `sync_ok: bool` with `resolution_class: MediaResolutionClass`
- [ ] Add `persistence_policy: MediaPersistencePolicy` and `fallback_ref: str | None`

### `tangl/media/media_resource/media_dependency.py`
- [ ] Add `render_ready` property
- [ ] Wire realized spec hash as `has_identifier` in `_pre_resolve` when `media_spec` present

### `tangl/media/dispatch.py`
- [ ] Add `get_media_registries` dispatch task (staged: keep `get_media_inventories` working
  in parallel until graph-as-registry path is proven alongside existing inventory chain)
- [ ] Add `resolve_media_data` dispatch task
- [ ] Add typed result classes: `ResolvedMediaResult`, `PendingMediaResult`, `FailedMediaResult`
- [ ] Default handlers: story graph (EARLY), world registry (NORMAL), sys registry (LATE)

### `tangl/media/media_resource/media_spec_registry.py` (new)
- [ ] `MediaSpecRegistry(Registry[MediaSpec])`
- [ ] `materialize_rit_from_spec()` — dispatches on `resolution_class`
- [ ] `MediaSpecProvisioner` — CREATE offers from spec templates

### `tangl/media/worker_dispatcher.py` (new)
- [ ] `WorkerResult` dataclass (with provenance fields)
- [ ] `WorkerDispatcher` Protocol

### `tangl/media/phase_hooks.py` (new)
- [ ] `reconcile_media_jobs` — `Priority.EARLY` PLANNING; polls RUNNING RITs
- [ ] `dispatch_media_jobs` — `Priority.LATE` PLANNING; dispatches PENDING→RUNNING

### `tangl/service/media.py`
- [ ] `MediaPendingPolicy`, `MediaContentProfile`, `MediaRenderProfile`
- [ ] Refactor `media_fragment_to_payload` to dispatch through `resolve_media_data`
- [ ] `resolve_media_data` default handlers using typed result objects

### `tangl/service/` (REST adapter / runtime controller)
- [ ] Construct `MediaRenderProfile` from request context / connection config
- [ ] Inject `WorkerDispatcher` into `VmPhaseCtx` at story creation

### Deferred
- [ ] `StableForgeDispatcher` — async wrapper over `StableForge.create_media`
- [ ] `ComfyDispatcher` — stub / future
- [ ] Anticipatory affordance quota policy (must be designed before shipping)

---

## Invariants

**Four-state lifecycle; `job_id` is evidence, not state.**
PENDING = accepted, not dispatched. RUNNING = dispatched, acknowledged. RESOLVED = content
available. FAILED = terminal. State carries meaning; `job_id` is an artifact of RUNNING.

**Story-scope media lives in the graph.**
Story RITs are full graph entities. The graph is the story-scope registry. No separate story
`MediaResourceRegistry` needed at runtime.

**Authority chain is a dispatch policy.**
`get_media_registries` handlers compose the chain at dispatch time. Style registries,
arc overrides, CMS integration — all handler registrations, not architectural changes.

**`provider_id` is always UUID; disk resolution is lazy.**
Rebind happens only at serve time, only when a path is stale. `@shelved` makes it cheap.

**Files stay human-readable; content hash is the lookup key.**
`ResourceManager` / `from_source` / `@shelved` indexes files by hash without hash-based filenames.

**RIT is topologically inert once claimed.**
A pending RIT satisfies its dep. The resolver never revisits it.

**Spec hash is the deduplication key.**
Same realized spec + same context → same hash → same RIT as EXISTING. No duplicate jobs.

**Journal is unaware of pending state.**
Journal emits `MediaFragment(content=rit, content_format="rit")` unconditionally.
`resolve_media_data` at serve time is the only place `status` matters.

**WorkerDispatcher is service-layer-only.**
Nothing below `tangl/service/` imports `WorkerDispatcher`. Phase-bus hooks receive it via `ctx`.

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
- **[`media_resurrection_plan.md`](../../notes/media_resurrection_plan.md)** — This design covers Phase 3 and parts of Phase 5.
  Phase 1–2 must be complete first.
- **[`PLANNING_DESIGN.md`](planning/PLANNING_DESIGN.md)** — `MediaSpecProvisioner` follows the same offer/accept protocol
  as `TokenProvisioner` and `TemplateProvisioner`.

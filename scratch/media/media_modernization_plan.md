# Media Subsystem Modernization Plan

## Purpose

Establish a roadmap for reshaping :mod:`tangl.media` and ``engine/tests/media`` so they
align with the contemporary core/vm architecture.  The current package still mixes
older design experiments with partial rewrites, leaving unclear responsibilities,
missing orchestration hooks, and shaky tests.  This plan inventories the delta between
the present state and the desired capabilities, then sequences the work streams needed
to deliver a coherent media inventory + provisioning subsystem.

## Architectural context

- **Core entities and registries** – Media inventory records should behave like modern
  :class:`~tangl.core.entity.Entity` derivatives and participate in the richer
  :class:`~tangl.core.registry.Registry`/dispatch orchestration already used for
  fragments, records, and runtime provisioning.【F:engine/src/tangl/core/entity.py†L24-L147】【F:engine/src/tangl/core/registry.py†L27-L187】
- **VM provisioning loop** – Media dependencies flow through
  :class:`~tangl.vm.planning.Requirement` objects and are satisfied by
  :class:`~tangl.vm.planning.Provisioner`, so media-specific extensions must adopt the
  same requirement/policy semantics instead of bespoke hooks.【F:engine/src/tangl/vm/planning/requirement.py†L19-L153】【F:engine/src/tangl/vm/planning/provisioning.py†L25-L210】
- **Fragment emission** – Deliverables eventually become
  :class:`~tangl.core.fragment.ContentFragment` derivatives that the service layer can
  serialize.  Media fragments therefore need clean dereferencing rules (RIT → concrete
  payload) compatible with service transports.【F:engine/src/tangl/core/fragment.py†L24-L173】【F:engine/src/tangl/media/media_fragment/media_fragment.py†L1-L76】

## Current gaps

1. **Inconsistent entity contracts**
   - ``MediaResourceInventoryTag`` still mixes ad-hoc validation with shelved caching,
     lacks explicit ties to the shared hashing utilities, and does not expose helper
     predicates the registries expect.【F:engine/src/tangl/media/media_resource/media_resource_inv_tag.py†L1-L85】
   - ``MediaResourceRegistry`` manually wires dispatch/creation logic instead of
     reusing the richer registry features (indexing strategies, scoped searches,
     structured receipts).  The API surface also diverges from the node registries the
     provisioning loop expects.【F:engine/src/tangl/media/media_resource/media_resource_registry.py†L1-L69】

2. **Provisioning flow mismatch**
   - ``MediaDep`` constructs requirements but does not clearly express media-specific
     policies (e.g., how to handle spec templates vs. direct data).  It should publish
     explicit requirement subclasses or helpers so service/graph code can reason about
     pending vs. realized media receipts.【F:engine/src/tangl/media/media_resource/media_dependency.py†L1-L52】
   - ``MediaProvisioner`` bypasses the base ``Provisioner`` logic (e.g., requirement
     registry discovery, offer generation) and embeds creation behavior directly,
     leaving no path for UPDATE/CLONE or async creator pipelines.【F:engine/src/tangl/media/media_resource/media_provisioning.py†L1-L69】

3. **Fragment dereferencing + service integration**
   - ``MediaFragment`` stores an opaque ``MediaRIT`` but offers no structured lifecycle
     for the service layer to resolve the blob, pick staging hints, or report missing
     assets.  The dispatch registry intended for handler pipelines is unused, and tests
     only cover trivial URL/binary cases.【F:engine/src/tangl/media/media_fragment/media_fragment.py†L1-L76】【F:engine/tests/media/test_media_fragment.py†L1-L40】

4. **Creator/adaptor plumbing**
   - ``media_spec`` declares dispatch registries but lacks actual adapters/creators and
     does not document how specs evolve from templates → realized media.  Existing
     creator stubs in ``media_creators`` are inconsistent with modern handler
     conventions (e.g., `StableForge` using bespoke APIs).【F:engine/src/tangl/media/media_spec.py†L1-L38】【F:engine/src/tangl/media/media_creators/stable_forge/stable_forge.py†L1-L34】

5. **Testing debt**
   - ``engine/tests/media`` only exercises fragment serialization.  There are no tests
     that pin requirement construction, registry deduplication, or provisioning offers,
     leaving the VM integration unguarded.

## Target capabilities

To match the core/vm model the media subsystem should support:

1. **Stable media inventory records**
   - ``MediaResourceInventoryTag`` behaves like other persistent entities: explicit
     identifiers (uid + aliases), deterministic hashing helpers, and expiry/availability
     checks callable from registries and requirements.
   - Inventory records expose convenience constructors for paths, in-memory blobs, or
     deferred specs, each producing consistent :attr:`content_hash` metadata.

2. **Registry + dispatch alignment**
   - ``MediaResourceRegistry`` reuses ``Registry`` mixins for alias lookup, dedupe, and
     dispatch-based indexing (``on_index``).  Indexing returns receipts (e.g.,
     ``JobReceipt`` or tailored records) that trace decisions for audit/testing.

3. **Media-aware requirements/provisioner**
   - ``MediaDependency`` (or ``MediaRequirement``) clarifies how graph nodes declare
     dependencies, mapping attributes (``media_id``/``media_path``/``media_spec``) to
     requirement fields and provisioning policies.
   - ``MediaProvisioner`` subclasses ``Provisioner`` cleanly: it reuses existing
     EXISTING/UPDATE/CLONE helpers and only overrides creation + registry selection to
     incorporate spec adaptation and media creator pipelines.

4. **Creator pipeline contract**
   - ``MediaSpec`` documents adapter/creator expectations, and ``media_creators``
     publishes actual handlers (e.g., image-from-path, synthesized audio, templated
     prompt).  Creators return both media payload and realized spec metadata.

5. **Fragment + service bridge**
   - ``MediaFragment`` advertises a clear dereference contract (e.g., ``resolve_content``
     hook that returns bytes/path + mime type) and defers actual IO to service-layer
     handlers.  Staging hints and media roles become optional metadata rather than loose
     strings.

6. **Test coverage for the lifecycle**
   - Unit tests cover: registry dedupe by hash/path, requirement building edge cases,
     provisioner offer selection (existing vs. create), and fragment serialization/
     dereferencing hooks.  Higher-level planning tests validate that a graph with media
     dependencies produces provisional RITs the service layer can resolve.

## Work streams

1. **Normalize entities + registries**
   1. Refactor ``MediaResourceInventoryTag`` to inherit from ``BaseModelPlus`` (or align
      with ``Entity`` helpers), add structured alias fields, and replace ad-hoc shelved
      caches with registry-backed memoization or service-layer caching.
   2. Update ``MediaResourceRegistry`` to expose ``index``, ``find_by_hash``, and
      ``ensure`` helpers returning deterministic receipts.  Wire ``on_index`` as a
      ``DispatchRegistry`` with ``aggregation_strategy="pipeline"`` (matching other
      registries).

2. **Define requirements + provisioner surface**
   1. Introduce a ``MediaRequirement`` subclass (``Requirement[MediaRIT]``) that
      validates policy inputs for media IDs/path/specs and stores staging preferences.
   2. Update ``MediaDep`` to wrap/unwrap the new requirement class and expose typed
      attributes for graph authors.
   3. Rework ``MediaProvisioner`` to delegate to ``Provisioner`` while inserting media
      registries, spec adaptation, and creator dispatch.

3. **Creator/adaptor pipeline**
   1. Document how ``MediaSpec``'s ``on_adapt_media_spec`` and ``on_create_media``
      registries should be used (phase semantics, handler signatures).
   2. Port/adapt existing creator implementations from ``media_creators`` to the new
      dispatch conventions, returning realized specs + inventory tags (or raw media to
      be wrapped).

4. **Fragment dereferencing contract**
   1. Expand ``MediaFragment`` with a ``dereference`` method (or dispatch hook) that the
      service layer can call with registry/context info to obtain a concrete blob/path.
   2. Add ``MediaFragment`` tests covering RIT dereferencing, staging hints, and
      serialization behavior for both direct data and inventory references.

5. **Testing + documentation**
   1. Build focused tests under ``engine/tests/media`` for registries, requirements, and
      provisioner flows using ``PYTHONPATH=./engine/src`` fixtures.
   2. Document the lifecycle in ``docs/source`` (or update ``notes``) once the APIs are
      stabilized so future contributors understand media inventory semantics.

## Next steps

- Draft API sketches for ``MediaRequirement`` and the revised provisioner to ensure they
  integrate cleanly with VM planning receipts.
- Prioritize registry/entity refactors before implementing new creators so the tests can
  pin storage semantics early.
- Coordinate with the service-layer code owners to define the dereference interface and
  confirm how media payloads are transported to clients (paths, bytes, or service URLs).

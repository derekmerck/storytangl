Ledger Persistence and Service Integration Plan
==============================================

Overview
--------

The v37 runtime needs a controller that orchestrates users, ledgers, and frames
while remaining compatible with multiple transports (FastAPI, CLI, and future
SDKs).  This note records how the persistence layer, service manager, and
account lookup should collaborate so runtime choices always flow through the
ledger-backed phase bus.

Goals
-----

* Keep persistence adapters generic—every backend should look like a
  ``dict[UUID, Any]`` to the service layer while storing ledgers efficiently.
* Reuse the existing user-domain relationship (API key → user → story/ledger)
  so controllers never guess which ledger belongs to a caller.
* Ensure ledger sessions participate in the same open/link/write-back lifecycle
  already used for ``User`` and ``Story`` objects.
* Support both direct snapshot persistence and event-sourced replay when
  reconstructing a ledger from storage.

Building blocks
---------------

* :mod:`tangl.persistence` already provides factories, serializers, and storage
  helpers so controllers can treat a backend as a mutable mapping.  The v37
  controller should receive a persistence manager capable of opening ledger
  documents by UUID.
* :class:`tangl.service.service_manager.ServiceManager` opens users and stories
  with ACL checks and can be extended to open ledgers/frames using similar
  context managers.
* ``Ledger`` instances encapsulate the active ``Graph``, step counter, stream
  registries, and snapshot metadata required to spin up frames via
  ``ledger.get_frame()``.

Proposed persistence schema
---------------------------

* **Primary identifier:** Persist ledgers under their UUID and store a pointer
  from each ``User`` to their active ledger/story id.  API keys resolve to
  users, which keeps compatibility with existing authentication hooks.
* **Serialized payload:** Start by serializing the current ``Graph`` snapshot,
  the ledger step counter, and the current record streams.  Group the data into
  a ``LedgerEnvelope`` structure so alternative serializers can add metadata
  (e.g., compression hints, timeline identifiers) without changing controller
  code.
* **Write-back cadence:** When a controller exits a ledger context, perform a
  diff-aware write-back: only persist when the ledger step counter advanced or a
  stream mutated.  This mirrors how ``ServiceManager.open_story`` decides when to
  write objects back into the context store.
* **Event-sourced mode:** Allow persistence backends to omit the full ``Graph``
  and reconstruct it from a recent snapshot plus the record stream.  Provide a
  helper in the persistence package (e.g., ``rebuild_ledger(envelope, *, upto)``)
  that the service manager can invoke before yielding the ledger to callers.

User and ledger domain flow
---------------------------

1. Resolve the incoming API key or authentication token to a ``User`` record
   using the persistence manager.
2. Read the user's active ledger/story UUID from the user domain document.
3. Load the ledger envelope from persistence and hydrate a ``Ledger`` instance.
4. Link the ledger's ``user`` attribute (if present) to the resolved ``User`` so
   downstream code can emit receipts tagged with the caller.
5. Yield the ledger/frame to the controller endpoint.  The controller runs
   ``ledger.get_frame()`` or similar operations to process choices.
6. After the endpoint returns, unlink the user reference and decide whether to
   write back the ledger and/or user documents based on mutation flags.

Controller lifecycle integration
--------------------------------

* Extend :class:`ServiceManager` with ``open_ledger`` and ``open_frame`` context
  managers that mirror ``open_story``.  Both helpers should accept ``write_back``
  and ``acl`` parameters so callers can request persisted updates explicitly.
* Update endpoint binding to inject ledger/frame parameters when an endpoint
  type-hints them.  Ledger-aware endpoints automatically gain persistence
  lifecycle management without duplicating boilerplate.
* When both ``story`` and ``ledger`` are requested, ensure the context managers
  open the story first (to locate the ledger id) and then hydrate the ledger.
  Controllers can then combine story metadata (title, tags) with ledger runtime
  receipts before responding to the client.

Snapshot and rebuild strategies
-------------------------------

* **Immediate snapshot:** For short-lived ledgers, persist the full graph and
  streams on every write-back.  This favors simplicity and deterministic reloads.
* **Incremental snapshot:** For longer sessions, capture a full graph snapshot
  every ``N`` steps (configured via the persistence manager) and rely on the
  event stream for intermediate steps.  Store the snapshot index inside the
  ledger envelope so the service manager knows how far to replay events during
  hydration.
* **Pluggable serializers:** Keep serializers discoverable via
  :mod:`tangl.persistence.factory` so new backends (e.g., object storage, SQL)
  can register custom ledger encoders without modifying controller code.

Multi-client considerations
---------------------------

* REST, CLI, and other adapters should treat the controller as the single source
  of truth for ledger mutations.  Each adapter passes the ``user_id`` (or API
  token) into the service manager, which ensures the correct ledger is opened
  and persisted.
* When adapters need read-only access (e.g., polling ledger streams), they can
  request a ``MethodType.READ`` endpoint so ``open_ledger`` avoids unnecessary
  write-backs.
* Batch operations (e.g., multi-choice submissions) should reuse the same ledger
  context to guarantee consistent snapshots and avoid interleaved write-backs.

Next steps
----------

* Prototype ``ServiceManager.open_ledger`` using the existing context store and
  inject it into a new ledger-centric controller.
* Define ``LedgerEnvelope`` (or similar) inside :mod:`tangl.persistence` with
  serializer hooks for the graph, counter, and streams.
* Update persistence adapters to understand the envelope contract and opt into
  event-sourced rebuilds.
* Document how API keys map to user ids and ledger ids so future transports can
  authenticate without hard-coding controller details.


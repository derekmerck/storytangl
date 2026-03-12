Mechanics Overview
==================

``tangl.mechanics`` is best understood as a library of mechanic families rather
than a grab-bag of optional subsystems.

Each family keeps a broad top-level identity such as ``games`` or
``demographics``, while internally we review it through a shared lens:

- **Shape**: what artifacts exist at rest?
- **Behavior**: what transitions or computations occur?
- **Attachment points**: where does it plug into compiler, VM, media, or service flow?
- **Appearance**: what does it project outward as?

The current mechanics resurrection work also uses a common internal layer model:

- **Kernel**: pure deterministic rule logic
- **Domain**: semantic catalogs and vocabulary bindings
- **Runtime**: spec, state, offers, intents, records, receipts
- **Render**: prose, journal, and media projection
- **Writeback**: explicit consequence application
- **Facade**: thin author-facing ``HasX`` surfaces

Current family status
---------------------

- ``games``: reference integrated mechanic family
- ``progression``: strong kernel/runtime foundation
- ``assembly``: constrained optimization foundation
- ``demographics``: profile/domain facet under modernization
- ``presence/wearable`` and ``presence/ornaments``: reusable presence primitives
- ``presence/look``: redesign target with a first explicit description/media payload facade
- ``sandbox`` and ``credentials``: incubating compositions

See also
--------

- :doc:`../design/story/MECHANICS_FAMILIES` for the current architecture note
- :doc:`games` for the reference integrated family

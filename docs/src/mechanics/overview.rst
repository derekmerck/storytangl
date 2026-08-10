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

The current mechanics work also uses common review facets. These organize one
family's responsibilities; they are not additional engine layers:

- **Kernel**: pure deterministic rule logic
- **Domain**: semantic catalogs and vocabulary bindings
- **Runtime**: spec, state, offers, intents, records, receipts
- **Render**: prose, journal, and media projection
- **Writeback**: explicit consequence application
- **Facade**: thin author-facing ``HasX`` surfaces

Current family status
---------------------

- ``games``: reference integrated mechanic family
- ``progression``: integrated training/challenge/growth foundation
- ``assembly`` and ``transaction``: shared component and writeback foundations
- ``demographics``: profile/domain facet under modernization
- ``presence/wearable`` and ``presence/ornaments``: reusable presence primitives
- ``presence/look``: integrated semantic text/portrait projection foundation
- ``sandbox``: integrated spatial/activity vertical
- ``credentials``: worked convergence capstone
- ``simulation``: deterministic operational-model foundation

See also
--------

- :doc:`../design/story/MECHANICS_FAMILIES` for the current architecture note
- :doc:`games` for the reference integrated family

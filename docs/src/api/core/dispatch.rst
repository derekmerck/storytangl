.. currentmodule:: tangl.core

tangl.core dispatch
===================

Behavior and dispatch primitives that higher layers use to register and execute
hooks.

.. storytangl-topic::
   :topics: dispatch
   :facets: api
   :relation: documents

.. rubric:: Related design docs

- :doc:`../../design/core/HOOK_REF`

.. rubric:: Related notes

- :doc:`../../notes/reference/code_adjacent_design_docs`

Behaviors
---------

.. autoclass:: tangl.core.Behavior
.. autoclass:: tangl.core.BehaviorRegistry
.. autoclass:: tangl.core.CallReceipt

Dispatch module
---------------

.. automodule:: tangl.core.dispatch

Creation hooks
--------------

.. autofunction:: tangl.core.dispatch.on_create
.. autofunction:: tangl.core.dispatch.do_create
.. autofunction:: tangl.core.dispatch.on_init
.. autofunction:: tangl.core.dispatch.do_init

Registry hooks
--------------

.. autofunction:: tangl.core.dispatch.on_add_item
.. autofunction:: tangl.core.dispatch.do_add_item
.. autofunction:: tangl.core.dispatch.on_get_item
.. autofunction:: tangl.core.dispatch.do_get_item
.. autofunction:: tangl.core.dispatch.on_remove_item
.. autofunction:: tangl.core.dispatch.do_remove_item

Graph hooks
-----------

.. autofunction:: tangl.core.dispatch.on_link
.. autofunction:: tangl.core.dispatch.do_link
.. autofunction:: tangl.core.dispatch.on_unlink
.. autofunction:: tangl.core.dispatch.do_unlink

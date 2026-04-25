.. currentmodule:: tangl.vm

tangl.vm.dispatch
=================

Dispatch decorators and handler entrypoints that allow higher layers to
contribute runtime, provisioning, and replay behavior.

.. storytangl-topic::
   :topics: dispatch, phase_ctx, resolution_phase
   :facets: api
   :relation: documents

.. rubric:: Related design docs

- :doc:`../../design/planning/PROVISIONING_BEHAVIOR`

.. rubric:: Related notes

- :doc:`../../notes/reference/code_adjacent_design_docs`

Dispatch module
---------------

.. automodule:: tangl.vm.dispatch

Phase decorators
----------------

.. autofunction:: tangl.vm.dispatch.on_validate
.. autofunction:: tangl.vm.dispatch.on_provision
.. autofunction:: tangl.vm.dispatch.on_prereqs
.. autofunction:: tangl.vm.dispatch.on_update
.. autofunction:: tangl.vm.dispatch.on_journal
.. autofunction:: tangl.vm.dispatch.on_finalize
.. autofunction:: tangl.vm.dispatch.on_postreqs

Phase runners
-------------

.. autofunction:: tangl.vm.dispatch.do_validate
.. autofunction:: tangl.vm.dispatch.do_provision
.. autofunction:: tangl.vm.dispatch.do_prereqs
.. autofunction:: tangl.vm.dispatch.do_update
.. autofunction:: tangl.vm.dispatch.do_journal
.. autofunction:: tangl.vm.dispatch.do_finalize
.. autofunction:: tangl.vm.dispatch.do_postreqs

Namespace and scope hooks
-------------------------

``on_gather_ns`` / ``do_gather_ns`` assemble the scoped runtime namespace.
Entity ``get_ns()`` remains the lower-level local publication seam.

.. autofunction:: tangl.vm.dispatch.on_gather_ns
.. autofunction:: tangl.vm.dispatch.do_gather_ns

Resolution override hooks
-------------------------

.. autofunction:: tangl.vm.dispatch.on_resolve
.. autofunction:: tangl.vm.dispatch.do_resolve

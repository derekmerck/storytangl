.. currentmodule:: tangl.vm

tangl.vm.dispatch
=================

Dispatch decorators and handler entrypoints that allow higher layers to
contribute runtime, provisioning, and replay behavior.

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

.. autofunction:: tangl.vm.dispatch.on_gather_ns
.. autofunction:: tangl.vm.dispatch.do_gather_ns
.. autofunction:: tangl.vm.dispatch.on_get_template_scope_groups
.. autofunction:: tangl.vm.dispatch.do_get_template_scope_groups
.. autofunction:: tangl.vm.dispatch.on_get_token_catalogs
.. autofunction:: tangl.vm.dispatch.do_get_token_catalogs

Resolution override hooks
-------------------------

.. autofunction:: tangl.vm.dispatch.on_resolve
.. autofunction:: tangl.vm.dispatch.do_resolve

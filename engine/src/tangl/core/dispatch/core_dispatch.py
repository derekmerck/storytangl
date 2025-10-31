# tangl/core/dispatch/core_dispatch.py
"""`core_dispatch` GLOBAL layer behavior registry and convenience decos"""

from functools import partial
from tangl.core.behavior.behavior import HandlerLayer as L
from tangl.core.behavior.layered_dispatch import LayeredDispatch

core_dispatch = LayeredDispatch(label="core.dispatch", handler_layer=L.GLOBAL)

# Used in HookedEntity for structuring and __post_init__
on_create = partial(core_dispatch.register, task="create")  # cls and kwargs resolution (unstructured data)
on_init   = partial(core_dispatch.register, task="init")    # post-init hook (self)

# Used in HookedGraph when adding or removing an edge
on_link   = partial(core_dispatch.register, task="link")    # connect nodes (source, dest)
on_unlink = partial(core_dispatch.register, task="unlink")  # disconnect nodes (source, dest)

# Core dispatch may have helpers, auditors, or other features; but lower
# layer tasks should never invoke or register with the core_dispatch directly,
# just inject it as a layer into its own task.
# If core _wants_ to define an application-specific handler, like an auditor
# for the vm "planning" task, that's fine, but it none of vm's business.
# vm will invoke it automatically along with core_dispatch.

# see `tangl/core/dispatch/hooked_registry.py` for a registry that uses the `on_index` hook and provides a local layer behavior registry.

# see `tangl/vm/vm_dispatch.py` for an example of a system layer registry and features.

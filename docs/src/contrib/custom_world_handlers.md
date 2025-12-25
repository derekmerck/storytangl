# Custom World Materialization Handlers

StoryTangl's materialization pipeline is dispatch-driven. Worlds can extend it by
registering handlers on the ``fabula.materialize`` task. Handlers run in phase
order and share a :class:`~tangl.vm.context.MaterializationContext` that carries
the template, payload, parent container, and created node.

## Phases

| Phase | Priority | Purpose | Context state |
| ----- | -------- | ------- | ------------- |
| EARLY | 10 | Mutate payload before creation | ``node`` is ``None`` |
| NORMAL | 50 | Create node (must set ``ctx.node``) | Node created |
| LATE | 80 | Standard wiring (roles/actions/media) | Node available |
| LAST | 90 | Custom world logic | Node fully wired |

## Registering a Handler

```python
from tangl.vm.dispatch import vm_dispatch
from tangl.vm.dispatch.materialize_task import MaterializePhase, MaterializeTask
from tangl.vm.context import MaterializationContext


@vm_dispatch.register(
    task=MaterializeTask.MATERIALIZE,
    priority=MaterializePhase.LAST,
    layer="my_world",
)
def generate_description(caller, *, ctx: MaterializationContext, **_):
    if ctx.node.has_tags("procedural"):
        ctx.node.description = f"Generated for {ctx.node.label}"
```

## Best Practices

1. Use EARLY for payload mutation; avoid patching node attributes post-creation
   unless necessary.
2. Keep NORMAL handlers small—only instantiate and attach the node.
3. Reserve LAST for world-specific behavior so the standard LATE wiring completes
   first.
4. Always unregister temporary handlers in tests with ``vm_dispatch.remove`` to
   avoid cross-test interference.

## Inspecting Handlers

You can inspect registered handlers to debug ordering:

```python
from tangl.vm.dispatch import vm_dispatch
from tangl.vm.dispatch.materialize_task import MaterializeTask

handlers = vm_dispatch.get_handlers(task=MaterializeTask.MATERIALIZE)
for behavior in handlers:
    print(behavior.priority, behavior.layer, behavior.func.__name__)
```


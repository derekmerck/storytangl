from tangl.core38 import on_get_item


class WraptProxy: ...

class WraptRegistry:

    registry: Registry

@on_get_item(priority=Priority.LATE)
def _return_a_proxy(registry, item_id, _ctx=None) -> WraptProxy:
    return WraptProxy.from_item(self.registry.get(item_id))
from tangl.core38 import on_get_item, Registry, Priority

class WraptProxy: ...

class WraptRegistry:
    registry: Registry

@on_get_item
def _return_a_proxy(registry, item_id, _ctx=None) -> WraptProxy:
    return WraptProxy.from_item(registry.get(item_id))

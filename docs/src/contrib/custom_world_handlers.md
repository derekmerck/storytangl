# Custom World Runtime Hooks

StoryTangl story38 no longer exposes the old ``fabula.materialize`` phase bus.
World-specific behavior now plugs in through explicit world and runtime hooks,
which keeps materialization passes deterministic and makes extension points
easier to see in code review.

## Current Extension Points

| Hook | Implement on | Used by | Purpose |
| ---- | ------------ | ------- | ------- |
| ``get_authorities()`` | world/domain facet | ``StoryGraph.get_authorities()`` -> ``PhaseCtx.get_authorities()`` | Add runtime behavior registries for tasks like ``gather_ns``, ``prereqs``, ``postreqs``, or scoped media/template lookups. |
| ``get_template_scope_groups(caller=..., graph=...)`` | world/templates facet | script manager, resolver, materializer | Add extra template registries in nearest-to-broadest scope order. |
| ``get_media_inventories(caller=..., requirement=..., graph=...)`` | world/resources facet | runtime media resolution | Expose world-scoped media inventories without hard-coding global registries. |
| ``frame.local_behaviors`` / ``ledger.local_behaviors`` | runtime or tests | ``PhaseCtx`` local authorities | Attach opt-in local behavior registries for experiments, auditing, or one-off tests. |

## Registering World Runtime Behaviors

World authorities are just explicit :class:`~tangl.core.behavior.BehaviorRegistry`
instances returned by a facet's ``get_authorities()`` method.

```python
from dataclasses import dataclass

from tangl.core import BehaviorRegistry, DispatchLayer
from tangl.story import World


world_registry = BehaviorRegistry(
    label="weather.world",
    default_dispatch_layer=DispatchLayer.APPLICATION,
)


@world_registry.register(task="gather_ns")
def inject_weather(caller, *, ctx, **_):
    return {"weather": "fog"}


@dataclass(slots=True)
class WeatherDomain:
    def get_authorities(self):
        return [world_registry]


world = World.from_script_data(script_data=script, domain=WeatherDomain())
result = world.create_story("weather_demo")
```

## Extending Template Scope

Additional authored templates should be contributed through
``get_template_scope_groups(...)`` rather than through a separate materialize
phase.

```python
from dataclasses import dataclass

from tangl.core import TemplateRegistry
from tangl.story import World


@dataclass(slots=True)
class ExtraTemplates:
    extra: TemplateRegistry

    def get_template_scope_groups(self, *, caller=None, graph=None):
        return [list(self.extra.values())]


world = World.from_script_data(
    script_data=script,
    templates=ExtraTemplates(extra=bonus_templates),
)
```

## Best Practices

1. Return explicit registries or groups from world facets; avoid mutating global
   dispatch registries in tests unless the behavior is truly shared.
2. Keep world authorities focused on runtime behavior. Use template/media scope
   hooks for lookup data instead of squeezing that data through dispatch tasks.
3. Use ``frame.local_behaviors`` or ``ledger.local_behaviors`` for short-lived
   experiments and test overrides rather than adding new global handlers.
4. Treat the old materialize-task docs and ``MaterializationContext`` examples as
   retired. The current story38 materializer is organized as explicit passes, not
   a public per-phase dispatch bus.

from dataclasses import dataclass, field

from tangl.core38 import Registry
from .patch import Event, Patch


@dataclass
class RegistryObserver:

    registry: Registry
    initial_value_hash: bytes
    events: list[Event] = field(default_factory=list)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial_value_hash = self.registry.value_hash()

    def submit_event(self, event: Event) -> None:
        self.events.append(event)

    def get_patch(self, label=None, tags=None) -> Patch:
        # label and tags for segmenting within trace stream
        return Patch(
            label=label,
            tags=tags,
            registry_id=self.registry.uid,
            initial_registry_value_hash=self.initial_value_hash,
            final_registry_value_hash=self.registry.value_hash(),
            events=sorted(self.events)
        )

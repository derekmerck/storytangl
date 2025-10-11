from __future__ import annotations
from typing import Callable

from tangl.type_hints import Pathlike

from .resource_inventory_tag import ResourceInventoryTag as RIT
from .resource_registry import ResourceRegistry


class MediaRegistryHandler:

    @classmethod
    def add_resource_domain(cls, domain: str):
        ResourceRegistry( label=domain )

    @classmethod
    def add_location(cls, domain: str, **kwargs):
        resource_domain = ResourceRegistry.get_instance(domain)
        resource_domain.add_location(**kwargs)

    @classmethod
    def add_file_location(cls, domain: str, base_path: Pathlike, tagging_func: Callable = None):
        resource_domain = ResourceRegistry.get_instance(domain)
        resource_domain.add_file_location(base_path, tagging_func=tagging_func)

    @classmethod
    def update_inventory(cls, domain: str = None):
        if domain is not None:
            registries = [ ResourceRegistry.get_instance(domain) ]
        else:
            registries = list( ResourceRegistry._instances.values() )
        for resource_domain in registries:
            resource_domain.update_inventory()

    @classmethod
    def find_resource(cls, domain: str, *aliases, **kwargs ) -> RIT:
        resource_domain = ResourceRegistry.get_instance(domain)
        return resource_domain.find_resource(*aliases, **kwargs)

    @classmethod
    def find_resources(cls, domain: str, *aliases, **kwargs ) -> list[RIT]:
        resource_domain = ResourceRegistry.get_instance(domain)
        return resource_domain.find_resources(*aliases, **kwargs)

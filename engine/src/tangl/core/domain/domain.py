from typing import Any, Iterable, TypeAlias, Optional, Callable
from collections import ChainMap
from uuid import UUID

from pydantic import Field

from tangl.info import __version__
from tangl.type_hints import StringMap
from tangl.core.entity import Entity
from tangl.core.registry import Registry
from tangl.core.dispatch import HandlerRegistry, DEFAULT_HANDLERS

DEFAULT_VARS = {'version': __version__}


class Domain(Entity):
    # Domains are collections of sharable identifiers, handlers,
    # provisioners that can be aggregated into a scope.
    #
    # Domains may be explicitly adopted, often as a singleton with a
    # label- or type-based opt-in, or implicitly assigned by membership
    # in a group, such as a subgraph that donates capabilities to its
    # members.
    #
    # Capabilities:
    # - shared vars
    # - shared handlers/providers

    vars: StringMap = Field(default_factory=dict)
    handlers: HandlerRegistry = Field(default_factory=HandlerRegistry)

    selector: Optional[Callable[[Entity], bool]] = Field(default=lambda x: False, repr=False)

    def add_vars(self, vars: dict[str, Any]) -> None:
        self.vars.update(vars)

    def add_handler(self, func, **attrs) -> None:
        self.handlers.add(func, **attrs)

    def register_handler(self, **attrs: Any) -> None:
        return self.handlers.register(**attrs)

class DomainRegistry(Registry[Domain]):
    # I'm not sure how this should be organized:
    # - a single global registry
    # - a singleton Domain class where every domain is named and findable in the _instances registry?
    # - A list of multiple registries per type and story world?

    def find_domains_for(self, item: Entity) -> Iterable[Domain]:
        """Yield domains whose tags intersect item/ancestor tags or whose selector returns True."""
        # check tags, class type for matching domains in self
        seen: set[UUID] = set()
        # Collect tags from item and ancestors
        tag_sets = [getattr(item, "tags", set())]
        for anc in getattr(item, "ancestors", lambda: [])():
            tag_sets.append(getattr(anc, "tags", set()))
        all_tags = set().union(*tag_sets)

        for d in self.values():
            if d.uid in seen:
                continue
            if d.selector and d.selector(item):
                seen.add(d.uid)
                yield d
                continue
            if d.tags and (d.tags & all_tags):
                seen.add(d.uid)
                yield d


# Not needed yet
# class SingletonDomain(Domain, Singleton):
#     # indicated explicitly by tags or type/class membership
#     ...

global_domain = Domain(label="globals",
                       vars=DEFAULT_VARS,
                       handlers=DEFAULT_HANDLERS,
                       )

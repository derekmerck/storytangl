from abc import abstractmethod
from typing import Any, Optional

from ...entity import Entity, Context, Registry
from .requirement import Requirement


class Provider(Entity):

    @abstractmethod
    def satisfies_requirement(self, req: Requirement) -> bool:
        ...

    @abstractmethod
    def get_provider(self, req: Requirement, ctx: Context):
        ...

class FindProvider(Registry[Entity]):
    # Search a scope for matching entities

    # todo: actually want to check satisfies req and ungated by predicate
    def satisfies_requirement(self, req: Requirement) -> bool:
        return self.get_provider(req) is not None

    def get_provider(self, req: Requirement, ctx = None):
        return self.find_one(**req.provider_criteria)

class ResourceBuilder(Entity):
    # templates
    data: dict[str, Any]

    def satisfies_requirement(self, req: Requirement) -> bool:
        ...

    @abstractmethod
    def build(self, ctx: Context) -> Entity:
        return self.structure(**self.data)

class CreateProvider(Registry[ResourceBuilder]):
    # Search a scope for matching builders

    def _find_builder(self, req: Requirement) -> Optional[ResourceBuilder]:
        return self.find_one(**req.provider_criteria)

    def satisfies_requirement(self, req: Requirement) -> bool:
        return self._find_builder(req) is not None

    def get_provider(self, req: Requirement, ctx: Context) -> Entity:
        builder = self._find_builder(req)
        return builder.build(ctx)

from __future__ import annotations
from typing import ClassVar, Any, Optional, TYPE_CHECKING, Self
from uuid import UUID
from copy import deepcopy
import abc

from pydantic import BaseModel

from tangl.entity import Entity
from tangl.entity.mixins import Templated, HasNamespace
from tangl.type_hints import UniqueLabel
from tangl.utils.uuid_for_secret import hash_for_secret, uuid_for_secret
from tangl.utils.deep_merge import deep_merge
from .protocols import MediaForgeProtocol

if TYPE_CHECKING:
    from tangl.graph import Node

class MediaSpecification(BaseModel):
    # This is pydantic, so it can be read directly from scripts as part of a reference.
    # todo: important, I think that this has to be properly separated into script and entity items.
    #       media node can't keep a bunch of entities of the same type attached to different properties
    #       without some work.  maybe like edges in traversables? or as singleton references like
    #       wrapped singletons?

    uid_: Optional[UUID] = None  #: Don't need a default uid

    def _secret(self):
        res = repr(self.model_dump(exclude_none=True, exclude_unset=True, exclude={'uid'}))
        return res

    def digest(self):
        return hash_for_secret(self._secret()).hex()

    @property
    def uid(self) -> UUID:
        return uuid_for_secret(self._secret())

    # def __init__(self, *args, template: str = None, **kwargs):
    #     # Inject spec template defaults
    #     # if template_kwargs := self.templates.get(template):
    #     #     # print(f'found template {template}')
    #     #     template_kwargs = deepcopy(template_kwargs)
    #     #     deep_merge(template_kwargs, kwargs)
    #     #     kwargs = template_kwargs
    #     # Inspect class fields and check for aliases
    #     # do this second, so it can convert n_prompt -> negative prompt
    #     for name, field in self.model_fields.items():
    #         if field.alias and name in kwargs:
    #             kwargs[field.alias] = kwargs.pop(name)
    #     super().__init__(**kwargs)

    def realize(self, ref: 'Node' = None, **overrides) -> Self:
        if overrides:
            kwargs = self.model_dump() | overrides | ref.get_namespace()
            return self.__class__(**kwargs)
        return self

    @classmethod
    def get_forge(cls, **kwargs) -> MediaForgeProtocol:
        # Do not mark this abstract, or it will prevent creating specs
        # without an explicit base class
        raise NotImplementedError

from typing import Self
from functools import partial

from pydantic import model_validator

from tangl.core.entity import Entity
from tangl.type_hints import StringMap
from tangl.core.behavior import CallReceipt
from .core_dispatch import core_dispatch

on_create = partial(core_dispatch.register, task="create")  # cls and kwargs resolution (unstructured data)
on_init   = partial(core_dispatch.register, task="init")    # post-init hook (self)


class HookedEntity(Entity):

    @model_validator(mode="after")
    def _post_init(self):
        core_dispatch.dispatch(self, ctx=None, task="init")
        return self

    @classmethod
    def structure(cls, data: StringMap) -> Self:
        receipts = core_dispatch.dispatch(data, ctx=None, task="init")
        data = CallReceipt.gather_results(*receipts)
        return super().structure(data)

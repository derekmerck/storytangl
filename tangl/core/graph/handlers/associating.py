from __future__ import annotations
from typing import Optional, Self, Any

from tangl.core.graph import Node
from tangl.core.task_handler import TaskPipeline

on_associate = TaskPipeline[Node, Any]("on_associate")
on_disassociate = TaskPipeline[Node, Any]("on_disassociate")

class Associating(Node):

    @property
    def associates(self) -> list[Self]:
        return self.find_children(obj_cls=self)

    @on_associate.register()
    def _call_other_associate(self, **context):
        # todo: Make sure this doesn't result in a recursion
        ...

    @on_disassociate.register()
    def _call_other_disassociate(self, **context):
        ...

    def associate(self, other: Associating, **context):
        ...

    def disassociate(self, other: Associating, **context):
        ...

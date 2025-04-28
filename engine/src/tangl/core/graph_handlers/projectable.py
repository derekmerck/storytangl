from typing import Any, Optional

from pydantic import ConfigDict

from ..graph import Node
from ..fragment import ContentFragment
from ..handler_pipeline import HandlerPipeline, PipelineStrategy
from ..entity_handlers import Renderable
from .traversable import TraversableNode

on_project = HandlerPipeline(
    label="on_project",
    pipeline_strategy=PipelineStrategy.GATHER,
)

class ProjectableNode(Renderable, Node):

    def create_projection(self, **context):
        context = context or self.gather_context(**context)
        on_project.execute(self, **context)

    @on_project.register()
    def _create_fragment_node(self, **context):
        fragments = self.render(**context)
        fragment_node = FragmentNode(
            graph=self.graph,
            fragments=fragments
        )
        self.add_child(fragment_node, as_parent=True)

    @property
    def projections(self):
        ...

class FragmentNode(Node):
    """
    An immutable leaf node representing the projection of a structural graph node.

    - Created during traversal of structure nodes
    - Contains rendered content fragments
    - Links back to its parent structure node and associated concepts
    - Only has fragment children
    """
    # Make immutable
    model_config = ConfigDict(frozen=True)

    fragments: list[ContentFragment]

    # @property
    # def parent(self) -> Optional[TraversableNode]:
    #     return super().parent
    #
    # def fragments(self) -> list[ContentFragment]:
    #     return self.find_children(has_cls=ContentFragment)  # type: list[ContentFragment]

    @classmethod
    def from_structure_node(cls, parent: TraversableNode, **context):
        """Factory method to create a projection from a structure node"""
        # this doesn't account for the fact that a single structure node can generate many projection leafs
        content_fragments = parent.render(**context)
        return cls(
            parent=parent,
            fragments=content_fragments,
            # Other fields as needed
        )
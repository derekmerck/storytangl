from __future__ import annotations
from typing import Optional, Any

from tangl.core import Node, BaseFragment, Graph
from tangl.vm import ChoiceEdge, Context
from tangl.story.runtime import ContentRenderer

class Action(ChoiceEdge):

    content: Optional[str] = None
    payload: Optional[Any] = None
    # `payload` is useful if you want to re-use the same action with
    # different parameters, or set a parameter on the client end and
    # return it via an action cb

    def get_content(self) -> str:
        return self.content or self.label or "continue"

    def choice_fragment(self: Action, *, ctx: Context, **locals_: Any) -> BaseFragment | None:
        """Render inline content for a block."""
        content = self.get_content()
        content = ContentRenderer.render_with_ctx(content, self, ctx=ctx)
        if content:
            if self.payload:
                return BaseFragment(
                    content=content,
                    payload=self.payload,
                    source_id=self.uid,
                    source_label=self.label,
                    fragment_type="choice",
                )
            return BaseFragment(
                content=content,
                source_id=self.uid,
                source_label=self.label,
                fragment_type="choice",
            )

    # Create an edge dynamically, as from a survey of nodes meeting a criteria.
    # Usually the target node itself will carry annotations for how to label
    # the action.
    @classmethod
    def from_episode(cls, node: Node):
        # todo: This type of action suffers from indeterminate namespace inheritance,
        #       should available() be based on the target node or the current
        #       node's availability or both?
        return cls(
            content = node.locals.get("action_text", node.get_label()),
            destination_id = node.uid,
            graph = node.graph,
            tags={'dynamic'}  # dynamic affordance, can gc aggressively
        )

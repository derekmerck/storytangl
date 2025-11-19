from __future__ import annotations
from collections.abc import Mapping
from typing import Optional, Any

from tangl.core import Node, BaseFragment, Graph
from tangl.journal.discourse import ChoiceFragment
from tangl.story.runtime import ContentRenderer
from tangl.vm import ChoiceEdge, Context
from tangl.vm.runtime import HasConditions, HasEffects
from tangl.vm.provision import Dependency

class Action(ChoiceEdge, HasConditions, HasEffects):

    content: Optional[str] = None
    payload: Optional[Any] = None
    # `payload` is useful if you want to re-use the same action with
    # different parameters, or set a parameter on the client end and
    # return it via an action cb

    def get_content(self) -> str:
        return self.content or self.label or "continue"

    def choice_fragment(self: Action, *, ctx: Context, **locals_: Any) -> ChoiceFragment | None:
        """Render this action as a journaled choice fragment."""

        content = self.get_content()
        content = ContentRenderer.render_with_ctx(content, self, ctx=ctx)

        if not content:
            return None

        is_available = self.is_available(ctx=ctx)
        unavailable_reason: str | None = None

        unmet_dependencies: list[Dependency] = []
        if self.destination_id:
            destination = self.graph.get(self.destination_id)
            if destination is not None:
                unmet_dependencies = [
                    edge
                    for edge in self.graph.find_edges(
                        source_id=destination.uid,
                        is_instance=Dependency,
                    )
                    if edge.requirement.hard_requirement and not edge.requirement.satisfied
                ]
                if unmet_dependencies:
                    is_available = False
                    labels = [edge.label or "requirement" for edge in unmet_dependencies]
                    unavailable_reason = f"Requires: {', '.join(labels)}"

        if not is_available and unavailable_reason is None:
            unavailable_reason = "Prerequisites not met"

        return ChoiceFragment(
            content=content,
            source_id=self.uid,
            label=self.label,
            source_label=self.label,
            active=is_available,
            unavailable_reason=unavailable_reason,
            activation_payload=self.payload,
        )

    def is_available(
        self,
        *,
        ctx: Context | None = None,
        ns: Mapping[str, Any] | None = None,
    ) -> bool:
        """Evaluate predicate and scripted conditions for this action."""

        resolved_ns: Mapping[str, Any] | None = ns
        if ctx is not None:
            action_ns = ctx.get_ns(self)
            if resolved_ns is None:
                resolved_ns = action_ns
            else:
                merged_ns = dict(resolved_ns)
                merged_ns.update(action_ns)
                resolved_ns = merged_ns

        if resolved_ns is not None and not ChoiceEdge.available(self, resolved_ns):
            return False

        if not self.conditions:
            return True

        if resolved_ns is None:
            return True  # Cannot evaluate without a namespace; assume available.

        rand = ctx.rand if ctx is not None else None
        return all(self._eval_expr(expr=expr, ns=resolved_ns, rand=rand) for expr in self.conditions)

    def apply_selected(self, *, ctx: Context) -> None:
        """Apply entry and final effects when this action is chosen."""

        if self.entry_effects:
            self.apply_entry_effects(ctx=ctx)
        if self.final_effects:
            self.apply_final_effects(ctx=ctx)

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

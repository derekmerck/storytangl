from .node import Edge, Node, Graph
from .context import ContextBuilder, ContextView
from .resolver import Resolver
from .conditions import ConditionChecker
from .renderer import Renderer
from .task_handler import TaskRegistry as HandlerPipeline
from .registry import Registry
from .template import Template

class CursorDriver:
    def __init__(self, graph: Graph, templates: Registry[Template], journal = None, return_stack=None):
        self.g = graph
        self.templates = templates
        self.journal = journal or []
        self.return_stack = return_stack or []

        self.effects_pipeline = HandlerPipeline(label="on_apply_effects")
        self.follow_edge_pipeline = HandlerPipeline(label="on_follow_edge")

    def step(self, edge: Edge | None = None, *, globals=None):
        e = edge or Edge(successor_id=self.g.cursor_id)
        while e:
            # todo: ctx here is complicated, do we use pred or successor?
            #       Do we need a follow pipeline at all?  It's just to finalize
            #       the pred if there is exit bookkeeping
            self._follow(e, ctx=None)
            node = self.g.cursor
            ctx = ContextBuilder.gather(node, self.g, globals=globals or {})

            # ------------- redirect -------------
            e = node._select(node.redirects, ctx)
            if e: continue

            # resolve → effects → render
            Resolver.resolve(node=node, graph=self.g, templates=self.templates, ctx=ctx)
            if not ConditionChecker.check(node, ctx): return
            self.effects_pipeline.execute_all(entity=node, ctx=ctx)
            frags = Renderer.render(node, ctx)
            self.journal.extend(frags)

            # ------------- continue -------------
            e = node._select(node.continues, ctx)
            if e: continue

            # ------------- choice or return -----
            if node.choices:
                return                                        # UI decides
            if self.return_stack:
                e = Edge(successor_id=self.return_stack.pop())
                continue
            return

    # -------------------------------------------------------
    def _follow(self, edge: Edge, ctx: ContextView):
        self.follow_edge_pipeline.execute_all(entity=self.g, edge=edge, ctx=ctx)       # pipeline
        self.g.cursor_id = edge.successor_id
        if edge.return_after:
            self.return_stack.append(edge.predecessor_id)

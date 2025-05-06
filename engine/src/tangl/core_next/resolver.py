from .task_handler import TaskRegistry as HandlerPipeline
from .registry import Registry
from .template import Template
from .node import Node, Graph
from .context import ContextView
from .fragment import ContentFragment

class Resolver:
    on_find     = HandlerPipeline(label='on_find_provider')
    on_find_template = HandlerPipeline(label='on_find_template')
    on_create  = HandlerPipeline(label='on_create_provider')
    on_link    = HandlerPipeline(label='on_link_provider')

    @classmethod
    def resolve(cls, node: Node, graph: Graph, templates: Registry[Template], ctx: ContextView):
        missing = node.requires - set(graph.index)
        for key in missing:
            associate = cls.on_find.execute_all(entity=graph, key=key, ctx=ctx)  # may return a satisfying node
            if associate is None:
                template = cls.on_find_template.execute_all(entity=node, templates=templates, ctx=ctx)  # may return a satisfying template
                if template is not None:
                    associate = cls.on_create.execute_all(entity=template, ctx=ctx) or template.build(ctx=ctx)
                    graph.add(associate)
            if associate is not None:
                cls.on_link.execute_all(entity=node, associate=associate, key=key, ctx=ctx)

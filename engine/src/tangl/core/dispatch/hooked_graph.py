from functools import partial

from tangl.core.graph import Graph
from .hooked_registry import HookedRegistry
from .core_dispatch import core_dispatch

on_link   = partial(core_dispatch.register, task="link")    # connect nodes (source, dest)
on_unlink = partial(core_dispatch.register, task="unlink")  # disconnect nodes (source, dest)


class HookedGraph(Graph, HookedRegistry):

    def add_edge(self, *args, **kwargs):
        edge = super().add_edge(*args, **kwargs)
        core_dispatch.dispatch(edge, ctx=None, task="link")

    def remove_edge(self, *args, **kwargs):
        edge = super().remove_edge(*args, **kwargs)
        core_dispatch.dispatch(edge, ctx=None, task="unlink")


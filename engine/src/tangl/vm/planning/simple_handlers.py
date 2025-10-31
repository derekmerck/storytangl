# tangl/vm/simple_handlers.py

import logging

from collections.abc import Iterable

from tangl.core import BaseFragment, Node
from tangl.vm.context import Context
from tangl.vm.frame import ResolutionPhase as P, ChoiceEdge

logger = logging.getLogger(__name__)


# ------- VALIDATION ---------

# ------- PLANNING ---------

# register planning handlers
from tangl.vm.planning import simple_planning_handlers

# @global_domain.handlers.register(phase=P.PLANNING, priority=50)
# def plan_provision(cursor: Node, **kwargs):
#     # satisfy open Dependency edges out of the cursor
#     g: Graph = cursor.graph
#     made = 0
#     for e in list(cursor.edges_out(is_instance=Dependency)):  # freeze the edge list
#         req = e.requirement
#         if not req.satisfied and not req.is_unresolvable:
#             # Search in graph (and optionally other registries)
#             prov = Provisioner(requirement=req, registries=[g])
#             if prov.resolve():
#                 made += 1
#     return made

# ------- PRE/POST REDIRECTS ---------

# ------- UPDATE/FINALIZE ---------

# ------- JOURNAL ---------

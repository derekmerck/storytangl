from typing import Optional

from ..enums import ServiceKind
from .requirement import Requirement
from .provider import DirectProvider, IndirectProvider

def resolve_requirements(*scopes, ctx) -> bool:

    node, graph, *scopes = scopes

    for req in node.requirements:  # type: Requirement
        if req.satisfied(ctx):
            continue
        prov = None
        match req.obligation:
            case "find_or_create":
                prov = find_provider(req, *scopes, ctx=ctx) or create_provider(req, *scopes, ctx=ctx)
            case "find_only":
                prov = find_provider(req, *scopes, ctx=ctx)
            case "always_create":
                prov = create_provider(req, *scopes, ctx=ctx)
            case _ if req.hard:
                return False
        if prov:
            graph.link('provides', prov, node)
    return True

def find_provider(req, *scopes, ctx) -> Optional[Provider]:
    for s in scopes:
        for p in s.get_handlers(ServiceKind.PROVISION, obj_cls=DirectProvider):
            if p.satisfies(req, ctx):
                return p.get_provider()

def create_provider(req, *scopes, ctx) -> Optional[Provider]:
    for s in scopes:
        for p in s.get_handlers(ServiceKind.PROVISION, obj_cls=IndirectProvider):
            if p.satisfies(req, ctx):
                builder = p.get_builder()
                return builder.create_provider(req, *scopes, ctx)

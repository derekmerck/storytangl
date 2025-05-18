from .requirement import Requirement
from .provider import try_find_provider, try_create_provider


def resolve_requirements(caller, graph, *scopes, ctx) -> bool:

    for req in caller.requirements:  # type: Requirement
        if req.satisfied(ctx=ctx):
            continue

        # try to find a provider else find an indirect provider and create for each
        # Update context with any new provisions

        prov = None
        match req.obligation:
            case "find_or_create":
                prov = try_find_provider(req, *scopes, ctx=ctx) or try_create_provider(req, *scopes, ctx=ctx)
            case "find_only":
                prov = try_find_provider(req, *scopes, ctx=ctx)
            case "always_create":
                prov = try_create_provider(req, *scopes, ctx=ctx)
            case _ if req.hard:
                return False
        if prov:
            graph.link('provides', prov, caller)
    return True

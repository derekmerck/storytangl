from ..scope import global_scope

def discover_scopes(node, graph, domain):
    # todo: appeal to bootstrap scope registry
    return [ node, graph, domain, global_scope ]

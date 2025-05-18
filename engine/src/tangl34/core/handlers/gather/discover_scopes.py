from ..scope import Scope

def discover_scopes(caller, *scopes: Scope):
    return Scope.discover_scopes(caller, *scopes)

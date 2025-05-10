from tangl33.core.context.context_handler import ContextHandler
from tangl33.core.enums import Tier, Phase

def make_role_injector(node_uid, requirement, provider_uid, slot_index=0):
    """
    Return a ContextHandler that injects a provider into ctx[role.name].
    """

    def layer(node, *_):
        return {requirement.params["role"]: provider_uid}

    # owner_uid = node that issued the requirement, tier = NODE
    return ContextHandler(layer,
                          tier=Tier.NODE,
                          owner_uid=node_uid)

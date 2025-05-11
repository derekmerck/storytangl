from tangl33.core.context.context_cap import ContextCap
from tangl33.core.enums import Tier, Phase

def make_role_injector(node_uid, requirement, provider_uid, slot_index=0):
    """
    Return a ContextCap that injects a provider into ctx[role.name].
    """

    def layer(node, *_):
        return {requirement.params["role"]: provider_uid}

    # owner_uid = node that issued the requirement, tier = NODE
    return ContextCap(layer,
                      tier=Tier.NODE,
                      owner_uid=node_uid)

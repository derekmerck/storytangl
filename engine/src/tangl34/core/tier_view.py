from typing import Dict, Any

class TierView:
    def __init__(self, *tiers: Dict[str, Any]):
        self.tiers = tiers

    def get(self, key: str) -> Any:
        for tier in self.tiers:
            if key in tier:
                return tier[key]
        return None

    def flatten(self) -> Dict[str, Any]:
        result = {}
        for tier in reversed(self.tiers):
            result.update(tier)
        return result

    # todo: I'm not sure how this works.  Context and Templates can be regular chainmaps
    #       ScopedCapabilities are a dict[Service, lists (per tier) of lists (of registered capabilities)]

    # todo: should we dispense with 'capability' and just call it a handler?

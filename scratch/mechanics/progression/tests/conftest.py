from tangl.utils.measure import Measure
from scratch.progression.quality import Quality
from scratch.progression.activity import ActivatorMixinABC

class TestActivator(ActivatorMixinABC):
    # implement abstract methods here
    def can_afford(self, cost: Quality) -> bool:
        return True

    def check_success(self, difficulty: Quality) -> Measure:
        return Measure.MEDIUM

    def gain_outcome(self, success: Quality, outcome: Quality):
        pass

    def pay_cost(self, cost: Quality):
        pass

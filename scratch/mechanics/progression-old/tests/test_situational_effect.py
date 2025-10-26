import pytest
from tangl.core.node import Node
from tangl.utils.measure import Measure
from scratch.progression.measured_domains import MeasuredDomain
from scratch.progression.quality import Quality
from scratch.progression.activity import ActivityMixin, ActivatorMixinABC, ActivityHandler
from scratch.progression.situational_effect import SituationalEffect, HasSituationalEffectsMixin, GlobalEffect

from conftest import TestActivator

@pytest.mark.skip(reason="not working")
def test_situational_effect():
    node = Node(tags={"#task1"})
    effect = SituationalEffect(applies_to_tags={"#task1"}, cost_modifier=Quality(Measure.CHEAPER, MeasuredDomain.ANY))
    assert effect.applicable_to(node)  # test if the effect is applicable to the node

@pytest.mark.skip(reason="not working")
def test_global_effect():
    node = Node(tags={"#task1"})
    effect = SituationalEffect(applies_to_tags={"#task1"}, cost_modifier=Quality(Measure.CHEAPER, MeasuredDomain.ANY))
    global_effect = GlobalEffect(situational_effect=effect)
    global_effect.activate()
    assert global_effect.applicable_to(node)  # test if the global effect is applicable to the node

from tangl.utils.measure import Measure
from tangl.core import Graph
from scratch.progression.measured_domains import MeasuredDomain
from scratch.progression.quality import Quality
from scratch.progression.activity import ActivityMixin, ActivatorMixinABC, ActivityHandler

import pytest

from conftest import TestActivator

def test_activity_handler():

    g = Graph()
    activator = TestActivator(graph=g)
    activity = ActivityMixin(cost=Quality(Measure.SMALL, MeasuredDomain.BODY),
                             difficulty=Quality(Measure.MEDIUM, MeasuredDomain.BODY),
                             outcome=Quality(Measure.LARGE, MeasuredDomain.BODY),
                             graph=g)
    handler = ActivityHandler(activator, activity)
    assert handler.can_afford()  # test if the activator can afford the cost
    handler.handle_activity()  # test if the activity is handled correctly

import attr
import yaml

from tangl.story.asset.badge import Badge, DynamicBadge, BadgedMixin
from tangl.core import Node

import pytest

def test_badge_from_kwargs():
    Badge._instances.clear()
    data_ = """
dyn_badges:
  - label: healthy
    conditions:
      - body > POOR

  - label: competent
    conditions:
      - mind > POOR

  - label: broken
    conditions: [ body is Q.NONE or mind == Q.NONE ]
    hides: [ healthy, competent ]
    permanent: True
    
  - label: ready
    conditions:
      - has_badges( healthy, competent )
"""

    data = yaml.safe_load(data_)
    for badge in data['dyn_badges']:
        DynamicBadge(**badge)

    print( Badge._instances )
    assert "ready" in Badge._instances


def test_badge_creation():
    Badge._instances.clear()
    badge = Badge(label="testBadge", text="This is a test badge")

    assert badge.label == "testBadge"
    assert badge.text == "This is a test badge"
    assert badge.hides == set()

def test_badge_with_hides():
    badge1 = Badge(label="badge1")
    badge2 = Badge(label="badge2", hides={badge1})

    assert badge1 in badge2.hides

def test_dynamic_badge_creation():
    Badge._instances.clear()
    dynamic_badge = DynamicBadge(label="dynamicBadge", text="This is a dynamic badge", permanent=True)

    assert dynamic_badge.label == "dynamicBadge"
    assert dynamic_badge.text == "This is a dynamic badge"
    assert dynamic_badge.permanent is True

def test_dynamic_badge_with_hides():
    Badge._instances.clear()
    badge1 = Badge(label="badge1")
    dynamic_badge = DynamicBadge(label="dynamicBadge", hides={badge1})

    assert badge1 in dynamic_badge.hides

def test_badge_applicability():
    Badge._instances.clear()
    badge = Badge(label="badge1")
    node = Node(label="node1")

    badge.conditions = ["True"]
    assert badge.is_satisfied_by(node) is True

    badge.conditions = ["False"]
    assert badge.is_satisfied_by(node) is False

@pytest.fixture
def dyn_badges():
    DynamicBadge._instances.clear()
    DynamicBadge._evaluation_order = None
    healthy_badge = DynamicBadge(
        label="healthy",
        conditions=["body > Q.POOR"]
    )
    competent_badge = DynamicBadge(
        label="competent",
        conditions=["mind > Q.POOR"]
    )
    broken_badge = DynamicBadge(
        label="broken",
        conditions=["body == Q.NONE or mind == Q.NONE"],
        hides=['healthy', 'competent'],
        permanent=True
    )
    ready_badge = DynamicBadge(
        label="ready",
        conditions=["has_badges('competent', 'healthy')"]
    )
    return healthy_badge, competent_badge, broken_badge, ready_badge

from enum import IntEnum

class Quality(IntEnum):
    NONE = 1
    POOR = 2
    OK = 3
    GOOD = 4
    MAX = 5

@attr.s
class BadgedNode(BadgedMixin, Node):
    mind: Quality = attr.ib( default=Quality.OK )
    body: Quality = attr.ib( default=Quality.OK )

    def ns(self):
        _ns = super().ns()
        _ns['mind'] = self.mind
        _ns['body'] = self.body
        _ns['Q'] = Quality
        return _ns

def test_badge_loading(dyn_badges):

    healthy_badge, competent_badge, broken_badge, ready_badge = dyn_badges
    node = BadgedNode()

    assert broken_badge.is_satisfied_by(node) is False
    assert healthy_badge.is_satisfied_by(node) is True
    assert competent_badge.is_satisfied_by(node) is True
    # for testing, let's add these dynamic badges permanently
    node.add_badge( healthy_badge )
    node.add_badge( competent_badge )
    assert ready_badge.is_satisfied_by(node) is True

    node.body = Quality.NONE
    assert healthy_badge.is_satisfied_by(node) is False
    assert broken_badge.is_satisfied_by(node) is True
    node.add_badge(broken_badge)
    # still competent though
    assert competent_badge.is_satisfied_by(node) is True
    # but it's hidden by broken
    assert node.has_badges(healthy_badge) is False
    # but not ready
    assert ready_badge.is_satisfied_by(node) is False

def test_badge_sort_order(dyn_badges):

    healthy_badge, competent_badge, broken_badge, ready_badge = dyn_badges

    badge_dependency_dict = DynamicBadge._dependency_dict()
    test_bdd = { k: set(v) for k, v in badge_dependency_dict.items()}
    assert test_bdd == {'healthy': set(), 'competent': set(), 'broken': {'competent', 'healthy'}, 'ready': {'competent', 'healthy'}}
    badge_evaluation_order = DynamicBadge.evaluation_order()

    # Verify each badge appears _after_ all of its dependencies
    for badge, dependencies in badge_dependency_dict.items():
        badge_index = badge_evaluation_order.index(Badge[badge])
        for dependency in dependencies:
            assert badge_evaluation_order.index(Badge[dependency]) < badge_index

def test_dynamic_badge_assignment(dyn_badges):

    healthy_badge, competent_badge, broken_badge, ready_badge = dyn_badges

    node = BadgedNode(locals={'Q': Quality})
    node.compute_dynamic_badges()
    assert ready_badge in node.badges

    # Damaged
    node.mind = Quality.NONE
    node.compute_dynamic_badges()
    assert broken_badge in node.badges
    assert ready_badge not in node.badges

    # It's permanent
    node.mind = Quality.GOOD
    node.compute_dynamic_badges()
    assert broken_badge in node.badges
    assert ready_badge not in node.badges

    # Fixed
    node.discard_badge(broken_badge)
    assert ready_badge in node.badges


import pydantic
import yaml
import pytest

pytest.skip(allow_module_level=True, reason="not refactored")

from tangl.mechanics.badge import Badge, HasBadges as Badged
# DynamicBadge, Badged
from tangl.core.entity import Node, Graph, Entity
from tangl.core.services import HasContext, on_gather_context



@pytest.fixture
def badge_data():
    return """
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

@pytest.fixture(autouse=True)
def clear_badges():
    Badge.clear_instances()

from enum import IntEnum

class Quality(IntEnum):
    NONE = 1
    POOR = 2
    OK = 3
    GOOD = 4
    MAX = 5

class BadgedNode(Badged, HasContext, Node):
    mind: Quality = Quality.OK
    body: Quality = Quality.OK

    @on_gather_context.register()
    def _include_attribs(self, **kwargs):
        return {
            'mind': self.mind,
            'body': self.body,
            'Q': Quality
        }

@pytest.fixture
def badges():
    # Badge.clear()
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


def test_badge_from_kwargs(badge_data):

    # Badge.clear_instances()
    data = yaml.safe_load(badge_data)
    for badge in data['dyn_badges']:
        DynamicBadge(**badge)

    # print( Badge._instances )
    assert "healthy" in Badge._instances
    assert "ready" in Badge._instances


def test_badge_creation():
    # Badge.clear_instances()
    badge = Badge(label="testBadge", content="This is a test badge")

    assert badge.content == "testBadge"
    assert badge.text == "This is a test badge"
    assert badge.hides == set()

def test_badge_with_hides():
    # Badge.clear_instances()
    badge1 = Badge(label="badge1")
    badge2 = Badge(label="badge2", hides={badge1})

    assert badge1 in badge2.hides

def test_dynamic_badge_creation():
    # Badge.clear_instances()
    dynamic_badge = DynamicBadge(label="dynamicBadge", text="This is a dynamic badge", permanent=True)

    assert dynamic_badge.label == "dynamicBadge"
    assert dynamic_badge.text == "This is a dynamic badge"
    assert dynamic_badge.permanent is True

def test_dynamic_badge_with_hides():
    # Badge.clear_instances()
    badge1 = Badge(label="badge1")
    dynamic_badge = DynamicBadge(label="dynamicBadge", hides={badge1})

    assert badge1 in dynamic_badge.hides

def test_badge_applicability():
    # Badge.clear_instances()
    badge = Badge(label="badge1")
    node = BadgedNode(label="node1")

    badge.conditions = ["True"]
    assert badge.check_satisfied_by(node) is True

    badge.conditions = ["False"]
    assert badge.check_satisfied_by(node) is False

def test_badges(badges):

    healthy_badge, competent_badge, broken_badge, ready_badge = badges
    # for testing, let's add these dynamic badges permanently
    healthy_badge.permanent = True
    competent_badge.permanent = True
    broken_badge.permanent = True
    ready_badge.permanent = True

    node = BadgedNode()
    assert node.graph
    assert not node.parent

    assert broken_badge.check_satisfied_by(node) is False
    assert healthy_badge.check_satisfied_by(node) is True
    assert competent_badge.check_satisfied_by(node) is True
    node.add_badge( healthy_badge )
    assert not node.parent

    assert healthy_badge in node.badges
    assert node.has_badges('healthy')
    node.add_badge( competent_badge )
    assert competent_badge in node.badges
    assert node.has_badges('competent')

    # Now we should meet conditions for the ready_badge
    assert ready_badge.check_satisfied_by(node) is True

    node.body = Quality.NONE
    assert healthy_badge.check_satisfied_by(node) is False
    assert broken_badge.check_satisfied_by(node) is True
    node.add_badge(broken_badge)
    # still competent though
    assert competent_badge.check_satisfied_by(node) is True
    # but it's hidden by broken
    assert node.has_badges(healthy_badge) is False
    assert healthy_badge not in node.badges
    # but not ready
    assert ready_badge.check_satisfied_by(node) is False

def test_badge_sort_order(badges):

    healthy_badge, competent_badge, broken_badge, ready_badge = badges

    badge_dependency_dict = DynamicBadge._dependency_dict()
    test_bdd = { k: set(v) for k, v in badge_dependency_dict.items()}
    assert test_bdd == {'healthy': set(), 'competent': set(), 'broken': {'competent', 'healthy'}, 'ready': {'competent', 'healthy'}}
    badge_evaluation_order = DynamicBadge.evaluation_order()

    # Verify each badge appears _after_ all of its dependencies
    for badge, dependencies in badge_dependency_dict.items():
        badge_index = badge_evaluation_order.index(Badge.get_instance(badge))
        for dependency in dependencies:
            assert badge_evaluation_order.index(Badge.get_instance(dependency)) < badge_index

def test_dynamic_badge_assignment(badges):

    healthy_badge, competent_badge, broken_badge, ready_badge = badges

    node = BadgedNode()
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

# @pytest.mark.xfail(reason="need to fix badges/frozen singleton association")
def test_serialization(badges):

    healthy_badge, competent_badge, broken_badge, ready_badge = badges

    node0 = BadgedNode(label="node0")
    assert not node0.parent
    node0.compute_dynamic_badges()
    assert not node0.parent
    assert ready_badge in node0.badges

    S = Entity
    u = S.unstructure(node0.graph)
    from pprint import pprint
    pprint( u )
    graph1 = S.structure(u)
    node1 = graph1.get_node('node0')
    assert node0 == node1


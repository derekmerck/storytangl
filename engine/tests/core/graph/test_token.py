import pytest

from pydantic import Field

from tangl.core import Entity, Node, Graph, Singleton
from tangl.core.graph import Token


class TestSingleton(Singleton):
    a: int = 100
    b: int = Field(200, json_schema_extra={'instance_var': True})

@pytest.fixture(autouse=True)
def reset_test_singleton():
    TestSingleton.clear_instances()
    TestSingleton(label="unique_singleton")
    yield
    TestSingleton.clear_instances()

@pytest.fixture
def ws():
    return Token[TestSingleton](label="unique_singleton", graph=Graph())

def test_token_creation(ws):

    assert isinstance(ws, Token)
    assert ws.label == "unique_singleton"
    assert ws.reference_singleton.label == "unique_singleton"

def test_token_invalid_ref():
    with pytest.raises(ValueError):
        Token[TestSingleton](label="invalid_singleton")

def test_token_missing(ws):
    TestSingleton._instances.clear()  # Simulate instance deletion

    with pytest.raises(ValueError, match="No instance of `TestSingleton` found"):
        _ = ws.reference_singleton  # Should raise ValueError

def test_token_getattr(ws):

    assert ws.a == 100
    assert ws.b == 200

    with pytest.raises(ValueError):
        # can't set an instance variable
        ws.a = 150

    # can set an instance variable
    ws.b = 250

def test_token_graph_integration(ws):

    g = Graph()
    g.add(ws)
    assert g.get(ws.uid) is ws
    assert g.find_one(label="unique_singleton") is ws

    # n = Node(label="node")
    # ws.add_child(n)
    # assert n.path == "unique_singleton/node"


def test_token_is_instance_checks_wrapped_type():
    """Token[NPC] matches is_instance=NPC."""

    class NPC(Singleton):
        hp: int = 100

    NPC(label="guard")
    token = Token[NPC](label="guard")

    # Should match wrapped type
    assert token.is_instance(NPC)
    assert token.is_instance(Singleton)
    assert token.is_instance(Node)
    assert token.is_instance(Entity)

    class NPC2(Singleton): ...

    assert not token.is_instance(NPC2)

    # Not a class, should raise instead of fail?
    assert not token.is_instance("dog")

    assert token.is_instance((NPC,NPC2))
    assert not token.is_instance((NPC2,))


def test_graph_find_includes_tokens():
    """Graph search finds tokens by wrapped type."""
    graph = Graph()

    class NPC(Singleton):
        pass

    NPC(label="guard")
    NPC(label="merchant")

    guard_token = Token[NPC](label="guard")
    merchant_token = Token[NPC](label="merchant")

    graph.add(guard_token)
    graph.add(merchant_token)

    # Should find both tokens
    npcs = list(graph.find_nodes(is_instance=NPC))
    assert len(npcs) == 2
    assert guard_token in npcs
    assert merchant_token in npcs


def test_token_delegation_works():
    """Token delegates non-instance-vars to base."""

    class Weapon(Singleton):
        damage: int
        durability: int = Field(100, json_schema_extra={'instance_var': True})

    Weapon(label="sword", damage=10)

    token = Token[Weapon](label="sword", durability=85)

    # Instance var (on token)
    assert token.durability == 85

    # Delegates to base
    assert token.damage == 10

    # Update base affects token
    base = Weapon.get_instance("sword")
    # Can't actually update frozen base, but concept works
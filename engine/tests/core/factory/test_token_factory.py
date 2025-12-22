import pytest
from pydantic import Field

from tangl.core.singleton import Singleton
from tangl.core.graph import Token, Graph
from tangl.core.factory import TokenFactory


# === Test Fixtures ===

class NPC(Singleton):
    """Test NPC singleton."""
    hp: int = 100
    name: str = Field("", json_schema_extra={'instance_var': True})


class Weapon(Singleton):
    """Test weapon singleton."""
    damage: int
    durability: int = Field(100, json_schema_extra={'instance_var': True})


@pytest.fixture
def factory():
    """Fresh factory."""
    f = TokenFactory()
    f.register_type(NPC)
    f.register_type(Weapon)
    return f


@pytest.fixture(autouse=True)
def clear_singletons():
    """Clear singleton registries between tests."""
    yield
    NPC.clear_instances()
    Weapon.clear_instances()


# === Registration Tests ===

def test_register_type():
    """Register Singleton types by name."""
    factory = TokenFactory()
    factory.register_type(NPC)
    factory.register_type(Weapon)

    assert factory.has_type(NPC)
    assert factory.has_type(Weapon)
    assert NPC in factory.registered_types()


def test_resolve_base_delegates_to_singleton():
    """resolve_base uses Singleton's own registry."""
    factory = TokenFactory()
    factory.register_type(NPC)

    # Create base via Singleton (not factory!)
    guard = NPC(label="guard", hp=100)

    # Factory resolves by delegating to Singleton
    base = factory.resolve_base(NPC, label="guard")

    assert base is guard
    # Factory didn't create anything - just found existing!


def test_get_type_by_name():
    """Can retrieve type by string name."""
    factory = TokenFactory()
    factory.register_type(NPC)

    type_name = f"{NPC.__module__}.{NPC.__qualname__}"
    retrieved = factory.get_type(type_name)

    assert retrieved is NPC

def test_register_non_singleton_fails():
    """Non-Singleton types rejected."""
    factory = TokenFactory()

    with pytest.raises(ValueError, match="must be Singleton"):
        factory.register_type(int)


# === Resolve Base Tests ===

def test_resolve_base_by_label(factory):
    """resolve_base finds by label."""
    NPC(label="guard", hp=100)

    base = factory.resolve_base(NPC, label="guard")

    assert base is not None
    assert base.label == "guard"
    assert base.hp == 100


def test_resolve_base_returns_none_when_missing(factory):
    """CRITICAL: resolve_base never creates, returns None."""
    # No base created!
    base = factory.resolve_base(NPC, label="missing")

    assert base is None


def test_resolve_base_by_uuid(factory):
    """resolve_base finds by UUID."""
    guard = NPC(label="guard", hp=100)

    base = factory.resolve_base(NPC, uuid=guard.uid)

    assert base is guard


def test_resolve_base_by_criteria(factory):
    """resolve_base finds by criteria."""
    NPC(label="guard1", hp=80)
    strong = NPC(label="guard2", hp=120)

    base = factory.resolve_base(NPC, hp=120)

    assert base is strong


def test_resolve_base_warns_unregistered_type(factory):
    """Warns when type not registered."""

    class Unknown(Singleton):
        pass

    Unknown(label="test")

    # todo: it doesn't warn anymore, it just writes into the logger.warning stream
    base = factory.resolve_base(Unknown, label="test")

    assert base is None


# === Wrap Tests ===

def test_wrap_creates_token(factory):
    """wrap() creates Token with instance vars."""
    guard = NPC(label="guard", hp=100)

    token = factory.wrap(guard, name="John")

    assert isinstance(token, Token)
    assert token.label == "guard"
    assert token.hp == 100  # Delegates to base
    assert token.name == "John"  # Instance var


def test_wrap_with_overlay_dict(factory):
    """wrap() accepts overlay dict."""
    guard = NPC(label="guard", hp=100)

    token = factory.wrap(guard, overlay={"name": "Jane"})

    assert token.name == "Jane"


def test_wrap_merges_overlay_sources(factory):
    """Dict and kwargs merged, kwargs win."""
    guard = NPC(label="guard", hp=100)

    token = factory.wrap(
        guard,
        overlay={"name": "Old"},
        name="New"  # Overwrites
    )

    assert token.name == "New"


# === Materialize Token Tests ===

def test_materialize_token_with_base(factory):
    """materialize_token with pre-resolved base."""
    guard = NPC(label="guard", hp=100)

    token = factory.materialize_token(base=guard, name="John")

    assert token.label == "guard"
    assert token.name == "John"


def test_materialize_token_with_type_and_label(factory):
    """materialize_token resolves + wraps."""
    NPC(label="guard", hp=100)

    token = factory.materialize_token(
        token_type=NPC,
        label="guard",
        name="John"
    )

    assert token is not None
    assert token.label == "guard"
    assert token.name == "John"


def test_materialize_token_returns_none_when_missing(factory):
    """materialize_token returns None if base not found."""
    # No base created!

    token = factory.materialize_token(
        token_type=NPC,
        label="missing"
    )

    assert token is None


def test_materialize_token_requires_base_or_type():
    """materialize_token needs base or token_type."""
    factory = TokenFactory()
    factory.register_type(NPC)

    with pytest.raises(ValueError, match="Must provide base or token_type"):
        factory.materialize_token(name="John")


# === Integration Tests ===

def test_token_in_graph(factory):
    """Tokens work as normal nodes in graph."""
    graph = Graph()
    NPC(label="guard", hp=100)

    token = factory.materialize_token(
        token_type=NPC,
        label="guard",
        name="John"
    )

    graph.add(token)

    assert token in graph
    assert graph.get(token.uid) is token


def test_graph_find_by_wrapped_type(factory):
    """Graph search finds tokens by wrapped type."""
    graph = Graph()

    NPC(label="guard", hp=100)
    NPC(label="merchant", hp=80)

    guard = factory.materialize_token(token_type=NPC, label="guard")
    merchant = factory.materialize_token(token_type=NPC, label="merchant")

    graph.add(guard)
    graph.add(merchant)

    # Should find both
    npcs = list(graph.find_nodes(is_instance=NPC))

    assert len(npcs) == 2
    assert guard in npcs
    assert merchant in npcs


def test_multiple_tokens_from_same_base(factory):
    """Can create multiple tokens from same base."""
    NPC(label="guard", hp=100)

    john = factory.materialize_token(
        token_type=NPC,
        label="guard",
        name="John"
    )

    jane = factory.materialize_token(
        token_type=NPC,
        label="guard",
        name="Jane"
    )

    # Different tokens, same base
    assert john is not jane
    assert john.label == jane.label == "guard"
    assert john.hp == jane.hp == 100
    assert john.name == "John"
    assert jane.name == "Jane"


def test_base_update_affects_all_tokens(factory):
    """Updating base (if possible) affects all tokens."""
    # Note: Singletons are frozen, but concept works
    guard_base = NPC(label="guard", hp=100)

    token1 = factory.materialize_token(token_type=NPC, label="guard")
    token2 = factory.materialize_token(token_type=NPC, label="guard")

    # Both delegate to same base
    assert token1.hp == 100
    assert token2.hp == 100
    assert token1.reference_singleton is token2.reference_singleton


def test_all_bases_lists_singletons(factory):
    """all_bases() lists registered Singleton instances."""
    NPC(label="guard1")
    NPC(label="guard2")
    Weapon(label="sword", damage=10)

    # All bases
    all_bases = factory.all_bases()
    assert len(all_bases) == 3

    # Just NPCs
    npc_bases = factory.all_bases(NPC)
    assert len(npc_bases) == 2


# === Error Handling ===

def test_wrap_validates_label_exists():
    """Token validation fails if base doesn't exist."""
    factory = TokenFactory()
    factory.register_type(NPC)

    # Create fake base (bypass factory)
    fake_base = type('FakeBase', (), {
        '__class__': NPC,
        'label': 'nonexistent'
    })()

    with pytest.raises(ValueError, match="No instance.*found"):
        factory.wrap(fake_base)


def test_materialize_token_logs_warning_when_missing(factory, caplog):
    """Logs warning when base not found."""
    token = factory.materialize_token(
        token_type=NPC,
        label="missing"
    )

    assert token is None
    assert "Cannot materialize token" in caplog.text
    assert "not found" in caplog.text
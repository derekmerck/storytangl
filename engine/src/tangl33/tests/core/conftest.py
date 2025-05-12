import pytest

from tangl33.core import Graph, Node, Domain

# -----------------------------------------------------------------------------
# Fixture helpers
# -----------------------------------------------------------------------------
@pytest.fixture
def graph():
    g = Graph()
    root = Node(label="root")
    child = Node(label="child", parent_uid=root.uid)
    g.add(root); g.add(child)
    return g

# @pytest.fixture
# def cap_cache():
#     return HandlerCache()
#
# @pytest.fixture
# def prov_reg():
#     return ProviderRegistry()

@pytest.fixture
def domain():
    return Domain()

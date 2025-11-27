import logging
import sys
import types

try:  # pragma: no cover - optional dependency shim for tests
    import wrapt  # type: ignore  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - executed in CI environment
    class _ObjectProxy:
        """Minimal stand-in for :class:`wrapt.ObjectProxy` used in tests."""

        def __init__(self, wrapped):
            object.__setattr__(self, "__wrapped__", wrapped)

        def __getattr__(self, name):
            return getattr(object.__getattribute__(self, "__wrapped__"), name)

        def __setattr__(self, name, value):
            if name == "__wrapped__" or name.startswith("_self_"):
                object.__setattr__(self, name, value)
            else:
                setattr(object.__getattribute__(self, "__wrapped__"), name, value)

        def __delattr__(self, name):
            if name == "__wrapped__" or name.startswith("_self_"):
                object.__delattr__(self, name)
            else:
                delattr(object.__getattribute__(self, "__wrapped__"), name)

    stub = types.SimpleNamespace(ObjectProxy=_ObjectProxy)
    sys.modules["wrapt"] = stub

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("markdown_it").setLevel(logging.WARNING)
logging.getLogger("matplotlib").setLevel(logging.WARNING)

# from pathlib import Path
# import pytest
# import yaml
#
# test_resources = Path(__file__).parent / 'resources'
#
# @pytest.fixture(scope='session')
# def my_script_data():
#     fp = test_resources / 'my_script.yaml'
#     with open(fp) as f:
#         data = yaml.safe_load(f)
#     return data

from tangl.type_hints import StringMap
from tangl.core.graph import Graph, Node, Subgraph

from pydantic import create_model, Field

import pytest

_dict_field = StringMap, Field(default_factory=dict)

GraphL_ = create_model("GraphL", __base__=Graph, locals=_dict_field)

@pytest.fixture(scope="session")
def GraphL():
    return GraphL_

SubgraphL_ = create_model("SubgraphL", __base__=Subgraph, locals=_dict_field)
@pytest.fixture(scope="session")
def SubgraphL():
    return SubgraphL_

NodeL_ = create_model("NodeL", __base__=Node, locals=_dict_field)
@pytest.fixture(scope="session")
def NodeL():
    return NodeL_

from pathlib import Path

@pytest.fixture(scope="session")
def resources_dir():
    return Path(__file__).resolve().parent / "resources"


@pytest.fixture
def media_mvp_path() -> Path:
    """Path to media_mvp test world directory."""

    return Path(__file__).parent / "resources" / "worlds" / "media_mvp"


@pytest.fixture
def media_mvp_root() -> Path:
    """Root directory containing media_mvp (for discovery tests)."""

    return Path(__file__).parent / "resources" / "worlds"


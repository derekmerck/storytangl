import pytest

from pathlib import Path

import pytest
from pydantic import Field, create_model

from tangl.core import Graph
from tangl.story.episode import Scene
from tangl.type_hints import StringMap


@pytest.fixture
def trivial_ctx():
    class Ctx:
        def get_active_layers(self):
            from tangl.vm.dispatch import vm_dispatch
            from tangl.story.dispatch import story_dispatch
            return vm_dispatch, story_dispatch
    return Ctx()
_dict_field = StringMap, Field(default_factory=dict)

SceneL_ = create_model("SceneL", __base__=Scene, locals=_dict_field)

@pytest.fixture(scope="session")
def SceneL():
    return SceneL_


@pytest.fixture
def media_mvp_path() -> Path:
    return Path(__file__).resolve().parents[1] / "resources" / "worlds" / "media_mvp"

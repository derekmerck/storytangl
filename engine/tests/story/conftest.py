import pytest

@pytest.fixture
def trivial_ctx():
    class Ctx:
        def get_active_layers(self):
            from tangl.vm.dispatch import vm_dispatch
            from tangl.story.dispatch import story_dispatch
            return vm_dispatch, story_dispatch
    return Ctx()

from tangl.core import Graph
from tangl.story.episode import Scene
from tangl.type_hints import StringMap
import pytest
from pydantic import Field, create_model
_dict_field = StringMap, Field(default_factory=dict)

@pytest.fixture(scope="session")
def SceneL():

    SceneL = create_model("SceneL", __base__=Scene, locals=_dict_field)
    return SceneL

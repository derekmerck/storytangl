from fastapi.testclient import TestClient
import pytest

from tangl.rest.app import app

# from tests.conftest import my_script_data
# from tests.story.conftest import world

@pytest.fixture(scope="session")
def world():
    from tangl.ir.core_ir import ScriptMetadata
    from tangl.ir.story_ir import StoryScript
    from tangl.story.fabula.world import World, ScriptManager
    master_script = StoryScript(
        label="test_world",
        metadata=ScriptMetadata(title="Hello World!", author="TanglDev"),
        scenes=[]
    )
    script_manager = ScriptManager(master_script=master_script)
    return World(label="test_world", script_manager=script_manager)

@pytest.fixture
def client():
    return TestClient(app, base_url="http://test/api/v2/")


def extract_choices_from_fragments(fragments: list[dict]) -> list[dict]:
    """Extract all choice fragments from a fragment stream."""

    choices: list[dict] = []

    def _normalize(choice: dict) -> dict:
        normalized = dict(choice)
        if "source_id" in normalized:
            normalized["uid"] = normalized["source_id"]
        elif "uid" in normalized:
            normalized["uid"] = normalized["uid"]
        if "source_label" in normalized and not normalized.get("label"):
            normalized["label"] = normalized["source_label"]
        return normalized

    for fragment in fragments:
        if fragment.get("fragment_type") == "block":
            embedded = fragment.get("choices", [])
            choices.extend(_normalize(choice) for choice in embedded)
        elif fragment.get("fragment_type") == "choice":
            choices.append(_normalize(fragment))

    return choices


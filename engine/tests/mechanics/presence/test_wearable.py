import pytest

from tangl.mechanics.presence.wearable import Wearable, WearableType

# pytest.skip(allow_module_level=True)

@pytest.fixture(autouse=True)
def setup_wearable():
    WearableType.clear_instances()
    WearableType.load_defaults()
    yield
    WearableType.clear_instances()

def test_wearable():
    instance_labels = Wearable.wrapped_cls.all_instance_labels()
    print(instance_labels)
    assert len(instance_labels) > 2, "Not enough instances loaded in default wearables"

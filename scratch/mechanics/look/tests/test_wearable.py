import pytest

from scratch.mechanics.look.wearable import Wearable, WearableType

pytest.skip(allow_module_level=True)

@pytest.fixture(autouse=True)
def setup_wearable():
    WearableType.load_defaults()

def test_wearable():
    instance_labels = list(Wearable.wrapped_cls._instances.keys())
    print(instance_labels)
    assert len(instance_labels) > 2, "Not enough instances loaded in default wearables"

import pytest

from tangl.resource_registry import ResourceInventoryTag as RIT, ResourceDataType
from tangl.resource_registry.resource_location import ResourceLocation

def test_add_and_find_resource():
    location = ResourceLocation()
    tag = RIT(name="test_resource", resource_type=ResourceDataType.IMAGE)
    location.add_resource(tag)

    # Test find_resource
    found = location.find_resource("test_resource")
    assert found == tag

    # Test find_resources
    found_list = location.find_resources("test_resource")
    assert tag in found_list

def test_filter_by_resource_type():
    location = ResourceLocation()
    image_tag = RIT(name="image_resource", resource_type=ResourceDataType.IMAGE)
    audio_tag = RIT(name="audio_resource", resource_type=ResourceDataType.AUDIO)
    location.add_resource(image_tag)
    location.add_resource(audio_tag)

    # Find only image resources
    found_images = location.find_resources(resource_type=ResourceDataType.IMAGE)
    assert image_tag in found_images
    assert audio_tag not in found_images

@pytest.mark.skip("todo: Need to write test")
def test_filter_by_tags():
    pass

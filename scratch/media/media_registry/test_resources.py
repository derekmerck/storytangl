import types

from tangl.core import ResourceRegistry, ResourceDataType

def test_resource_handler():

    DOMAIN_NAME = "blah"
    FILE_LOC = "resources/my_file.txt"
    SAMPLE_FILE = types.SimpleNamespace(name="my_file.txt",
                                        content_hash="8f9fbff8fbaf3e50f1c0030d2")

    ResourceHandler.add_resource_domain(DOMAIN_NAME)

    ResourceHandler.add_file_location(
        DOMAIN_NAME,
        FILE_LOC)

    resource1 = ResourceHandler.find_resource(
        DOMAIN_NAME,
        SAMPLE_FILE.name,
        resource_type=ResourceDataType.IMAGE)

    resource2 = ResourceHandler.find_resource(
        DOMAIN_NAME,
        SAMPLE_FILE.data_hash,
        resource_type=ResourceDataType.IMAGE
    )

    assert resource1 is resource2

    # resource2.image.show()

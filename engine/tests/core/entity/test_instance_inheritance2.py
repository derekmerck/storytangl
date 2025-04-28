import pytest

from tangl.core import InheritingSingleton

class TestInheritingSingleton(InheritingSingleton):
    extra_field: str = None

class TestMultivalueInheritingSingleton(InheritingSingleton):
    attribute1: str
    attribute2: str

# Cleanup after tests
@pytest.fixture(autouse=True, scope="function")
def cleanup():
    InheritingSingleton.clear_instances(clear_subclasses=True)
    yield
    InheritingSingleton.clear_instances(clear_subclasses=True)

@pytest.fixture
def setup_singletons():
    # Create a base instance to be referenced later
    TestInheritingSingleton(label="base_entity", extra_field="base_value")
    yield
    TestInheritingSingleton.clear_instances()

@pytest.fixture
def setup_mv_singletons():
    TestMultivalueInheritingSingleton(label="base_entity", attribute1="value1", attribute2="value2")

def test_inheriting_singleton_hashes(setup_singletons):
    base = TestInheritingSingleton(label="base_entity")
    { base }

def test_inheritance_from_existing_instance(setup_singletons):
    # Create a new singleton instance, referencing the base instance for defaults
    new_instance = TestInheritingSingleton(label="new_label", from_ref="base_entity")
    assert new_instance.extra_field == "base_value", "Should inherit 'extra_field' from the base entity"
    assert new_instance.label == "new_label", "Label should be unique and not inherited"

    # hashes
    { new_instance }

def test_error_on_nonexistent_ref():
    with pytest.raises(KeyError) as exc_info:
        # Attempt to create an instance with a reference to a non-existent instance
        TestInheritingSingleton(label="faulty_instance", from_ref="nonexistent")
    assert "nonexistent" in str(exc_info.value), "Should raise KeyError for non-existent reference"

# Additional test to ensure data overriding works correctly
def test_data_overriding(setup_singletons):
    overriding_instance = TestInheritingSingleton(label="overriding_instance",
                                                  from_ref="base_entity",
                                                  extra_field="overridden_value")
    assert overriding_instance.extra_field == "overridden_value", "Should override 'extra_field' value, not inherit"

def test_label_not_inherited(setup_singletons):
    Singleton = setup_singletons
    derived_entity = TestInheritingSingleton(label="unique_label", from_ref="base_entity")
    assert derived_entity.label == "unique_label"

def test_inheritance_from_reference_entity(setup_mv_singletons):
    # Singleton = setup_mv_singletons
    derived_entity = TestMultivalueInheritingSingleton(label="derived_entity", from_ref="base_entity")
    assert derived_entity.attribute1 == "value1"
    assert derived_entity.attribute2 == "value2"

def test_override_inherited_attributes(setup_mv_singletons):
    Singleton = setup_mv_singletons
    derived_entity = TestMultivalueInheritingSingleton(label="derived_entity", from_ref="base_entity", attribute1="overridden_value")
    assert isinstance( derived_entity, TestMultivalueInheritingSingleton )
    print( derived_entity.model_dump() )
    assert derived_entity.attribute1 == "overridden_value"
    assert derived_entity.attribute2 == "value2"


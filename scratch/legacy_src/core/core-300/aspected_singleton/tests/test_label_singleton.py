import pytest
from pydantic import ValidationError
from uuid import UUID

from pydantic import BaseModel, Field

from tangl.core.singleton import LabelSingleton

class SimpleLabelSingleton(LabelSingleton):
    """Test fixture class"""
    value: int = Field(default=0)


def test_basic_label_singleton():
    """Test basic label singleton functionality"""
    s1 = SimpleLabelSingleton(label="test")
    s2 = SimpleLabelSingleton(label="test")
    assert s1 is s2
    assert s1.label == "test"
    assert len(SimpleLabelSingleton._instances) == 1
    assert len(SimpleLabelSingleton._instances_by_label) == 1


def test_different_labels():
    """Test instances with different labels"""
    s1 = SimpleLabelSingleton(label="test1")
    s2 = SimpleLabelSingleton(label="test2")
    assert s1 is not s2
    assert s1.label != s2.label
    assert len(SimpleLabelSingleton._instances) == 2
    assert len(SimpleLabelSingleton._instances_by_label) == 2


def test_label_validation():
    """Test label validation"""
    with pytest.raises(ValidationError):
        SimpleLabelSingleton(label="")  # Empty label

    with pytest.raises(ValidationError):
        SimpleLabelSingleton()  # Missing label


def test_get_instance_by_label():
    """Test getting instance by label"""
    s1 = SimpleLabelSingleton(label="test")
    s2 = SimpleLabelSingleton.get_instance("test")
    assert s1 is s2


def test_get_instance_by_uuid():
    """Test getting instance by UUID"""
    s1 = SimpleLabelSingleton(label="test")
    s2 = SimpleLabelSingleton.get_instance(s1.uid)
    assert s1 is s2


def test_has_instance():
    """Test instance existence checking"""
    s = SimpleLabelSingleton(label="test")
    assert SimpleLabelSingleton.has_instance("test")
    assert SimpleLabelSingleton.has_instance(s.uid)
    assert not SimpleLabelSingleton.has_instance("nonexistent")
    assert not SimpleLabelSingleton.has_instance(UUID(int=0))


def test_label_inheritance():
    """Test label singleton inheritance"""

    class ChildLabelSingleton(SimpleLabelSingleton):
        pass

    parent = SimpleLabelSingleton(label="test")
    child = ChildLabelSingleton(label="test")

    assert parent is not child  # Different registries
    assert parent.label == child.label

    # Each class should have one instance
    assert len(SimpleLabelSingleton._instances) == 1
    assert len(SimpleLabelSingleton._instances_by_label) == 1
    assert len(ChildLabelSingleton._instances) == 1
    assert len(ChildLabelSingleton._instances_by_label) == 1


def test_pydantic_integration():
    """Test Pydantic integration"""
    s1 = SimpleLabelSingleton(label="test", value=42)
    s2 = SimpleLabelSingleton(label="test", value=0)  # Different value
    assert s1 is s2
    assert s1.value == 42  # Keeps original value

    # Test validation
    with pytest.raises(ValidationError):
        SimpleLabelSingleton(label=123)  # Wrong type for label


def test_clear_instances():
    """Test instance clearing"""

    class ChildLabelSingleton(SimpleLabelSingleton):
        pass

    SimpleLabelSingleton(label="test1")
    SimpleLabelSingleton(label="test2")
    ChildLabelSingleton(label="test3")

    SimpleLabelSingleton.clear_instances(clear_subclasses=True)

    assert len(SimpleLabelSingleton._instances) == 0
    assert len(SimpleLabelSingleton._instances_by_label) == 0
    assert len(ChildLabelSingleton._instances) == 0
    assert len(ChildLabelSingleton._instances_by_label) == 0


def test_filter_by_label():
    """Test filtering by label"""
    s1 = SimpleLabelSingleton(label="test1")
    s2 = SimpleLabelSingleton(label="test2")

    found = SimpleLabelSingleton.find_instances(label="test1")
    assert len(found) == 1
    assert found[0] is s1

    found = SimpleLabelSingleton.find_instance(label="test2")
    assert found is s2


def test_inheritance_search():
    """Test searching through inheritance hierarchy"""

    class ChildLabelSingleton(SimpleLabelSingleton):
        pass

    child = ChildLabelSingleton(label="test")
    found = SimpleLabelSingleton.get_instance("test", search_subclasses=True)
    assert found is child


def test_duplicate_label_error():
    """Test error on duplicate label registration"""
    s = SimpleLabelSingleton(label="test")

    # Try to register same label
    with pytest.raises(KeyError):
        SimpleLabelSingleton.register_instance(s)


@pytest.fixture(autouse=True)
def cleanup():
    SimpleLabelSingleton.clear_instances(clear_subclasses=True)
    yield
    SimpleLabelSingleton.clear_instances(clear_subclasses=True)
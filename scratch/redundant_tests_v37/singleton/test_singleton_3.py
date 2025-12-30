import pytest
from pydantic import ValidationError
from uuid import UUID

from pydantic import BaseModel, Field

from tangl.core.singleton import Singleton as LabelSingleton

class SimpleLabelSingleton(LabelSingleton):
    """Test fixture class"""
    value: int = Field(default=0)


def test_basic_label_singleton():
    """Test basic label singleton functionality"""
    s1 = SimpleLabelSingleton(label="test")
    s2 = SimpleLabelSingleton.get_instance('test')
    assert s1 is s2
    assert s1.label == "test"
    assert len(SimpleLabelSingleton._instances) == 1
    assert len(SimpleLabelSingleton.all_instance_labels()) == 1


def test_different_labels():
    """Test instances with different labels"""
    s1 = SimpleLabelSingleton(label="test1")
    s2 = SimpleLabelSingleton(label="test2")
    assert s1 is not s2
    assert s1.label != s2.label
    assert len(SimpleLabelSingleton._instances) == 2
    assert len(SimpleLabelSingleton.all_instance_labels()) == 2


def test_label_validation():
    """Test label validation"""
    with pytest.raises((ValueError, ValidationError),):
        SimpleLabelSingleton(label="")  # Empty label

    with pytest.raises((TypeError, ValueError, ValidationError),):
        SimpleLabelSingleton()  # Missing label

    # Test validation
    with pytest.raises((ValueError, ValidationError),):
        SimpleLabelSingleton(label=123)  # Wrong type for label


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
    assert len(SimpleLabelSingleton.all_instance_labels()) == 1
    assert len(ChildLabelSingleton._instances) == 1
    assert len(ChildLabelSingleton.all_instance_labels()) == 1

def test_clear_instances():
    """Test instance clearing"""

    class ChildLabelSingleton(SimpleLabelSingleton):
        pass

    SimpleLabelSingleton(label="test1")
    SimpleLabelSingleton(label="test2")
    ChildLabelSingleton(label="test3")

    assert len(SimpleLabelSingleton.all_instance_labels()) == 2
    assert len(ChildLabelSingleton.all_instance_labels()) == 1

    SimpleLabelSingleton.clear_instances()

    assert len(SimpleLabelSingleton.all_instance_labels()) == 0
    assert len(ChildLabelSingleton.all_instance_labels()) == 1


def test_filter_by_label():
    """Test filtering by label"""
    s1 = SimpleLabelSingleton(label="test1")
    s2 = SimpleLabelSingleton(label="test2")

    # found = SimpleLabelSingleton.find_instances(label="test1")
    # assert len(found) == 1
    # assert found[0] is s1

    found = SimpleLabelSingleton.find_instance(label="test2")
    assert found is s2

@pytest.mark.xfail(reason="No longer works like this")
def test_inheritance_search():
    """Test searching through inheritance hierarchy"""

    class ChildLabelSingleton(SimpleLabelSingleton):
        pass

    child = ChildLabelSingleton(label="test")
    found = SimpleLabelSingleton.get_instance("test")
    assert found is child



@pytest.fixture(autouse=True)
def cleanup():
    SimpleLabelSingleton.clear_instances()
    yield
    SimpleLabelSingleton.clear_instances()

import pytest
import io
from pathlib import Path
from tempfile import NamedTemporaryFile

from pydantic import ValidationError, model_validator

from tangl.core.singleton import DataSingleton

def test_basic_data_singleton():
    """Test basic data singleton functionality"""
    data = b"test data"
    s1 = DataSingleton(data=data)
    s2 = DataSingleton(data=data)
    assert s1 is s2
    assert s1.data == data
    assert len(DataSingleton._instances) == 1


def test_different_data():
    """Test instances with different data"""
    s1 = DataSingleton(data=b"data1")
    s2 = DataSingleton(data=b"data2")
    assert s1 is not s2
    assert s1.data != s2.data
    assert len(DataSingleton._instances) == 2

class DeferredDataSingleton(DataSingleton):

    deferred_data: bytes

    @model_validator(mode="after")
    def _load_deferred_data(self):
        # Override frozen setattr if computing a deferred digest
        object.__setattr__(self, 'data', self.deferred_data)
        return self

def test_deferred_loading():
    """Test deferred data loading"""
    # Create without data first
    data = b"test data"
    s1 = DeferredDataSingleton(deferred_data=data)

    # New instance with same data should return original
    s2 = DeferredDataSingleton(data=data)
    assert s2 is s1


def test_from_file():
    """Test loading from file"""
    test_data = b"test file data"

    with NamedTemporaryFile(suffix='.txt') as tf:
        tf.write(test_data)
        tf.flush()

        # Load same file twice
        s1 = DataSingleton.from_file(tf.name)
        s2 = DataSingleton.from_file(tf.name)

        assert s1 is s2
        assert s1.data == test_data
        assert s1.content_type == 'txt'
        assert s1.source == tf.name


def test_from_stream():
    """Test loading from streams"""
    # Binary stream
    binary_data = b"binary data"
    binary_stream = io.BytesIO(binary_data)
    s1 = DataSingleton.from_stream(binary_stream)

    # Text stream
    text_data = "text data"
    text_stream = io.StringIO(text_data)
    s2 = DataSingleton.from_stream(text_stream)

    assert s1.data == binary_data
    assert s2.data == text_data.encode('utf-8')


def test_content_type():
    """Test content type handling"""
    s = DataSingleton(data=b"data", content_type="text/plain")
    assert s.content_type == "text/plain"

    # From file should infer type
    with NamedTemporaryFile(suffix='.json') as tf:
        tf.write(b"{}")
        tf.flush()
        s = DataSingleton.from_file(tf.name)
        assert s.content_type == 'json'


def test_size():
    """Test size calculation"""
    s1 = DataSingleton(data=b"1234")
    assert s1.size() == 4

    s2 = DataSingleton(data='')
    assert s2.size() == 0


def test_identifiers():
    """Test identifier generation"""
    with NamedTemporaryFile() as tf:
        s = DataSingleton.from_file(tf.name)
        ids = s._get_identifiers()
        assert tf.name in ids


def test_immutability():
    """Test immutability after loading"""
    s = DataSingleton(data=b"test")

    with pytest.raises(ValidationError):
        s.data = b"new data"

    with pytest.raises(ValidationError):
        s.content_type = "new/type"

#
# def test_load_data_updates():
#     """Test that load_data properly updates digest"""
#     s = DataSingleton(data=b"some data")
#     original_digest = s.digest
#
#     s.load_data(b"new data")
#     assert s.digest != original_digest
#     assert s.data == b"new data"
#
#     # Loading same data again should work
#     s.load_data(b"new data")
#
#     # Different data should raise error due to immutability
#     with pytest.raises(KeyError):
#         s.load_data(b"different data")


@pytest.mark.parametrize("encoding", ['utf-8', 'ascii', 'utf-16'])
def test_text_encodings(encoding):
    """Test handling of different text encodings"""
    text = "Hello, 世界!"  # Mix of ASCII and Unicode
    data = text.encode(encoding, errors='ignore')
    s = DataSingleton(data=data, content_type=f"text/{encoding}")
    assert s.data == data


def test_large_data():
    """Test handling of larger data"""
    large_data = b"x" * 1024 * 1024  # 1MB
    s = DataSingleton(data=large_data)
    assert s.size() == len(large_data)
    assert s.data == large_data


@pytest.fixture(autouse=True)
def cleanup():
    DataSingleton.clear_instances()
    yield
    DataSingleton.clear_instances()

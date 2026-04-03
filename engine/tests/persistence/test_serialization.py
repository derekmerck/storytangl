import json
import uuid
from datetime import datetime, timedelta

from tangl.persistence.serializers import *

def test_round_trip(serializer):

    unstructured = {
        'str': 'my_name',
        'dict': {'foo': 'bar'},
        'num': 123,
        'list': ['fish', 'cat', 'dog'],

        # Problematic types
        'uid': uuid.uuid4(),
        'dt': datetime.now(),
        'set': {'fishbowl', 'bowling-ball'},
        'blob': b'\x12\x34\xab\xcd',
    }

    flat = serializer.serialize(unstructured)
    unflat = serializer.deserialize(flat)

    if serializer is JsonSerializationHandler:
        # pydantic will cast these back if properly annotated
        unflat['set'] = set( unflat['set'] )

    if serializer is BsonSerializationHandler:
        unflat['set'] = set( unflat['set'] )
        # bson saves these in some kind of fixed point that is apparently less accurate than microseconds
        if unflat['dt'] - unstructured['dt'] < timedelta(seconds=0.5):
            unflat['dt'] = unstructured['dt']

    # Assertion to verify that the deserialized data is equivalent to the original
    assert unflat == unstructured


def test_json_bytes_round_trip_uses_explicit_tagged_shape() -> None:
    payload = {"blob": b"\x12\x34\xab\xcd"}

    flat = JsonSerializationHandler.serialize(payload)
    wire = json.loads(flat)
    unflat = JsonSerializationHandler.deserialize(flat)

    assert wire == {
        "blob": {
            "__tangl_type__": "bytes",
            "hex": "1234abcd",
        }
    }
    assert unflat == payload

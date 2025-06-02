import base64
import uuid

def mk_eid() -> str:
    """Unique entity ID"""
    hash = uuid.uuid4().bytes
    b64 = base64.b64encode(hash, b"Aa")
    res = b64.decode('utf8')[0:10]
    return res


def as_eid( value ) -> str:
    """Represent item as its eid (for references to avoid recursion)"""

    if isinstance(value, dict):
        for k, v in value.items():
            value[k] = v.pid
    elif isinstance(value, list):
        for i, v in enumerate(value):
            value[i] = v.pid
    elif hasattr(value, "pid"):
        value = value.pid

    try:
        return str( value )
    except AttributeError as e:  # pragma: no cover
        print( "Failed to repr as eid" )
        print( e )
        print( object.__repr__( value ) )
        print( value.__dict__ )
        raise

def as_uid(value) -> str:
    """Represent entity as its uid (for references to avoid recursion)"""

    if isinstance(value, dict):
        for k, v in value.items():
            value[k] = v.uid
    elif isinstance(value, list):
        for i, v in enumerate(value):
            value[i] = v.uid
    elif hasattr(value, "uid"):
        value = value.uid

    try:
        return str(value)
    except AttributeError as e:  # pragma: no cover
        print( "Failed to repr as eid" )
        print(e)
        print(object.__repr__(value))
        print(value.__dict__)
        raise

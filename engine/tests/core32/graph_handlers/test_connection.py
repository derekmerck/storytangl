import logging

from tangl.core import Node
from tangl.core.graph_handlers.connection import Connection

logger = logging.getLogger(__name__)

class TestConnectionNode(Connection, Node):
    ...

def test_connect_compatible():
    connector1 = TestConnectionNode(connection_gender='xy', connection_shape='round')
    connector2 = TestConnectionNode(connection_gender='xx', connection_shape='round')
    assert connector1.can_connect_to(connector2)
    assert connector2.can_connect_to(connector1)
    connector1.connect_to(connector2)
    assert connector1.connected_to is connector2
    assert connector2.connected_to is connector1

def test_connect_incompatible_gender():
    connector1 = TestConnectionNode(connection_gender='xy', connection_shape='round')
    connector2 = TestConnectionNode(connection_gender='xy', connection_shape='round')
    assert not connector1.can_connect_to(connector2)
    assert not connector2.can_connect_to(connector1)

def test_connect_incompatible_shape():
    connector1 = TestConnectionNode(connection_gender='xy', connection_shape='round')
    connector2 = TestConnectionNode(connection_gender='xx', connection_shape='square')
    logger.debug(connector1.can_connect_to(connector2))
    assert not connector1.can_connect_to(connector2)
    assert not connector2.can_connect_to(connector1)

def test_disconnect():
    connector1 = TestConnectionNode(connection_gender='xy', connection_shape='round')
    connector2 = TestConnectionNode(connection_gender='xx', connection_shape='round')
    assert connector1.can_connect_to(connector2)
    assert connector2.can_connect_to(connector1)
    connector1.connect_to(connector2)
    assert connector1.connected_to is connector2
    assert connector2.connected_to is connector1

    assert connector1.can_disconnect()
    assert connector2.can_disconnect()
    connector1.disconnect()
    assert connector1.connected_to is None
    assert connector2.connected_to is None

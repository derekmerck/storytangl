from __future__ import annotations
from enum import Enum
import logging

from tangl.core.entity_handlers import Available
from .associating import Associating, on_can_associate, on_can_disassociate

logger = logging.getLogger(__name__)

# Simple example for connection properties
class ConnectionGender(Enum):
    XX = "xx"
    XY = "xy"

class ConnectionShape(Enum):
    SQUARE = "square"
    ROUND = "round"

class Connection(Available, Associating):
    """
    Connections are 1-to-1 non-hierarchical Associates with availability conditions
    and compatibility constraints.
    """

    connection_gender: ConnectionGender  # must be opposite
    connection_shape: ConnectionShape    # must be the same

    @property
    def connected_to(self) -> Connection:
        # in-use
        return self.find_child(has_cls=Connection)

    # Strategies

    @on_can_associate.register()
    def _check_is_compatible(self, other: Connection, **kwargs):
        # opposite genders
        return self.connection_gender is not other.connection_gender and \
            self.connection_shape is other.connection_shape

    @on_can_associate.register()
    def _check_is_not_in_use(self, other: Connection, **context):
        return self.connected_to is None

    @on_can_disassociate.register()
    def _check_is_connected_to(self, other: Connection, **context):
        logger.debug(f"{self!r}.connected_to = {self.connected_to!r}")
        return self.connected_to is other

    # Accessors

    def can_connect_to(self, other: Connection, **context) -> bool:
        return self.can_associate_with(other=other, **context)

    def can_disconnect(self, **context) -> bool:
        return self.can_disassociate_from(other=self.connected_to, **context)

    def connect_to(self, other: Connection, **context):
        return self.associate_with(other=other, **context)

    def disconnect(self, **context):
        return self.disassociate_from(other=self.connected_to, **context)

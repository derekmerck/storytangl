from __future__ import annotations
from enum import Enum

from tangl.entity.mixins import Lockable
from .associating import AssociationHandler, Associating

# Simple example for connection properties
class ConnectionGender(Enum):
    XX = "xx"
    XY = "xy"

class ConnectionShape(Enum):
    SQUARE = "square"
    ROUND = "round"

class Connection(Lockable, Associating):
    """
    Connections are 1-to-1 non-hierarchical Associates with availability conditions
    and compatibility constraints.
    """

    connection_gender: ConnectionGender  # must be opposite
    connection_shape: ConnectionShape    # must be the same

    @property
    def connected_to(self) -> Connection:
        # in-use
        return self.find_child(Connection)

    # Strategies

    @AssociationHandler.can_associate_with_strategy
    def _check_is_compatible(self, other: Connection, **kwargs):
        # opposite genders
        return self.connection_gender is not other.connection_gender and \
            self.connection_shape is other.connection_shape

    @AssociationHandler.can_associate_with_strategy
    def _check_is_not_in_use(self, other: Connection, **kwargs):
        return self.connected_to is None

    @AssociationHandler.can_disassociate_from_strategy
    def _check_is_connected_to(self, other: Connection):
        return self.connected_to is other

    @AssociationHandler.can_associate_with_strategy
    def _check_available_connect(self, other: Connection, **kwargs) -> bool:
        return self.available()

    @AssociationHandler.can_disassociate_from_strategy
    def _check_available_disconnect(self, other: Connection, **kwargs) -> bool:
        return self.available()

    # Accessors

    def can_connect_to(self, other: Connection) -> bool:
        return AssociationHandler.can_associate_with(self, other)

    def can_disconnect(self) -> bool:
        return AssociationHandler.can_disassociate_from(self, self.connected_to)

    def connect_to(self, other: Connection):
        AssociationHandler.associate_with(self, other)

    def disconnect(self):
        AssociationHandler.disassociate_from(self, self.connected_to)

# todo: swap these in to make exception management more precise

class TanglException( Exception ):
    # all StoryTangl-specific exceptions are derived from this one
    pass


class WorldInitializationError( TanglException, ValueError ):
    # raised when a world cannot be loaded properly
    pass


class ProvisionError( TanglException, RuntimeError):
    # raised when a provisioning task fails and a node cannot be resolved
    pass


class AssociationHandlerError( TanglException, ValueError ):
    # raised when an illegal node association is attempted (e.g., a trade
    # for an item that node does not own)
    pass


class StoryAccessError( TanglException, RuntimeError ):
    # raised when a locked or unavailable resource is requested
    pass


class UserAccessError( TanglException, ConnectionError ):
    # raised when a user is not authorized to access a requested endpoint
    pass


class RemoteApiUnavailable( TanglException, ConnectionError ):
    # raised when attempting to access an unavailable db or dev tool api
    pass

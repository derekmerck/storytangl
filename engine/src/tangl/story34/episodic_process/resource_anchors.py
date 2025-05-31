# resources that fill roles, actor, location, asset

from tangl34.core.structure import Node

class Actor(Node):
    # satisfies character role
    ...

class Location(Node):
    # satisfies setting role
    ...

# wrapped domain singleton (linked), fungible domain singleton (counted)
class Asset(Node):
    ...

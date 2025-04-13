"""
Assets come in two flavors:
- Discrete
- Countable

Both are based on singleton reference classes.
- Discrete assets are wrapped in a SingletonNode class and associated with other nodes in the story graph.
- Countable assets are inventoried in an AssetWallet counter that can be attached to a story node type.

Moving assets is handled through a Transaction handler pipeline.

Assets of a given class have instance inheritance from already registered peers via a "from" field.

Note, Entities can have countable assets stored in a wallet component, however, discrete assets
are associated, so they require a node/graph structure.
"""
from tangl.core.entity import InheritingSingleton
from tangl.core.handlers import Renderable

class Asset(Renderable, InheritingSingleton):

    name: str = None
    value: float = None

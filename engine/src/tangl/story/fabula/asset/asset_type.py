"""
Assets come in three flavors:
- Discrete
- Countable
- Simple

Discrete and Countable are based on singleton reference classes.
- Discrete assets are wrapped in a SingletonNode class and associated with other nodes in the story graph.
- Countable assets are inventoried in an AssetWallet counter that can be attached to a story node type.

Simple assets are just a tag-like inventory of strings and enums with no higher-order handlers.
In a pinch, they could also contain asset type singletons.

Moving assets is handled through a Transaction handler pipeline.

Assets of a given class have instance inheritance from already registered peers via a "from" field.

Note, Entities can have countable assets stored in a wallet component, however, discrete assets
are associated, so they require a node/graph structure.  Simple assets require neither wallet
nor graph, they are tracked via a set attribute "inv" on the host entity.
"""

from tangl.core.singleton import InheritingSingleton
from tangl.core.services import Renderable, HasContext  # Associating

class AssetType(Renderable, HasContext, InheritingSingleton):
    """
    An AssetType is a singleton entity node that represents a specific
    noun within the narrative, such as a sword, a bag of money, or a shirt.

    AssetTypes have 'instance inheritance', by referring to another of the same subclass
    at creation, the asset will take any attributes from that class as its defaults for
    unset attributes. (So be careful not to instantiate them out of order.)

    :ivar label: Singleton's require unique labels within their class
    :ivar text: A brief description of the asset
    :ivar from_ref: A reference asset for instance inheritance
    """
    ...

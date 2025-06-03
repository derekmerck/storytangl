from typing import Optional

from tangl.core.solver.feature_nodes import DependencyEdge
from ..media_creators import MediaCreatorSpec
from .media_resource_inv_tag import MediaResourceInventoryTag as MediaRIT

class MediaDependency(DependencyEdge[MediaRIT]):
    media_spec: Optional[MediaCreatorSpec] = None

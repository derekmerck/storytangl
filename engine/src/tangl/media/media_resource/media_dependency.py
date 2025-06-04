from typing import Optional

from tangl.core.solver.provisioner import DependencyEdge
from ..media_spec import MediaSpec
from .media_resource_inv_tag import MediaResourceInventoryTag as MediaRIT

class MediaDependency(DependencyEdge[MediaRIT]):
    media_spec: Optional[MediaSpec] = None

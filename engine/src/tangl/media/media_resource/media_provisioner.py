from tangl.core.solver.provisioner.provision_dependency import DependencyProvisioner
from ..media_creators import MediaCreatorSpec
from .media_resource_inv_tag import MediaResourceInventoryTag as MediaRIT
from .media_resource_registry import MediaResourceRegistry

class MediaProvisioner(DependencyProvisioner):
    """
    - story media script w path/url, media registry alias, or spec
    - story media dep is provisioned:
      - **path** rit is discovered or created directly from the path/url and linked
      - **registry alias** is validated linked
      - **spec** is transformed using an appropriate adapter for the parent node (actor, block, etc.) and its aliases are searched in the registry
        - if the spec alias is already in the media registry: link it
        - otherwise:
          - invoke the creator pipeline
          - the spec may also be updated creator-side with seed info or other random processes, so creators return a _realized_ spec and associated media data
          - register the returned media and update the node spec if the node is unrepeatable, otherwise leave it as the template so it can be re-rendered when the context is updated
          - link the new rit
    """
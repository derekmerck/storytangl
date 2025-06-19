from tangl.core.dispatch import HandlerRegistry
from tangl.core.solver.provisioner import ResoluableNode
from .media_dependency import MediaDep

on_provision_media = HandlerRegistry(label="provision_media")


class HasMedia(ResoluableNode):
    # May have multiple media objects with different roles

    def media_dependencies(self):
        return self.edges(has_cls=MediaDep)

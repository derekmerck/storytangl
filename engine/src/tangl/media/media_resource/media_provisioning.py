from tangl.core.handler import HandlerRegistry
from .media_dependency import MediaDep

on_provision_media = HandlerRegistry(label="provision_media")

Resolvable = object

class HasMedia(Resolvable):
    # May have multiple media objects with different roles

    def media_dependencies(self):
        return self.edges(has_cls=MediaDep)

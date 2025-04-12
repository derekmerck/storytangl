from __future__ import annotations
from typing import Any, Optional
from uuid import UUID

from tangl.utils.uuid_for_secret import uuid_for_secret
from tangl.graph import Node
from tangl.resource_registry.resource_inventory_tag import ResourceInventoryTag as RIT
from .script_model import MediaItemScript
from .media_spec import MediaSpecification
from .journal_model import JournalMediaItem

class MediaNode(MediaItemScript, Node):
    """
    MediaNode is an intermediate representation of a script-referenced media object.

    It may be a state url or data, or it may be a named media resource, or it may be a
    prepared media resource.  Prepared media is created dynamically or semi-dynamically
    (for example, at world-initialization).

    For named or prepared media objects, the file or data is actually managed by the
    backend service layer.  The node carries a `ResourceInventoryTag` (RIT) that provides
    the service layer with input to generate the final file location relative to a given
    server.

    Technically, the `media_role` is _not_ part of the associated resource, the role
    _links_ a resource to a narrative object, so the same resource can actually be used
    in many places and many roles.
    """
    # todo: need some sort of indicator about what _kind_ of a collection the RIT belongs to,
    #       ie, is it served from world/public media or from story/client media...

    spec: Optional[MediaSpecification] = None          #: overload field with correct type
    realized_spec: Optional[MediaSpecification] = None #: most recently realized specification
    final_spec: Optional[MediaSpecification] = None    #: final spec with forge defaults, etc. for auditing
    rit: RIT = None                                    #: Resource inventory tag for final resource response

    # Hashed uid

    uid_: Optional[UUID] = None  #: Don't need a default uid

    def _secret(self):
        if self.spec:
            return self.spec._secret()
        elif self.url:
            return str(self.url)
        elif self.name:
            # todo: Does this need salted by world or path or are named objects are unique in a registry?
            return self.name
        elif self.data:
            return self.data
        else:
            raise ValueError(f"No target field for secret in {self}")

    @property
    def uid(self) -> UUID:
        return uuid_for_secret(self._secret())

    # -----------------------
    # Handler accessors
    # -----------------------

    def clear_media_resource(self):
        from .media_handler import MediaHandler
        return MediaHandler.clear_media_resource(self)

    def prepare_media_resource(self) -> RIT:
        from .media_handler import MediaHandler
        return MediaHandler.prepare_media_resource(self)

    def get_media_resource(self) -> JournalMediaItem:
        from .media_handler import MediaHandler
        return MediaHandler.get_media_resource(self)

    # @MediaHandler.get_aliases_strategy
    def _get_aliases(self):
        aliases = { self.uid,
                    self.name,
                    self.spec.uid,
                    self.realized_spec.uid,
                    self.final_spec.uid }
        aliases.discard(None)
        return aliases




from uuid import UUID
from dataclasses import dataclass
import logging

from ..entity import Entity
from ..scope.scope_mixin import ScopeMixin

logger = logging.getLogger(__name__)

@dataclass(kw_only=True)
class Node(ScopeMixin, Entity):
    parent_uid: UUID | None = None

    def iter_ancestors(self, *, graph):
        uid = self.parent_uid
        logger.debug(f"initial parent uid {uid}")
        while uid:
            node = graph.get(uid)
            logger.debug(f"yielding ancestor {node!r}")
            yield node
            uid = node.parent_uid

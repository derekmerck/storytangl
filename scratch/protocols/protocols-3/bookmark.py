# todo: bookmarks should reference both journal and history entries
from __future__ import annotations
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel

from tangl.type_hints import UniqueLabel, Identifier
from .entity import TaskHandler, Registry, EntityMixin
from .content import MediaFragment

class BookmarkMetadata(BaseModel):
    uid: UUID
    journal_fragment_id: UUID
    graph_history_id: UUID
    label: UniqueLabel = None
    chapter: str | None = None
    location: str | None = None
    text: str = None             # preview comment
    media: list[MediaFragment]   # preview thumbnail


class HasBookmarks(EntityMixin):
    bookmarks: Registry[BookmarkMetadata]


class BookmarkManager(TaskHandler):

    graph: HasBookmarks

    # create, get, update/restore state, delete

    def create_bookmark(self, **kwargs): ...
    def get_bookmarks(self) -> list[BookmarkInfo]: ...
    def restore_bookmark(self, bookmark_id: Identifier): ...
    def delete_bookmark(self, bookmark_id: Identifier): ...


# ----------------
# Graph History Bookmark Info
# ----------------

class BookmarkInfo(BaseModel):
    step_id: UUID
    timestamp: datetime
    automatic: bool = False
    label: UniqueLabel = None
    chapter: str | None = None
    location: str | None = None
    text: str = None             # preview comment
    media: list[MediaFragment]   # preview thumbnail

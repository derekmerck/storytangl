from __future__ import annotations
from typing import Protocol, TYPE_CHECKING, Any
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from .type_hints import UniqueString, StringMap, Identifier
from .entity import HasContext, Registry, Entity
from .graph import Graph
from .bookmark import BookmarkInfo
from .graph_history import HasGraphHistory
from .journal import HasJournal, JournalFeature, JournalEntry

if TYPE_CHECKING:
    from .world import World, AchievementId, AchievementInfo, WorldId
    from .content import MediaFragment
    from .story_nodes import StoryNode

# ----------------
# Story-related Type Hints
# ----------------
StoryId = UUID
StoryFeature = UniqueString    # maps, stats, inv, etc.

# ----------------
# Story Model
# ----------------
class Story(HasJournal, HasGraphHistory, HasContext, Graph):
    uid: StoryId
    world: World
    nodes: Registry[StoryNode]
    player: Entity
    achievements: set[tuple[AchievementId, datetime]]

# ----------------
# Story Instance Manager
# ----------------
class StoryManager(Protocol):
    """Story instance interaction"""

    story: Story

    async def get_journal_entry(self,
                                which: int | str = -1,
                                feature_config: dict[JournalFeature, Any] = None
                                ) -> JournalEntry:
        """Get story journal entry - text, choices, media - latest or specific historical entry"""

    async def get_info(self, feature_config: dict[StoryFeature, Any] = None) -> StoryInfo:
        """Get current story state by features, including bookmarks"""

    async def do_action(self,
                        action: StoryNode,
                        action_payload: StringMap = None) -> JournalEntry:
        """Execute a story action and return resulting update"""

    # dev/restricted functions
    async def check_value(self, expr: str) -> Any: ...
    async def apply_effect(self, expr: str) -> None: ...
    async def goto_node(self, node: StoryNode) -> JournalEntry: ...

    # story history management

    async def create_bookmark(self,
                              story: Story,
                              label: str = None,
                              bookmark_info: BookmarkInfo = None
                              ) -> Identifier:
        """Create manual save point"""

    async def delete_bookmark(self,
                              story: Story,
                              bookmark_id: Identifier
                              ) -> None:
        """Remove a saved state"""

    async def restore_bookmark(self,
                               bookmark_id: Identifier
                               ) -> JournalEntry:
        """Restore to a saved state"""

# ----------------
# Story Info
# ----------------
class StoryAchievementInfo(AchievementInfo):
    timestamp: datetime

class StoryInfo(BaseModel, allow_extra=True):
    story_id: StoryId
    world_id: WorldId
    created: datetime
    last_modified: datetime
    is_complete: bool = False

    media: list[MediaFragment] = None      # avatar and other media
    bookmarks: list[BookmarkInfo] = None

    total_turns: int
    achievements: list[StoryAchievementInfo]

    current_chapter: str | None
    current_location: str | None

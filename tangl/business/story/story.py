from uuid import UUID

from tangl.core import Graph, Node

def setup_story_pipelines():
    """
    Story pipelines include:
    - on_create (get class, update args/kwargs) -> type[Entity], args, kwargs
    - on_init (post init bookkeeping and registrations) -> in place
    - on_gather_context (collect scoped local and global variables and callables) -> mapping
    - on associate/disassociate dynamically linked nodes -> in place
    - on_enter/exit traversable nodes (invokes processing) -> new cursor update loc or None
    - on_render_content (invokes services to assemble a journal entry) -> list[JournalFragment]
    """


class StoryNode(Node):
    @property
    def story(self):
        return self.graph


class Story(Graph[StoryNode]):

    cursor_id: UUID = None

    @property
    def cursor(self) -> StoryNode:  # a traversable story node, no less
        return self[self.cursor_id]

    # def get_scenes(self):
    #     from .scene import Scene
    #     self.find(obj_cls=Scene)

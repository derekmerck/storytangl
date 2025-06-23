from typing import Any

from pydantic import BaseModel

from tangl.type_hints import Identifier, Expr, UnstructuredData
from tangl.service.api_endpoint import ApiEndpoint, MethodType, ResponseType, AccessLevel, HasApiEndpoints
# from tangl.media.media_record import MediaRecord, MediaDataType
# from tangl.service.response import ContentResponse, InfoResponse
from tangl.core.entity import Node, AnonymousEdge
from tangl.core.handler import on_gather_context, Predicate, RuntimeEffect
from tangl.core.solver import ChoiceEdge
from .story import Story
from .content_fragment import ContentFragment

class StoryController(HasApiEndpoints):
    """
    This is the library API for the Story logic implemented as a
    collection of methods.

    client:
    - read entries from a story journal (ro)
    - get info about a story (player status, maps, etc.) (ro)
    - get story media (dynamic content) (maybe rw if new content is generated?)
    - resolve a traversal step in a story (rw)
    - undo a step in a story (rw) (*optional*)

    restricted:
    - jump to a traversable node in a story
    - get info about a node in a story
    - evaluate an expression in a story
    - apply an effect in a story

    Wrapping the methods with ApiEndpoint provides the ServiceManager
    class with hints for creating appropriate service-layer endpoints
    with context.
    """

    @ApiEndpoint.annotate(access_level=AccessLevel.USER, response_type=ResponseType.CONTENT)
    def get_journal_entry(self, story: Story, item = -1) -> list[ContentFragment]:
        # JournalEntries are formatted as content fragments and interpreted as an
        # ordered list of styled narrative entries
        return story.get_journal_entry(item)

    @ApiEndpoint.annotate(access_level=AccessLevel.USER, response_type=ResponseType.CONTENT)
    def get_story_info(self, story: Story, **kwargs) -> list[ContentFragment]:
        # StoryInfo is formatted as content fragments and can be interpreted as
        # an ordered, styled kv list
        return story.get_info(**kwargs)

    @ApiEndpoint.annotate(access_level=AccessLevel.USER)
    def get_story_media(self, story: Story, media: 'MediaRIT' | Identifier, **kwargs) -> 'MediaDataType':
        if isinstance(media, Identifier):
            media = story.find_one(alias=media)  # type: MediaRIT
        return media.get_content(**kwargs)

    @ApiEndpoint.annotate(access_level=AccessLevel.USER, method_type=MethodType.UPDATE)
    def do_step(self, story: Story, edge: ChoiceEdge | Identifier, **kwargs):
        if isinstance(edge, Identifier):
            edge = story.find_one(alias=edge)  # type: ChoiceEdge
        story.resolve_choice(edge, **kwargs)

    @ApiEndpoint.annotate(access_level=AccessLevel.USER, method_type=MethodType.UPDATE)
    def undo_step(self, story: Story):
        raise NotImplementedError

    # Restricted functions
    # --------------------
    # For testing, these functions mark the story as "dirty" to indicate that the
    # local story logic has been manually inspected or tampered with, but has no
    # other effect.  It is primarily to indicate that achievements are off and errors
    # may not be reproducible.

    @ApiEndpoint.annotate(access_level=AccessLevel.RESTRICTED, method_type=MethodType.UPDATE)
    def goto_node(self, story: Story, node: Node | Identifier):
        if isinstance(node, Identifier):
            node = story.find_one(alias=node)
        node.dirty = True  # Jumping logic arbitrarily
        anonymous_edge = AnonymousEdge(source=story.cursor, dest=node)
        story.resolve_choice(anonymous_edge)

    # Read func, but make this an update, so it writes back the story marked as dirty
    @ApiEndpoint.annotate(access_level=AccessLevel.RESTRICTED, method_type=MethodType.UPDATE)
    def get_node_info(self, story: Story, node: Node | Identifier) -> UnstructuredData:
        if isinstance(node, Identifier):
            node = story.find_one(alias=node)
        node.dirty = True  # Inspecting internal values
        data = node.model_dump()
        return data

    # Read func, but make this an update, so it writes back the story marked as dirty
    @ApiEndpoint.annotate(access_level=AccessLevel.RESTRICTED,
                          method_type=MethodType.UPDATE,
                          response_type=ResponseType.RUNTIME)
    def check_condition(self, story: Story, expr: Expr) -> Any:
        story.dirty = True  # Testing internal values
        ctx = on_gather_context.execute_all(story, ctx=None)
        result = Predicate.eval_raw_expr(expr, ctx=ctx)
        return result

    @ApiEndpoint.annotate(access_level=AccessLevel.RESTRICTED,
                          method_type=MethodType.UPDATE,
                          response_type=ResponseType.RUNTIME)
    def apply_effect(self, story: Story, effect: Expr):
        story.dirty = True  # Updating internal values arbitrarily
        ctx = on_gather_context.execute_all(story, ctx=None)
        RuntimeEffect.exec_raw_expr(effect, ctx=ctx)

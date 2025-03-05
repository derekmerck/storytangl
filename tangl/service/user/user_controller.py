from tangl.type_hints import Identifier
from tangl.service.api_endpoints import ApiEndpoint, AccessLevel, HasApiEndpoints
from tangl.business.content.media.media_record import MediaRecord, MediaDataType
from tangl.business.story.story_graph import Story
from .user import User, UserSecret, UserInfo

class UserController(HasApiEndpoints):
    """
    client:
    - create new user (rw)
    - create new story from a world (rw) **currently in world controller
    - update user api key or current_story (rw)
    - get info about user (achievements, global story stats) (ro)
    - get media related to this user (avatar) (possibly rw if new media is generated?)
    - drop this user (rw)
    - drop a story (rw)

    Wrapping the methods with ApiEndpoint provides the ServiceManager
    class with hints for creating appropriate service-layer endpoints
    with context.
    """

    @ApiEndpoint.annotate(access_level=AccessLevel.USER)
    def create_user(self, **kwargs) -> User:
        return User(**kwargs)

    @ApiEndpoint.annotate(access_level=AccessLevel.USER)
    def update_user(self, user: User, **kwargs):
        user.update(**kwargs)

    @ApiEndpoint.annotate(access_level=AccessLevel.USER)
    def get_user_info(self, user: User, **kwargs) -> UserInfo:
        return user.get_info(**kwargs)

    @ApiEndpoint.annotate(access_level=AccessLevel.USER)
    def get_user_media(self, user: User, media: MediaRecord | Identifier, **kwargs) -> MediaDataType:
        if isinstance(media, Identifier):
            media = user.find_one(alias=media)
        return media.get_content(**kwargs)

    @ApiEndpoint.annotate(access_level=AccessLevel.USER)
    def drop_user(self, user: User, **kwargs):
        # returns a list of uids to drop from service context
        story_ids = user.get_story_ids()
        for story_id in story_ids:
            user.unlink_story(story_id)
        return user.uid, *story_ids

    @ApiEndpoint.annotate(access_level=AccessLevel.USER, group="user")
    def drop_story(self, story: Story, **kwargs):
        # returns a list of uids to drop from service context, user is written back
        story.user.unlink_story(story)
        return (story.uid,)

    @ApiEndpoint.annotate(access_level=AccessLevel.PUBLIC, group="system")
    def get_key_for_secret(self, secret: str, **kwargs):
        ...

import pytest
import uuid

from tangl.info import __title__, __version__
from tangl.cli.app import TanglShell
from tangl.service import ServiceManager
from tangl.story import JournalStoryUpdate
from tangl.utils.response_models import KVItem

# request models
from tangl.service.request_models import ActionRequest

# response models
from tangl.story import Story, StoryStatus, NodeInfo, JournalStoryUpdate
JournalEntry = list[JournalStoryUpdate]
from tangl.user import UserInfo, UserSecret
from tangl.world import WorldInfo, WorldList, WorldSceneList
from tangl.service.response_models import SystemInfo


# Mock the Story object to always return the same output
class MockServiceManager(ServiceManager):

    # === Story services ===
    # --- Client ---

    def get_story_update(self, *args, **kwargs) -> JournalEntry:  # user_id
        return [ JournalStoryUpdate( **{'text': 'You are in a dark room.',
                                        'uid': uuid.uuid4(),
                                        'label': 'block1',
                                        'actions': [{'uid': uuid.uuid4(),
                                                     'text': 'Turn on the light.'}]} ) ]

    def get_story_status(self, *args, **kwargs):  # user_id
        return [ KVItem( **{'key': 'status',
                            'value': 'ongoing',
                            'style_cls': 'ok'} ) ]

    def do_story_action(self, *args, **kwargs):  # user_id, action_id, **kwargs
        return [ JournalStoryUpdate( **{'text': 'The room is now bright.',
                                        'uid': uuid.uuid4(),
                                        'label': 'block2',
                                        'actions': []}  ) ]


    # --- Dev ---

    def inspect_node(self, *args, **kwargs) -> NodeInfo:
        return NodeInfo(uid=uuid.uuid4(), label="secret_node", text="you shouldn't be here!")

    def goto_node(self, *args, **kwargs) -> JournalEntry:
        return [ JournalStoryUpdate( **{'text': 'You are in a totally different place.',
                                        'uid': uuid.uuid4(),
                                        'label': 'block3',
                                        'actions': [{'uid': uuid.uuid4(),
                                                     'text': 'How did you get here?'}]} ) ]

    def check_expr(self, *args, **kwargs) -> dict:
        return {'condition': 'player.has_sword',
                'result': True}

    def apply_effect(self, *args, **kwargs) -> dict:
        return {'effect': "player.inv.add('sword')",
                'result': 'apply ok'}

    # === User services ===
    # --- Public ---

    def create_user(self, secret: str = None) -> UserSecret:
        return UserSecret(uuid.uuid4(), secret)

    @staticmethod
    def key_for_secret(secret: str = None) -> UserSecret:
        return UserSecret(uuid.uuid4(), secret)

    # --- Client ---

    def update_user_secret(self, user_id, secret) -> UserSecret:
        return UserSecret( uuid.uuid4(), secret )

    def get_user_info(self, *args, **kwargs) -> UserInfo:
        return UserInfo(uid=uuid.uuid4())

    def remove_user(self, *args, **kwargs):
        user_id = uuid.uuid4()
        story_ids = [uuid.uuid4() for _ in range(3)]
        return {'remove_user': user_id,
                'result': f'remove user {user_id} and stories {story_ids} ok'}

    def remove_story(self, *args, **kwargs) -> dict:
        world_id = "sample world"
        story_id = uuid.uuid4()
        return {'remove_story': world_id, 'result': f"remove {story_id} ok"}

    def set_current_story_id(self, *args, **kwargs):
        return [ JournalStoryUpdate( **{'text': 'You are in a totally different world.',
                                        'uid': uuid.uuid4(),
                                        'label': 'story 2, block1',
                                        'actions': [{'uid': uuid.uuid4(),
                                                     'text': 'How did you get here?'}]} ) ]

    def create_story(self, *args, **kwargs) -> JournalEntry:
        return [ JournalStoryUpdate( **{'text': 'You are in a totally different story.',
                                        'uid': uuid.uuid4(),
                                        'label': 'story 3, block1',
                                        'actions': [{'uid': uuid.uuid4(),
                                                     'text': 'How did you get here?'}]} ) ]


    # === World services ===
    # --- Public ---

    def get_world_info(self, *args, **kwargs) -> WorldInfo:
        return WorldInfo(
            label="sample world",
            text="info"
        )

    def get_world_list(self) -> WorldList:

        worlds_data = [
            {'key': 'Sample World',
             'value': 'sample_world',
             'style_dict': {'color': "blue"}
             },
            {'key': 'A Different World',
             'value': 'different_world',
             'style_dict': {'color': "green"}
             }
        ]

        return [ KVItem(**data) for data in worlds_data ]


    # --- Dev ---

    def get_scene_list(self, *args, **kwargs) -> WorldSceneList:
        scene_data = [
            {'key': 'Sample Scene',
             'value': 'sample_scene'}
        ]

        return [KVItem(**data) for data in scene_data]

    # === System services ===
    # --- Public ---

    def get_system_info(self) -> SystemInfo:
        # just pass this through
        return super().get_system_info()

    # --- Dev ---

    @staticmethod
    def reset_system(hard=False):
        return {f"resetting system ({hard})": "ok"}


@pytest.fixture
def mock_service_manager():
    return MockServiceManager()

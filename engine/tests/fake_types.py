from uuid import uuid4
from tangl.service.api_endpoints import AccessLevel

class FakeWorld:
    """
    Minimal imitation of 'World'.
    Has label, name, and static tracking of instances in a dict.
    """
    _instances = {}

    def __init__(self, label, name):
        self.label = label
        self.name = name
        self.media_registry = FakeMediaRegistry()

    @classmethod
    def get_instance(cls, world_id):
        """
        Mimic the real World.get_instance. If not found, create a dummy world or raise error.
        """
        if world_id not in cls._instances:
            cls._instances[world_id] = FakeWorld(label=world_id, name=f"FakeWorld-{world_id}")
        return cls._instances[world_id]

    @classmethod
    def clear_instance(cls, label):
        if label in cls._instances:
            del cls._instances[label]

    @classmethod
    def all_instances(cls):
        return list(cls._instances.values())

    def get_info(self, **kwargs):
        return {"label": self.label, "name": self.name, "extra": kwargs}

    def create_story(self, user=None, **kwargs):
        # Return a stub story object
        return FakeStory(uid=f"story-{self.label}", user=user)

class FakeUser:
    def __init__(self, uid, access_level=AccessLevel.USER, current_story_id=None):
        self.uid = uid
        self.access_level = access_level
        self.current_story_id = current_story_id
        self.story_ids = []

    def add_story(self, story_id):
        self.story_ids.append(story_id)
        self.current_story_id = story_id


class FakeJournal(list):
    """A simple subclass of list to mimic a story's journal."""
    pass

class FakeNode:
    """Represents a story node, with a 'dirty' flag and a 'model_dump' method."""
    def __init__(self, alias=None):
        self.alias = alias
        self.dirty = False

    def model_dump(self):
        # Return a minimal dictionary representation
        return {"alias": self.alias, "dirty": self.dirty}

class FakeEdge:
    """Mimics a TraversableEdge with predecessor/successor nodes."""
    def __init__(self, predecessor=None, successor=None):
        self.predecessor = predecessor
        self.successor = successor

class FakeStory:
    """
    A minimal imitation of the 'Story' domain object.
    - Has a journal (list of entries)
    - A 'cursor' node
    - A 'dirty' boolean
    - find_one(...) for edges, nodes, media, etc.
    - gather_context() for check_condition, apply_effect, etc.
    - do_step(...) or resolve_step(...) to manipulate the story state
    """

    def __init__(self, uid = None, user = None):
        self.journal = FakeJournal(["entry0", "entry1", "entry2"])
        self.dirty = False
        self.cursor = FakeNode(alias="start")
        self.nodes = {
            "node1": FakeNode(alias="node1"),
            "edgeX": FakeEdge(),
            "mediaX": FakeMediaRecord("mediaX"),
        }
        self.uid = uid or uuid4()
        self.user = user  # might be a FakeUser or just user_id

    def get_info(self, **kwargs):
        # Return content-like data, you can mimic your real story logic
        return {"info": "FakeStory Info", "kwargs": kwargs}

    def find_one(self, alias=None):
        return self.nodes.get(alias)

    def resolve_step(self, edge, **kwargs):
        # Just mark the story dirty or do minimal logic
        self.dirty = True
        self.cursor = edge.successor or self.cursor

    def gather_context(self):
        return {"story_state": "demo"}

class FakeMediaRecord:
    """Mimics a media record."""
    def __init__(self, alias):
        self.alias = alias

    def get_content(self, **kwargs):
        return f"Media content for {self.alias} with {kwargs}"

# The "AnonymousEdge" is basically the same as FakeEdge with a different name
FakeAnonymousEdge = FakeEdge


class FakeMediaRegistry:
    """
    If your real 'world.media_registry' has a 'find_one' method, we mimic it here.
    """

    def find_one(self, alias):
        return FakeMediaRecord(alias)


from contextlib import contextmanager

from tangl.type_hints import Uid
from tangl.persistence import PersistenceManager

class StoryPersistenceManager(PersistenceManager):
    """
    Manager for persisting and managing graph-based data structures.

    Extends the generic PersistenceManager with additional functionality to handle
    Story-specific structuring.

    Provides methods to open and manage story data within a context manager, handling
    user-story associations and optional write-backs.
    """

    @contextmanager
    def open_story(self, user_id: Uid = None, story_id: Uid = None, write_back: bool = False):
        """
        Context manager for opening a story and writing any changes back if indicated.

        The user is associated and disassociated because they may be attached to multiple different stories.
        """

        if user_id is not None:
            with self.open(user_id, write_back=write_back) as user:
                if story_id is not None and story_id != user.current_story_id:
                    raise RuntimeError("Requested story is not the user's current story!")
                elif story_id is None:
                    story_id = user.current_story_id
                with self.open(story_id, write_back=write_back) as story:
                    story.user = user  # reassociate the user
                    yield story
                    story.user = None  # disassociate the user

        elif story_id is not None:

            with self.open(story_id, write_back=write_back) as story:
                if user_id is not None and user_id != story.user_id:   # pragma: no cover
                    # it is impossible to hit this clause given the current control flow
                    raise RuntimeError("Requesting user is not the story owner!")
                elif user_id is None:
                    user_id = story.user_id
                with self.open(user_id, write_back=write_back) as user:
                    story.user = user  # reassociate the user
                    yield story
                    story.user = None  # disassociate the user

        else:

            raise TypeError("Must call with at least one of story_id or user_id!")

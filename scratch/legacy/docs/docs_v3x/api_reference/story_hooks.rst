
Story Hooks
------------

Story handler methods can be hooked by registering a function by task id with a custom handler.

- :code:`on_create_story`: When a new story is instantiated for a world
- :code:`on_get_story_status`: When the story status is requested
- :code:`on_do_action`: When an action is executed for a story

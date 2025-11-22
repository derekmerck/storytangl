from pydantic import BaseModel, Field

from tangl.story.scene import BlockScript

TaskScript = BaseModel

# todo: how do we indicate these are allowed block types in the story script schema?
# todo: how do we indicate that "task" field discriminates Activities from other types of Blocks?

class ActivityScript(BlockScript):
    task: TaskScript

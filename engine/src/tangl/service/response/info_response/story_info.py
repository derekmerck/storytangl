from tangl.journal.content import KvFragment

from tangl.service.response import BaseResponse

# This can be whatever the author wants...
class StoryInfo(BaseResponse):
    info: KvFragment = None

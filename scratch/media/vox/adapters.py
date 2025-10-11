
from __future__ import annotations
from enum import Enum

from tangl.story.actor.vocals import Vocals
# this provides the voice parameters and/or model

def vocals_to_kwargs(vocals: Vocals):
    res = vocals.model_dump()
    res = { k: v.value.lower() if isinstance(v, Enum) else v for k, v in res.items()}
    return res

# def spoken_to_kwargs(spoken: Spoken):
#     res = spoken.model_dump()
#     res = { k: v.value.lower() if isinstance(v, Enum) else v for k, v in res.items()}
#     return res

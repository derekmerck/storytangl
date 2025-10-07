from collections import UserDict
import random

import attr

from tangl.story.actor import Actor
from .credentialed import Credentialed
from .enums import Outcome


class ScreeningResponses(UserDict[Outcome, list[str]]):

    def __getitem__(self, k) -> str:
        k = Outcome(k)
        res = super().__getitem__(k)
        if isinstance(res, list) and len(list) == 1:
            return res[0]
        elif isinstance(res, list):
            return random.choice( res )
        else:
            return res

    def __setitem__(self, k, v):
        if v is not None:
            k = Outcome(k)
            super().__setitem__(k, v)


DEFAULT_RESPONSES = {
    'wrong seal': None,
    'forged credential': ["That cannot be possible!"],
    'wrong holder': ["That is my id!"],
    'concealed contraband': ["That is not mine!"],
    'blacklisted': ["That is not me!"],
    'crime': ["There must be some mistake!"],

    'missing seal': [],
    'bad issue date': [],
    'expired': [],
    'bad credential': [],
    'missing credential': [],
    'declined mediation': ["I refuse."],
    'deny': ["You should reconsider."],

    'possible wrong holder': ["I changed my hair recently..."],
    'possible missing credential': ["I have it right here."],
    'possible concealed contraband': ["You won't find anything."],
    'mediation': [],

    'accept': ['Of course.']
}

@define
class ScreeningCandidate(Credentialed, Actor):

    responses: ScreeningResponses = attr.ib()

    def response(self, inspection: Outcome):
        return self.responses[inspection]

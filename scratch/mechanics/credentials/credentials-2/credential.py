from __future__ import annotations
import random
from enum import Enum, auto

from pydantic import Field, model_validator, PrivateAttr

from tangl.entity.mixins import RenderHandler
from tangl.graph import Node
from tangl.graph.mixins import WrappedSingleton
from tangl.story.asset import AssetType
from tangl.type_hints import Uid, Turn

from .enums import Region, Indication, Presentation
from .seal import Seal


class CredentialStatus(Enum):
    VALID = auto()

    # Invalid
    EXPIRED = auto()
    BAD_ISSUE_DATE = auto()
    MISSING_SEAL = auto()
    HOLDER_MISMATCH = auto()  # valid id, wrong permit ref

    # Criminal
    BAD_SEAL = auto()         # forged
    WRONG_ID_HOLDER = auto()  # possible invalid id (only for id)

    @classmethod
    def for_presentation(cls,
                         presentation: Presentation,
                         requires_id: bool = False):
        match presentation:
            case Presentation.INVALID_CREDENTIAL:
                candidates = [ CS.EXPIRED,
                               CS.BAD_ISSUE_DATE,
                               CS.MISSING_SEAL ]
                if requires_id:
                    candidates.append( CS.HOLDER_MISMATCH )
                return random.choice( candidates )
            case Presentation.FORGED_CREDENTIAL:
                return CS.BAD_SEAL
            case Presentation.WRONG_ID_HOLDER:
                return CS.WRONG_ID_HOLDER

CS = CredentialStatus



class CredentialHandler:

    @classmethod
    def is_valid(cls, credential: Credential) -> bool:
        ...


class CredentialType(AssetType):
    """
    Credentials do not carry specific features like holder name or expiry
    date as internal variables.  They only reference or compute those values
    when requested.

    Setting a specific invalidation flag on creation will _present_ an invalid
    credential.  But the underlying credential object will be the same.  Thus,
    most credentials do not need to be recreated ('evolved') if they are updated
    to include errors.

    Credentials wrap CredentialType SingletonEntities, just as Wearables wrap
    WearableType.  The CredentialPacket manager serves a similar role as the
    Outfit manager does for delegating credential management to a separate handler.
    """

    indication: Indication         # None is not valid!
    valid_period: Turn = 10        # 0 = today only
    # base_image: MediaResource = None
    req_id: bool = False           # requires id

    # A particular credential instance may have an invalidation
    credential_status: CS = Field( CS.VALID, json_schema_extra={'instance_var': True} )

    @property
    def holder(self) -> Node:
        return self._holder or self.parent

    _holder: Node = PrivateAttr(None)

    @model_validator(mode='after')
    def _mk_holder(self):
        if self.credential_status is CS.WRONG_ID_HOLDER:
            # Create a random holder
            from .credential_packet import Credentialed
            wrong_holder = Credentialed()
            self._holder = wrong_holder
        return self

    issuer_: Region = Field( Region.LOCAL, json_schema_extra={'instance_var': True} )
    @property
    def issuer(self):
        return self.issuer_

    issued_turn: Turn = Field(None)

    @model_validator(mode='after')
    def _mk_issued_turn(self):
        """
        Generate a issue turn within the valid period given the current turn.

        If CS.EXPIRED, the issue turn is randomly set back a few turns before
        the earliest valid issue turn.

        If CS.BAD_ISSUE_DATE, the issue turn is set to a turn in the future.
        """

        def _get_current_turn():
            try:
                return self.story.turn
            except AttributeError:
                return 1

        def _turns_since_issued():
            turns = 0
            if self.credential_status is CS.BAD_ISSUE_DATE:
                # a turn in the future
                turns = - random.randint(1, 5)
            elif self.credential_status is CS.EXPIRED:
                # before the earliest valid turn
                turns += (self.valid_period + random.randint(1, 5))
            elif self.valid_period > 1:
                turns = random.randint(0, self.valid_period)
            return turns

        self.issued_turn = _get_current_turn() - _turns_since_issued()
        return self

    @property
    def expiry_turn(self):
        turn = self.issued_turn + self.valid_period
        return turn

    @property
    def seal(self):
        return Seal.type_for(self.issuer, self.indication, self.credential_status)

    # from tangl.media import JournalMediaItem
    # def get_media(self) -> JournalMediaItem:
    #     base_im =

    @RenderHandler.strategy
    def _render(self, **kwargs) -> dict:
        res = {
            "credential_type": self.__class__.__name__,
            "credential_id": self.guid2credential(self.guid),
            "issuer": self.issuer,
            "media": {
                # todo: - These should be RIT's
                #       - The seal should be assigned a temporary url that obfuscates its status
                #       - The credential could be flattened into a single image
                "seal": { "url": self.seal2image( self.seal ) },
                "base_image": { "url": self.base_image or "NONE" },
                "holder_photo": {},
            },
            "issued": self.turn2date(self.issued_turn),
        }
        if self.req_id:
            res['holder_id'] = self.holder.id_card.credential_id
        if self.valid_period > 0:
            res["expiry"] = self.turn2date(self.expiry_turn)

        return res

    @staticmethod
    def turn2date(turn: Turn) -> str:
        return f"Day {turn}"

    @staticmethod
    def guid2credential(guid: Uid) -> str:
        return str(guid)

    @staticmethod
    def seal2image(seal: Seal) -> str:
        return repr(seal)

CredentialType.load_instances_from_yaml("tangl.mechanics.credentials.resources", "default_credential_types.yaml")
Credential = WrappedSingleton.create_wrapper_cls('Credential', CredentialType)

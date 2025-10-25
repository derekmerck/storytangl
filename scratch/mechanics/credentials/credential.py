from __future__ import annotations
import functools
from typing import *
import random

import attr

from .enums import Region, Indication, Seal, Move, Outcome
from .restrictions import RestrictionLevel as RL
from .utils import turn2date, guid2credential, seal2image


@attr.define
class Credential:
    """
    Credentials do not carry specific features like holder name or expiry
    date as internal variables.  They only reference or compute those values
    when requested.

    Setting a specific invalidation flag on creation will _present_ an invalid
    credential.  But the underlying credential object will be the same.  Thus,
    most credentials do not need to be recreated ('evolved') if they are updated
    to include errors.
    """

    # class vars
    valid_period: ClassVar[int] = 10
    base_image: ClassVar = None
    req_id: ClassVar[bool] = False
    indication: ClassVar[Indication|None] = None

    _issuer: Region = Region.LOCAL

    # hint
    hidden: bool = False

    # invalidations
    bad_issue_date: bool = False
    expired: bool = False
    missing_seal: bool = False

    # crimes
    wrong_holder: bool = False
    wrong_seal: bool = False

    _holder: 'Credentialed' = None

    @property
    def holder(self) -> 'Credentialed':
        from .credentialed import Credentialed
        # generate a random holder
        if self.wrong_holder:
            return Credentialed()
        return self._holder

    @property
    def issuer(self) -> Region:
        return self._issuer

    @property
    def issued(self) -> int:

        def _get_turn():
            try:
                return self.story.turn
            except AttributeError:
                return 1

        def _turns_since_issued():
            turns = 0
            if self.valid_period > 1:
                turns = random.randint(1, self.valid_period)
            if self.expired:
                turns += random.randint(1, 5)
            return turns

        turn_ = _get_turn()
        if self.bad_issue_date:
            # a future date
            turn = turn_ + random.randint(1, 5)
        else:
            turn = turn_ - _turns_since_issued()
        return turn

    @property
    def expiry(self):
        turn = self.issued + self.valid_period
        return turn

    @property
    def seal(self):
        if self.missing_seal:
            return Seal.NONE
        return Seal.type_for(self.issuer, self.indication, not self.wrong_seal)

    def render(self, **kwargs) -> dict:
        res = super().render(**kwargs)
        res |= {
            "credential_type": self.__class__.__name__,
            "credential_id": guid2credential(self.guid),
            "issuer": self.issuer,
            "seal_image": seal2image( self.seal ),
            "base_image": self.base_image,
            "issued": turn2date(self.issued),
        }
        if self.valid_period > 0:
            res["expiry"] = turn2date(self.expiry)
        if self.req_id:
            res["holder_id"] = guid2credential(self.holder.id_card.guid)

        return res

    def get_moves(self) -> list[Move]:
        moves = [Move.INSPECT_SEAL, Move.INSPECT_ISSUER, Move.INSPECT_ISSUE_DATE]
        if self.req_id:
            moves.append( Move.INSPECT_HOLDER_ID )
        if self.valid_period > 0:
            moves.append( Move.INSPECT_EXPIRY )
        return moves

    def inspect(self, move: Move):
        # this sets the current justification state for the game round
        # this need to match the expected candidate outcome for the
        # final decision to be considered 'appropriate'.
        match move:

            # DENY credentialing problems
            case Move.INSPECT_SEAL if self.missing_seal:
                return Outcome.BAD_CREDENTIAL
            case Move.INSPECT_ISSUE_DATE if self.bad_issue_date:
                return Outcome.BAD_CREDENTIAL
            case Move.INSPECT_EXPIRY if self.expired:
                return Outcome.BAD_CREDENTIAL

            # CRIME credentialing problems
            case Move.INSPECT_SEAL if self.invalid_seal:
                return Outcome.FORGED_CREDENTIAL

            # MEDIATE credentialing problems
            # These shift the state to mediate and enable mediation
            # actions, i.e., VALIDATE_HOLDER or REQUEST_CREDENTIAL
            case Move.INSPECT_HOLDER_DETAIL if \
                  (self.parent.outcome in [Outcome.WRONG_HOLDER, Outcome.POSSIBLE_WRONG_HOLDER]):
                return Outcome.POSSIBLE_MISSING_CREDENTIAL
            case Move.INSPECT_HOLDER_ID if self.parent.outcome in [Outcome.MISSING_CREDENTIAL, Outcome.POSSIBLE_MISSING_CREDENTIAL]:
                return Outcome.POSSIBLE_WRONG_HOLDER

        return Outcome.NO_ERROR

    @classmethod
    def cls_for(cls, indication: Indication, restriction: RL) -> Type['Credential'] | None:
        match (indication, restriction):
            case _, RL.ALLOWED | RL.FORBIDDEN:
                return None
            case Indication.TRAVEL, RL.WITH_ANON:
                return AnonTravelPermit
            case Indication.TRAVEL, RL.WITH_PERMIT:
                return TravelPermit
            case Indication.WORK, RL.WITH_PERMIT:
                return WorkPermit
            case Indication.EMIGRATE, RL.WITH_ANON:
                return AsylumPetition
            case Indication.EMIGRATE, RL.WITH_PERMIT:
                return EmigrationPermit

            case Indication.WEAPON, RL.WITH_PERMIT:
                return WeaponPermit
            case Indication.DRUGS, RL.WITH_PERMIT:
                return DrugPermit
            case Indication.SECRETS, RL.WITH_ANON:
                return AnonSecretsPermit
            case Indication.SECRETS, RL.WITH_PERMIT:
                return SecretPermit
        raise TypeError(f"No credential type for {indication}, {restriction}")

@define
class AnonTravelPermit(Credential):

    valid_period: ClassVar = 0
    base_image: ClassVar = None
    indication: ClassVar[Indication] = Indication.TRAVEL

Ticket = AnonTravelPermit

@define
class AnonEmigrationPermit(Credential):

    valid_period: ClassVar = 30
    base_image: ClassVar = None
    indication: ClassVar[Indication.EMIGRATE] = Indication.TRAVEL


AsylumPetition = AnonEmigrationPermit

@define
class AnonSecretsPermit(Credential):

    valid_period: ClassVar = 0
    base_image: ClassVar = None
    indication: ClassVar[Indication] = Indication.SECRETS


SecureTicket = AnonSecretsPermit


@define
class IdCard(Credential):
    # can be local or foreign, needs different images and seals for each

    # 300 = 3 centuries = 1 year
    valid_period: ClassVar = 300

    @property
    def issuer(self):
        return self.holder.region

    def _possible_moves(self) -> list[Move]:
        res = super()._possible_moves()
        res.append( Move.INSPECT_HOLDER_DETAIL )
        return res

    def render(self, **kwargs) -> dict:
        res = super().render(**kwargs)
        res |= {
            "holder_id": guid2credential( self.holder.guid ),
            # "holder_name": self.holder.name,
            "holder_image": self.holder.credential_image(),
            "holder_text": self.holder.credential_text()
        }
        return res

@define
class Permit(Credential):

    # 100 days = 1 century = 10 decades
    valid_period: ClassVar = 100
    req_id: ClassVar[bool] = True

    def render(self, **kwargs) -> dict:
        res = super().render(**kwargs)
        res |= {
            "holder_id": guid2credential( self.holder.guid ),
            "holder_name": self.holder.name,
        }
        return res


@define
class TravelPermit(Permit):

    indication: ClassVar[Indication] = Indication.TRAVEL



Visa = TravelPermit


@define
class WorkPermit(Permit):

    indication: ClassVar[Indication] = Indication.WORK


@define
class EmigrationPermit(Permit):

    valid_period: ClassVar = 1000
    indication: ClassVar[Indication] = Indication.EMIGRATE


# Contraband

@define
class WeaponPermit(Permit):

    indication: ClassVar[Indication] = Indication.WEAPON



@define
class DrugPermit(Permit):

    indication: ClassVar[Indication] = Indication.DRUGS


MedicalId = DrugPermit


@define
class SecretPermit(Permit):

    indication: ClassVar[Indication] = Indication.SECRETS


DiplomaticId = SecretPermit

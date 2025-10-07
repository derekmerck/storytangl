from __future__ import annotations
from typing import *
import random

import attr

from .enums import Region, Indication, Move, Outcome
from .restrictions import Restrictions, RestrictionLevel as RL
from .credential import Credential, IdCard


if TYPE_CHECKING:
    from tangl.story.actor import Actor as Actor_
else:
    Actor_ = object


    @define
    class Credentialed(Actor_):
        """
        Mixin for Actors carrying credential packets.

        Key extra parameters for credentialing are:
          - region
          - purpose
          - contraband

        At each screening scene, credentials will be regenerated with appropriate
        credentials given the current story restrictions.

        Passing in an outcome (crime, hint, or invalidation) flag will update the
        credential packet accordingly.
        """

        region: Region = Region.LOCAL
        purpose: Indication.PURPOSE = Indication.TRAVEL
        contraband: Indication.CONTRABAND | None = None

        outcome: Outcome = Outcome.NO_ERROR
        hidden_contraband: bool = False  # any contraband is initially hidden
        searched: bool = False  # candidate has been searched for contraband

        id_card: IdCard = attr.ib()

        @id_card.default
        def _mk_id_card(self):
            # generate and stash a single proper id card, for consistency
            return IdCard(parent=self)

        credentials: set[Credential] = attr.ib(factory=set)

    def get_restrictions(self) -> Restrictions:
        """This has to retrieve the restrictions on the current scene, or
           it will use default restrictions"""

        DEFAULT_RESTRICTIONS = {
            'travel': 'allowed',
            'work': 'with permit',
            'emigrate': 'with anon',
            'weapon': 'with permit',
            'drugs': 'forbidden',
            'secrets': 'with permit' }

        return Restrictions(DEFAULT_RESTRICTIONS)

    def generate_credentials(self,
                             restrictions: Restrictions = None,
                             outcome: Outcome = None):
        """
        This is the complex bit of the screening scenario generation.
        Adding a new invalidation type requires thinking through how to
        invalidate a packet appropriately.

        - pass restrictions in, or access them from an internal mechanism
        - passing in a new outcome will override the current outcome
        - outcomes may be indicated at any level of generalization and
          will be specified as possible within categories

        Note, credentials are _never_ tested against restrictions, instead
        credentials are _created_ to pass or violate specific restrictions.
        """

        if not restrictions:
            restrictions = self.get_restrictions()
        if self.region in restrictions:
            restrictions = restrictions[self.region]

        if outcome:
            # setting new
            self.outcome = outcome
        else:
            # using as generated
            outcome = self.outcome

        self.credentials.clear()

        # generate a default proper packet
        for indication, restriction in restrictions.items():
            if indication is self.purpose or indication is self.contraband:
                if restriction is RL.WITH_ID:
                    self.credentials.add( self.id_card )
                else:
                    # this indication applies to my purpose or contraband
                    credential_type = Credential.cls_for(indication, restriction)
                    if credential_type:
                        cr = credential_type(parent=self)
                        self.credentials.add( cr )
                        if cr.req_id:
                            # at least one credential requires an id card
                            self.credentials.add( self.id_card )

        # determine if there is any disallowed contraband for dropping permits,
        # carrying forbidden, or carrying hidden
        disallowed_contraband = [k for k, v in restrictions.items() if
                                 k == Indication.CONTRABAND and v is not RL.ALLOWED]

        # disallowed_purposes =   [k for k, v in restrictions.items() if
        #                          k in Indication.PURPOSE and v is not RL.ALLOWED]

        # CRIMES

        def _wrong_id_holder():
            # carrying a bogus id card
            # todo: permits should reference this id as well?
            # raises if called without having an id requirement
            if self.id_card not in self.credentials:
                raise RuntimeError
            self.credentials.remove(self.id_card)
            cr = attr.evolve(self.id_card, wrong_holder=True)
            self.credentials.add(cr)

        def _forged_credential():
            # credential with fake seal
            s = random.choice(tuple(self.credentials))  # type: Credential
            s.wrong_seal = True

        def _unpermitted_contraband():
            # find a forbidden contraband and discard contraband permits
            # raises if called without any currently disallowed contraband
            if not disallowed_contraband:
                raise RuntimeError

            if self.contraband in disallowed_contraband:
                pass
            elif len(disallowed_contraband) > 1:
                self.contraband = random.choice(disallowed_contraband)
            else:
                self.contraband = disallowed_contraband[0]

            for s in self.credentials:
                if s.indication is self.contraband:
                    self.credentials.remove(s)

        def _hidden_contraband():
            self._unpermitted_contraband()
            self.hidden_contraband = True

        def _blacklisted():
            # add holder to restriction blacklist, crime
            # todo: how to reference?
            pass

        def _whitelisted():
            # add holder to restriction whitelist
            # todo: how to reference?
            pass

        def _crime():
            # forged credential (which, deal with id?)
            # blacklist
            # wrong holder
            # hidden contraband

            which = outcome.specify()
            if not disallowed_contraband:
                while which is Outcome.HIDDEN_CONTRABAND:
                    which = outcome.specify()

            match which:
                case Outcome.FORGED_CREDENTIAL:
                    _forged_credential()
                case Outcome.WRONG_ID_HOLDER:
                    _wrong_id_holder()
                case Outcome.BLACKLISTED:
                    _blacklisted()
                case Outcome.HIDDEN_CONTRABAND:
                    _hidden_contraband()
                case _:
                    raise RuntimeError

        # INVALIDATIONS

        def _bad_credential():
            # unsealed, bad date, or expired credential
            # grab a random credential and edit it

            s = random.choice(tuple(self.credentials))  # type: Credential
            which = outcome.specify()
            if isinstance(s, IdCard) or not s.req_id:
                # no holder mismatch for id cards (crime) or anon
                while which is Outcome.HOLDER_MISMATCH:
                    which = outcome.specify()

            match which:
                case Outcome.BAD_ISSUE_DATE:
                    s.bad_issue_date = True
                case Outcome.EXPIRED:
                    s.expired = True
                case Outcome.MISSING_SEAL:
                    s.missing_seal = True
                case Outcome.HOLDER_MISMATCH:
                    s.wrong_holder = True
                case _:
                    raise RuntimeError

        def _missing_id():
            if self.id_card in self.credentials:
                self.credentials.remove(self.id_card)
            else:
                raise RuntimeError

        def _missing_credential():
            # a missing credential must be requested to be approved
            s = random.choice(tuple(self.credentials))
            self.credentials.remove(s)

        def _deny():
            # missing credential (which)
            # bad credential (which, how, deal with id?)
            # forbidden contraband

            which = outcome.specify()
            if not disallowed_contraband:
                while which is Outcome.FORBIDDEN_CONTRABAND:
                    which = outcome.specify()

            match which:
                case Outcome.MISSING_ID:
                    _missing_id()
                case Outcome.FORBIDDEN_CONTRABAND:
                    _unpermitted_contraband()
                case Outcome.MISSING_PERMIT:
                    _missing_credential()
                case Outcome.BAD_CREDENTIAL:
                    _bad_credential()
                case _:
                    raise RuntimeError(f"No strategy for {which}")

        # MEDIATIONS

        def _possible_missing_credential():
            # grab a random credential and _hide_ it
            # todo: figure out if the id is supposed to be missing
            s = random.choice(tuple(self.credentials))
            s.hidden = True

        def _possible_wrong_id_holder():
            # the holder must be validated to be approved
            # adjust the _avatar_ with a minor discrepancy such as hair color
            # raises if called without having an id requirement
            if self.id_card not in self.credentials:
                raise RuntimeError
            pass

        def _mediation():
            # possible missing credential
            # possible wrong holder

            which = outcome.specify()

            match which:
                case Outcome.POSSIBLE_MISSING_CREDENTIAL:
                    _possible_missing_credential()
                case Outcome.POSSIBLE_WRONG_ID_HOLDER:
                    _possible_wrong_id_holder()
                case _:
                    raise RuntimeError

        # can pass in various levels of specificity:
        # crime or crime/forged_credential or crime/forged_credential/forged_permit
        match outcome:
            case x if x in Outcome.CRIME:
                _crime()

            case x if x in Outcome.DENY:
                _deny()

            case x if x in Outcome.MEDIATE:
                _mediation()

            case Outcome.WHITELISTED:
                # todo: this isn't useful like this, typically you want to
                #       whitelist someone who is otherwise not allowed
                _whitelisted()

            case x if x in Outcome.ACCEPT:
                # no error
                pass

            case _:
                raise RuntimeError

    def get_moves(self) -> list[Move]:

        # for move in Move:
        #     match move, outcome:
        #         # mediations
        #         case Move.REQ_MISSING_PERMIT, Outcome.POSSIBLE_MISSING_CREDENTIAL:
        #             return True
        #         case Move.VALIDATE_HOLDER_ID, Outcome.POSSIBLE_WRONG_ID_HOLDER:
        #             return True
        #         case Move.SEARCH_CANDIDATE, _ if candidate.searched == False:
        #             return True
        #
        # # indications

        moves = [ Move.REQ_SEARCH, Move.INSPECT_BLACKLIST, Move.INSPECT_PURPOSE ]
        # todo: not right -- contraband is _currently_hidden_, but it may have been smuggled originally
        if self.contraband and not self.hidden_contraband:
            moves.append( Move.INSPECT_CONTRABAND )
        return moves

    def credential_image(self, **kwargs):
        # id portrait
        pass

    def credential_text(self):
        # height, weight, etc.
        pass

    def render(self, **kwargs):
        # actions are not injected here b/c this class only knows about moves
        try:
            res = super().render(**kwargs)
        except AttributeError:
            res = {}
        res |= {
            "credentials": [ c.render(**kwargs) for c in self.credentials ],
            # "avatar_image": self.avatar_image(**kwargs)
        }
        return res

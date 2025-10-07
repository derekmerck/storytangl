"""
Todo -- update to follow Wearable/OutfitManager paradigm
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import model_validator

from tangl.entity.mixins import RenderHandler
from tangl.story.story import StoryNode

from .enums import Indication, Presentation, Outcome, Region, RegionalRestrictionMaps
from .credential import Credential, CS
# from .id_card import IdCard

IdCard = object


class PacketHandler:

    @classmethod
    def is_valid(cls, packet: PacketManager):
        return all([x.is_valid for x in packet.credentials])


class Credentialed(StoryNode):
    """
    Mixin for Actors carrying credential packets.

    Key extra parameters for credentialing are:
      - region
      - purpose
      - contraband

    In the factory method, passing in an outcome (arrest, deny, allow)
    and a set of restrictions will create an appropriate presentation and
    credential packet status, if possible.
    """
    region: Region = Region.LOCAL
    purpose: Indication = Indication.TRAVEL
    contraband: Indication | None = None

    expected_outcome: Outcome = Outcome.ALLOW
    # presentation is selected based on the expected outcome
    presentation: Presentation = Presentation.NO_PROBLEMS
    # credential packet status is selected based on the presentation
    credential_status: CS = CS.VALID

    @property
    def credentials(self) -> list[Credential]:
        return self.find_children(Credential)

    @property
    def id_card(self) -> IdCard:
        return self.find_child(IdCard)

    @property
    def credential_packet(self) -> PacketManager:
        return PacketManager(self)

    @RenderHandler.strategy
    def _render_credential_packet(self):
        return {'credentials': self.credential_packet.render()}


class PacketManager:

    def __init__(self, node: Credentialed):
        self.node = node
        super().__init__()

    @property
    def credentials(self) -> list[Credential]:
        return self.node.credentials

    # @model_validator(mode='after')
    # def _validate_outfit(self):
    #     PacketHandler.validate_packet(*self.credentials)
    #     return self

    # todo: are these mu-blocks/cards?
    def render(self) -> list[dict]:
        return [ x.render() for x in self.credentials ]





    # this is in the encounter state?
    hidden_contraband: bool = False  # any contraband is initially hidden
    id_verified: bool = False        # candidate has verified id
    searched: bool = False           # candidate has been searched for contraband



    @classmethod
    def create_credentialed_candidate(cls,
                                      outcome: Outcome = None,
                                      presentation: Presentation = None,
                                      credential_status: CS = None,
                                      indication: Indication = None,
                                      region: Region = None,
                                      regional_restriction_map: RegionalRestrictionMaps = None) -> Credentialed:

        # If there is no outcome
        if outcome is None:
            # If there is no presentation, infer presentation from credential status
            if presentation is None and credential_status is not None:
                presentation = credential_status.get_presentation()
            # Infer outcome from presentation
            if presentation is not None:
                outcome = presentation.get_outcome()

        # If there is no presentation
        if presentation is None:
            # If there is no credential status, get the possible presentations given the outcome
            if credential_status is None and outcome is not None:
                presentations = outcome.get_possible_presentations()
            # Infer the presentation from the credential status
            elif credential_status is not None:
                presentation = credential_status.get_presentation()

        # If there is no credential status
        if credential_status is None:
            # Check each of the possible presentations to see if it can be satisfied by the current restrictions
            for potential_presentation in presentations:
                if potential_presentation.satisfies_restriction(regional_restriction_map, region):
                    presentation = potential_presentation
                    break
            # Pick a credential status, indication (and region if applicable) that is satisfyable
            credential_status = presentation.get_credential_status()
            indication = presentation.get_indication()
            region = presentation.get_region()

        # Create a CredentialedMixin instance with the specified attributes
        candidate = cls(
            region=region,
            purpose=indication,  # Assuming the Indication serves as the purpose of the candidate
            contraband=None,  # Assuming contraband is not determined by this function
            expected_outcome=outcome,
            presentation=presentation,
            credential_status=credential_status
        )

        return candidate


from __future__ import annotations
from typing import Type
from enum import Enum

from tangl.media.media_spec import MediaSpecification
from tangl.media.type_hints import Image
from tangl.mechanics.credential.credential import Credential, CredentialType, Region, Indication
from tangl.mechanics.credential.credential_packet import Credentialed

class CredentialMediaRoles(Enum):

    BASE_IM = "base_im"
    SEAL_IM = "seal_im"
    TEXT_IM = "text_im"
    HOLDER_IM = "holder_im"


class CredentialMediaSpec(MediaSpecification, arbitrary_types_allowed = True):
    # implements media spec
    credential: Credential

    def realize(self,
                node: Credential = None,
                missing_seal: bool = False,
                invalid_seal: bool = False,
                wrong_holder: bool = False,
                invalid_date: bool = False) -> CredentialMediaSpec:
        # evolve a new credential with the given overrides
        ...

    @classmethod
    def get_forge(cls, **forge_kwargs) -> Type[CredentialForge]:
        return CredentialForge


class CredentialForge:
    # Implements MediaForge

    @classmethod
    def create_ticket(cls,
                      issue_date: str,
                      seal: Image | None,
                      issuer: Region = Region.LOCAL,
                      indication: Indication = Indication.TRAVEL) -> Image:
        # anonymous, no id field
        ...

    @classmethod
    def create_id_card(cls,
                       holder_id: str,
                       issue_date: str,
                       expiry_date: str,
                       seal: Image | None,
                       holder_photo: Image,
                       holder_info: dict[str] = None,
                       issuer: Region = Region.LOCAL) -> Image:
        # includes id portrait frame
        ...

    @classmethod
    def create_permit(cls,
                      holder_id: str,
                      issue_date: str,
                      expiry_date: str,
                      seal: Image | None,
                      issuer: Region = Region.LOCAL,
                      indication: Indication = Indication.TRAVEL) -> Image:
        # includes field for holder id
        ...

    # ------------

    @classmethod
    def create_ticket_for(cls, candidate: Credentialed) -> Image:
        kwargs = {}  # parse candidate situation
        im = cls.create_ticket(**kwargs)
        return im


    @classmethod
    def create_id_card_for(cls, candidate: Credentialed) -> Image:
        kwargs = {}  # parse candidate situation
        im = cls.create_id_card(**kwargs)
        return im

    @classmethod
    def create_permit_for(cls, candidate: Credentialed) -> Image:
        kwargs = {}  # parse candidate situation
        im = cls.create_permit(**kwargs)
        return im

    # -------------

    def create_media(self, media_spec: CredentialMediaSpec, **kwargs) -> tuple[Image, CredentialMediaSpec]:
        # returns the media and a possibly revised spec
        ...

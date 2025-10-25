from pydantic import BaseModel

from tangl.core.graph import Node
from tangl.story.asset import DiscreteAsset

from .enums import CredStatus, CredDisposition

class Demographic:
    ...

class CredentialManager:
    ...


class Credential(DiscreteAsset):
    ...


class HasCredentials(BaseModel):

    demographic: Demographic
    credential_status: CredStatus = CredStatus.OK


    @property
    def credentials(self: Node) -> list[Credential]:
        return self.find_nodes(Credential)

    @property
    def credential_packet(self) -> CredentialManager:
        return CredentialManager(self)
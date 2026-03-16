from types import SimpleNamespace

from tangl.media.media_creators.svg_forge.vector_spec import VectorSpec
from tangl.media.media_resource import MediaDep
from tangl.media.media_data_type import MediaDataType
from tangl.media.media_resource.media_provisioning import MediaProvisioner
from tangl.media.media_resource.media_resource_registry import MediaResourceRegistry
from tangl.media.media_resource.media_resource_inv_tag import MediaResourceInventoryTag
from tangl.vm.provision import ProvisionPolicy, Requirement


class _GraphStub:
    def __contains__(self, _item):
        return True

    def add(self, _item):
        return None


class _StubContext:
    """Minimal context wrapper for offer acceptance."""

    def __init__(self) -> None:
        self.graph = _GraphStub()


def test_media_provisioner_creates_media_from_template() -> None:
    registry = MediaResourceRegistry(label="test_media")
    requirement = Requirement(template={"data": b"sample"}, policy=ProvisionPolicy.CREATE)
    provisioner = MediaProvisioner(requirement=requirement, registries=[registry])

    offers = provisioner.generate_offers(ctx=_StubContext())

    assert len(offers) == 1
    provider = offers[0].accept(ctx=_StubContext())

    assert registry.find_one(has_identifier=provider.content_hash) is provider


def test_media_provisioner_returns_existing_provider() -> None:
    registry = MediaResourceRegistry(label="existing_media")
    existing = MediaResourceInventoryTag(
        label="alias",
        data=b"cached",
        data_type=MediaDataType.OTHER,
    )
    registry.add(existing)
    requirement = Requirement(identifier="alias", policy=ProvisionPolicy.EXISTING)
    provisioner = MediaProvisioner(requirement=requirement, registries=[registry])

    offers = provisioner.generate_offers(ctx=_StubContext())

    assert len(offers) == 1
    assert offers[0].provider_id == registry.find_one(label="alias").uid


def test_media_dep_inline_data_defaults_to_any_policy() -> None:
    dep = MediaDep(media_data=b"inline-bytes", data_type=MediaDataType.OTHER)

    assert dep.requirement.provision_policy == ProvisionPolicy.ANY


def test_media_dep_sanitizes_media_basename_from_label() -> None:
    dep = MediaDep(
        label="Hero Banner!?",
        media_spec=VectorSpec(label="hero_banner"),
        media_role="avatar im",
    )

    assert dep.requirement.media_basename == "Hero_Banner"

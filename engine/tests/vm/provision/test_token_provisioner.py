from __future__ import annotations

from types import SimpleNamespace

from pydantic import Field

from tangl.core.factory.token_factory import TokenFactory
from tangl.core.graph import Graph, Token
from tangl.core.singleton import Singleton
from tangl.vm.provision import ProvisioningPolicy, Requirement, TokenProvisioner


class Weapon(Singleton):
    damage: int = 0
    durability: int | None = Field(default=None, json_schema_extra={"instance_var": True})


def _ctx(graph: Graph, factory: TokenFactory) -> SimpleNamespace:
    return SimpleNamespace(graph=graph, token_factory=factory)


def test_token_provisioner_creates_token_from_factory() -> None:
    graph = Graph(label="test")
    factory = TokenFactory(label="tokens")
    factory.register_type(Weapon)
    Weapon(label="sword", damage=10)

    requirement = Requirement(
        graph=graph,
        policy=ProvisioningPolicy.CREATE_TOKEN,
        token_type=f"{Weapon.__module__}.{Weapon.__qualname__}",
        token_label="sword",
        overlay={"durability": 85},
    )

    provisioner = TokenProvisioner(token_factory=factory)
    ctx = _ctx(graph, factory)

    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))
    assert len(offers) == 1

    token = offers[0].accept(ctx=ctx)

    assert isinstance(token, Token)
    assert token.label == "sword"
    assert token.durability == 85
    assert token in graph


def test_token_provisioner_skips_missing_base() -> None:
    graph = Graph(label="test")
    factory = TokenFactory(label="tokens")
    factory.register_type(Weapon)

    requirement = Requirement(
        graph=graph,
        policy=ProvisioningPolicy.CREATE_TOKEN,
        token_type=f"{Weapon.__module__}.{Weapon.__qualname__}",
        token_label="missing",
    )

    provisioner = TokenProvisioner(token_factory=factory)
    ctx = _ctx(graph, factory)

    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))
    assert offers == []

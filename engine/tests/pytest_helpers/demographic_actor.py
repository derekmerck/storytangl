"""An opt-in test world composes profile facts and the existing prose name owner."""
from __future__ import annotations

from dataclasses import dataclass

from tangl.core import TokenCatalog
from tangl.mechanics.demographics import HasDemographics, NameBank, load_pack, register_pack
from tangl.prose.naming import PersonalNamedActor, get_authorities
from tangl.story import World


class ProfileActor(PersonalNamedActor, HasDemographics):
    pass


@dataclass
class NamingAssets:
    names: TokenCatalog[NameBank]

    def get_token_catalogs(self, **_kwargs: object) -> list[TokenCatalog]:
        return [self.names]


def bootstrap_world(label: str) -> World:
    """Load declared definitions and authorities; never generate individual values."""
    catalog = register_pack(load_pack("sample"))
    world = World.from_script_data(
        script_data={
            "label": label,
            "metadata": {"start_at": "intro.start"},
            "scenes": {"intro": {"blocks": {"start": {"content": "Casting."}}}},
        },
        assets=NamingAssets(catalog),
    )
    world.extra_authorities.extend(get_authorities())
    return world

from __future__ import annotations
from typing import *
from enum import Enum

# -------------------------------
# Actor Classes
# -------------------------------

class AvatarMixin:

    class Avatar:
        def svg(self) -> Svg: ...
        @classmethod
        def random_avatar(cls, seed: bytes) -> Avatar: ...

    def avatar(self, **kwargs) -> Svg: ...


class Actor(RenderableMixin, StoryNode):

    name: str

    class Gens(Enum): ...
    gens: Gens

    class AoC(Enum): ...
    class DetailAoC(Enum):
        @classmethod
        def in_aoc(cls, value: Actor.DetailAoC) -> Actor.AoC: ...

    class Outfit(RenderableMixin, StoryNode):
        # collection of wearables

        class Wearable(Asset, Renderable, StoryNode):
            class Layer(Enum): ...

            aoc: Actor.AoC
            layer: Layer

        class WearableState(Enum): ...

        items: dict[Uid, WearableState]  # key is wearable asset uid
        def layer_avail(self, aoc: Actor.AoC, layer: Wearable.Layer) -> bool: ...  # everything above at least shifted
        def remove_layer_avail(self, aoc: Actor.AoC, layer: Wearable.Layer) -> bool: ...  # everything above removed
        def shift_layer(self, aoc: Actor.AoC, layer: Wearable.Layer, voice: Voice = None) -> str: ...
        def remove_layer(self, aoc: Actor.AoC, layer: Wearable.Layer, voice: Voice = None) -> str: ...

    outfit: Outfit

    class Ornamentation(RenderableMixin, StoryNode):
        # collection of ornaments

        class OrnamentType(Enum): ...

        class Ornament(Renderable, StoryNode):

            ornament_typ: Actor.Ornamentation.OrnamentType
            loc: Actor.DetailAoC

        items: list[Ornament]
        def by_aoc(self) -> dict[Actor.DetailAoC, Ornament]: ...
        def by_type(self) -> dict[OrnamentType, Ornament]: ...
        # desc recursively describes the largest remaining group in by_aoc/by_type

    ornamentation: Ornamentation

    # As well as various characteristics and demographics


# -------------------------------
# Game Classes
# -------------------------------

class Game(RenderableMixin, StoryNode):

    class GameState(Enum): ...
    class GameMove: ...
    class GamePlayer:
        current_move: Game.GameMove
        current_score: int

    player: GamePlayer
    opponent: GamePlayer

    def advance(self, player_move = None, **kwargs): ...
    def reset(self): ...
    score: tuple[int, int]
    round_result: GameState
    game_state: GameState

    def avatar(self, **kwargs) -> str: ...  # svg
    def avatar_update(self, **kwargs) -> dict: ...  # svg update commands

class Encounter(Game):

    class Pace(Enum): ...

    class EncAction('Action', Runtime, MultiRenderable, StoryNode):
        use: Actor.AoC
        on: Actor.AoC
        responses: dict[Encounter.Pace, dict[Encounter.Pace, MultiRenderable]]

    roles: dict[str, Role]
    actions: dict[Enum, dict[Enum, list[EncAction]]]
    voice: Voice

class RpsGame(Game):
    ...

class TwentyOneGame(Game):
    ...

class TwentyTwoGame(Game):
    ...

class UnitGame(Game):

    class Unit(Asset, Renderable, StoryNode):
        power: float
        affiliation: Enum

    class UnitGroup(Wallet):
        power: float
        affiliation: float
        def decimate(self, power: float): ...

    ...

class ResourceManagerGame(Game):
    ...

# -------------------------
# Utility Classes
# -------------------------

class Demographics(Singleton):

    class NameMint(Singleton):
        def name(self, origin: str = None, subtype: str = None) -> tuple[str, str]: ...

    @classmethod
    def demographic( cls, origin: str = None, subtype: str = None,
                     name: tuple[str, str] = None, **kwargs ) -> tuple[str, str, str]: ...

class SvgForge(Singleton):

    class SvgSpec:
        shapes: list
        styles: dict

    def forge( self, spec: SvgSpec, fmt: Enum, **kwargs ) -> Svg: ...
    def forge_many( self, *specs: SvgSpec, fmt: Enum, dims: tuple[int, int],
                    offsets: tuple[int, int], **kwargs ) -> Svg: ...

class Haberdasher(Singleton):

    def svg_spec_for(self, obj: Renderable) -> SvgForge.SvgSpec: ...

class Avatar:

    @classmethod
    def from_actor(cls, Actor) -> Avatar: ...

    def svg_spec(self) -> SvgForge.SvgSpec: ...

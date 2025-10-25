# Special scene type for managing challenges

import typing as typ
import attr
from tangl.scene import Scene, ContentBlock
from .rps import Player
from .sig import Unit, Force, SigType
from .challenge_desc import ChallengeDescMixin


# Need world to get unit info

@attr.s(auto_attribs=True, repr=False)
class Challenge(ChallengeDescMixin, Scene):

    challenge_typ: str = None
    # repeatable: bool = False

    # This is just a holder for init values, converted into player and opponent
    forces: typ.Dict = attr.Factory(dict)
    # blocks: typ.Dict[str, ContentBlock] = attr.ib(converter=mk_content_block_dict, default=None)

    results: typ.Dict = None
    @property
    def outcome(self) -> bool:
        # True (player won), False (player lost or drew)
        if self.results:
            return self.results.get("outcome")

    @property
    def rounds(self) -> int:
        # True (player won), False (player lost or drew)
        if self.results:
            return self.results.get("rounds")

    def loss_summary_by_round(self) -> typ.Optional[typ.List[typ.Tuple[typ.Dict, typ.Dict]]]:
        if not self.results:
            return
        rounds = []
        for p_losses_, op_losses_ in self.results["rounds"]:
            p_losses = Unit.summarize(p_losses_)
            op_losses = Unit.summarize(op_losses_)
            rounds.append( (p_losses, op_losses) )
        return rounds

    def total_losses_summary(self) -> typ.Optional[typ.Tuple[typ.Dict, typ.Dict]]:
        if not self.results:
            return
        p_losses = []
        op_losses = []
        for p_losses_, op_losses_ in self.results["rounds"]:
            p_losses += p_losses_
            op_losses += op_losses_
        return Unit.summarize(p_losses), Unit.summarize(op_losses)

    player: Player = attr.ib(init=False)

    def mk_forces(self, force_key: str):
        f = Force()
        for _u in self.forces.get(force_key, []):
            __u = {**_u}  # Make a copy b/c we want to reuse kwargs
            count = __u.pop("count", 1)
            f.add_units(count, __u)
        return Player(active=f)

    @player.default
    def mk_player(self):
        """ :meta private: """
        return self.mk_forces("player")

    opponent: Player = attr.ib(init=False)
    @opponent.default
    def mk_opponent(self):
        """ :meta private: """
        return self.mk_forces("opponent")

    def _init(self, state: typ.Dict = None, world: 'World' = None):
        """I thought I was going to do this differently, so I sort of
        backed into this clumsy post facto update hack"""
        def update_units(force: Force):
            if not force:
                return
            u: Unit
            for u in force.contents:
                if u.uid in world.unit_mint.templates:
                    templ = world.unit_mint.templates[u.uid]
                    # print(f"{u.uid}: {templ.get('sig_typ')}")
                    if "power" in templ:
                        u.power = templ["power"]
                    if "sig_typ" in templ:
                        u.sig_typ = SigType.from_str(templ["sig_typ"])
                else:
                    # print(f"No key {u.uid}")
                    pass

        update_units(self.player.active)
        update_units(self.player.reserve)
        update_units(self.opponent.active)
        update_units(self.opponent.reserve)

        # print(self.opponent.active.contents)

    def play(self) -> typ.Dict:
        self.results = Force.play(self.player.active, self.opponent.active)
        return self.results

    # todo: info_for_unit returns both avatar and desc
    # could initialize a list of all this info at creation...
    def info_for_unit(self, unit_uid, world: "World"):

        result = {}

        def find_in_forces() -> typ.Optional[typ.Dict]:
            return None

        # unit_desc = find_in_forces()
        # if unit_desc and "avatar" in unit_desc:
        #     result["avatar"] = unit_desc.get("avatar")

        unit_desc = world.unit_mint.templates.get(unit_uid)
        if unit_desc and "label" in unit_desc:
            result["label"] = unit_desc.get("label")

        if unit_desc and "desc" in unit_desc:
            result["desc"] = unit_desc.get("desc")

        if unit_desc and "avatar" in unit_desc:
            result["avatar"] = unit_desc.get("avatar")

        return result

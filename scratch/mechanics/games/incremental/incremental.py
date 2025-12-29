from __future__ import annotations
from typing import *
from pprint import pformat
from enum import Enum, auto
from numbers import Number

from pydantic import BaseModel, Field, model_validator, field_validator

class GameStatus(Enum):
    WIN = auto()
    LOSE = auto()
    IN_PROGRESS = auto()

class Resource(Enum):
    CASH = auto()
    LABOR = auto()
    MATERIALS = auto()

UniqueLabel = str | Resource   # Commodity label or Resource
CommodityType = BaseModel      # Singleton

class Wallet(dict[UniqueLabel, Number]):

    def __add__(self, other):
        res  = { k: v + other.get(k, 0) for k, v in self.items() }
        res |= { k: v for k, v in other.items() if k not in self }
        return Wallet( **res )

    def __sub__(self, other: Wallet):
        return self + -1*other

    def __mul__(self, other: Number):
        res = { k: v*other for k, v in self.items() }
        return Wallet( **res )

    def can_afford(self, other: Wallet):
        res = self - other
        return all([ v >= 0 for v in res.values() ])


class Generator(CommodityType):
    """Generators are commodity (purchasable) assets with a _cost_.
    They can _consume_ assets in order to _produce_ other assets.

    Common examples:
      - Font: costs (cash) and generates (labor)
      - Factory: costs (cash, labor) and converts (labor) into (materials)
      - Refinery: costs (cash, labor, materials) and converts (labor, materials) -> (cash)

    Generators also carry a _premium_ that can boost the price as certain conditions are
    met.

    Externally, in the game, a player may have discounts, efficiencies (consumption), and
    production boosts for each generator type.
    """

    label: str  # req for Singletons
    _instances: ClassVar[dict] = dict()  # map of label -> instance

    @model_validator(mode='after')
    def _register_instance(self):
        self._instances[self.label] = self

    cost: Wallet = Field(default_factory=Wallet)      # req input to build
    consumes: Wallet = Field(default_factory=Wallet)  # req input to operate
    produces: Wallet = Field(default_factory=Wallet)  # output per operation

    premium: float = 0.05

    def next_cost(self, num: int, discount: float = 0.0 ) -> Wallet:
        # can get discount upgrades to reduce the cost
        num += 1  # num is current, n+1 is next
        return self.cost * ( 1.0 + self.premium - discount )**(num - 1)

    def generate(self, num: int,
                 input_: Wallet,
                 productivity: float = 1.0,
                 efficiency: float = 1.0) -> Tuple[Wallet, Wallet]:
        # upgrades improve productivity (effort), efficiency
        output = Wallet()
        in_ = self.consumes * productivity
        out_ = self.produces * efficiency
        for i in range(num):
            if input_ >= in_:
                input_ -= in_
                output += out_
        return input_, output


class Player(BaseModel):

    resources: Wallet = Field(default_factory=Wallet)

    # within a game, generators have discount, productivity boost, efficiency boost
    discounts: Wallet = Field( default_factory=Wallet)
    productivity_boost: Wallet = Field( default_factory=Wallet)
    efficiency_boost: Wallet = Field( default_factory=Wallet)

    @field_validator('resources', 'discounts', 'productivity_boost', 'efficiency_boot', mode='before')
    @classmethod
    def _convert_to_wallet(cls, data):
        if not isinstance(data, Wallet):
            return Wallet(**data)
        return data

    def next_cost(self, gen_typ: UniqueLabel) -> Wallet:
        gen = Generator._instances[ gen_typ ]  # type: Generator
        num = self.resources[ gen_typ ]
        discount = self.discounts.get( gen_typ, 0 )
        res = gen.next_cost(num=num, discount=discount)
        return res

    def buy_gen(self, gen_typ: str):
        print( f"\nTrying to buy {gen_typ}" )
        next_cost = self.next_cost( gen_typ )
        if self.resources.can_afford( next_cost ):
            print( "Incr: Can afford OK" )
            self.resources -= next_cost
            self.resources[gen_typ] += 1
        else:
            print( f"Incr: Not enough to cover {next_cost}")

    def update(self):
        # In this case, there are no allocation choices to make, resources are
        # simply consumed as much as possible.
        self.turn += 1
        print( f"\nTurn {self.turn}\n------------" )
        input_ = self.resources
        result = Wallet()

        generators = {Generator.instance(k): v for k, v in self.resources.items()
                      if isinstance( Generator.instance(k), Generator )}
        for gen_typ, num in generators.items():
            # todo: Should probably keep the order consistent
            productivity = 1.0 + self.productivity_boost.get( gen_typ, 0 )
            efficiency = 1.0 + self.efficiency_boost.get( gen_typ, 0 )
            print( f"Invoking generator ({gen_typ}/{num}/{productivity}/{efficiency}):\n{gen_typ}")
            input_, output = gen_typ.generate( num=num, input_=input_,
                                               productivity=productivity,
                                               efficiency=efficiency )
            result += output

        # exhaust ephemeral resources
        for k, v in self.resources.items():
            try:
                res = CommodityType._instances.get( k )
                if res.locals.get("ephemeral"):
                    input_[k] = 0
            except KeyError:
                pass
        # conserve the rest
        result += input_

        self.resources = result

    @property
    def current_score(self):
        return self.resources.total()

    def __repr__(self):
        s = "\nResources: " + pformat(self.resources)
        return s


class GameManager(BaseModel):
    """
    Clicker-like variant on :class:\`TokenGame\`

    Solitaire resource management strategy game model

    Basic token exchanges:
    - fonts                           -> labor
    - factories  + labor              -> materials, cash
    - refineries + labor, materials   -> cash

    - buy new or improve fonts, factories, refiners with materials, labor, cash
    - improve/unlock labor or materials with materials, labor, cash
    - improvements: capacity/throughput, efficiency (wastage and conversion rate)

    num factories is actually just capacity...buy capacity in increments of 1.0
    uses uncapped factories -- a single factory is limited by input, not capacity

    Could layer milling on top, spoilage of resources, maintenance of capital, or
    other mandatory upkeep sinks like defense
    """

    win_at: Wallet
    player: Player = Field( default_factory=Player )
    num_rounds: int = 10

    # Non-durable assets that cannot be banked between rounds in this game
    # for example, labor is non-durable, cash is durable, materials and/or
    # improved materials may be durable (metal) or not (food)
    ephemeral: set[UniqueLabel] = Field(default_factory=set)

    @property
    def game_status(self) -> GameStatus:
        if self.win_at and self.player.resources > self.win_at:
            return GameStatus.WIN
        elif self.num_rounds and self.round > self.num_rounds:
            return GameStatus.LOSE
        return GameStatus.IN_PROGRESS

    def _compute_round_result(self):
        self.player.update()

CalvinCards
===========

1. Core Concept:
CalvinCards is a best-of-three contested skill check game disguised as a collectible card game, with procedurally generated narratives based on "Calvin-ball" rules.

Conceivably, CC could be extended to multiple players, like rps can be.  Each round has 1 loser, (m/n)+1 losses drops them from a game of m rounds with n players.

2. Key Components:
- Variant-based theming (e.g., space opera, steampunk)
- Procedural card generation
- Rock-paper-scissors core mechanics with added complexity
- Skill-based gameplay
- Affiliation system
- AI-generated card art (using Stable Diffusion)

3. Code Snippets:

a) Card Generation using Pydantic:

```python
from pydantic import BaseModel, Field
from enum import Enum
import random

class Rarity(str, Enum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    LEGENDARY = "legendary"

class Affiliation(str, Enum):
    RED = "red"
    BLUE = "blue"
    GREEN = "green"

class StrategyType(str, Enum):
    ROCK = "rock"
    PAPER = "paper"
    SCISSORS = "scissors"

class Card(BaseModel):
    variant: str
    seed: int = Field(default_factory=lambda: random.randint(0, 2**32 - 1))
    rarity: Rarity
    affiliation: Optional[Affiliation] = None
    name: str
    strategy_type: Optional[StrategyType] = None
    power_modifier: int = 0

    @classmethod
    def create(cls, variant: str, **kwargs):
        seed = kwargs.get('seed', random.randint(0, 2**32 - 1))
        rng = random.Random(seed)
        
        if 'rarity' not in kwargs:
            kwargs['rarity'] = rng.choices(
                [Rarity.COMMON, Rarity.UNCOMMON, Rarity.RARE, Rarity.LEGENDARY],
                weights=[75, 20, 4, 1]
            )[0]
        
        if 'affiliation' not in kwargs:
            kwargs['affiliation'] = rng.choice(list(Affiliation))
        
        if 'name' not in kwargs:
            # This would use the variant data to generate a name
            kwargs['name'] = f"{kwargs['affiliation'].value.capitalize()} {kwargs['rarity'].value.capitalize()}"
        
        return cls(variant=variant, seed=seed, **kwargs)
```

b) Strategy Resolution:

```python
class Strategy(BaseModel):
    type: StrategyType
    power: int

    def resolve_against(self, other: 'Strategy') -> int:
        base_result = {
            (StrategyType.ROCK, StrategyType.SCISSORS): 1,
            (StrategyType.SCISSORS, StrategyType.PAPER): 1,
            (StrategyType.PAPER, StrategyType.ROCK): 1,
            (StrategyType.ROCK, StrategyType.PAPER): -1,
            (StrategyType.SCISSORS, StrategyType.ROCK): -1,
            (StrategyType.PAPER, StrategyType.SCISSORS): -1,
        }.get((self.type, other.type), 0)
        
        return base_result * 3 + (self.power - other.power)
```

c) Game Loop:

```python
class CalvinGame(BaseModel):
    player1: 'CalvinPlayer'
    player2: 'CalvinPlayer'
    variant: str
    current_round: int = 1
    p1_wins: int = 0
    p2_wins: int = 0

    def play_round(self) -> str:
        p1_strategy = self.player1.select_strategy()
        p2_strategy = self.player2.select_strategy()
        
        power_difference = p1_strategy.resolve_against(p2_strategy)
        skill_difference = self.player1.skill - self.player2.skill
        
        final_difference = power_difference + skill_difference
        
        result = self.skill_check(final_difference)
        
        if result > 0:
            self.p1_wins += 1
        else:
            self.p2_wins += 1
        
        narrative = self.generate_narrative(p1_strategy, p2_strategy, result)
        
        self.current_round += 1
        return narrative

    def play_game(self) -> str:
        game_narrative = []
        while max(self.p1_wins, self.p2_wins) < 2:
            round_narrative = self.play_round()
            game_narrative.append(round_narrative)
        
        return "\n".join(game_narrative)
```

4. Example Data (Variant Configuration):

```yaml
name: Cosmic Confluence

phase_names:
- launch
- navigate
- encounter

strategy_types:
- explore:  # scissors equivalent
    adj:
      - pioneering
      - bold
    nominal:
      - expedition
      - probe
- negotiate:  # paper equivalent
    adj:
      - diplomatic
      - cunning
    nominal:
      - alliance
      - treaty
- fortify:  # rock equivalent
    adj:
      - defensive
      - resilient
    nominal:
      - shield
      - outpost

affiliations:
- red:
    name: nova
    modifiers: explore+1
    adj:
      - blazing
      - volatile
    nominal:
      - star
      - flare
    special_nominal:
      - quasar
- blue:
    name: quantum
    modifiers: fortify+1
    adj:
      - entangled
      - probabilistic
    nominal:
      - particle
      - wormhole
    special_nominal:
      - tesseract
- green:
    name: biome
    modifiers: negotiate+1
    adj:
      - symbiotic
      - adaptive
    nominal:
      - ecosystem
      - spore
    special_nominal:
      - panspermia

card_adj:
- interstellar
- cybernetic
- gravitational
- quantum
- nebulous

card_nominal:
- starship
- android
- nebula
- asteroid
- alien

special_card_nominal:
- mothership
- space-time rift
- dark matter
- dyson sphere
- nanite swarm
```

5. Key Ideas to Implement:
- Procedural card generation based on variant themes
- Strategy generation based on player skill and deck contents
- Affiliation system with bonuses and maluses
- Skill-based resolution system
- Dynamic narrative generation using variant word lists
- AI-generated card art using Stable Diffusion

6. Next Steps:
- Implement the full game loop with round resolution
- Develop the narrative generation system
- Create a deck-building and card collection system
- Implement an AI for strategy selection (for computer opponents)
- Integrate with Stable Diffusion for card art generation

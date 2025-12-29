from enum import Enum
from .look import Look

class FantasticType(Enum):
    HUMAN = "human"

    BEAST = "beast"
    CAT = "cat"
    DOG = "dog"
    GOAT = "goat"
    HORSE = "horse"
    BIRD = AVIAN = "bird"     # feathered
    SNAKE = SERPENT = "snake"
    SPIDER = "spider"
    INSECT = "insect"  # tags: butterfly, dragonfly, scorpion, wasp

    DRAGON = DRACONIC = "dragon"
    ALIEN = "alien"
    TENTACLE = "tentacle"
    SLIME = GELATINOUS = "slime"

    ROBOT = "robot"    # fully robotic

    DEMON = ONI = "demon"
    ANGEL = "angel"

    PLANT = FLOWER = "plant"
    TREE = "tree"


class FantasticLook(Look):
    # For creatures with unusual features
    # Quite probably need a BodyPart extension map for wings, tails

    body_type: FantasticType | str = None  # human, snakelike, robot
    taur: bool = False  # non-bipedal, e.g., horse/spider body

    eye_type: FantasticType | str = None   # human, cat, spider (6)
    eye_count: int = 2

    mandible_type: FantasticType | str = None  # human (1, vertical), insectoid (2, lateral), snout
    mandible_count: int = 1

    arm_type: FantasticType | str = None   # human, insect, tentacle, robot
    arm_count: int = 2

    leg_type: FantasticType | str = None   # horse, goat, dog, insect, tentacle, robot
    leg_count: int = 2     # indicate digitigrade

    fur_color: str = None

    horn_count: int = 0
    horn_type: FantasticType | str = None  # goat (2), oni (1), unicorn (1), antlers (2+)
    horn_color: str = None  # bone

    wing_count: int = 0
    wing_type: FantasticType | str = None  # bug, dragonfly, butterfly, bird/feathered, bat/leather, robotic
    wing_palette: str = None

    tail_count: int = 0
    tail_type: str = None  # catlike, spaded, forked, prehensile
    tail_color: str = None

    ovipositor_type: str = None
    ovipositor_color: str = None
    stinger_type: str = None   # scorpion, wasp
    stinger_color: str = None


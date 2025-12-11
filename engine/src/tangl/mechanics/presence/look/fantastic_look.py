from enum import Enum
from .look import Look

class FantasticType(Enum):
    HUMAN = "human"

    BEAST = "beast"
    CAT = "cat"
    DOG = "dog"
    GOAT = "goat"
    HORSE = "horse"
    BIRD = "bird"     # feathered
    SNAKE = "snake"
    SPIDER = "spider"
    INSECT = "insect"  # tags: butterfly, dragonfly, scorpion, wasp
    TAUR = "taur"

    ALIEN = "alien"
    TENTACLE = "tentacle"
    GELATINOUS = "gelatinous"

    ROBOT = "robot"

    DEMON = ONI = "demon"
    ANGEL = "angel"

    FLOWER = "flower"
    TREE = "tree"


class FantasticLook(Look):
    # For creatures with unusual features
    # Quite probably need a BodyPart map for this

    body_type: FantasticType | str = None  # human, snakelike, taur, robot

    eye_type: FantasticType | str = None   # human, cat, spider (6)
    eye_count: int = 2

    mandible_type: FantasticType | str = None # human (1, vertical), insectoid (2, lateral), snout
    mandible_count: int = 1

    arm_type: FantasticType | str = None   # human, insect, tentacle, robot
    arm_count: int = 2

    leg_type: FantasticType | str = None   # horse, goat, dog, insect, tentacle, robot
    leg_count: int = 2     # indicate digitigrade

    fur_color: str = None

    horn_count: int = 0
    horn_type: FantasticType | str = None  # goat (2), oni (1), unicorn (1)
    horn_color: str = None # bone

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


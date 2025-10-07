from enum import Enum, auto
from tangl.mechanics.games.picking_game import PickingGameHandler, PickingGame, GameToken

# language=YAML
moves = """
# disposition
# -----------
- pass
- deny
- arrest

# problem with origin or indication
# ---------------------------------
# clear unpermitted by producing credential
# clear contraband by relinquishing
- indicate origin              # on id
- indicate purpose             # on declaration
- request relinquish contraband

- confirm revealed credential
- confirm declined relinquish

# hidden contraband
# -----------------
# clear or confirm with search
- request search

- confirm clear search
- confirm discovered contraband

# invalid credential
# ------------------
# requires _which_ credential
- indicate bad seal
- indicate bad date
- indicate bad holder id  # permit only

# id holder problem
# -----------------
# clear or confirm holder with id test
- request id test         # on id biometrics only
- confirm id test result  # wrong holder or match and on blacklist
"""


class CredCheckGameHandler(PickingGameHandler):
    """
    Credential inspection game is a PickingGame where the player is presented
    with a set of rules and objects and must identify the mis-matches or pass
    the candidate.

    Heavily inspired by Lucas Pope's innovative Papers Please core game loop.
    """
    ...


class CredCheckGame(PickingGame):
    ...

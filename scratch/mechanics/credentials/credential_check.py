

from tangl.mechanics.game.challenge_block import Challenge


class CredentialCheck(Challenge):
    """
    This is a challenge inspired by Lucas Pope's innovative [Papers Please][] game.

    It is implemented as a "HiddenObject" game in this framework.  The goal is to work
    from the "presenting status" of a candidate to uncover their "real status", given the
    current accept/deny/detain rule set.

    Basic credentials and restrictions include anonymous tickets, id cards, and permits
    for prohibited objects or purposes.

    A CredentialCheck is models a single encounter in four sub-phases:
      - presentation
      - questioning
      - mitigation
      - disposition

    A candidate may be created manually in the script, or generated through the "Extras"
    mechanism.  A randomly generated candidate takes a disposition parameter and their
    presenting and real status will be sampled and appropriate credentials generated
    """
    ...




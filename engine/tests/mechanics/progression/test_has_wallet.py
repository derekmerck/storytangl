from __future__ import annotations

from tangl.mechanics.progression.definition import CanonicalSlot, StatDef, StatSystemDefinition
from tangl.mechanics.progression.entity.has_wallet import HasWallet


def _currency_system() -> StatSystemDefinition:
    return StatSystemDefinition(
        name="economy",
        theme="test",
        complexity=3,
        handler="probit",
        stats=[
            StatDef(
                name="body",
                is_intrinsic=True,
                currency_name="stamina",
                canonical_slot=CanonicalSlot.PHYSICAL,
            ),
            StatDef(
                name="mind",
                is_intrinsic=True,
                currency_name="focus",
                canonical_slot=CanonicalSlot.MENTAL,
            ),
            StatDef(
                name="will",
                is_intrinsic=True,
                currency_name="resolve",
                canonical_slot=CanonicalSlot.SPIRITUAL,
            ),
        ],
    )


def test_wallet_from_system_initialization():
    system = _currency_system()
    wallet = HasWallet.from_system(system, base_amount=5)

    assert wallet.wallet == {
        "stamina": 5,
        "focus": 5,
        "resolve": 5,
    }


def test_wallet_overrides():
    system = _currency_system()
    wallet = HasWallet.from_system(
        system,
        base_amount=0,
        overrides={"stamina": 10},
    )

    assert wallet.wallet["stamina"] == 10
    assert wallet.wallet["focus"] == 0
    assert wallet.wallet["resolve"] == 0


def test_can_afford_and_spend_and_earn():
    system = _currency_system()
    wallet = HasWallet.from_system(system, base_amount=5)

    cost = {"stamina": 3, "focus": 2}
    assert wallet.can_afford(cost) is True

    wallet.spend(cost)
    assert wallet.wallet["stamina"] == 2
    assert wallet.wallet["focus"] == 3

    try:
        wallet.spend({"resolve": 10})
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for overspend")

    wallet.earn({"resolve": 4, "focus": 1})
    assert wallet.wallet["resolve"] == 9
    assert wallet.wallet["focus"] == 4

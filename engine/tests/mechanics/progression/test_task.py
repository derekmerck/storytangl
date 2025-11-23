from __future__ import annotations

from __future__ import annotations

from mechanics.progression.definition import CanonicalSlot, StatDef, StatSystemDefinition
from mechanics.progression.tasks.task import Task


def _example_system() -> StatSystemDefinition:
    return StatSystemDefinition(
        name="example",
        theme="test",
        complexity=3,
        handler="probit",
        stats=[
            StatDef(name="body", is_intrinsic=True, canonical_slot=CanonicalSlot.PHYSICAL),
            StatDef(name="mind", is_intrinsic=True, canonical_slot=CanonicalSlot.MENTAL),
            StatDef(name="will", is_intrinsic=True, canonical_slot=CanonicalSlot.SPIRITUAL),
        ],
    )


def test_task_infer_domain_and_get_difficulty():
    system = _example_system()

    # explicit domain wins
    t = Task(
        name="Body check",
        domain="body",
        difficulty={"body": 12.0, "mind": 14.0},
    )
    assert t.infer_domain(system) == "body"
    assert t.get_difficulty(domain="body", system=system) == 12.0

    # if domain None, first difficulty key
    t2 = Task(
        name="Unlabeled check",
        difficulty={"mind": 13.0, "body": 11.0},
    )
    assert t2.infer_domain(system) == "mind"
    assert t2.get_difficulty(domain=None, system=system) == (13.0 + 11.0) / 2.0

    # empty difficulty → neutral 10.0
    t3 = Task(name="Easy", difficulty={})
    assert t3.infer_domain(system) == "body"  # system.default_domain = first intrinsic
    assert t3.get_difficulty(domain="body", system=system) == 10.0


def test_task_cost_and_reward_helpers():
    wallet = {"gold": 10, "stamina": 3}

    task = Task(
        name="Pay and gain",
        cost={"gold": 4},
        reward={"stamina": 2},
    )

    assert task.can_afford(wallet) is True

    wallet_after_cost = task.apply_cost(wallet)
    assert wallet_after_cost["gold"] == 6
    assert wallet_after_cost["stamina"] == 3

    wallet_after_reward = task.apply_reward(wallet_after_cost)
    assert wallet_after_reward["gold"] == 6
    assert wallet_after_reward["stamina"] == 5

    # overspend
    big_task = Task(
        name="Too expensive",
        cost={"gold": 100},
    )
    assert big_task.can_afford(wallet) is False
    try:
        big_task.apply_cost(wallet)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for unaffordable cost")

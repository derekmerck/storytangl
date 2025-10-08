from __future__ import annotations

from uuid import UUID, uuid4

from tangl.vm.planning import BuildReceipt, PlanningReceipt, ProvisioningPolicy


def _build_receipt(*, caller_id, operation, accepted, hard_req=None, reason=None, provider_id=None):
    return BuildReceipt(
        provisioner_id=uuid4(),
        requirement_id=caller_id,
        provider_id=provider_id,
        operation=operation,
        accepted=accepted,
        hard_req=hard_req,
        reason=reason,
    )


def test_planning_receipt_marks_no_offers_unresolved():
    requirement_id = uuid4()
    receipt = _build_receipt(
        caller_id=requirement_id,
        operation=ProvisioningPolicy.CREATE,
        accepted=False,
        hard_req=True,
        reason="no_offers",
    )

    summary = PlanningReceipt.summarize(receipt)

    assert summary.unresolved_hard_requirements == [requirement_id]
    assert summary.waived_soft_requirements == []


def test_planning_receipt_counters_preserved_for_positive_receipts():
    unresolved_id = uuid4()
    success_id = uuid4()

    successful = _build_receipt(
        caller_id=success_id,
        operation=ProvisioningPolicy.CREATE,
        accepted=True,
        provider_id=uuid4(),
    )
    unresolved = _build_receipt(
        caller_id=unresolved_id,
        operation=ProvisioningPolicy.EXISTING,
        accepted=False,
        hard_req=True,
        reason="no_offers",
    )

    summary = PlanningReceipt.summarize(successful, unresolved)

    assert summary.created == 1
    assert summary.attached == 0
    assert summary.unresolved_hard_requirements == [unresolved_id]
    assert summary.waived_soft_requirements == []
    assert isinstance(summary.unresolved_hard_requirements[0], UUID)


def test_planning_receipt_tracks_waived_soft_requirements():
    waived_id = uuid4()

    waived = _build_receipt(
        caller_id=waived_id,
        operation=ProvisioningPolicy.CREATE,
        accepted=False,
        hard_req=False,
        reason="waived_soft",
    )

    summary = PlanningReceipt.summarize(waived)

    assert summary.unresolved_hard_requirements == []
    assert summary.waived_soft_requirements == [waived_id]

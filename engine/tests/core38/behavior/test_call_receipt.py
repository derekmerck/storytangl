"""Contract tests for ``tangl.core.behavior.CallReceipt``."""

from __future__ import annotations

import pytest

from tangl.core.behavior import AggregationMode, CallReceipt


class TestCallReceiptResolve:
    def test_create_both_raises(self) -> None:
        with pytest.raises(ValueError):
            CallReceipt(result=1, callback=lambda *_, **__: 2)

    def test_create_neither_raises(self) -> None:
        with pytest.raises(ValueError):
            CallReceipt()

    def test_resolve_deferred_uses_ctx_and_args(self) -> None:
        receipt = CallReceipt(callback=lambda *args, ctx=None, **kwargs: (args, ctx, kwargs), ctx="ctx")
        assert receipt.resolve(1, x=2) == ((1,), "ctx", {"x": 2})
        assert receipt.resolve(9, x=5) == ((1,), "ctx", {"x": 2})


class TestCallReceiptAggregation:
    def test_iter_results_skips_none(self) -> None:
        receipts = [CallReceipt(result=None), CallReceipt(result=1), CallReceipt(result=2)]
        assert list(CallReceipt.iter_results(*receipts)) == [1, 2]

    def test_merge_results_dicts_later_wins(self) -> None:
        merged = CallReceipt.merge_results(CallReceipt(result={"a": 1}), CallReceipt(result={"a": 2}))
        assert dict(merged)["a"] == 2

    def test_merge_results_mixed_returns_gathered_values(self) -> None:
        assert CallReceipt.merge_results(CallReceipt(result={"a": 1}), CallReceipt(result=[2])) == [{"a": 1}, [2]]

    def test_aggregate_dispatches_by_mode(self) -> None:
        receipts = [CallReceipt(result=1), CallReceipt(result=2)]
        assert CallReceipt.aggregate(AggregationMode.GATHER, *receipts) == [1, 2]

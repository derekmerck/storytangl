"""Tests for tangl.core.behavior

Organized by functionality:
- CallReceipt: result codes, aggregation
- Behavior: creation, priority, layer
- BehaviorRegistry: registration, dispatch
"""
from __future__ import annotations

import pytest
from uuid import uuid4
from collections import ChainMap

from tangl.core.behavior import (
    CallReceipt,
    Behavior,
    HandlerPriority,
    HandlerLayer,
    BehaviorRegistry,
)
from tangl.core.behavior.call_receipt import ResultCode


# ============================================================================
# Test Fixtures and Helpers
# ============================================================================

def sample_handler(ctx):
    """Simple test handler."""
    return "result"


def failing_handler(ctx):
    """Handler that raises an error."""
    raise ValueError("Test error")


def skip_handler(ctx):
    """Handler that returns None."""
    return None


@pytest.fixture
def sample_behavior():
    """Fixture providing a basic behavior."""
    return Behavior(
        func=sample_handler,
        task="test_task",
        layer=HandlerLayer.LOCAL,
        priority=HandlerPriority.NORMAL
    )


# ============================================================================
# CallReceipt Tests
# ============================================================================

class TestCallReceiptCreation:
    """Tests for CallReceipt creation and basic properties."""

    def test_create_receipt_with_result(self):
        """Test creating a receipt with a result."""
        behavior_id = uuid4()
        receipt = CallReceipt(behavior_id=behavior_id, result="test_result")

        assert receipt.origin_id == behavior_id
        assert receipt.result == "test_result"
        assert receipt.result_code == ResultCode.OK

    def test_create_receipt_with_result_code(self):
        """Test creating receipt with specific result code."""
        behavior_id = uuid4()
        receipt = CallReceipt(
            behavior_id=behavior_id,
            result=None,
            result_code=ResultCode.SKIP
        )

        assert receipt.result_code == ResultCode.SKIP

    def test_receipt_ok_helper(self):
        """Test CallReceipt.ok() helper."""
        from types import SimpleNamespace
        origin = SimpleNamespace(uid=uuid4())

        receipt = CallReceipt.ok(origin, "success")

        assert receipt.result == "success"
        assert receipt.result_code == ResultCode.OK

    def test_receipt_skip_helper(self):
        """Test CallReceipt.skip() helper."""
        from types import SimpleNamespace
        origin = SimpleNamespace(uid=uuid4())

        receipt = CallReceipt.skip(origin, msg="Skipping test")

        assert receipt.result is None
        assert receipt.result_code == ResultCode.SKIP
        assert receipt.message == "Skipping test"

    def test_receipt_invalid_helper(self):
        """Test CallReceipt.invalid() helper."""
        from types import SimpleNamespace
        origin = SimpleNamespace(uid=uuid4())

        receipt = CallReceipt.invalid(origin, msg="Invalid input")

        assert receipt.result is None
        assert receipt.result_code == ResultCode.INVALID
        assert receipt.message == "Invalid input"

    def test_receipt_error_helper(self):
        """Test CallReceipt.error() helper."""
        from types import SimpleNamespace
        origin = SimpleNamespace(uid=uuid4())

        receipt = CallReceipt.error(origin, msg="Error occurred")

        assert receipt.result is None
        assert receipt.result_code == ResultCode.ERROR
        assert receipt.message == "Error occurred"


class TestCallReceiptAggregation:
    """Tests for CallReceipt aggregation methods."""

    def test_gather_results(self):
        """Test gathering results from multiple receipts."""
        r1 = CallReceipt(behavior_id=uuid4(), result="a")
        r2 = CallReceipt(behavior_id=uuid4(), result="b")
        r3 = CallReceipt(behavior_id=uuid4(), result=None)

        results = list(CallReceipt.gather_results(r1, r2, r3))

        assert results == ["a", "b"]

    def test_first_result(self):
        """Test getting first result."""
        r1 = CallReceipt(behavior_id=uuid4(), result=None)
        r2 = CallReceipt(behavior_id=uuid4(), result="first")
        r3 = CallReceipt(behavior_id=uuid4(), result="second")

        result = CallReceipt.first_result(r1, r2, r3)

        assert result == "first"

    def test_first_result_all_none(self):
        """Test first_result when all results are None."""
        r1 = CallReceipt(behavior_id=uuid4(), result=None)
        r2 = CallReceipt(behavior_id=uuid4(), result=None)

        result = CallReceipt.first_result(r1, r2)

        assert result is None

    def test_last_result(self):
        """Test getting last result."""
        r1 = CallReceipt(behavior_id=uuid4(), result="first")
        r2 = CallReceipt(behavior_id=uuid4(), result="last")
        r3 = CallReceipt(behavior_id=uuid4(), result=None)

        result = CallReceipt.last_result(r1, r2, r3)

        assert result == "last"

    def test_any_truthy(self):
        """Test any_truthy aggregation."""
        r1 = CallReceipt(behavior_id=uuid4(), result=False)
        r2 = CallReceipt(behavior_id=uuid4(), result=True)
        r3 = CallReceipt(behavior_id=uuid4(), result=False)

        assert CallReceipt.any_truthy(r1, r2, r3) is True

    def test_any_truthy_all_false(self):
        """Test any_truthy when all are false."""
        r1 = CallReceipt(behavior_id=uuid4(), result=False)
        r2 = CallReceipt(behavior_id=uuid4(), result=None)

        assert CallReceipt.any_truthy(r1, r2) is False

    def test_all_truthy(self):
        """Test all_truthy aggregation."""
        r1 = CallReceipt(behavior_id=uuid4(), result=True)
        r2 = CallReceipt(behavior_id=uuid4(), result="truthy")
        r3 = CallReceipt(behavior_id=uuid4(), result=1)

        assert CallReceipt.all_truthy(r1, r2, r3) is True

    def test_all_truthy_with_false(self):
        """Test all_truthy with a false value."""
        r1 = CallReceipt(behavior_id=uuid4(), result=True)
        r2 = CallReceipt(behavior_id=uuid4(), result=False)

        assert CallReceipt.all_truthy(r1, r2) is False

    def test_merge_results_dicts(self):
        """Test merging dict results."""
        r1 = CallReceipt(behavior_id=uuid4(), result={"a": 1})
        r2 = CallReceipt(behavior_id=uuid4(), result={"b": 2})

        merged = CallReceipt.merge_results(r1, r2)

        assert isinstance(merged, ChainMap)
        assert merged["a"] == 1
        assert merged["b"] == 2

    def test_merge_results_lists(self):
        """Test merging list results."""
        r1 = CallReceipt(behavior_id=uuid4(), result=[1, 2])
        r2 = CallReceipt(behavior_id=uuid4(), result=[3, 4])

        merged = CallReceipt.merge_results(r1, r2)

        assert merged == [1, 2, 3, 4]

    def test_merge_results_incompatible_types(self):
        """Test that merging incompatible types raises error."""
        r1 = CallReceipt(behavior_id=uuid4(), result={"a": 1})
        r2 = CallReceipt(behavior_id=uuid4(), result=[1, 2])

        with pytest.raises(TypeError):
            CallReceipt.merge_results(r1, r2)


# ============================================================================
# Behavior Tests
# ============================================================================

class TestBehaviorCreation:
    """Tests for Behavior creation and properties."""

    def test_create_basic_behavior(self, sample_behavior):
        """Test creating a basic behavior."""
        assert sample_behavior.func == sample_handler
        assert sample_behavior.task == "test_task"
        assert sample_behavior.layer == HandlerLayer.LOCAL
        assert sample_behavior.priority == HandlerPriority.NORMAL

    def test_behavior_has_uid(self, sample_behavior):
        """Test that behavior has a unique ID."""
        assert sample_behavior.uid is not None

    def test_behavior_with_different_layers(self):
        """Test creating behaviors with different layers."""
        b_inline = Behavior(
            func=sample_handler,
            task="test",
            layer=HandlerLayer.INLINE
        )
        b_global = Behavior(
            func=sample_handler,
            task="test",
            layer=HandlerLayer.GLOBAL
        )

        assert b_inline.layer == HandlerLayer.INLINE
        assert b_global.layer == HandlerLayer.GLOBAL

    def test_behavior_with_different_priorities(self):
        """Test creating behaviors with different priorities."""
        b_first = Behavior(
            func=sample_handler,
            task="test",
            priority=HandlerPriority.FIRST
        )
        b_last = Behavior(
            func=sample_handler,
            task="test",
            priority=HandlerPriority.LAST
        )

        assert b_first.priority == HandlerPriority.FIRST
        assert b_last.priority == HandlerPriority.LAST


# Note: Behavior calling tests are in test_dispatch_comprehensive.py
# which will be moved to this package. Commenting out incomplete tests
# for now.
#
# class TestBehaviorCalling:
#     """Tests for calling behaviors and receipt generation."""
#
#     def test_call_behavior_returns_receipt(self, sample_behavior):
#         """Test that calling a behavior returns a CallReceipt."""
#         ctx = {}
#         receipt = sample_behavior(ctx)
#
#         assert isinstance(receipt, CallReceipt)
#         assert receipt.result == "result"
#         assert receipt.result_code == ResultCode.OK
#
#     def test_call_behavior_with_context(self):
#         """Test calling behavior with context."""
#         def handler_with_ctx(ctx):
#             return ctx.get("value", "default")
#
#         b = Behavior(func=handler_with_ctx, task="test")
#         ctx = {"value": "custom"}
#
#         receipt = b(ctx)
#
#         assert receipt.result == "custom"
#
#     def test_call_behavior_captures_origin(self, sample_behavior):
#         """Test that receipt captures behavior origin."""
#         ctx = {}
#         receipt = sample_behavior(ctx)
#
#         assert receipt.origin_id == sample_behavior.uid


# ============================================================================
# Priority and Layer Tests
# ============================================================================

class TestHandlerPriority:
    """Tests for HandlerPriority enum."""

    def test_priority_ordering(self):
        """Test that priorities have correct numeric ordering."""
        assert HandlerPriority.FIRST < HandlerPriority.NORMAL
        assert HandlerPriority.NORMAL < HandlerPriority.LAST

    def test_all_priority_values(self):
        """Test that all priority values are defined."""
        priorities = [p.name for p in HandlerPriority]
        assert "FIRST" in priorities
        assert "NORMAL" in priorities
        assert "LAST" in priorities


class TestHandlerLayer:
    """Tests for HandlerLayer enum."""

    def test_layer_ordering(self):
        """Test that layers have correct numeric ordering."""
        assert HandlerLayer.INLINE < HandlerLayer.LOCAL
        assert HandlerLayer.LOCAL < HandlerLayer.AUTHOR
        assert HandlerLayer.AUTHOR < HandlerLayer.APPLICATION
        assert HandlerLayer.APPLICATION < HandlerLayer.SYSTEM
        assert HandlerLayer.SYSTEM < HandlerLayer.GLOBAL

    def test_all_layer_values(self):
        """Test that all layer values are defined."""
        layers = [layer.name for layer in HandlerLayer]
        assert "INLINE" in layers
        assert "LOCAL" in layers
        assert "AUTHOR" in layers
        assert "APPLICATION" in layers
        assert "SYSTEM" in layers
        assert "GLOBAL" in layers


# ============================================================================
# Result Code Tests
# ============================================================================

class TestResultCode:
    """Tests for ResultCode enum."""

    def test_all_result_codes(self):
        """Test that all result codes are defined."""
        codes = [code.value for code in ResultCode]
        assert "ok" in codes
        assert "skip" in codes
        assert "invalid" in codes
        assert "none" in codes
        assert "error" in codes

    def test_result_code_is_string(self):
        """Test that result codes are string values."""
        assert isinstance(ResultCode.OK.value, str)
        assert ResultCode.OK.value == "ok"


# ============================================================================
# Edge Cases and Special Scenarios
# ============================================================================

class TestBehaviorEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_receipt_with_none_result(self):
        """Test receipt with None result."""
        receipt = CallReceipt(behavior_id=uuid4(), result=None)
        assert receipt.result is None

    def test_receipt_with_complex_result(self):
        """Test receipt with complex data structures."""
        complex_result = {
            "items": [1, 2, 3],
            "metadata": {"key": "value"},
            "nested": {"deep": {"value": 42}}
        }
        receipt = CallReceipt(behavior_id=uuid4(), result=complex_result)

        assert receipt.result == complex_result
        assert receipt.result["nested"]["deep"]["value"] == 42

    def test_gather_results_empty(self):
        """Test gathering results with no receipts."""
        results = list(CallReceipt.gather_results())
        assert results == []

    def test_first_result_empty(self):
        """Test first_result with no receipts."""
        result = CallReceipt.first_result()
        assert result is None

    def test_receipt_with_message(self):
        """Test receipt with message field."""
        receipt = CallReceipt(
            behavior_id=uuid4(),
            result="test",
            message="Test message"
        )
        assert receipt.message == "Test message"

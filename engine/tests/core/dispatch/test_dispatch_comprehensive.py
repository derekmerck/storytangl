"""
Comprehensive test suite for Behavior and BehaviorRegistry (v37.2 dispatch system)

Tests cover:
- Behavior construction and inference
- All five HandlerType patterns
- Selection and filtering
- Dispatch and execution
- Priority ordering
- Task filtering
- Origin tracking and distance sorting
- Chained registry dispatch
- Edge cases and error conditions
"""

from __future__ import annotations
import weakref
from typing import Any, Self
import logging

import pytest

from tangl.core import Entity, CallReceipt
from tangl.core.behavior.behavior import (
    Behavior,
    HandlerLayer,
    HandlerType,
    HandlerPriority
)
from tangl.core.behavior.behavior_registry import BehaviorRegistry

from tangl.utils.func_info import FuncInfo


# ============================================================================
# Test Fixtures
# ============================================================================

class Character(Entity):
    """Test entity representing a caller."""
    health: int = 100

    def self_heal(self, ctx=None) -> str:
        return "healed_self"

    @classmethod
    def class_heal_all(cls, caller: Self, ctx=None) -> str:
        return "healed_all"


class GameMaster(Entity):
    """Test entity representing an owner/manager."""

    def manage_character(self, caller: Character, ctx=None) -> str:
        return f"managed_{caller.label}"

    @classmethod
    def oversee(cls, caller: Character, ctx=None) -> str:
        return "overseeing"


def static_handler(caller: Character, ctx=None) -> str:
    """Free function handler."""
    return "static_result"


# ============================================================================
# Behavior Construction and Inference Tests
# ============================================================================

class TestBehaviorConstruction:
    """Test Behavior model construction and FuncInfo inference."""

    def test_static_handler_inference(self):
        """Static handler inferred from free function."""
        b = Behavior(func=static_handler)
        assert b.handler_type == HandlerType.STATIC
        assert b.caller_cls == Character
        assert b.owner is None
        assert b.owner_cls is None

    def test_instance_on_caller_inference(self):
        """Instance-on-caller inferred from unbound method."""
        b = Behavior(func=Character.self_heal)
        assert b.handler_type == HandlerType.INSTANCE_ON_CALLER
        assert b.caller_cls == Character
        assert b.owner is None

    def test_class_on_caller_inference(self):
        """Class-on-caller inferred from classmethod."""
        b = Behavior(func=Character.class_heal_all)

        info = FuncInfo.debug_func(Character.class_heal_all)
        logging.debug(info)

        assert b.handler_type == HandlerType.CLASS_ON_CALLER
        assert b.caller_cls == Character
        assert b.owner is None

    def test_instance_on_owner_inference_unbound(self):
        """Instance-on-owner inferred from manager method."""

        logging.debug(GameMaster.manage_character)

        b = Behavior(func=GameMaster.manage_character)
        assert b.handler_type == HandlerType.INSTANCE_ON_OWNER
        assert b.caller_cls == Character
        assert b.owner_cls == GameMaster
        assert b.owner is None

    def test_instance_on_owner_with_bound_method(self):
        """Instance-on-owner with bound method weakrefs owner."""
        gm = GameMaster(label="gm1")
        b = Behavior(func=gm.manage_character)

        assert b.handler_type == HandlerType.INSTANCE_ON_OWNER
        assert b.caller_cls == Character
        assert b.owner_cls == GameMaster
        assert isinstance(b.owner, weakref.ReferenceType)
        assert b.owner() is gm

    def test_instance_on_owner_explicit_owner(self):
        """Instance-on-owner with explicit owner parameter."""
        gm = GameMaster(label="gm2")
        b = Behavior(func=GameMaster.manage_character, owner=gm)

        logging.debug(FuncInfo.debug_func(GameMaster.manage_character))

        assert b.handler_type == HandlerType.INSTANCE_ON_OWNER
        assert isinstance(b.owner, weakref.ReferenceType)
        assert b.owner() is gm
        assert b.owner_cls == GameMaster

    def test_class_on_owner_explicit(self):
        """Class-on-owner requires explicit owner_cls."""
        b = Behavior(
            func=GameMaster.oversee,
            owner_cls=GameMaster,
            handler_type=HandlerType.CLASS_ON_OWNER
        )
        assert b.handler_type == HandlerType.CLASS_ON_OWNER
        assert b.caller_cls == Character
        assert b.owner_cls == GameMaster

    def test_explicit_handler_type_preserved(self):
        """Explicit handler_type overrides inference."""
        b = Behavior(
            func=static_handler,
            handler_type=HandlerType.INSTANCE_ON_CALLER
        )
        assert b.handler_type == HandlerType.INSTANCE_ON_CALLER

    def test_weakref_cleanup_on_owner_deletion(self):
        """Weakref returns None after owner is deleted."""
        gm = GameMaster(label="temp")
        b = Behavior(func=gm.manage_character)

        assert b.owner() is gm

        del gm
        assert b.owner() is None


class TestBehaviorProperties:
    """Test Behavior properties and methods."""

    def test_default_priority(self):
        """Default priority is NORMAL."""
        b = Behavior(func=static_handler)
        assert b.priority == HandlerPriority.NORMAL

    def test_custom_priority(self):
        """Custom priority is preserved."""
        b = Behavior(func=static_handler, priority=HandlerPriority.FIRST)
        assert b.priority == HandlerPriority.FIRST

    def test_task_assignment(self):
        """Task can be assigned directly."""
        b = Behavior(func=static_handler, task="validate")
        assert b.task == "validate"

    def test_has_task_exact_match(self):
        """has_task returns True for exact match."""
        b = Behavior(func=static_handler, task="validate")
        assert b.has_task("validate")

        # Loose handlers always match tho bc they are considered to be INLINE
        assert b.has_task("render")

        # Add it to a registry and it will still match validate, but NOT render
        r = BehaviorRegistry()
        r.add_behavior(b)

        assert b.has_task("validate")
        assert not b.has_task("render")

        # Unless we attach "render" as a global task for the registry
        r.task = "render"
        assert b.has_task("render")

    def test_has_task_none_always_matches(self):
        """has_task(None) always returns True."""
        b = Behavior(func=static_handler, task="validate")
        assert b.has_task(None)

    def test_has_task_inline_handlers(self):
        """Inline handlers match any task."""
        b = Behavior(func=static_handler)
        # Set handler_layer to INLINE via origin
        registry = BehaviorRegistry(handler_layer=HandlerLayer.INLINE)
        b.origin = registry

        assert b.has_task("validate")
        assert b.has_task("render")
        assert b.has_task("anything")

    def test_label_defaults_to_func_name(self):
        """Label defaults to function name."""
        b = Behavior(func=static_handler)
        assert b.get_label() == "static_handler"

    def test_label_can_be_overridden(self):
        """Label can be explicitly set."""
        b = Behavior(func=static_handler, label="custom_label")
        assert b.get_label() == "custom_label"

    def test_has_func_name(self):
        """has_func_name matches function name."""
        b = Behavior(func=static_handler)
        assert b.has_func_name("static_handler")
        assert not b.has_func_name("other_name")


class TestBehaviorSorting:
    """Test Behavior sorting and comparison."""

    def test_priority_ordering(self):
        """Behaviors sort by priority ascending."""
        b1 = Behavior(func=static_handler, priority=HandlerPriority.FIRST)
        b2 = Behavior(func=static_handler, priority=HandlerPriority.LAST)
        b3 = Behavior(func=static_handler, priority=HandlerPriority.NORMAL)

        behaviors = sorted([b2, b3, b1])
        assert behaviors == [b1, b3, b2]

    def test_mro_dist_calculation(self):
        """mro_dist calculates inheritance distance."""

        class BaseChar(Character):
            pass

        class SpecialChar(BaseChar):
            pass

        b = Behavior(func=static_handler)
        b.caller_cls = Character

        assert b.mro_dist(Character()) == 0
        assert b.mro_dist(BaseChar()) == 1
        assert b.mro_dist(SpecialChar()) == 2

    def test_mro_dist_unrelated_class(self):
        """mro_dist returns large value for unrelated classes."""
        b = Behavior(func=static_handler)
        b.caller_cls = Character

        class UnrelatedEntity(Entity):
            pass

        dist = b.mro_dist(UnrelatedEntity())
        assert dist > 1000  # "very far"


# ============================================================================
# Behavior Execution Tests
# ============================================================================

class TestBehaviorExecution:
    """Test calling behaviors with different handler types."""

    def test_static_handler_execution(self):
        """Static handler executes with caller."""
        b = Behavior(func=static_handler)
        char = Character(label="hero")

        receipt = b(char, ctx={})
        assert receipt.result == "static_result"

    def test_instance_on_caller_execution(self):
        """Instance-on-caller binds to caller."""
        b = Behavior(func=Character.self_heal)
        char = Character(label="hero")

        receipt = b(char, ctx={})
        assert receipt.result == "healed_self"

    def test_class_on_caller_execution(self):
        """Class-on-caller passes caller to classmethod."""
        b = Behavior(func=Character.class_heal_all)
        char = Character(label="hero")

        receipt = b(char, ctx={})
        assert receipt.result == "healed_all"

    def test_instance_on_owner_execution(self):
        """Instance-on-owner binds to owner instance."""
        gm = GameMaster(label="gm")
        b = Behavior(func=gm.manage_character)
        char = Character(label="hero")

        receipt = b(char, ctx={})
        assert receipt.result == "managed_hero"

    def test_class_on_owner_execution(self):
        """Class-on-owner uses owner class."""
        b = Behavior(
            func=GameMaster.oversee,
            owner_cls=GameMaster,
            handler_type=HandlerType.CLASS_ON_OWNER
        )
        char = Character(label="hero")

        receipt = b(char, ctx={})
        assert receipt.result == "overseeing"

    def test_execution_with_context(self):
        """Context is passed through to handler."""

        def handler_with_ctx(caller, ctx=None):
            return ctx.get("value", "default")

        b = Behavior(func=handler_with_ctx)
        char = Character(label="hero")

        receipt = b(char, ctx={"value": "custom"})
        assert receipt.result == "custom"

    def test_execution_creates_receipt(self):
        """Execution creates CallReceipt with metadata."""
        b = Behavior(func=static_handler, task="validate")
        char = Character(label="hero")

        receipt = b(char, ctx={})

        assert isinstance(receipt, CallReceipt)
        assert receipt.result == "static_result"
        assert receipt.origin_id is b.uid


# ============================================================================
# BehaviorRegistry Tests
# ============================================================================

class TestBehaviorRegistryConstruction:
    """Test BehaviorRegistry initialization and configuration."""

    def test_default_layer(self):
        """Default handler layer is GLOBAL."""
        registry = BehaviorRegistry()
        assert registry.handler_layer == HandlerLayer.GLOBAL

    def test_custom_layer(self):
        """Behavior layer can be set."""
        registry = BehaviorRegistry(handler_layer=HandlerLayer.APPLICATION)
        assert registry.handler_layer == HandlerLayer.APPLICATION

    def test_default_task(self):
        """Task can be set on registry."""
        registry = BehaviorRegistry(task="validate")
        assert registry.task == "validate"


class TestBehaviorRegistryAddBehavior:
    """Test adding behaviors to registry."""

    def test_add_callable(self):
        """add_behavior accepts callable and creates Behavior."""
        registry = BehaviorRegistry()
        registry.add_behavior(static_handler, task="test")

        assert len(registry) == 1
        b = list(registry.values())[0]
        assert isinstance(b, Behavior)
        assert b.func is static_handler

    def test_add_behavior_object(self):
        """add_behavior accepts Behavior object."""
        registry = BehaviorRegistry()
        b = Behavior(func=static_handler)
        registry.add_behavior(b)

        assert len(registry) == 1
        assert list(registry.values())[0] is b

    def test_add_sets_origin(self):
        """add_behavior sets origin to registry."""
        registry = BehaviorRegistry()
        registry.add_behavior(static_handler)

        b = list(registry.values())[0]
        assert b.origin is registry

    def test_add_with_priority(self):
        """Priority is passed through."""
        registry = BehaviorRegistry()
        registry.add_behavior(
            static_handler,
            priority=HandlerPriority.FIRST
        )

        b = list(registry.values())[0]
        assert b.priority == HandlerPriority.FIRST

    def test_add_with_handler_type(self):
        """Behavior type hint is respected."""
        registry = BehaviorRegistry()
        registry.add_behavior(
            static_handler,
            handler_type=HandlerType.INSTANCE_ON_CALLER
        )

        b = list(registry.values())[0]
        assert b.handler_type == HandlerType.INSTANCE_ON_CALLER

    def test_add_with_owner(self):
        """Owner parameter is handled."""
        registry = BehaviorRegistry()
        gm = GameMaster(label="gm")
        registry.add_behavior(
            GameMaster.manage_character,
            owner=gm
        )
        logging.debug(FuncInfo.debug_func(GameMaster.manage_character))

        b = list(registry.values())[0]
        assert b.handler_type == HandlerType.INSTANCE_ON_OWNER
        assert isinstance(b.owner, weakref.ReferenceType)

    def test_add_multiple_behaviors(self):
        """Multiple behaviors can be added."""
        registry = BehaviorRegistry()

        registry.add_behavior(static_handler, task="task1")
        registry.add_behavior(Character.self_heal, task="task2")
        registry.add_behavior(GameMaster.oversee, task="task3")

        assert len(registry) == 3

        for t in ["task1", "task2", "task3"]:
            assert t in registry.all_tasks()


class TestBehaviorRegistryDecorator:
    """Test @registry.register decorator."""

    def test_register_decorator_basic(self):
        """@register decorator adds behavior."""
        registry = BehaviorRegistry()

        @registry.register()
        def my_handler(caller: Character, ctx=None):
            return "decorated"

        assert len(registry) == 1
        b = list(registry.values())[0]
        assert b.func is my_handler

    def test_register_decorator_with_attrs(self):
        """@register passes through attributes."""
        registry = BehaviorRegistry()

        @registry.register(priority=HandlerPriority.FIRST, task="validate")
        def my_handler(caller: Character, ctx=None):
            return "first"

        b = list(registry.values())[0]
        assert b.priority == HandlerPriority.FIRST
        assert b.task == "validate"

    def test_register_decorator_preserves_function(self):
        """@register returns original function."""
        registry = BehaviorRegistry()

        @registry.register()
        def my_handler(caller: Character, ctx=None):
            return "result"

        # Function is still callable
        assert callable(my_handler)
        assert my_handler.__name__ == "my_handler"

    def test_register_adds_behavior_attribute(self):
        """@register adds _behavior attribute."""
        registry = BehaviorRegistry()

        @registry.register()
        def my_handler(caller: Character, ctx=None):
            return "result"

        assert hasattr(my_handler, "_behavior")
        assert isinstance(my_handler._behavior, Behavior)


class TestBehaviorRegistrySelection:
    """Test selecting behaviors from registry."""

    def test_select_all_for_basic(self):
        """select_all_for returns matching behaviors."""
        registry = BehaviorRegistry()
        registry.add_behavior(static_handler, task="validate")

        char = Character(label="hero")
        behaviors = list(registry.select_all_for(selector=char))

        assert len(behaviors) == 1
        assert behaviors[0].func is static_handler

    def test_select_all_for_task_filter(self):
        """select_all_for filters by has_task."""
        registry = BehaviorRegistry()
        registry.add_behavior(static_handler, task="validate")
        registry.add_behavior(Character.self_heal, task="heal")

        char = Character(label="hero")
        behaviors = list(registry.select_all_for(
            selector=char,
            has_task="validate"
        ))

        assert len(behaviors) == 1
        assert behaviors[0].func is static_handler

    def test_select_all_for_caller_cls_filter(self):
        """select_all_for filters by caller class."""
        registry = BehaviorRegistry()

        def char_handler(caller: Character, ctx=None):
            return "char"

        def gm_handler(caller: GameMaster, ctx=None):
            return "gm"

        registry.add_behavior(char_handler)
        registry.add_behavior(gm_handler)

        char = Character(label="hero")
        behaviors = list(registry.select_all_for(selector=char))

        # Should only get char_handler
        assert len(behaviors) == 1
        assert behaviors[0].func is char_handler

    def test_select_all_for_sorting(self):
        """select_all_for returns sorted behaviors."""
        registry = BehaviorRegistry()

        # Add in reverse priority order
        registry.add_behavior(
            static_handler,
            priority=HandlerPriority.LAST,
            label="last"
        )
        registry.add_behavior(
            Character.self_heal,
            priority=HandlerPriority.FIRST,
            label="first"
        )
        registry.add_behavior(
            Character.class_heal_all,
            priority=HandlerPriority.NORMAL,
            label="normal"
        )

        char = Character(label="hero")
        # Need to invoke the built-in __lt__ for sorting
        behaviors = list(registry.select_all_for(selector=char, sort_key=lambda x: x))

        # Should be sorted FIRST -> NORMAL -> LAST
        assert len(behaviors) == 3
        assert behaviors[0].get_label() == "first"
        assert behaviors[1].get_label() == "normal"
        assert behaviors[2].get_label() == "last"


class TestBehaviorRegistryDispatch:
    """Test dispatching behaviors."""

    def test_dispatch_basic(self):
        """dispatch executes matching behaviors."""
        registry = BehaviorRegistry()
        registry.add_behavior(static_handler)

        char = Character(label="hero")
        receipts = list(registry.dispatch(caller=char, ctx=None))

        assert len(receipts) == 1
        assert receipts[0].result == "static_result"

    def test_dispatch_with_task_param(self):
        """dispatch task parameter filters behaviors."""
        registry = BehaviorRegistry()
        registry.add_behavior(static_handler, task="validate")
        registry.add_behavior(Character.self_heal, task="heal")

        char = Character(label="hero")
        receipts = list(registry.dispatch(caller=char, task="heal", ctx=None))

        assert len(receipts) == 1
        assert receipts[0].result == "healed_self"

    def test_dispatch_with_context(self):
        """dispatch passes context to behaviors."""

        def ctx_handler(caller, ctx=None):
            return ctx.get("test_value")

        registry = BehaviorRegistry()
        registry.add_behavior(ctx_handler)

        char = Character(label="hero")
        receipts = list(registry.dispatch(
            caller=char,
            ctx={"test_value": "success"}
        ))

        assert receipts[0].result == "success"

    def test_dispatch_with_extra_handlers(self):
        """dispatch includes extra_handlers."""
        registry = BehaviorRegistry()
        registry.add_behavior(static_handler)

        def extra_handler(caller, ctx=None):
            return "extra"

        char = Character(label="hero")
        receipts = list(registry.dispatch(
            caller=char,
            ctx=None,
            extra_handlers=[extra_handler]
        ))

        assert len(receipts) == 2
        results = [r.result for r in receipts]
        assert "static_result" in results
        assert "extra" in results

    def test_dispatch_empty_registry(self):
        """dispatch returns empty iterator for empty registry."""
        registry = BehaviorRegistry()
        char = Character(label="hero")

        receipts = list(registry.dispatch(caller=char, ctx=None))
        assert len(receipts) == 0

    def test_dispatch_preserves_order(self):
        """dispatch executes behaviors in priority order."""
        registry = BehaviorRegistry()
        results = []

        def make_handler(name, priority):
            def handler(caller, ctx=None):
                results.append(name)
                return name

            return handler

        registry.add_behavior(
            make_handler("last", HandlerPriority.LAST),
            priority=HandlerPriority.LAST
        )
        registry.add_behavior(
            make_handler("first", HandlerPriority.FIRST),
            priority=HandlerPriority.FIRST
        )
        registry.add_behavior(
            make_handler("normal", HandlerPriority.NORMAL),
            priority=HandlerPriority.NORMAL
        )

        char = Character(label="hero")
        list(registry.dispatch(caller=char, ctx=None))

        assert results == ["first", "normal", "last"]


class TestBehaviorRegistryChainDispatch:
    """Test chaining multiple registries."""

    def test_chain_dispatch_basic(self):
        """chain_dispatch merges behaviors from multiple registries."""
        reg1 = BehaviorRegistry(handler_layer=HandlerLayer.GLOBAL)
        reg1.add_behavior(static_handler)

        reg2 = BehaviorRegistry(handler_layer=HandlerLayer.APPLICATION)
        reg2.add_behavior(Character.self_heal)

        char = Character(label="hero")
        receipts = list(BehaviorRegistry.chain_dispatch(
            reg1, reg2,
            caller=char,
            ctx=None
        ))

        assert len(receipts) == 2
        results = [r.result for r in receipts]
        assert "static_result" in results
        assert "healed_self" in results

    def test_chain_dispatch_with_task(self):
        """chain_dispatch filters by task across registries."""
        reg1 = BehaviorRegistry()
        reg1.add_behavior(static_handler, task="validate")

        reg2 = BehaviorRegistry()
        reg2.add_behavior(Character.self_heal, task="heal")

        char = Character(label="hero")
        receipts = list(BehaviorRegistry.chain_dispatch(
            reg1, reg2,
            caller=char,
            ctx=None,
            task="validate"
        ))

        assert len(receipts) == 1
        assert receipts[0].result == "static_result"

    def test_chain_dispatch_priority_across_registries(self):
        """chain_dispatch sorts by priority across all registries."""
        reg1 = BehaviorRegistry()
        reg2 = BehaviorRegistry()
        results = []

        def make_handler(name, priority):
            def handler(caller, ctx=None):
                results.append(name)
                return name

            return handler

        reg1.add_behavior(
            make_handler("reg1_normal", HandlerPriority.NORMAL),
            priority=HandlerPriority.NORMAL
        )
        reg2.add_behavior(
            make_handler("reg2_first", HandlerPriority.FIRST),
            priority=HandlerPriority.FIRST
        )
        reg1.add_behavior(
            make_handler("reg1_last", HandlerPriority.LAST),
            priority=HandlerPriority.LAST
        )

        char = Character(label="hero")
        list(BehaviorRegistry.chain_dispatch(reg1, reg2, caller=char, ctx=None))

        assert results == ["reg2_first", "reg1_normal", "reg1_last"]


# ============================================================================
# Integration and Edge Case Tests
# ============================================================================

class TestCompleteWorkflow:
    """Integration tests for complete dispatch workflows."""

    def test_full_game_scenario(self):
        """Complete scenario with multiple handler types."""
        # Setup registries
        global_reg = BehaviorRegistry(
            handler_layer=HandlerLayer.GLOBAL,
            task="turn"
        )
        app_reg = BehaviorRegistry(
            handler_layer=HandlerLayer.APPLICATION,
            task="turn"
        )

        # Global validation
        def validate_state(caller: Character, ctx=None):
            return {"valid": caller.health > 0}

        global_reg.add_behavior(
            validate_state,
            priority=HandlerPriority.FIRST
        )

        # Application logic
        gm = GameMaster(label="gm")
        app_reg.add_behavior(
            gm.manage_character,
            priority=HandlerPriority.NORMAL
        )

        # Character self-action
        app_reg.add_behavior(
            Character.self_heal,
            priority=HandlerPriority.LATE
        )

        # Execute
        char = Character(label="hero", health=50)
        receipts = list(BehaviorRegistry.chain_dispatch(
            global_reg, app_reg,
            caller=char,
            ctx=None,
            task="turn"
        ))

        assert len(receipts) == 3
        assert receipts[0].result["valid"] is True
        assert receipts[1].result == "managed_hero"
        assert receipts[2].result == "healed_self"

    def test_deterministic_execution_order(self):
        """Execution order is deterministic across multiple runs."""
        registry = BehaviorRegistry()

        for i in range(10):
            registry.add_behavior(
                lambda caller, ctx=None, n=i: n,
                priority=HandlerPriority.NORMAL,
                label=f"handler_{i}"
            )

        char = Character(label="hero")

        # Run multiple times
        runs = []
        for _ in range(5):
            receipts = list(registry.dispatch(caller=char, ctx=None))
            order = [registry.get(r.origin_id) for r in receipts]
            runs.append(order)

        # All runs should have same order
        first_run = runs[0]
        for run in runs[1:]:
            assert run == first_run

    def test_receipt_gathering(self):
        """CallReceipt.gather_results collects results."""
        registry = BehaviorRegistry()

        registry.add_behavior(lambda caller, ctx=None: 1)
        registry.add_behavior(lambda caller, ctx=None: 2)
        registry.add_behavior(lambda caller, ctx=None: 3)

        print([r.func(None) for r in registry.values()])

        char = Character(label="hero")
        receipts = list(registry.dispatch(caller=char, ctx=None))
        print([r.result for r in receipts])

        results = list( CallReceipt.gather_results(*receipts) )
        assert results == [1, 2, 3]


class TestErrorConditions:
    """Test error handling and edge cases."""

    def test_invalid_item_type_raises_error(self):
        """add_behavior raises error for invalid types."""
        registry = BehaviorRegistry()

        with pytest.raises(ValueError, match="Unknown behavior type"):
            registry.add_behavior("not a callable")

    def test_task_and_has_task_conflict_raises_error(self):
        """dispatch raises error if both task and has_task provided."""
        registry = BehaviorRegistry()
        registry.add_behavior(static_handler)

        char = Character(label="hero")

        with pytest.raises(TypeError, match="unexpected.*has_task"):
            list(registry.dispatch(
                caller=char,
                ctx=None,
                task="validate",
                has_task="validate"
            ))

    def test_weakref_dead_owner_handling(self):
        """Behavior handles dead weakref gracefully."""
        gm = GameMaster(label="temp")
        b = Behavior(func=gm.manage_character)

        char = Character(label="hero")

        # Delete owner
        del gm

        # Should handle gracefully (implementation dependent)
        # At minimum, should not crash
        try:
            receipt = b(char, ctx={})
            # Might fail or return None, but shouldn't crash unexpectedly
        except Exception as e:
            # Expected behavior - owner is gone
            assert "not defined" in str(e).lower() or "dead" in str(e).lower() or "none" in str(e).lower()


# ============================================================================
# Behavior Layer and Origin Distance Tests
# ============================================================================

class TestOriginTracking:
    """Test origin tracking and distance calculations."""

    def test_origin_set_on_add(self):
        """Origin is set when behavior added to registry."""
        registry = BehaviorRegistry()
        b = Behavior(func=static_handler)

        assert b.origin is None
        registry.add_behavior(b)
        assert b.origin is registry

    def test_handler_layer_from_origin(self):
        """handler_layer returns origin's layer."""
        app_reg = BehaviorRegistry(handler_layer=HandlerLayer.APPLICATION)
        b = Behavior(func=static_handler)
        app_reg.add_behavior(b)

        assert b.handler_layer() == HandlerLayer.APPLICATION

    def test_inline_layer_behavior(self):
        """Inline layer behaviors match any task."""
        inline_reg = BehaviorRegistry(handler_layer=HandlerLayer.INLINE)
        b = Behavior(func=static_handler)
        inline_reg.add_behavior(b)

        assert b.handler_layer() == HandlerLayer.INLINE
        assert b.has_task("any_task")
        assert b.has_task("another_task")


class TestSelectionCriteria:
    """Test custom selection criteria."""

    def test_get_selection_criteria_includes_caller_cls(self):
        """get_selection_criteria includes caller_cls."""
        b = Behavior(func=static_handler)
        criteria = b.get_selection_criteria()

        assert "is_instance" in criteria
        assert criteria["is_instance"] == Character

    def test_custom_selection_criteria(self):
        """Custom selection criteria can be added."""
        b = Behavior(
            func=static_handler,
            selection_criteria={"custom": "value"}
        )
        criteria = b.get_selection_criteria()

        assert criteria["custom"] == "value"


# ============================================================================
# Documentation Examples as Tests
# ============================================================================

class TestDocumentationExamples:
    """Test examples that should appear in docs."""

    def test_css_specificity_metaphor(self):
        """More specific behaviors run last (like CSS specificity)."""
        registry = BehaviorRegistry()
        results = []

        # General handler
        def general(caller: Entity, ctx=None):
            results.append("general")
            return "general"

        # Specific handler
        def specific(caller: Character, ctx=None):
            results.append("specific")
            return "specific"

        registry.add_behavior(general, priority=HandlerPriority.NORMAL)
        registry.add_behavior(specific, priority=HandlerPriority.NORMAL)

        char = Character(label="hero")
        list(registry.dispatch(caller=char, ctx=None))

        # Both should run, but specific should be able to
        # "clobber" general if needed (runs later)
        assert "general" in results
        assert "specific" in results


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
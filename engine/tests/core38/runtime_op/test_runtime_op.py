"""Contract tests for ``tangl.core38.runtime_op``."""

from __future__ import annotations

from random import Random

import pytest

from tangl.core38.runtime_op import RuntimeOp


class TestRuntimeOpNamespaceHandling:
    def test_exec_preserves_passed_empty_namespace_identity(self) -> None:
        ns: dict[str, int] = {}
        result = RuntimeOp(expr="x = 1").exec(ns)
        assert result is ns
        assert ns["x"] == 1

    def test_eval_preserves_passed_empty_namespace_object(self) -> None:
        ns: dict[str, int] = {}
        RuntimeOp(expr="0").eval(ns)
        assert ns == {}

    def test_apply_all_mutates_shared_passed_empty_namespace(self) -> None:
        ns: dict[str, int] = {}
        result = RuntimeOp.apply_all("x = 1", "x = x + 1", ns=ns)
        assert result is ns
        assert ns["x"] == 2

    def test_eval_restricts_unsafe_builtins(self) -> None:
        with pytest.raises(NameError):
            RuntimeOp(expr="__import__('os')").eval({})

    def test_all_satisfied_by_accepts_rand(self) -> None:
        result = RuntimeOp.all_satisfied_by(
            "rand.random() < 0.5",
            "x == 1",
            ns={"x": 1},
            rand=Random(1),
        )
        assert isinstance(result, bool)
        assert result is True

    def test_eval_ignores_extra_globals_builtins_override(self) -> None:
        result = RuntimeOp._eval_expr(
            "len([1, 2, 3])",
            {},
            extra_globals={"__builtins__": {}},
        )
        assert result == 3

    def test_exec_ignores_extra_globals_builtins_override(self) -> None:
        ns: dict[str, int] = {}
        RuntimeOp._exec_expr(
            "x = len([1, 2, 3])",
            ns,
            extra_globals={"__builtins__": {}},
        )
        assert ns["x"] == 3

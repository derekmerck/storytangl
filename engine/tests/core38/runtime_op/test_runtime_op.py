"""Contract tests for ``tangl.core38.runtime_op``."""

from __future__ import annotations

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

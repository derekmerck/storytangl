"""Review direct serialization calls in Core, VM, and Story.

This static syntax guard permits reviewed constructor-form implementations and
local schema or DTO operations. It is not a ban on Pydantic or JSON, nor proof
of graph persistence fidelity; constructor-form round-trip tests still matter.
The scan recognizes direct calls and simple JSON import aliases, without type
inference or tracking dynamically rebound names.
"""

from __future__ import annotations

import ast
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[2] / "src" / "tangl"

# Keys identify the narrow reviewed scope and operation, not incidental line counts.
REVIEWED = {
    ("core/bases.py", "Unstructurable.unstructure", "model_dump"):
        "Canonical constructor-form field extraction.",
    ("core/token.py", "Token.unstructure", "model_dump"):
        "Canonical token instance-field selection.",
    ("core/base_fragment.py", "BaseFragment.model_dump", "model_dump"):
        "Public fragment DTO dump customization.",
    ("story/episode/action.py", "Action._serialize_accepts", "model_dump"):
        "Typed accepts DTO projection.",
    ("story/fabula/compiler.py", "StoryCompiler.validate_ir", "model_validate"):
        "Explicit authored schema validation.",
    ("story/fabula/compiler.py", "StoryCompiler.compile", "model_dump"):
        "Local validated StoryScript snapshot.",
    ("story/fabula/compiler.py", "StoryCompiler._phase_effects", "model_validate"):
        "Typed authored effect validation.",
    ("story/analysis.py", "_dot_quote", "json.dumps"):
        "JSON string escaping for DOT output.",
}


def _calls(source: str, path: str) -> list[tuple[str, str, int, str]]:
    tree = ast.parse(source, filename=path)
    json_modules: set[str] = set()
    json_functions: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            json_modules.update(alias.asname or alias.name for alias in node.names
                                if alias.name == "json")
        elif isinstance(node, ast.ImportFrom) and node.module == "json" and node.level == 0:
            json_functions.update({alias.asname or alias.name: f"json.{alias.name}"
                                   for alias in node.names if alias.name in {"dumps", "loads"}})

    calls: list[tuple[str, str, int, str]] = []

    class Visitor(ast.NodeVisitor):
        scope: list[str]

        def __init__(self) -> None:
            self.scope = []

        def _visit_scope(self, node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef) -> None:
            self.scope.append(node.name)
            self.generic_visit(node)
            self.scope.pop()

        visit_ClassDef = _visit_scope
        visit_FunctionDef = _visit_scope
        visit_AsyncFunctionDef = _visit_scope

        def visit_Call(self, node: ast.Call) -> None:
            func = node.func
            operation = None
            if isinstance(func, ast.Attribute):
                if func.attr in {"model_dump", "model_validate"}:
                    operation = func.attr
                elif (func.attr in {"dumps", "loads"} and isinstance(func.value, ast.Name)
                      and func.value.id in json_modules):
                    operation = f"json.{func.attr}"
            elif isinstance(func, ast.Name):
                operation = json_functions.get(func.id)
            if operation:
                calls.append((path, ".".join(self.scope) or "<module>", node.lineno, operation))
            self.generic_visit(node)

    Visitor().visit(tree)
    return calls


def _unreviewed(calls: list[tuple[str, str, int, str]]) -> list[tuple[str, str, int, str]]:
    return [call for call in calls if (call[0], call[1], call[3]) not in REVIEWED]


def test_direct_serialization_calls_are_reviewed() -> None:
    calls = [
        call
        for package in ("core", "vm", "story")
        for path in sorted((SOURCE / package).rglob("*.py"))
        for call in _calls(path.read_text(encoding="utf-8"), path.relative_to(SOURCE).as_posix())
    ]
    violations = _unreviewed(calls)
    used = {(path, scope, operation) for path, scope, _, operation in calls}
    stale = REVIEWED.keys() - used
    assert not violations and not stale, (
        "Review new direct serialization calls; graph persistence uses unstructure/structure.\n"
        + "\n".join(f"{path}:{line}: {scope}: {operation}" for path, scope, line, operation in violations)
        + f"\nStale reviewed scopes: {sorted(stale)}"
    )


def test_review_is_scoped_to_the_enclosing_method() -> None:
    source = '''
class Token:
    def unstructure(self):
        return self.model_dump()
    def new_method(self):
        return self.model_dump()
'''
    assert _unreviewed(_calls(source, "core/token.py")) == [
        ("core/token.py", "Token.new_method", 6, "model_dump")
    ]
    assert _unreviewed(_calls("def save(x):\n    return x.model_validate({})\n", "vm/new.py")) == [
        ("vm/new.py", "save", 2, "model_validate")
    ]


def test_json_imports_are_recognized_without_matching_text_or_unrelated_helpers() -> None:
    source = '''
"""json.dumps(value) is only an example."""
import json
import json as j
from json import loads as decode
def dumps(value):
    return value
def read(value):
    # j.loads(value) is not a call
    dumps(value)
    j.dumps(value)
    json.loads(value)
    return decode(value)
'''
    assert _calls(source, "story/example.py") == [
        ("story/example.py", "read", 11, "json.dumps"),
        ("story/example.py", "read", 12, "json.loads"),
        ("story/example.py", "read", 13, "json.loads"),
    ]

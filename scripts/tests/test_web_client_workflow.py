"""Automatic relevant-change web checks and the always-reported final gate."""

from fnmatch import fnmatchcase
import os
from pathlib import Path
import subprocess

import pytest
import yaml


WORKFLOW_PATH = Path(__file__).resolve().parents[2] / ".github/workflows/web-client.yml"


@pytest.fixture
def workflow() -> dict:
    return yaml.load(WORKFLOW_PATH.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def test_pr_opening_and_main_pushes_participate_without_an_opt_in_label(workflow: dict) -> None:
    triggers = workflow["on"]
    pr = triggers["pull_request"]
    assert pr["branches"] == ["**"]
    if "types" in pr:
        assert {"opened", "synchronize", "reopened"} <= set(pr["types"])
    assert "main" in triggers["push"]["branches"]
    for trigger in (pr, triggers["push"]):
        assert "paths" not in trigger
        assert "paths-ignore" not in trigger

    checks = workflow["jobs"]["web-client-tests"]
    assert checks["needs"] == "changes"
    assert checks["if"] == "needs.changes.outputs.relevant == 'true'"
    assert "ci:web" not in yaml.dump(checks)
    commands = [step.get("run", "") for step in checks["steps"]]
    assert {
        "yarn type-check", "yarn test --run", "yarn build:e2e",
        "yarn test:e2e", "yarn test:e2e:restart",
    } <= set(commands)
    assert "yarn playwright install --with-deps chromium" in commands


@pytest.mark.parametrize("path, relevant", [
    ("apps/web/src/App.vue", True),
    ("apps/server/src/tangl/rest/app.py", True),
    ("engine/src/tangl/service/response.py", True),
    ("worlds/reference/script.yaml", True),
    ("settings.toml", True),
    ("pyproject.toml", True),
    ("poetry.lock", True),
    ("apps/web/yarn.lock", True),
    (".github/workflows/web-client.yml", True),
    ("docs/src/index.md", False),
    ("README.md", False),
])
def test_change_filter_covers_runtime_inputs_but_not_docs_only_changes(
    workflow: dict,
    path: str,
    relevant: bool,
) -> None:
    detector = next(
        step for step in workflow["jobs"]["changes"]["steps"] if step.get("id") == "filter"
    )
    patterns = yaml.safe_load(detector["with"]["filters"])["web"]
    assert any(fnmatchcase(path, pattern) for pattern in patterns) is relevant
    assert "steps.filter.outputs.web" in workflow["jobs"]["changes"]["outputs"]["relevant"]


@pytest.mark.parametrize("change_result, relevant, test_result, passes", [
    ("success", "true", "success", True),
    ("success", "false", "skipped", True),
    ("failure", "true", "success", False),
    ("failure", "false", "skipped", False),
    ("skipped", "false", "skipped", False),
    ("success", "true", "failure", False),
    ("success", "true", "skipped", False),
    ("success", "true", "cancelled", False),
    ("success", "", "skipped", False),
])
def test_final_gate_runs_the_actual_shell_and_rejects_failures_or_unexpected_skips(
    workflow: dict,
    change_result: str,
    relevant: str,
    test_result: str,
    passes: bool,
) -> None:
    gate = workflow["jobs"]["web-client-gate"]
    assert gate["if"] == "always()"
    assert set(gate["needs"]) == {"changes", "web-client-tests"}
    assert gate["env"] == {
        "CHANGE_RESULT": "${{ needs.changes.result }}",
        "RELEVANT": "${{ needs.changes.outputs.relevant }}",
        "TEST_RESULT": "${{ needs.web-client-tests.result }}",
    }
    result = subprocess.run(
        ["bash", "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", gate["steps"][0]["run"]],
        env={
            **os.environ,
            "CHANGE_RESULT": change_result,
            "RELEVANT": relevant,
            "TEST_RESULT": test_result,
        },
        capture_output=True,
        timeout=5,
    )
    assert (result.returncode == 0) is passes

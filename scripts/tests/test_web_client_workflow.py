"""Static contracts for the opt-in web-client workflow."""

from pathlib import Path

import yaml


WORKFLOW_PATH = Path(__file__).resolve().parents[2] / ".github/workflows/web-client.yml"


def test_labeled_web_prs_rerun_while_unlabeled_prs_stay_skipped() -> None:
    workflow = yaml.load(WORKFLOW_PATH.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)

    assert workflow["on"]["pull_request"]["types"] == [
        "labeled",
        "synchronize",
        "reopened",
    ]
    assert workflow["jobs"]["web-client-tests"]["if"] == (
        "github.event_name != 'pull_request' || "
        "contains(github.event.pull_request.labels.*.name, 'ci:web')"
    )

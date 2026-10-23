from __future__ import annotations

import io
import json
from types import SimpleNamespace

import pytest

pytest.importorskip("rich")

from rich.table import Table

from tangl.cli.rendering import PlainTerminalRenderer, RichTerminalRenderer
from tangl.journal.fragments import MediaFragment
from tangl.service.remote_service_manager import RemoteServiceManager
from tangl.service.response import RuntimeEnvelope


@pytest.mark.parametrize("renderer_type", [PlainTerminalRenderer, RichTerminalRenderer])
@pytest.mark.parametrize("remote", [False, True])
def test_unresolved_media_names_survive_remote_dto_without_repr(
    renderer_type: type[PlainTerminalRenderer] | type[RichTerminalRenderer], remote: bool,
) -> None:
    fragment = MediaFragment(
        content={
            "name": "world/audio/theme.mp3",
            "unresolved_reason": "no_offers",
            "resolution_meta": {"alternatives": [{"path": "private/other.mp3"}]},
        },
        content_format="json",
        media_role="music",
    )
    envelope = RuntimeEnvelope(fragments=[fragment])
    if remote:
        wire = json.loads(json.dumps(envelope.to_dto()))
        envelope = RemoteServiceManager("https://example.test/api/v2")._decode_runtime_envelope(wire)
    renderer = renderer_type()
    output = io.StringIO()
    renderer.emit(
        SimpleNamespace(stdout=output, poutput=lambda line: output.write(line + "\n")),
        renderer.story_update(fragments=envelope.fragments, choices=[]),
    )

    transcript = output.getvalue()
    assert "theme.mp3 (unresolved: no_offers)" in transcript
    assert "music" in transcript
    if renderer_type is PlainTerminalRenderer:
        assert "[music: theme.mp3 (unresolved: no_offers)]" in transcript
    for leak in ("resolution_meta", "alternatives", "private/", "world/audio/", "{'name'"):
        assert leak not in transcript


def test_rich_renderer_exports_envelope_text() -> None:
    renderer = RichTerminalRenderer()
    output = io.StringIO()
    cmd = SimpleNamespace(stdout=output)

    renderables = renderer.story_update(
        fragments=[
            SimpleNamespace(
                fragment_type="content",
                content_format="md",
                content="You unfold the **permit**.",
            ),
            SimpleNamespace(
                fragment_type="media",
                media_role="narrative_image",
                content="/tmp/permit-9472.jpg",
            ),
            SimpleNamespace(
                fragment_type="kv",
                content=[
                    {"key": "permit_seal", "value": "Imperial"},
                    {"key": "permit_expiry", "value": "expired"},
                ],
            ),
            {
                "fragment_type": "piece",
                "piece_id": "permit-7",
                "content": "Gate permit",
            },
        ],
        ux_events=[
            {
                "event_type": "shift_bell",
                "message": "Ten minutes remain.",
                "presentation": "interrupt",
                "severity": "warning",
            }
        ],
        choices=[
            {
                "label": "Verify ID",
                "available": True,
                "accepts": {"kind": "pieces", "min": 1, "max": 1},
                "cost_previews": (
                    {"ledger_key": "time", "delta": -1, "unit": "minute"},
                ),
            },
            SimpleNamespace(
                label="Allow passage",
                active=False,
                unavailable_reason="Permit expired",
                blockers=(
                    {
                        "code": "permit_expired",
                        "message": "The permit expired yesterday.",
                    },
                ),
            ),
        ],
        metadata={
            "info_state": {"available_channels": ["ui-map"]},
        },
    )
    renderer.emit(cmd, renderables)

    transcript = output.getvalue()
    assert "Story Update" in transcript
    assert "You unfold the permit." in transcript
    assert "narrative_image" in transcript
    assert "permit-9472.jpg" in transcript
    assert "permit_expiry" in transcript
    assert "shift_bell" in transcript
    assert "[permit-7] Gate permit" in transcript
    assert "Verify ID" in transcript
    assert "piece ids: 1" in transcript
    assert "cost: time -1 minute" in transcript
    assert "Allow passage" in transcript
    assert "Permit expired" in transcript
    assert "cost: time -1 minute" in transcript
    assert "The permit expired yesterday." in " ".join(transcript.split())
    assert "/m Map" not in transcript


def test_rich_renderer_exports_diagnostic_transcript() -> None:
    renderer = RichTerminalRenderer()
    output = io.StringIO()
    cmd = SimpleNamespace(stdout=output)

    renderer.emit(cmd, renderer.diagnostic())

    transcript = output.getvalue()
    assert "Diagnostic Envelope" in transcript
    assert "Bek" in transcript
    assert "narrative_image" in transcript
    assert "Allow passage" in transcript
    assert "Permit expired" in transcript
    assert "Unknown fragments remain visible" in transcript
    assert "Projected State" in transcript
    assert "Candidates" in transcript


def test_rich_projected_state_renders_native_tables() -> None:
    renderer = RichTerminalRenderer()

    renderables = renderer.projected_state(
        {
            "sections": [
                {
                    "section_id": "candidates",
                    "title": "Candidates",
                    "value": {
                        "value_type": "table",
                        "columns": ["Candidate", "Decision"],
                        "rows": [["Bek Tarsus", "Review"]],
                    },
                }
            ]
        }
    )

    assert len(renderables) == 1
    assert isinstance(renderables[0], Table)
    assert renderables[0].title == "Candidates"

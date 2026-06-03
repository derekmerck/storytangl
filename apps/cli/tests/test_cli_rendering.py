from __future__ import annotations

import io
from types import SimpleNamespace

from tangl.cli.rendering import RichTerminalRenderer


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
            SimpleNamespace(
                fragment_type="user_event",
                event_type="shift_bell",
                content="Ten minutes remain.",
            ),
        ],
        choices=[
            SimpleNamespace(label="Verify ID", active=True),
            SimpleNamespace(
                label="Allow passage",
                active=False,
                unavailable_reason="Permit expired",
            ),
        ],
        metadata={
            "info_affordances": [
                {"kind": "map", "label": "Map", "shortcuts": ["m"]},
                {"kind": "inventory", "label": "Inventory", "shortcuts": ["i"]},
            ],
            "info_state": {"available_kinds": ["map"]},
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
    assert "Verify ID" in transcript
    assert "Allow passage" in transcript
    assert "Permit expired" in transcript
    assert "/m Map" in transcript
    assert "Inventory" not in transcript


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
    assert "/r Registry" in transcript

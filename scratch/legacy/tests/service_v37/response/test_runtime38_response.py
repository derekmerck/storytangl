from __future__ import annotations

from uuid import uuid4

from tangl.service.response import RuntimeEnvelope38


def test_runtime_envelope38_defaults() -> None:
    envelope = RuntimeEnvelope38()
    assert envelope.fragments == []
    assert envelope.redirect_trace == []
    assert envelope.metadata == {}


def test_runtime_envelope38_preserves_fragment_order() -> None:
    cursor_id = uuid4()
    fragments = [
        {"fragment_type": "content", "content": "line 1"},
        {"fragment_type": "media", "url": "/img/a.svg"},
        {"fragment_type": "choice", "text": "take cab", "edge_id": str(uuid4())},
    ]
    envelope = RuntimeEnvelope38(cursor_id=cursor_id, step=3, fragments=fragments)
    assert envelope.cursor_id == cursor_id
    assert envelope.step == 3
    assert envelope.fragments == fragments

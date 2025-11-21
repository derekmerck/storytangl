from __future__ import annotations


def test_native_types_importable() -> None:
    from tangl.service.response import FragmentStream, InfoModel, NativeResponse, RuntimeInfo

    assert FragmentStream is not None
    assert InfoModel is not None
    assert NativeResponse is not None
    assert RuntimeInfo is not None

from __future__ import annotations

from uuid import UUID, uuid4

from pydantic import BaseModel

from tangl.persistence.structuring import StructuringHandler


class StructuringModel(BaseModel):
    uid: UUID
    label: str


def test_unstructure_emits_kind() -> None:
    model = StructuringModel(uid=uuid4(), label="demo")

    payload = StructuringHandler.unstructure(model)

    assert payload["kind"] is StructuringModel


def test_structure_prefers_kind() -> None:
    uid = uuid4()
    payload = {"kind": StructuringModel, "uid": uid, "label": "demo"}

    loaded = StructuringHandler.structure(payload)

    assert isinstance(loaded, StructuringModel)
    assert loaded.uid == uid
    assert loaded.label == "demo"

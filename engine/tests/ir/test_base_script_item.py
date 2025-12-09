"""Tests for :mod:`tangl.ir.core_ir.base_script_model`."""

from tangl.core import Record
from tangl.ir.core_ir import BaseScriptItem


def test_base_script_item_is_record() -> None:
    """``BaseScriptItem`` should inherit :class:`~tangl.core.Record`."""

    assert issubclass(BaseScriptItem, Record)


def test_base_script_item_defaults_and_extras() -> None:
    """Instantiation should set defaults and allow Record features."""

    item = BaseScriptItem(obj_cls="Node", templates="demo", extra_field=3)

    assert item.uid is not None
    assert item.template_names == "demo"
    assert item.extra_field == 3
    # Tags come from :class:`Entity` so `None` becomes an empty set.
    assert item.tags == set()


def test_model_dump_emits_string_class_without_entity_fields() -> None:
    """Serialized scripts should match legacy export semantics."""

    item = BaseScriptItem(obj_cls="tangl.story.Node", label="demo")

    payload = item.model_dump()

    assert payload["obj_cls"] == "tangl.story.Node"
    assert payload["label"] == "demo"
    assert "uid" not in payload
    assert "seq" not in payload

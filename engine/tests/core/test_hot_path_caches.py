"""Tests for two hot-path fixes.

Both changes are claimed to be pure speedups, so each is checked against the
behaviour it replaced rather than against a hand-written expectation. Each also
has a witness that the speedup itself is still present, since equivalence alone
would pass against the code it replaced.

- ``_match_fields`` / ``_match_methods`` now cache per class and criteria.
  Field and method markers are class metadata, but ``unstructure`` asked for
  them three times per call, for every entity, on every snapshot.
- ``_TemplateIndex._index_identifier`` now dedupes through a set. It used a
  linear ``templ not in matches`` scan whose comparisons each ran two full
  content hashes, which made materialization quadratic in template count.
"""

from __future__ import annotations

import gc
import weakref
from collections import defaultdict
from typing import Annotated
from uuid import uuid4

from pydantic import Field

from tangl.core import EntityTemplate, Node, TemplateRegistry
from tangl.core._pydantic import _MATCH_CACHE, BaseModelPlus
from tangl.core.bases import HasContent
from tangl.core.factory import _TemplateIndex


# --- cached marker scans -----------------------------------------------------


class _Marked(Node):
    shown: int = Field(0, json_schema_extra={"include": True})
    hidden: int = Field(0, json_schema_extra={"exclude": True})


class _MarkedChild(_Marked):
    also_hidden: int = Field(0, json_schema_extra={"exclude": True})


def test_cached_field_scan_matches_a_fresh_scan() -> None:
    for cls in (Node, EntityTemplate, _Marked, _MarkedChild):
        for criteria in ({"exclude": True}, {"include": True}, {"unstructurable": True}):
            assert tuple(cls._match_fields(**criteria)) == cls._scan_fields(criteria)


def test_cached_method_scan_matches_a_fresh_scan() -> None:
    for cls in (Node, EntityTemplate, _Marked):
        criteria = {"is_identifier": True}
        assert tuple(cls._match_methods(**criteria)) == cls._scan_methods(criteria)


def test_subclass_answers_do_not_leak_between_classes() -> None:
    # The cache is keyed on the class; a subclass that adds a marked field must
    # not be served its parent's cached answer, nor poison the parent's.
    assert set(_Marked._match_fields(exclude=True)) == {"hidden"} | _base_excluded()
    assert set(_MarkedChild._match_fields(exclude=True)) == (
        {"hidden", "also_hidden"} | _base_excluded()
    )
    assert "also_hidden" not in set(_Marked._match_fields(exclude=True))


def test_repeated_calls_are_served_from_the_cache(monkeypatch) -> None:
    scans = 0
    real_scan = _Marked._scan_fields.__func__

    def counting_scan(cls, criteria):
        nonlocal scans
        scans += 1
        return real_scan(cls, criteria)

    _MATCH_CACHE.pop(_Marked, None)
    monkeypatch.setattr(_Marked, "_scan_fields", classmethod(counting_scan))
    for _ in range(50):
        list(_Marked._match_fields(exclude=True))

    assert scans == 1


def test_the_cache_does_not_keep_a_class_alive() -> None:
    # The cache must not own its keys. A class that has answered a match - a
    # test fixture, or anything built with ``create_model`` - has to be
    # collectable once nothing else refers to it.
    class Temporary(BaseModelPlus):
        x: int = Field(0, json_schema_extra={"exclude": True})

    assert list(Temporary._match_fields(exclude=True)) == ["x"]
    assert Temporary in _MATCH_CACHE
    ref = weakref.ref(Temporary)

    del Temporary
    gc.collect()

    assert ref() is None


def test_an_incomplete_model_is_not_served_a_stale_answer() -> None:
    # A marker inside ``Annotated`` on a forward ref cannot be read until the
    # ref resolves. Before ``model_rebuild()`` pydantic reports only ``z``;
    # caching that would hide ``y`` for the life of the process.
    class Early(BaseModelPlus):
        y: Annotated["DefinedLater", Field(json_schema_extra={"exclude": True})] = None
        z: int = Field(0, json_schema_extra={"exclude": True})

    assert Early.__pydantic_complete__ is False
    assert list(Early._match_fields(exclude=True)) == ["z"]

    class DefinedLater(BaseModelPlus):
        pass

    Early.model_rebuild(_types_namespace={"DefinedLater": DefinedLater})

    assert list(Early._match_fields(exclude=True)) == ["y", "z"]


def _base_excluded() -> set[str]:
    return set(Node._scan_fields({"exclude": True}))


# --- template index dedup ----------------------------------------------------


def _templates() -> list[EntityTemplate]:
    registry = TemplateRegistry(label="dedup")
    shared = uuid4()
    a = EntityTemplate(label="scene.a", payload=Node(label="a", uid=shared), registry=registry)
    b = EntityTemplate(label="scene.b", payload=Node(label="b"), registry=registry)
    # A distinct object with identical content. Template content is the
    # payload's unstructured form, uid included, so the payloads share a uid.
    # Equality is by content, so the old scan collapsed these; the new index
    # has to as well.
    dup = EntityTemplate(label="scene.a", payload=Node(label="a", uid=shared), registry=registry)
    return [a, b, dup, a]


def _old_algorithm(templates: list[EntityTemplate]) -> dict:
    """The replaced implementation, verbatim in behaviour."""
    by_identifier: dict = defaultdict(list)

    def index(identifier, templ):
        matches = by_identifier[identifier]
        if templ not in matches:
            matches.append(templ)

    for templ in templates:
        index(templ.content_hash(), templ)
        for identifier in templ.get_identifiers():
            index(identifier, templ)
    return by_identifier


def test_template_index_dedup_is_identical_to_the_linear_scan() -> None:
    templates = _templates()
    expected = _old_algorithm(templates)
    actual = _TemplateIndex(templates).by_identifier

    assert set(actual) == set(expected)
    for identifier, matches in expected.items():
        # Same members, in the same first-seen order.
        assert [id(t) for t in actual[identifier]] == [id(t) for t in matches], identifier


def test_content_identical_templates_are_collapsed() -> None:
    templates = _templates()
    index = _TemplateIndex(templates)
    a_hash = templates[0].content_hash()

    assert templates[2] is not templates[0]
    assert templates[2].content_hash() == a_hash
    assert len(index.by_identifier[a_hash]) == 1


def test_indexing_shared_identifiers_makes_no_equality_comparisons(monkeypatch) -> None:
    """Pin the complexity fix, not only its result.

    A hundred distinct templates share one label. The replaced scan compared
    each new template against every one already filed under that label - about
    n**2 / 2 calls to ``eq_by_content``, each running two content hashes. The
    index should make none. Counting calls rather than timing them keeps this
    deterministic.
    """
    registry = TemplateRegistry(label="many")
    templates = [
        EntityTemplate(label="scene.shared", payload=Node(label=f"n{i}"), registry=registry)
        for i in range(100)
    ]
    calls = 0
    real_eq = HasContent.eq_by_content

    def counting_eq(self, other):
        nonlocal calls
        calls += 1
        return real_eq(self, other)

    monkeypatch.setattr(HasContent, "eq_by_content", counting_eq)

    index = _TemplateIndex(templates)
    assert len(index.by_identifier["scene.shared"]) == 100
    assert calls == 0

    # The witness can tell the difference: the replaced algorithm, on the same
    # input, makes at least one comparison per pair.
    _old_algorithm(templates)
    assert calls >= 100 * 99 // 2

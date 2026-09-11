"""Equivalence tests for two hot-path fixes.

Both changes are claimed to be pure speedups, so each is checked against the
behaviour it replaced rather than against a hand-written expectation.

- ``_match_fields`` / ``_match_methods`` now cache per class and criteria.
  Field and method markers are class metadata, but ``unstructure`` asked for
  them three times per call, for every entity, on every snapshot.
- ``_TemplateIndex._index_identifier`` now dedupes through a set. It used a
  linear ``templ not in matches`` scan whose comparisons each ran two full
  content hashes, which made materialization quadratic in template count.
"""

from __future__ import annotations

from collections import defaultdict
from uuid import uuid4

from pydantic import Field

from tangl.core import EntityTemplate, Node, TemplateRegistry
from tangl.core._pydantic import _MATCH_CACHE
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


def test_repeated_calls_are_served_from_the_cache() -> None:
    _MATCH_CACHE.clear()
    list(_Marked._match_fields(exclude=True))
    populated = len(_MATCH_CACHE)
    for _ in range(50):
        list(_Marked._match_fields(exclude=True))

    assert populated >= 1
    assert len(_MATCH_CACHE) == populated


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

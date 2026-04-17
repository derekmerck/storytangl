from __future__ import annotations

from tangl.devref.query import build_context_pack, get_topic_map, search_topics


def test_entity_search_prefers_overview_before_code_or_tests(devref_db_path) -> None:
    response = search_topics("entity", db_path=devref_db_path, limit=8)

    assert response.topics[0].topic_id == "entity"
    assert response.artifacts[0].facet == "overview"
    assert any(item.source_path == "ARCHITECTURE.md" for item in response.artifacts[:3])


def test_entity_search_filtered_to_tests_surfaces_test_guidance_and_modules(devref_db_path) -> None:
    response = search_topics("entity tests", db_path=devref_db_path, limit=8)

    assert response.artifacts
    assert response.artifacts[0].facet == "tests"
    top_paths = {item.source_path for item in response.artifacts[:5]}
    assert "engine/tests/AGENTS.md" in top_paths or "engine/tests/core/entity/test_entity.py" in top_paths


def test_dispatch_search_prioritizes_core_vm_docs_and_tests(devref_db_path) -> None:
    response = search_topics("dispatch", db_path=devref_db_path, limit=10)
    top_paths = [item.source_path for item in response.artifacts[:6]]

    assert any("docs/src/api/core/dispatch.rst" == path for path in top_paths) or any(
        "engine/tests/vm/test_dispatch.py" == path for path in top_paths
    )
    assert top_paths[0] != "engine/src/tangl/story/dispatch.py"


def test_ledger_and_phase_ctx_context_packs_preserve_facet_order(devref_db_path) -> None:
    ledger_pack = build_context_pack(["ledger"], db_path=devref_db_path, limit=8)
    phase_ctx_pack = build_context_pack(["phase_ctx"], db_path=devref_db_path, limit=8)

    assert ledger_pack.items
    assert phase_ctx_pack.items
    ledger_facets = [item.facet for item in ledger_pack.items]
    phase_ctx_facets = [item.facet for item in phase_ctx_pack.items]
    assert ledger_facets == sorted(ledger_facets, key=lambda facet: {"overview": 0, "design": 1, "api": 2, "code": 3, "tests": 4, "demos": 5, "governance": 6, "notes": 7}[facet])
    assert phase_ctx_facets == sorted(phase_ctx_facets, key=lambda facet: {"overview": 0, "design": 1, "api": 2, "code": 3, "tests": 4, "demos": 5, "governance": 6, "notes": 7}[facet])


def test_get_topic_map_returns_related_topics_and_artifacts(devref_db_path) -> None:
    topic_map = get_topic_map("phase_ctx", db_path=devref_db_path, limit=12)

    assert topic_map.topic.topic_id == "phase_ctx"
    assert {item.topic_id for item in topic_map.related_topics} >= {"frame", "ledger"}
    assert topic_map.artifacts

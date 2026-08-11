from __future__ import annotations

from tangl.devref.storage import DevRefDatabase
from tangl.devref.topics import load_topics


def test_topic_registry_covers_active_extension_packages() -> None:
    topics = {topic.topic_id: topic for topic in load_topics()}

    assert {"games", "progression", "transaction", "prose", "lang"} <= topics.keys()
    assert all(
        related in topics
        for topic in topics.values()
        for related in topic.related_topic_ids
    )

    assert {"node", "edge"}.isdisjoint(topics["graph"].aliases)
    assert "journal" not in topics["ledger"].aliases
    assert "planning" not in topics["provisioning"].aliases
    assert {"import", "export"}.isdisjoint(topics["codec"].aliases)


def test_every_topic_has_a_manual_canonical_anchor(devref_db_path) -> None:
    database = DevRefDatabase(devref_db_path)
    with database.connect() as conn:
        rows = conn.execute(
            """
            SELECT topics.topic_id
            FROM topics
            LEFT JOIN artifact_topics
              ON artifact_topics.topic_id = topics.topic_id
             AND artifact_topics.evidence_source = 'manual_annotation'
            GROUP BY topics.topic_id
            HAVING COUNT(artifact_topics.artifact_id) = 0
            ORDER BY topics.topic_id
            """
        ).fetchall()

    assert [row["topic_id"] for row in rows] == []

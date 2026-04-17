from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from .models import TopicDefinition


TOPICS_PATH = Path(__file__).with_name("topics.json")


@lru_cache(maxsize=1)
def load_topics() -> list[TopicDefinition]:
    """Load the curated developer-topic registry."""

    payload = json.loads(TOPICS_PATH.read_text(encoding="utf-8"))
    return [TopicDefinition.model_validate(item) for item in payload]


def topic_registry_hash() -> str:
    """Return the current on-disk registry contents for build invalidation."""

    return TOPICS_PATH.read_text(encoding="utf-8")

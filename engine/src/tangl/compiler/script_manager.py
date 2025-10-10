from __future__ import annotations

import logging
from collections.abc import Iterator
from copy import deepcopy
from pathlib import Path
from typing import Any, Self

from pydantic import ValidationError

from tangl.type_hints import StringMap, UnstructuredData
from tangl.ir.core_ir import MasterScript
from tangl.ir.story_ir import StoryScript

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

class ScriptManager():
    """
    ScriptManager mediates between input files and the world/story creation.
    """

    master_script: MasterScript

    def __init__(self, master_script: MasterScript) -> None:
        self.master_script = master_script

    @classmethod
    def from_data(cls, data: UnstructuredData) -> Self:
        try:
            ms: MasterScript = StoryScript(**data)
        except ValidationError:
            ms = MasterScript(**data)
        # todo: Want to call "on new script" here too.
        return cls(master_script=ms)

    @classmethod
    def from_files(cls, fp: Path) -> Self:
        # todo: implement a file reader
        data = {}
        return cls.from_data(data)

    def get_story_globals(self) -> StringMap:
        if self.master_script.locals:
            return deepcopy(self.master_script.locals)
        return {}

    def get_unstructured(self, key: str) -> Iterator[UnstructuredData]:
        if not hasattr(self.master_script, key):
            return

        logger.debug("Starting node data %s", key)
        section = getattr(self.master_script, key)
        if not section:
            return

        if isinstance(section, dict):
            for label, item in section.items():
                payload = self._dump_item(item)
                payload.setdefault("label", label)
                logger.debug(payload)
                yield payload
            return

        for item in section:
            payload = self._dump_item(item)
            logger.debug(payload)
            yield payload

    def get_story_metadata(self) -> UnstructuredData:
        return self.master_script.metadata.model_dump()

    @staticmethod
    def _dump_item(item: Any) -> dict[str, Any]:
        if hasattr(item, "model_dump"):
            return item.model_dump()
        if isinstance(item, dict):
            return dict(item)
        return dict(item)

    def get_story_text(self) -> list[tuple[str, str]]:

        result = []

        def _get_text_fields(path: str, item: list | dict):
            nonlocal result
            if not item:
                return
            if isinstance(item, list) and isinstance( item[0], dict ):
                [ _get_text_fields(path + f'.{i}', v) for i, v in enumerate(item) ]
            elif isinstance(item, dict):
                if 'text' in item:
                    data = {"path": path,
                            # "hash": key_for_secret(item['text'])[:6],
                            "text": item['text']}
                    result.append(data)
                [ _get_text_fields( path + f'.{k}', v) for k, v in item.items() ]

        _get_text_fields(self.master_script.label, self.master_script.model_dump())
        return result

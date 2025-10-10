import logging
from typing import Self, Literal, Iterator
from pathlib import Path

from copy import deepcopy

from tangl.type_hints import UnstructuredData, StringMap
from tangl.ir.core_ir import MasterScript

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

    def get_unstructured(self, key: Literal['scenes', 'actors']) -> Iterator[UnstructuredData]:
        if hasattr(self.master_script, key):
            logger.debug(f"Starting node data {key}")
            data = getattr( self.master_script, key )
            if data:
                if isinstance(data, dict):
                    data = data.values()
                for item in data:
                    logger.debug(item)
                    yield item.model_dump()

    def get_story_metadata(self) -> UnstructuredData:
        return self.master_script.metadata.model_dump()

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

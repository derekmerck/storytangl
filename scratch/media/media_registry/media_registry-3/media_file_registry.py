from typing import ClassVar, Type, Callable
from pathlib import Path
import re

from tangl.type_hints import Pathlike, Tags
from .media_registry import MediaRegistry, MediaRegistryHandler
from .media_file_record import MediaFileRecord, ImageFileRecord

class MediaFileRegistryHandler(MediaRegistryHandler):

    record_cls: ClassVar[Type[MediaFileRecord]] = MediaFileRecord

    @classmethod
    def register_media_files(cls,
                             registry: MediaRegistry,
                             base_path: Pathlike,
                             default_tags: Tags = None,
                             tagging_func: Callable[[str], set[str]] = None):
        base_path = Path(base_path)
        default_tags = default_tags or set()
        pattern = re.compile(r".*\.(webp|png|jpg|jpeg)$", re.IGNORECASE)
        files = [f for f in base_path.glob(r'*') if pattern.match(str(f))]
        for f in files:
            fn_tags = tagging_func(f.stem) if tagging_func else set()
            cls.create_record(registry, label=None, path=f, tags=fn_tags.union(default_tags))

class MediaFileRegistry(MediaRegistry):

    def register_media_files(self,
                             path: Pathlike,
                             default_tags: Tags = None,
                             tagging_func: Callable[[str], set[str]] = None):
        MediaFileRegistryHandler.register_media_files(self, path, default_tags, tagging_func)

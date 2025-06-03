from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import Optional, ClassVar, Callable

from pydantic import model_validator, Field, field_validator

from tangl.utils.pixel_avg_hash import pix_avg_hash
from tangl.utils.shelved2 import shelved, clear_shelf
from tangl.utils.file_check_values import compute_file_hash, get_file_mtime
from tangl.type_hints import Pathlike
from .enums import ResourceDataType
from .resource_inventory_tag import ResourceInventoryTag as RIT
from .resource_location import ResourceLocation


class FileRIT(RIT):
    path: Pathlike
    file_hash: str = Field(None, init_var=False)
    mtime: datetime = Field(None, init_var=False)

    # infers name from path file stem
    # infers resource data type from ext

    @field_validator("path")
    @classmethod
    def _check_exists(cls, value: Path):
        if not value.is_file():
            raise FileNotFoundError
        return value

    @model_validator(mode='before')
    @classmethod
    def _compute_defaults(cls, values) -> FileRIT:
        if 'path' not in values:
            raise KeyError("Missing required 'path' attribute for FileRIT")
        path = Path( values['path'] )
        if 'name' not in values:
            values['name'] = path.stem
        if 'resource_type' not in values:
            values['resource_type'] = ResourceDataType(path.suffix)
        if 'file_hash' not in values:
            values['file_hash'] = compute_file_hash(path)
        if 'mtime' not in values:
            values['mtime'] = get_file_mtime(path)
        return values

    def get_aliases(self) -> list[FileRIT]:
        res = super().get_aliases() or []
        res += [ self.path, self.file_hash ]
        return res


class ImageFileRIT(FileRIT):

    resource_type: ResourceDataType = ResourceDataType.IMAGE

    # computing data hashes for images can be slow, so we can cache the results
    shelf_name: ClassVar[str] = "image_hashes"

    @shelved(fn=shelf_name)
    @staticmethod
    def compute_px_hash(path: Pathlike, check_value=None):
        # check value gets passed to the cache for invalidating stale entries
        from PIL import Image
        im = Image.open(path)
        data_hash = pix_avg_hash(im)
        return data_hash

    @classmethod
    def clear_cache(cls):
        clear_shelf(cls.shelf_name)

    @model_validator(mode='after')
    def _set_data_hash(self):
        if not self.data_hash and self.path.exists():
            check_value = ( self.file_hash, self.mtime )
            self.data_hash = ImageFileRIT.compute_px_hash(self.path, check_value=check_value)
        return self

    @property
    def image(self):
        from PIL import Image
        return Image.open(self.path)


class FileResourceLocation(ResourceLocation):

    base_path: Pathlike
    tagging_func: Callable[[str], set[str]]
    extra_suffixes: Optional[list[str]] = None

    def __init__(self,
                 base_path: Path,
                 tagging_func: Callable = None,
                 clear_cache: bool = False,
                 extra_suffixes: list[str] = None,
                 **kwargs):
        self.base_path = Path(base_path).expanduser()
        self.tagging_func = tagging_func
        self.extra_suffixes = extra_suffixes
        if clear_cache:
            ImageFileRIT.clear_cache()
        super().__init__(**kwargs)

    def _file_inventory(self) -> list[Path]:
        suffixes = ResourceDataType.extension_map().values()
        if self.extra_suffixes:
            suffixes = list(suffixes) + self.extra_suffixes
        return [path for i in suffixes for path in self.base_path.glob("*." + i)]

    def update_inventory(self, clear_cache=False):
        for fp in self._file_inventory():
            resource = self.create_resource_from_fp(fp)
            # print(f"adding {fp} as resource {resource.uid} ({resource.data_hash})")
            self.add_resource(resource)

    def create_resource_from_fp(self, fp: Path):
        suffix = fp.suffix[1:]
        if suffix in ['jpg', 'webp', 'jpeg']:
            # it's a non-standard image
            resource_type = ResourceDataType.IMAGE
        else:
            resource_type = ResourceDataType(suffix)
        if self.tagging_func:
            tags = self.tagging_func(fp.stem)
        else:
            tags = None
        if resource_type is ResourceDataType.IMAGE:
            ResourceCls = ImageFileRIT
        else:
            ResourceCls = FileRIT
        resource = ResourceCls(
            path=fp,
            resource_type=resource_type,
            tags=tags
        )
        return resource


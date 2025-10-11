

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


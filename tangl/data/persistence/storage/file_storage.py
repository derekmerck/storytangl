from pathlib import Path

from tangl.type_hints import FlatData

class FileStorage:

    def __init__( self, base_path: str | Path = "~/tmp/persist", ext: str = 'txt', binary_rw: bool = False ):
        base_path = Path(base_path).expanduser()
        # ensure bp exists
        if not base_path.is_dir():  # pragma: no cover
            base_path.mkdir(parents=True, exist_ok=True)
        self.base_path = base_path
        self.ext = ext
        self.binary_rw = binary_rw

    def get_fn(self, key):
        return f"{key}.{self.ext}"

    def __setitem__(self, key, value: FlatData):
        fp = self.base_path / self.get_fn(key)
        flags = "wb" if self.binary_rw else "w"
        with open(fp, flags) as f:
            f.write(value)

    def __getitem__(self, key) -> FlatData:
        fp = self.base_path / self.get_fn(key)
        if not fp.exists():
            raise KeyError(f"No such key {key}")
        flags = "rb" if self.binary_rw else "r"
        with open(fp, flags) as f:
            value = f.read()
            return value

    def __contains__(self, key):
        fp = self.base_path / self.get_fn(key)
        if not fp.exists():
            return False
        return True

    def __delitem__(self, key):
        fp = self.base_path / self.get_fn(key)
        if not fp.exists():
            raise KeyError(f"No such key {key}")
        fp.unlink()

    def __len__(self) -> int:
        return sum(1 for item in self.base_path.iterdir() if item.is_file())

    def __iter__(self):
        return iter(self.base_path.iterdir())

    def __bool__(self) -> bool:
        return len(self) != 0


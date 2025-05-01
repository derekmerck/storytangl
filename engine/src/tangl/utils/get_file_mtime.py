import io

from pathlib import Path
from datetime import datetime

def get_file_mtime( arg: Path | io.IOBase ):
    if isinstance(arg, io.FileIO):
        arg = arg.name

    return datetime.fromtimestamp(arg.stat().st_mtime)


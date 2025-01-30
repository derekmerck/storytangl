from uuid import UUID
from typing import Any

UniqueLabel = str
Hash = int
Identifier = Hash | UniqueLabel | UUID
Tag = str
UnstructuredData = dict[str, Any]

from typing import Any
import yaml

from pydantic import BaseModel

import tangl.utils.setup_yaml

class BaseResponse(BaseModel, extra="allow"):
    """
    Basic output model for service-layer journal and info objects
    """

    def model_dump(self, *args, **kwargs) -> dict[str, Any]:
        kwargs.setdefault('exclude_none', True)
        return super().model_dump(*args, **kwargs)

    def __str__(self):
        data = self.model_dump()
        s = yaml.dump(data, default_flow_style=False)
        return s

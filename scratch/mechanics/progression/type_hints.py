from typing import Type
from enum import IntEnum

FloatValue = float    # 1.-20.
QuantizedValue = int  # 1-5
Statlike = FloatValue | QuantizedValue | IntEnum | str
Measure = Type[IntEnum]

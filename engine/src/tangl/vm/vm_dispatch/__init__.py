# application layer dispatch:  global > *app* > author > inline

from .on_get_ns import on_get_ns
from .on_apply_effect import on_apply_effect, HasEffects
from .on_check_conditions import on_check_conditions, HasConditions

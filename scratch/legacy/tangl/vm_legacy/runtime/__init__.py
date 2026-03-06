"""
Mixins for runtime conditions and effects on nodes.

Conditions are evaluated against the caller's namespace during VALIDATE.
Effects are applied on the caller's namespace during UPDATE and FINALIZE.

.. admonition:: Python Specific Features

These are _python dependent_, no system using them can port to other
platforms without an embedded python interpreter of some kind.
"""
from .apply_effects import HasEffects
from .check_conditions import HasConditions

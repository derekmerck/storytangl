"""Legacy compatibility shim that re-exports ``tangl.vm38``."""

import os

import tangl.vm38 as _vm38

from tangl.vm38 import *  # noqa: F401,F403
from tangl.core import CallReceipt as _LegacyCallReceipt, Record as _LegacyRecord
from tangl.core38 import CallReceipt as _Core38CallReceipt, Record as _Core38Record
from tangl.vm.context import Context as LegacyContext
from tangl.vm.frame import ChoiceEdge as LegacyChoiceEdge, Frame as LegacyFrame
from tangl.vm.ledger import Ledger as LegacyLedger
from tangl.vm.resolution_phase import ResolutionPhase as LegacyResolutionPhase
from tangl.vm38.provision import ProvisionPolicy
from tangl.vm38.replay import Patch
from tangl.vm38.runtime.frame import PhaseCtx
from tangl.vm38.traversable import TraversableEdge


_V38_VALUES = {"1", "true", "yes", "on", "v38", "new"}
_LEGACY_VALUES = {"0", "false", "no", "off", "legacy", "old"}


def _pick(symbol: str, legacy_value, v38_value, *, default: str = "legacy"):
    raw_value = os.getenv(
        f"TANGL_SHIM_VM_{symbol}",
        os.getenv("TANGL_SHIM_VM_DEFAULT", default),
    )
    selected = str(raw_value).strip().lower()
    if selected in _LEGACY_VALUES:
        return legacy_value
    if selected in _V38_VALUES:
        return v38_value
    raise ValueError(
        f"Invalid shim value '{raw_value}' for TANGL_SHIM_VM_{symbol}. "
        f"Use one of {sorted(_LEGACY_VALUES | _V38_VALUES)}."
    )


__all__ = getattr(
    _vm38,
    "__all__",
    [name for name in dir(_vm38) if not name.startswith("_")],
)

# Legacy compatibility aliases for import-surface blast-radius testing.
BuildReceipt = _pick("BUILDRECEIPT", _LegacyCallReceipt, _Core38CallReceipt)
ChoiceEdge = _pick("CHOICEEDGE", LegacyChoiceEdge, TraversableEdge)
Context = _pick("CONTEXT", LegacyContext, PhaseCtx)
Frame = _pick("FRAME", LegacyFrame, _vm38.Frame)
Ledger = _pick("LEDGER", LegacyLedger, _vm38.Ledger)
PlanningReceipt = _pick("PLANNINGRECEIPT", _LegacyRecord, _Core38Record)
ProvisioningPolicy = ProvisionPolicy
ResolutionPhase = _pick("RESOLUTIONPHASE", LegacyResolutionPhase, _vm38.ResolutionPhase)

__all__ += [
    "BuildReceipt",
    "ChoiceEdge",
    "Context",
    "Frame",
    "Ledger",
    "Patch",
    "PlanningReceipt",
    "ProvisioningPolicy",
    "ResolutionPhase",
]

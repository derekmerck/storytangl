"""
Composable loadout containers built on :class:`tangl.core.Selector`.
"""

from .base import ComponentManager, HasResourceCost, HasSlottedContainer, SlottedContainer
from .budget import BudgetTracker, ResourceBudget
from .component import Component, ComponentFacet, Connector, ConnectorPolarity
from .connection import ConnectionGroupManager
from .slot import Slot, SlotGroup

__all__ = [
    "Component",
    "ComponentFacet",
    "ComponentManager",
    "ConnectionGroupManager",
    "Connector",
    "ConnectorPolarity",
    "HasResourceCost",
    "HasSlottedContainer",
    "SlottedContainer",
    "BudgetTracker",
    "ResourceBudget",
    "Slot",
    "SlotGroup",
]

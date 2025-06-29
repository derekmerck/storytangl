from dataclasses import dataclass, field

from tangl.core.services import CoreServices
from tangl.core.solver.journal import JournalManager
from tangl.core.solver.provisioner import ProvisionManager


@dataclass
class SolverServices(CoreServices):
    prov:     ProvisionManager = field(default_factory=ProvisionManager)
    journal:  JournalManager = field(default_factory=JournalManager)

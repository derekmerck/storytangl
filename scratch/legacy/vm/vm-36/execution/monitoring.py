from dataclasses import dataclass
from typing import Dict
import logging

from tangl.vm36.execution.phases import Phase

logger = logging.getLogger(__name__)

# todo suggestion: monitoring

@dataclass
class TickMetrics:
    phase_durations: Dict[Phase, float]
    effect_count: int
    journal_size: int

    def log(self):
        logger.info("Tick metrics", extra=self.__dict__)
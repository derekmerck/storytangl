from pydantic import BaseModel, field_validator
from typing import List, Literal, Optional, Dict, Union
from enum import Enum
from datetime import time

class DayType(str, Enum):
    EVERYDAY = "everyday"
    WORKDAYS = "workdays"
    WEEKEND = "weekend"
    SPECIFIC = "specific"  # Optional for specific day handling

class TimePeriod(str, Enum):
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    NIGHT = "night"

    ALL_DAY = MORNING, AFTERNOON, EVENING

class ScheduleEntry(BaseModel):
    day_type: DayType
    period: TimePeriod
    location: str
    specific_days: Optional[List[int]] = None  # Optional: [0, 2] for Mon, Wed if SPECIFIC

    @field_validator("specific_days")
    def validate_specific_days(cls, v, values):
        if values.get("day_type") == DayType.SPECIFIC and not v:
            raise ValueError("specific_days must be provided for SPECIFIC day_type.")
        return v

class Schedule(BaseModel):
    entries: List[ScheduleEntry]

    def get_schedule_for_day(self, day: int) -> List[ScheduleEntry]:
        """Fetch schedule entries for a specific day (0=Mon, 6=Sun)."""
        day_type_map = {
            0: "workdays", 1: "workdays", 2: "workdays", 3: "workdays", 4: "workdays",
            5: "weekend", 6: "weekend"
        }
        relevant_type = DayType.SPECIFIC if day in [e.specific_days for e in self.entries if e.specific_days] else None
        day_label = relevant_type or day_type_map.get(day, "everyday")
        return [
            entry for entry in self.entries
            if entry.day_type == day_label or entry.day_type == "everyday"
        ]

    def get_location_for_period(self, day: int, period: TimePeriod) -> str:
        ...

    def add_entry(self, entry: ScheduleEntry):
        self.entries.append(entry)

    def remove_entry(self, location: str, day_type: DayType, period: TimePeriod):
        self.entries = [
            e for e in self.entries
            if not (e.location == location and e.day_type == day_type and e.period == period)
        ]

    def __str__(self) -> str:
        """Provides a readable summary of the schedule."""
        return "\n".join([f"{e.day_type} - {e.period}@{e.location}" for e in self.entries])

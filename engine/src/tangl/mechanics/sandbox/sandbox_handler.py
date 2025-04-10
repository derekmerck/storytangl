from __future__ import annotations

from pydantic import BaseModel, Field

from tangl.core.entity.handlers import Lockable, AvailabilityHandler, HasEffects, EffectHandler
from tangl.core.graph import Graph, Node
from tangl.core.graph.handlers import TraversableGraph, TraversalHandler
from tangl.story.place import Location

class SandboxHandler(TraversalHandler):

    @classmethod
    def check_loc_and_time(cls,
                           req_locs: list[Location],
                           req_times: list[float],
                           current_loc: Location,
                           current_time: float,
                           ) -> bool:
        # todo: placeholder logic
        if current_loc in req_locs and current_time in req_times:
            return True
        return False

    @classmethod
    def check_schedule_conditions(cls, sandbox: Sandbox, schedule: list[ScheduleCondition]) -> bool:
        return all([cls.check_loc_and_time(sched.loc, sched.time, sandbox.cursor, sandbox.current_time) for sched in schedule])

    @classmethod
    def get_scheduled_location(cls, sandbox: Sandbox, schedule: list[ScheduleCondition]) -> Location:
        NotImplemented


CalendarPeriod = [1, 2, 3, 4]        # per day
CalendarDay = [1, 2, 3, 4, 5, 6, 7]  # per week
CalendarMonth = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]  # per year
CalendarSeason = [1, 2, 3, 4]        # per year
CalendarYear = int

class WorldTime(BaseModel):
    period: CalendarPeriod
    day: CalendarDay
    month: CalendarMonth
    season: CalendarSeason
    year: CalendarYear

class Sandbox(TraversableGraph, Graph):

    world_turn: int = 0
    player_location: Location = None

    def world_time(self) -> WorldTime:
        period = self.world_turn % len(CalendarPeriod)
        day = self.world_turn % len(CalendarDay)
        week = self.world_turn // len(CalendarDay)
        month = self.world_turn // len(CalendarMonth)
        season = self.world_turn // len(CalendarSeason)
        year = ...
        return period, day, week

    @property
    def locations(self) -> list[ConnectedLocation]:
        # locations may have events, in which case they are implicitly conditioned on that location
        return self.children(ConnectedLocation)

    @property
    def mobs(self) -> list[MobileNode]:
        loc_mobs = [ x for loc in self.locations for x in loc.mobs ]
        return self.children(MobileNode) + loc_mobs

    @property
    def events(self) -> list[ScheduledNode]:
        loc_events = [ x for loc in self.locations for x in loc.events ]
        return self.children(ScheduledNode) + loc_events

    # todo: want a factory function to create connections from a map


class ConnectedLocation(Node):

    @property
    def connections(self) -> list[ConnectedLocation]:
        # generate an action for each connection
        return self.find_children(ConnectedLocation, filt=lambda x: isinstance( x.successor, ConnectedLocation ))

    @property
    def mobs(self) -> list[MobileNode]:
        return self.find_children(MobileNode)

    @property
    def events(self) -> list[ScheduledNode]:
        return self.find_children(ScheduledNode)


class ScheduleCondition(BaseModel):
    req_loc: str = None
    req_time: str = None

    def check(self, loc: Location, time: float) -> bool:
        # todo: placeholder!
        return True


# basically a block
class ScheduledNode(Lockable, Node):
    """
    "Check Schedule", equivalent to "check condition" entity availability, attach to "Scenes"
    or other pinned entities.
    """
    schedule_conditions: list[ScheduleCondition] = Field(default_factory=list)

    @AvailabilityHandler.strategy()
    def _include_event_conditions(self, **kwargs) -> bool:
        return SandboxHandler.check_schedule_conditions(self.sandbox, self.event_conditions)


class MobileNode(HasEffects, Node):
    """
    "Set Loc", equivalent to "apply effect" entity effect handler, attach to "Actors" or
    other roaming entities.
    """

    schedule: list[ScheduleCondition] = Field(default_factory=list)

    @property
    def current_location(self) -> ConnectedLocation:
        return self.find_child(ConnectedLocation)

    @EffectHandler.strategy()
    def _set_current_loc(self, **kwargs):
        current_location = SandboxHandler.get_scheduled_location(self.sandbox, self.schedule)
        if current_location and current_location is not self.current_location:
            self.disassociate(self.current_location)
            self.associate(current_location)

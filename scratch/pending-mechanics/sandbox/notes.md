# Sandbox Calendar and Scheduling System

## Overview

This system provides a flexible way to model events, NPC movements, and activities based on a hierarchical in-game calendar. It is designed for a sandbox-style game, where events occur and NPCs move around the world based on the current in-game time, represented by periods within a day, days within a week, months, seasons, and years.

### Key Concepts

1. **WorldTime Model**:
   - Represents the in-game time using various granularities:
     - **Periods**: Divides the day into four parts (e.g., Morning, Afternoon, Evening, Night).
     - **Days**: Tracks days of the week (1 = Monday, 7 = Sunday).
     - **Months**: Standard 1 to 12, representing January to December.
     - **Seasons**: Derived from the months, with 3 months per season (e.g., Spring, Summer, Fall, Winter).
     - **Years**: Tracks the progression of years in the game world.

2. **ScheduleEntry and Schedule Models**:
   - **ScheduleEntry** represents an event or activity scheduled to happen at a specific time and location. Fields include:
     - **Description**: Details of the event (e.g., "Market is open").
     - **Location**: Where the event happens (e.g., "market").
     - **Period, Day, Month, Season, Year**: Optional fields that specify the timing of the event.
   - **Schedule** holds multiple `ScheduleEntry` instances and provides:
     - A method to **add new entries**.
     - **Matching logic** (`get_events_for_time()`) to retrieve events that occur at the given `WorldTime`.

3. **Sandbox Integration**:
   - The **Sandbox** class simulates the game world, using:
     - A `world_turn` counter to track the passage of in-game time.
     - The `world_time()` method calculates the current `WorldTime` based on `world_turn`.
     - The `update_world()` method advances the world by one turn and triggers any scheduled events matching the current time.

### Implementation Details

1. **Hierarchical Calendar**
   - In-game time is represented using `WorldTime`, which includes periods, days, months, seasons, and years.
   - The calendar system can handle recurring events (e.g., every Monday morning) and one-time events (e.g., New Year Celebration in Year 2).

2. **Schedule Matching Logic**
   - Each `ScheduleEntry` can match on different granularities (e.g., specific day and period, entire season).
   - The **`matches()`** method checks whether an event is scheduled to happen during the current `WorldTime`.
   - The **`get_events_for_time()`** method returns a list of all matching events for a given time.

3. **World Progression**
   - Each **world turn** advances the game time by one period.
   - Events are triggered based on matching entries in the schedule.
   - NPC movements and interactions can be driven by these scheduled events, ensuring dynamic world interactions.

### Example Usage

- You can define a schedule entry for recurring events like the market opening every Saturday afternoon:
  ```python
  sandbox.schedule.add_entry(ScheduleEntry(description="Market is open", location="market", period=2, day=6))
  ```
- Seasonal or annual events can also be added:
  ```python
  sandbox.schedule.add_entry(ScheduleEntry(description="Festival of Lights", location="plaza", season=4, day=7))
  ```
- The world is updated with each **world turn**, and events are printed when they occur:
  ```python
  sandbox.update_world()
  ```

### Advantages

1. **Granularity Control**: Events and NPC movements can be scheduled at any time level—from periods within a day to annual festivals.
2. **Recurring and One-Time Events**: Flexibility to add recurring schedules as well as unique, one-time events.
3. **Dynamic NPC Movement**: NPCs can move around the game world based on schedules, making the sandbox more immersive and interactive.

### Future Considerations
- **Complex Dependencies**: You can extend the system to support dependencies between events, such as triggering an event only if certain prior conditions are met.
- **NPC Behavior States**: Each NPC can have states tied to the schedule entries, allowing more detailed behaviors (e.g., "working," "resting," "participating in a festival").

This calendar and scheduling system forms the backbone of a dynamic in-game world, allowing a variety of recurring and unique events that enhance the player's experience.


Response Model
--------------

If a world map is available, the 'game_status' response may include a 'world_map' field.  By default, this includes a grid representation of the world map, the current world-time, and the player's current grid location.  It can be extended to also include map media and scheduled events, or to hide unexplored or distant locations, for example.  

As usual, it is left up to the UI to interpret and display these cues to the player.  For example, the CLI interface has no mechanism for displaying a world map, although one could be implemented with `curses` or the like.

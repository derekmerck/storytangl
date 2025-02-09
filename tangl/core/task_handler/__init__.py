"""
task_handler

This subpackage provides a flexible and extensible "task handler" system for
processing ``Entity`` objects. It comprises:

- **HandlerPriority**: An IntEnum specifying relative execution order
  (FIRST, EARLY, NORMAL, LATE, LAST).
- **PipelineStrategy**: An Enum detailing how multiple handler results
  should be combined (e.g. gather them all, short-circuit on the first,
  chain them in a pipeline, etc.).
- **TaskHandler**: A callable wrapper (also an Entity) that holds
  metadata about a function's priority, domain, and caller class
  constraints.
- **TaskPipeline**: A Singleton that stores and runs a set of TaskHandlers
  in a particular strategy (GATHER, PIPELINE, FIRST, ALL, ANY, etc.).

Using these components, users can register “hooks” or “handlers”
for specific tasks and execute them in a controlled order on Entities.
"""

from .task_handler import TaskHandler, HandlerPriority
from .task_pipeline import PipelineStrategy, TaskPipeline

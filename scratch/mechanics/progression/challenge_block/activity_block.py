from tangl.core.services import BaseHandler
from tangl.story.scene import Block
from .task import Task, Tasker, TaskHandler

class ActivityManager(BaseHandler):
    ...

class Activity(Block):
    """
    Activity blocks are wrappers for "Task" interactions.

    Task interactions are stat-tests with an associated cost and reward.
    """

    @property
    def task(self) -> Task:
        return self.find_child(Task)

    def can_do_task(self, tasker: Tasker) -> bool:
        return TaskHandler.can_do_task(self, tasker)

    def do_task(self, tasker: Tasker) -> bool:
        return TaskHandler.do_task(self, tasker)

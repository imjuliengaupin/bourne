
import inspect
from collections import deque
from types import FrameType
from typing import Deque, Optional

from core.logger import Logger
from core.workflow_task import WorkflowTask


class WorkflowTaskQueue:

    def __init__(self, logger: Logger) -> None:
        self.logger: Logger = logger
        self.workflow_tasks: Deque[WorkflowTask] = deque()

    def get_class_label(self) -> str:
        return type(self).__name__

    def get_caller_method(self) -> str:
        frame: Optional[FrameType] = inspect.currentframe()

        if frame is not None and frame.f_back is not None:
            return frame.f_back.f_code.co_name + "()"

        return "unknown_caller_method()"

    def get_size(self) -> int:
        try:
            return len(self.workflow_tasks)

        except Exception as e:
            self.logger.log(self.get_class_label(), f"❌ FAILURE: Error occurred in {self.get_caller_method()}.\n{e}")
            return 0

    def get_next_workflow_task(self) -> Optional[WorkflowTask]:
        try:
            if not self.workflow_tasks:
                return None

            if self.workflow_tasks:
                next_workflow_task: WorkflowTask = self.workflow_tasks.popleft()
                return next_workflow_task

            return None

        except Exception as e:
            self.logger.log(self.get_class_label(), f"❌ FAILURE: Error occurred in {self.get_caller_method()}.\n{e}")
            return None

    def add_workflow_task(self, workflow_task: WorkflowTask) -> None:
        try:
            self.workflow_tasks.append(workflow_task)

        except Exception as e:
            self.logger.log(self.get_class_label(), f"❌ FAILURE: Error occurred in {self.get_caller_method()}.\n{e}")

    def is_empty(self) -> bool:
        try:
            return self.get_size() == 0

        except Exception as e:
            self.logger.log(self.get_class_label(), f"❌ FAILURE: Error occurred in {self.get_caller_method()}.\n{e}")
            return True

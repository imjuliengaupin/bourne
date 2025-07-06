
import inspect
import time
from collections import deque
from types import FrameType
from typing import Optional

from core.workflow.workflow_task import WorkflowTask


class WorkflowQueue:

    def __init__(self) -> None:
        self.tasks: deque[WorkflowTask] = deque()

    def get_class_label(self) -> str:
        return type(self).__name__

    def get_caller_method(self) -> str:
        frame: Optional[FrameType] = inspect.currentframe()

        if frame is not None and frame.f_back is not None:
            return frame.f_back.f_code.co_name + "()"

        return "unknown_caller_method()"

    def get_timestamp(self) -> str:
        return time.strftime("%Y-%m-%d %H:%M:%S")

    def get_size(self) -> int:
        try:
            return len(self.tasks)
        except Exception as e:
            print(f"[{self.get_timestamp()}] [{self.get_class_label()}] ❌ FAILURE: Error occurred in {self.get_caller_method()}\n{e}")
            return 0

    def get_next_task(self) -> Optional[WorkflowTask]:
        try:
            if not self.tasks:
                return None

            if self.tasks:
                next_task: WorkflowTask = self.tasks.popleft()
                return next_task

            return None

        except Exception as e:
            print(f"[{self.get_timestamp()}] [{self.get_class_label()}] ❌ FAILURE: Error occurred in {self.get_caller_method()}\n{e}")
            return None

    def add_task(self, task: WorkflowTask) -> None:
        try:
            self.tasks.append(task)
        except Exception as e:
            print(f"[{self.get_timestamp()}] [{self.get_class_label()}] ❌ FAILURE: Error occurred in {self.get_caller_method()}\n{e}")

    def is_empty(self) -> bool:
        try:
            return self.get_size() == 0
        except Exception as e:
            print(f"[{self.get_timestamp()}] [{self.get_class_label()}] ❌ FAILURE: Error occurred in {self.get_caller_method()}\n{e}")
            return True

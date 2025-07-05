
import collections
import inspect
import time
from types import FrameType
from typing import Any, Dict, Optional

from core.workflow.workflow_task import WorkflowTask


class WorkflowQueue:

    def __init__(self) -> None:
        self.queue: collections.deque[WorkflowTask] = collections.deque()

    def get_class_label(self) -> str:
        return type(self).__name__

    def get_caller_method(self) -> str:
        frame: FrameType = inspect.currentframe()

        if frame is not None and frame.f_back is not None:
            return frame.f_back.f_code.co_name + "()"

        return "unknown_caller_method()"

    def get_timestamp(self) -> str:
        return time.strftime("%Y-%m-%d %H:%M:%S")

    def get_size(self) -> int:
        try:
            return len(self.queue)
        except Exception as e:
            print(f"[{self.get_timestamp()}] [{self.get_class_label()}] ❌ FAILURE: Error occurred in {self.get_caller_method()}\n{e}")
            return 0

    def get_next_task(self) -> Optional[WorkflowTask]:
        try:
            if not self.queue:
                return None

            next_task: Dict[str, Any] = self.queue.popleft()
            return next_task

        except Exception as e:
            print(f"[{self.get_timestamp()}] [{self.get_class_label()}] ❌ FAILURE: Error occurred in {self.get_caller_method()}\n{e}")
            return None

    def add_task(self, task: WorkflowTask) -> None:
        try:
            self.queue.append(task)
        except Exception as e:
            print(f"[{self.get_timestamp()}] [{self.get_class_label()}] ❌ FAILURE: Error occurred in {self.get_caller_method()}\n{e}")

    def is_empty(self) -> bool:
        try:
            return self.get_size() == 0
        except Exception as e:
            print(f"[{self.get_timestamp()}] [{self.get_class_label()}] ❌ FAILURE: Error occurred in {self.get_caller_method()}\n{e}")
            return True

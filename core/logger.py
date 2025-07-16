
import inspect
import time
from types import FrameType
from typing import List, Optional


class Logger:

    def __init__(self, max_logs: int) -> None:
        self.max_logs: int = max(0, max_logs)
        self.logs: List[str] = []

    def get_class_label(self) -> str:
        return type(self).__name__

    def get_caller_method(self) -> str:
        frame: Optional[FrameType] = inspect.currentframe()

        if frame is not None and frame.f_back is not None:
            return frame.f_back.f_code.co_name + "()"

        return "unknown_caller_method()"

    def get_timestamp(self) -> str:
        return time.strftime("%Y-%m-%d %H:%M:%S")

    def get_logs(self) -> List[str]:
        return self.logs[:]

    def log(self, class_label: str, message: str) -> None:
        try:
            formatted_message: str = f"[{self.get_timestamp()}] [{class_label}] {message}"

            self.logs.append(formatted_message)

            if self.max_logs > 0:
                excess_logs: int = len(self.logs) - self.max_logs

                if excess_logs > 0:
                    self.logs = self.logs[excess_logs:]

        except Exception as e:
            print(f"[{self.get_timestamp()}] [{self.get_class_label()}] ❌ FAILURE: Error occurred in {self.get_caller_method()}.\n{e}")


import time
from typing import List

from core.base_utility import IntrospectionMixin


class Logger(IntrospectionMixin):

    def __init__(self, max_logs: int, debug_mode_enabled: bool) -> None:
        self.max_logs: int = max(0, max_logs)
        self.debug_mode_enabled: bool = debug_mode_enabled
        self.logs: List[str] = []

    def get_timestamp(self) -> str:
        return time.strftime("%Y-%m-%d %H:%M:%S")

    def get_logs(self) -> List[str]:
        return self.logs[:]

    def log(self, class_label: str, message: str) -> None:
        try:
            formatted_message: str = f"[{self.get_timestamp()}] [{class_label}] {message}"

            if self.debug_mode_enabled:
                self.logs.append(formatted_message)

                if self.max_logs > 0:
                    excess_logs: int = len(self.logs) - self.max_logs

                    if excess_logs > 0:
                        self.logs = self.logs[excess_logs:]

        except Exception as e:
            print(f"[{self.get_timestamp()}] [{self.get_class_label()}] ❌ FAILURE: Error occurred in {self.get_caller_method()}.\n{e}")


from typing import Any, Dict, List, Optional

from core.logger import Logger
from core.workflow.workflow_task import WorkflowTask


class WorkflowState:

    def __init__(self, logger: Logger) -> None:
        self.logger: Logger = logger
        self.tasks: List[WorkflowTask] = []
        self.outputs_by_task: Dict[str, Any] = {}

    def get_tasks(self) -> List[WorkflowTask]:
        return self.tasks

    def get_outputs_by_task(self, task_name: str) -> Optional[Any]:
        return self.outputs_by_task.get(task_name)

    def store_output_by_task(self, task_name: str, output: Any) -> None:
        self.outputs_by_task[task_name] = output

    def update_task_status(self, task_name: str, status: str) -> None:
        for task in self.tasks:
            if task.get("task_name") == task_name:
                task["task_status"] = status
                break


from typing import Any, Dict, List, cast

from core.base_utility import IntrospectionMixin
from core.constants import AgentTaskResult
from core.logger import Logger
from core.workflow_task import WorkflowTask


class WorkflowManager(IntrospectionMixin):

    def __init__(self, logger: Logger) -> None:
        self.logger: Logger = logger
        self.workflow_tasks: List[WorkflowTask] = []
        self.outputs_by_workflow_task: Dict[str, Any] = {}
        self.required_keys: List[str] = [
            "task_name",
            "agent_name",
            "agent_method_name",
            # optional: "depends_on",
            # optional: "requires_input",
            # optional: "produces_output",
            # optional: "max_retries",
        ]

    def get_workflow_tasks(self) -> List[WorkflowTask]:
        return self.workflow_tasks

    def update_workflow_task_status(self, workflow_task_name: str, status: str) -> None:
        for task in self.workflow_tasks:
            if task.get("task_name") == workflow_task_name:
                task["task_status"] = status
                break

    def validate_keys_and_load_workflow_tasks(self, workflow_plan: List[Dict[str, Any]]) -> bool:
        validated_workflow_tasks: List[WorkflowTask] = []

        for i, workflow_step in enumerate(workflow_plan):
            missing_keys: list[str] = [key for key in self.required_keys if key not in workflow_step]

            if missing_keys:
                self.logger.log(self.get_class_label(), f"❌ FAILURE: The workflow plan task at index {i} is missing required keys: {missing_keys}. Exiting...")
                return False

            try:
                workflow_step.setdefault("depends_on", [])
                workflow_step.setdefault("requires_input", False)
                workflow_step.setdefault("produces_output", False)
                workflow_step.setdefault("max_retries", 0)

                workflow_step["retries_left"] = workflow_step.get("max_retries")
                workflow_step["task_status"] = AgentTaskResult.PENDING.value

                workflow_task: WorkflowTask = cast(WorkflowTask, workflow_step)

                validated_workflow_tasks.append(workflow_task)

            except Exception as e:
                self.logger.log(self.get_class_label(), f"❌ FAILURE: Invalid workflow task at index {i}. Exiting...\n{e}")
                return False

        self.workflow_tasks = validated_workflow_tasks

        return True

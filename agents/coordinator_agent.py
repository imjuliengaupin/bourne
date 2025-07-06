
from typing import Any, Callable, Dict, List, Optional, Tuple

from rich.live import Live

from agents.base_agent import BaseAgent
from core import constants
from core.dashboard import Dashboard
from core.logger import Logger
from core.workflow.workflow_config_manager import WorkflowConfigManager
from core.workflow.workflow_queue import WorkflowQueue
from core.workflow.workflow_state import WorkflowState
from core.workflow.workflow_task import WorkflowTask


class CoordinatorAgent(BaseAgent):

    def __init__(self, logger: Logger, dashboard: Dashboard, dashboard_state: Live, workflow_plan_conf: WorkflowConfigManager, workflow_state: WorkflowState, agents: Dict[str, BaseAgent]) -> None:
        super().__init__(logger, dashboard, dashboard_state, workflow_plan_conf, workflow_state)
        self.agents: Dict[str, BaseAgent] = agents
        self.workflow_queue: WorkflowQueue = WorkflowQueue()

    def load_workflow(self, workflow_plan: List[WorkflowTask]) -> None:
        try:
            self.workflow_state.tasks.clear()
            self.workflow_queue.tasks.clear()

            for step in workflow_plan:
                task_data: WorkflowTask = step.copy()
                agent_name: Optional[str] = task_data.get("agent_name")
                agent_method_name: Optional[str] = task_data.get("agent_method_name")
                task_name: Optional[str] = task_data.get("task_name")
                task_data["retries_left"] = task_data.get("max_retries", 0)
                task_data["task_status"] = "PENDING"

                if not agent_name:
                    self.log_and_update_dashboard(f"⚠️ WARNING: Task '{task_data.get('task_name')}' missing 'agent_name'. Skipping...")
                    continue

                if not agent_method_name:
                    self.log_and_update_dashboard(f"⚠️ WARNING: Task '{task_data.get('task_name')}' missing 'agent_method_name'. Skipping...")
                    continue

                if not task_name:
                    self.log_and_update_dashboard(f"⚠️ WARNING: Task missing 'task_name' in workflow plan: {task_data}. Skipping...")
                    continue

                self.workflow_state.tasks.append(task_data)
                self.workflow_queue.add_task(task_data)

        except Exception as e:
            self.log_and_update_dashboard(f"❌ FAILURE: Error occurred in {self.get_caller_method()}\n{e}")

    def run_workflow(self) -> None:
        # NOTE For shared_input_data w/ type Any, if (long-term) common data structures emerge, you could define TypedDicts or Pydantic models for them and potentially have agents declare the types they expect/produce, allowing for more type checking, but this adds complexity.
        shared_input_data: Any = None

        processed_tasks_in_cycle: int = 0
        max_cycles_without_progress: int = 3
        initial_max_cycles: int = max_cycles_without_progress

        try:
            while any(task.get("task_status") in [constants.STATUS_PENDING, constants.STATUS_RETRIED, constants.STATUS_IN_PROGRESS] for task in self.workflow_state.tasks):
                runnable_task: Optional[WorkflowTask] = self.get_next_runnable_task()

                if runnable_task:
                    result, success = self.execute_task(runnable_task, shared_input_data)
                    new_shared_data: Any = self.handle_task_result(runnable_task, result, success)

                    if success and runnable_task.get("produces_output"):
                        shared_input_data = new_shared_data

                    processed_tasks_in_cycle += 1
                    max_cycles_without_progress = initial_max_cycles
                else:
                    if self.workflow_queue.is_empty():
                        if not any(task.get("task_status") in [constants.STATUS_PENDING, constants.STATUS_RETRIED, constants.STATUS_IN_PROGRESS] for task in self.workflow_state.tasks):
                            self.log_and_update_dashboard("ℹ️ INFO: Workflow queue is empty and all tasks are finished.")
                        else:
                            self.log_and_update_dashboard("⚠️ WARNING: Workflow queue is empty, but unfinished tasks remain (potential dependency cycle or error). Checking final state...")

                        break

                    self.log_and_update_dashboard("ℹ️ INFO: No runnable task found this cycle (dependencies unmet). Waiting...")

                    if processed_tasks_in_cycle == 0:
                        max_cycles_without_progress -= 1

                        # IDEA For stall detection, consider adding an explicit cyclic dependency check. This can be done using a graph traversal algorithm (like Depth First Search) on the task dependencies. This would provide an earlier error message if the workflow plan itself is invalid. This can be complex, so it's an advanced improvement.
                        if max_cycles_without_progress <= 0:
                            self.log_and_update_dashboard("❌ FAILURE: Workflow stalled. No tasks could run for several cycles. Check dependencies.")
                            break

                    processed_tasks_in_cycle = 0

            self.report_final_status()

        except Exception as e:
            self.log_and_update_dashboard(f"❌ FAILURE: Error occurred in {self.get_caller_method()}\n{e}")

    def report_final_status(self) -> None:
        final_statuses: List[str] = [task.get("task_status", "") for task in self.workflow_state.tasks]

        if all(status == constants.STATUS_SUCCESS for status in final_statuses):
            self.log_and_update_dashboard("🎉 FINISHED: No failed or unfinished tasks.")
        else:
            failed_tasks: List[str] = [task.get("task_name", "") for task in self.workflow_state.tasks if task.get("task_status") == constants.STATUS_FAILED]
            unfinished_tasks: List[str] = [task.get("task_name", "") for task in self.workflow_state.tasks if task.get(
                "task_status") in [constants.STATUS_PENDING, constants.STATUS_RETRIED, constants.STATUS_IN_PROGRESS]]

            if failed_tasks:
                self.log_and_update_dashboard(f"⚠️ FINISHED: Failed tasks: {failed_tasks}.")

            if unfinished_tasks:
                self.log_and_update_dashboard(f"⚠️ FINISHED: Unfinished tasks (check dependencies/errors): {unfinished_tasks}.")

    def check_task_dependencies(self, task: WorkflowTask) -> bool:
        try:
            depends_on_list: List[str] = task.get("depends_on", [])

            if not isinstance(depends_on_list, list):
                self.log_and_update_dashboard(
                    f"⚠️ WARNING: Invalid 'depends_on' format for task '{task.get('task_name')}': Expected list, but got {type(depends_on_list)}. Assuming no dependencies and proceeding.")
                return True

            for dependent_task_name in depends_on_list:
                dependent_task: Optional[WorkflowTask] = next((task for task in self.workflow_state.tasks if task.get("task_name") == dependent_task_name), None)

                if not dependent_task:
                    self.log_and_update_dashboard(
                        f"⚠️ WARNING: Dependency check failed for task '{task.get('task_name')}': Dependent task '{dependent_task_name}' not found in workflow state.")
                    return False

                if dependent_task.get("task_status") != constants.STATUS_SUCCESS:
                    return False

            return True

        except Exception as e:
            self.log_and_update_dashboard(f"❌ FAILURE: Error checking dependencies for task '{task.get('task_name')}'\n{e}")
            return False

    def get_next_runnable_task(self) -> Optional[WorkflowTask]:
        max_checks: int = self.workflow_queue.get_size()
        num_checks_performed: int = 0

        while num_checks_performed < max_checks:
            task: Optional[WorkflowTask] = self.workflow_queue.get_next_task()

            if not task:
                break

            if self.check_task_dependencies(task):
                return task
            else:
                self.workflow_queue.add_task(task)
                self.log_and_update_dashboard(f"🔁 REQUEUE: Task '{task.get('task_name')}' dependencies not met. Re-queuing.")

            num_checks_performed += 1

        return None

    def execute_task(self, task: WorkflowTask, shared_input_data: Any) -> Tuple[Any, bool]:
        task_name: Optional[str] = task.get("task_name")
        agent_name: Optional[str] = task.get("agent_name")
        agent_method_name: Optional[str] = task.get("agent_method_name")

        if not all([task_name, agent_name, agent_method_name]):
            self.log_and_update_dashboard(f"❌ FAILURE: Task '{task_name or 'Unknown'}' is missing essential keys ('task_name', 'agent_name', 'agent_method_name').")
            return None, False

        if not agent_name:
            self.log_and_update_dashboard(f"❌ FAILURE: Agent name is None for task '{task_name}'.")
            return None, False

        agent: Optional[Any] = self.agents.get(agent_name)

        if not agent:
            self.log_and_update_dashboard(f"❌ FAILURE: Agent '{agent_name}' not found for task '{task_name}'.")
            return None, False

        agent_method: Optional[Callable] = None

        try:
            if agent_method_name:
                agent_method = getattr(agent, agent_method_name)

        except Exception as e:
            self.log_and_update_dashboard(f"❌ FAILURE: Error accessing method '{agent_method_name}' on agent '{agent_name}'\n{e}")
            return None, False

        if task_name:
            self.workflow_state.update_task_status(task_name, constants.STATUS_IN_PROGRESS)
            self.log_and_update_dashboard(f"▶️ START: Executing task '{task_name}' using {agent_name}.{agent_method_name}")

        result: Any = None
        success: bool = False

        try:
            requires_input: bool = task.get("requires_input", False)

            if requires_input:
                if shared_input_data is None:
                    self.log_and_update_dashboard(f"⚠️ WARNING: Task '{task_name}' requires input, but no 'shared_input_data' is available. Proceeding with None.")

                if agent_method:
                    result = agent_method(shared_input_data)
            else:
                if agent_method:
                    result = agent_method()

            success = True

        except Exception as e:
            self.log_and_update_dashboard(f"❌ FAILURE: Exception occurred in task '{task_name}' during execution\n{e}")
            success = False

        return result, success

    def handle_task_result(self, task: WorkflowTask, result: Any, success: bool) -> Any:
        task_name: Optional[str] = task.get("task_name")
        new_shared_data: Any = None

        try:
            if success and task_name:
                self.workflow_state.update_task_status(task_name, constants.STATUS_SUCCESS)

                if task.get("produces_output"):
                    new_shared_data = result
                    self.workflow_state.outputs_by_task[task_name] = result
            else:
                retries_left: int = task.get("retries_left", 0)

                if retries_left > 0:
                    task["retries_left"] = retries_left - 1
                    if task_name:
                        self.workflow_state.update_task_status(task_name, constants.STATUS_RETRIED)

                    self.workflow_queue.add_task(task)
                    self.log_and_update_dashboard(f"🔁 REQUEUE: Task '{task_name}' failed. Re-queuing to retry ({task.get('retries_left', 0)} left).")
                else:
                    if task_name:
                        self.workflow_state.update_task_status(task_name, constants.STATUS_FAILED)
                        self.log_and_update_dashboard(f"❌ FAILURE: Task '{task_name}' failed permanently after all retries.")

        except Exception as e:
            if task_name:
                self.workflow_state.update_task_status(task_name, constants.STATUS_FAILED)
                self.log_and_update_dashboard(f"❌ FAILURE: Error handling result for task '{task_name}'\n{e}")

        return new_shared_data

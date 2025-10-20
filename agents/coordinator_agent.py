
from typing import Any, Callable, Dict, List, Optional, Tuple

from agents.base_agent import BaseAgent
from agents.dataclasses.agent_context import AgentContext
from core.constants import AgentTaskResult
from core.workflow_task import WorkflowTask
from core.workflow_task_queue import WorkflowTaskQueue


class CoordinatorAgent(BaseAgent):

    def __init__(self, agent_context: AgentContext, agents: Dict[str, BaseAgent]) -> None:
        super().__init__(agent_context)
        self.agents: Dict[str, BaseAgent] = agents
        self.workflow_task_queue: WorkflowTaskQueue = WorkflowTaskQueue(agent_context.logger)

    def run_workflow(self) -> None:
        if not self.agent_context.workflow_plan_state.workflow_tasks:
            self.log_and_update_dashboard("❌ FAILURE: No validated workflow tasks are available to execute.")
            return

        for task in self.agent_context.workflow_plan_state.workflow_tasks:
            self.workflow_task_queue.add_workflow_task(task)

        shared_input_data: Any = None
        processed_tasks_in_cycle: int = 0
        max_cycles_without_progress: int = 3
        initial_max_cycles: int = max_cycles_without_progress

        try:
            while any(task.get("task_status") in [AgentTaskResult.PENDING.value, AgentTaskResult.IN_PROGRESS.value, AgentTaskResult.RETRIED.value] for task in self.agent_context.workflow_plan_state.workflow_tasks):
                workflow_task: Optional[WorkflowTask] = self.get_next_runnable_task()

                if workflow_task:
                    result, success = self.execute_task(workflow_task, shared_input_data)

                    new_shared_input_data: Any = self.handle_task_result(workflow_task, result, success)

                    if success and workflow_task.get("produces_output"):
                        shared_input_data = new_shared_input_data

                    processed_tasks_in_cycle += 1
                    max_cycles_without_progress = initial_max_cycles
                else:
                    if self.workflow_task_queue.is_empty():
                        if not any(task.get("task_status") in [AgentTaskResult.PENDING.value, AgentTaskResult.IN_PROGRESS.value, AgentTaskResult.RETRIED.value] for task in self.agent_context.workflow_plan_state.workflow_tasks):
                            self.log_and_update_dashboard("ℹ️ INFO: Workflow queue is empty and all tasks are finished.")
                        else:
                            self.log_and_update_dashboard("⚠️ WARNING: Workflow queue is empty, but unfinished tasks remain (potential dependency cycle or error). Checking final state...")
                        break

                    self.log_and_update_dashboard("ℹ️ INFO: No runnable task found this cycle (dependencies unmet). Waiting...")

                    if processed_tasks_in_cycle == 0:
                        max_cycles_without_progress -= 1

                        if max_cycles_without_progress <= 0:
                            self.log_and_update_dashboard("❌ FAILURE: Workflow stalled. No tasks could run for several cycles. Check dependencies.")
                            break

                    processed_tasks_in_cycle = 0

            self.report_final_status()

        except Exception as e:
            self.log_and_update_dashboard(f"❌ FAILURE: Error occurred in {self.get_caller_method()}.\n{e}")

    def report_final_status(self) -> None:
        final_statuses: List[str] = [str(task.get("task_status")) for task in self.agent_context.workflow_plan_state.workflow_tasks]

        if all(status == AgentTaskResult.SUCCESS.value for status in final_statuses):
            self.log_and_update_dashboard("🎉 FINISHED: No failed or unfinished tasks.")
        else:
            failed_tasks: List[str] = [str(task.get("task_name")) for task in self.agent_context.workflow_plan_state.workflow_tasks if task.get("task_status") == AgentTaskResult.FAILED.value]
            unfinished_tasks: List[str] = [str(task.get("task_name")) for task in self.agent_context.workflow_plan_state.workflow_tasks if task.get("task_status") in [AgentTaskResult.PENDING.value, AgentTaskResult.IN_PROGRESS.value, AgentTaskResult.RETRIED.value]]

            if failed_tasks:
                self.log_and_update_dashboard(f"⚠️ WARNING: Failed tasks: {failed_tasks}.")

            if unfinished_tasks:
                self.log_and_update_dashboard(f"⚠️ WARNING: Unfinished tasks (check dependencies/errors): {unfinished_tasks}.")

    def check_task_dependencies(self, task: WorkflowTask) -> bool:
        try:
            depends_on_list: List[str] = task.get("depends_on") or []

            if not isinstance(depends_on_list, list):
                self.log_and_update_dashboard(f"⚠️ WARNING: Invalid 'depends_on' format for task '{task.get('task_name')}': Expected list, but got {type(depends_on_list)}. Assuming no dependencies and proceeding.")
                return True

            for dependent_task_name in depends_on_list:
                dependent_task: Optional[WorkflowTask] = next((task for task in self.agent_context.workflow_plan_state.workflow_tasks if task.get("task_name") == dependent_task_name), None)

                if not dependent_task:
                    self.log_and_update_dashboard(f"⚠️ WARNING: Dependency check failed for task '{task.get('task_name')}': Dependent task '{dependent_task_name}' not found in workflow state.")
                    return False

                if dependent_task.get("task_status") != AgentTaskResult.SUCCESS.value:
                    return False

            return True

        except Exception as e:
            self.log_and_update_dashboard(f"❌ FAILURE: Error checking dependencies for task '{task.get('task_name')}'.\n{e}")
            return False

    def get_next_runnable_task(self) -> Optional[WorkflowTask]:
        max_checks: int = self.workflow_task_queue.get_size()
        num_checks_performed: int = 0

        while num_checks_performed < max_checks:
            task: Optional[WorkflowTask] = self.workflow_task_queue.get_next_workflow_task()

            if not task:
                break

            if self.check_task_dependencies(task):
                return task
            else:
                self.workflow_task_queue.add_workflow_task(task)
                self.log_and_update_dashboard(f"🔁 RE-QUEUE: Task '{task.get('task_name')}' dependencies not met. Re-queuing.")

            num_checks_performed += 1

        return None

    def execute_task(self, task: WorkflowTask, shared_input_data: Any) -> Tuple[Any, bool]:
        task_name: Optional[str] = task.get("task_name")
        agent_name: Optional[str] = task.get("agent_name")
        agent_method_name: Optional[str] = task.get("agent_method_name")

        if not agent_name:
            self.log_and_update_dashboard(f"❌ FAILURE: Agent name is None for task '{task_name}'.")
            return None, False

        agent: Optional[Any] = self.agents.get(agent_name)

        if not agent:
            self.log_and_update_dashboard(f"❌ FAILURE: Agent '{agent_name}' not found for task '{task_name}'. Available agents: {list(self.agents.keys())}.")
            return None, False

        agent_method: Optional[Callable[..., Any]] = None

        try:
            if agent_method_name:
                agent_method = getattr(agent, agent_method_name)

        except Exception as e:
            self.log_and_update_dashboard(f"❌ FAILURE: Error accessing method '{agent_method_name}' on agent '{agent_name}'.\n{e}")
            return None, False

        if task_name:
            self.agent_context.workflow_plan_state.update_workflow_task_status(task_name, AgentTaskResult.IN_PROGRESS.value)
            self.log_and_update_dashboard(f"▶️ START: Executing task '{task_name}' using '{agent_name}.{agent_method_name}'.")

        result: Any = None
        success: bool = False

        try:
            requires_input: bool = task.get("requires_input") or False

            if requires_input:
                if shared_input_data is None:
                    self.log_and_update_dashboard(f"⚠️ WARNING: Task '{task_name}' requires input, but no 'shared_input_data' is available. Proceeding with None.")

                if agent_method:
                    result = agent_method(shared_input_data)
            else:
                if agent_method:
                    result = agent_method()

            if hasattr(result, 'value') and hasattr(result, 'is_success'):
                # Method returned TaskResult enum
                success = result.is_success
                task_status = result.status_string
            elif isinstance(result, bool):
                # Method returned boolean (for backward compatibility)
                success = result
                task_status = AgentTaskResult.SUCCESS.value if result else AgentTaskResult.FAILED.value
            else:
                # Fallback for other return types
                success = bool(result)
                task_status = AgentTaskResult.SUCCESS.value if success else AgentTaskResult.FAILED.value

        except Exception as e:
            self.log_and_update_dashboard(f"❌ FAILURE: Exception occurred in task '{task_name}' during execution.\n{e}")
            success = False
            task_status = AgentTaskResult.FAILED.value

        if success and task_name:
            self.agent_context.workflow_plan_state.update_workflow_task_status(task_name, task_status)
        elif task_name:
            self.agent_context.workflow_plan_state.update_workflow_task_status(task_name, AgentTaskResult.FAILED.value)

        return result, success

    def handle_task_result(self, task: WorkflowTask, result: Any, success: bool) -> Any:
        task_name: Optional[str] = task.get("task_name")
        new_shared_input_data: Any = None

        try:
            if success and task_name:
                produces_output: bool = task.get("produces_output") or False

                if produces_output:
                    new_shared_input_data = result
                    self.agent_context.workflow_plan_state.outputs_by_workflow_task[task_name] = result
            else:
                retries_left: int = task.get("retries_left") or 0

                if retries_left > 0:
                    task["retries_left"] = retries_left - 1

                    if task_name:
                        self.agent_context.workflow_plan_state.update_workflow_task_status(task_name, AgentTaskResult.RETRIED.value)

                    self.workflow_task_queue.add_workflow_task(task)
                    self.log_and_update_dashboard(f"🔁 RE-QUEUE: Task '{task_name}' failed. Re-queuing to retry ({task.get('retries_left')} left).")
                else:
                    if task_name:
                        self.agent_context.workflow_plan_state.update_workflow_task_status(task_name, AgentTaskResult.FAILED.value)
                        self.log_and_update_dashboard(f"❌ FAILURE: Task '{task_name}' failed permanently after all retries.")

        except Exception as e:
            if task_name:
                self.agent_context.workflow_plan_state.update_workflow_task_status(task_name, AgentTaskResult.FAILED.value)
                self.log_and_update_dashboard(f"❌ FAILURE: Error handling result for task '{task_name}'.\n{e}")

        return new_shared_input_data


import json
from typing import Any, Dict, List, Optional

from rich.live import Live

from agents.base_agent import BaseAgent
from agents.coordinator_agent import CoordinatorAgent
from agents.dingestion_agent import DataIngestionAgent
from agents.dstorage_agent import DataStorageAgent
from agents.dtransformation_agent import DataTransformationAgent
from agents.dvalidation_agent import DataValidationAgent
from core.dashboard import Dashboard
from core.logger import Logger
from core.workflow.workflow_config_manager import WorkflowConfigManager
from core.workflow.workflow_state import WorkflowState
from core.workflow.workflow_task import WorkflowTask


def main() -> None:
    logger: Logger = Logger(max_logs=10)
    dashboard: Dashboard = Dashboard(logger.max_logs)

    workflow_plan: Optional[List[WorkflowTask]] = load_json("workflows/demo.json")
    workflow_plan_conf: WorkflowConfigManager = WorkflowConfigManager(load_json("workflows/configs/demo.json"))
    workflow_state: WorkflowState = WorkflowState(logger)

    with Live(dashboard.render(workflow_state.tasks, logger.get_logs()), refresh_per_second=4, console=dashboard.console) as dashboard_state:
        if workflow_plan is None or workflow_plan_conf is None:
            logger.log("Main", "❌ Error during attempted load of the workflow plan and/or workflow plan configurations. Exiting...")
            dashboard_state.update(dashboard.render([], logger.get_logs()))
            return

        if not workflow_plan_conf.validate_keys():
            logger.log("Main", f"❌ The workflow plan configurations are missing required keys: {workflow_plan_conf.required_keys}. Exiting...")
            dashboard_state.update(dashboard.render([], logger.get_logs()))
            return

        def unpack_agent() -> tuple:
            return (logger, dashboard, dashboard_state, workflow_plan_conf, workflow_state)

        agents: Dict[str, BaseAgent] = {
            "DataIngestionAgent": DataIngestionAgent(*unpack_agent()),
            "DataValidationAgent": DataValidationAgent(*unpack_agent()),
            "DataTransformationAgent": DataTransformationAgent(*unpack_agent()),
            "DataStorageAgent": DataStorageAgent(*unpack_agent()),
        }

        coordinator: CoordinatorAgent = CoordinatorAgent(*unpack_agent(), agents)
        coordinator.load_workflow(workflow_plan)
        coordinator.run_workflow()


def load_json(path: str) -> Optional[Any]:
    try:
        with open(path, 'r', encoding='utf-8') as file:
            return json.load(file)

    except Exception:
        return None


if __name__ == "__main__":
    main()


import json
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from rich.live import Live

from agents.base_agent import BaseAgent
from agents.coordinator_agent import CoordinatorAgent
from agents.data_ingestion_agent import DataIngestionAgent
from agents.data_storage_agent import DataStorageAgent
from agents.data_transformation_agent import DataTransformationAgent
from agents.data_validation_agent import DataValidationAgent
from agents.dataclasses.agent_context import AgentContext
from core.connector_manager import ConnectorManager
from core.dashboard import Dashboard
from core.logger import Logger
from core.workflow_manager import WorkflowManager


def main(workflow: str, connector: str) -> None:
    logger: Logger = Logger(max_logs=10)
    dashboard: Dashboard = Dashboard(logger)

    workflow_plan_json: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = load_json(logger, Path(workflow))
    workflow_plan: Optional[List[Dict[str, Any]]] = workflow_plan_json if isinstance(workflow_plan_json, list) else None
    workflow_plan_state: WorkflowManager = WorkflowManager(logger)

    source_data_connector_json: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = load_json(logger, Path(connector))
    source_data_connector: Optional[Dict[str, Any]] = source_data_connector_json if isinstance(source_data_connector_json, dict) else None
    source_data_connector_state: ConnectorManager = ConnectorManager(logger, source_data_connector)

    with Live(dashboard.render(workflow_plan_state.get_workflow_tasks(), logger.get_logs()), refresh_per_second=3.0, console=dashboard.console) as dashboard_state:
        agent_context: AgentContext = AgentContext(logger, dashboard, dashboard_state, workflow_plan_state, source_data_connector_state)

        if not is_workflow_ready(agent_context, workflow_plan, source_data_connector):
            return

        agents: Dict[str, BaseAgent] = setup_agents(agent_context)
        coordinator_agent: CoordinatorAgent = CoordinatorAgent(agent_context, agents)
        coordinator_agent.run_workflow()


def setup_agents(agent_context: AgentContext) -> Dict[str, BaseAgent]:
    return {
        "DataIngestionAgent": DataIngestionAgent(agent_context),
        "DataValidationAgent": DataValidationAgent(agent_context),
        "DataTransformationAgent": DataTransformationAgent(agent_context),
        "DataStorageAgent": DataStorageAgent(agent_context),
    }


def is_workflow_ready(agent_context: AgentContext, workflow_plan: Optional[List[Dict[str, Any]]], source_data_connector: Optional[Dict[str, Any]]) -> bool:
    if workflow_plan is None or source_data_connector is None:
        agent_context.dashboard_state.update(agent_context.dashboard.render([], agent_context.logger.get_logs()))
        return False

    if not agent_context.workflow_plan_state.validate_keys_and_load_workflow_tasks(workflow_plan):
        agent_context.dashboard_state.update(agent_context.dashboard.render([], agent_context.logger.get_logs()))
        return False

    if not agent_context.source_data_connector_state.validate_keys():
        agent_context.dashboard_state.update(agent_context.dashboard.render([], agent_context.logger.get_logs()))
        return False

    return True


def load_json(logger: Logger, path: Union[str, Path]) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:
    try:
        with open(path, "r", encoding="utf-8") as file:
            json_content: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = json.load(file)
            return json_content

    except FileNotFoundError as e:
        logger.log("Main", f"❌ FAILURE: Configuration file not found {path}: {e}. Exiting...")
        return None

    except json.JSONDecodeError as e:
        logger.log("Main", f"❌ FAILURE: Invalid JSON structure found in file {path}: {e}. Exiting...")
        return None

    except Exception as e:
        logger.log("Main", f"❌ FAILURE: Unexpected error while loading configuration file {path}: {e}. Exiting...")
        return None


def parse_program_args() -> Namespace:
    parser: ArgumentParser = ArgumentParser()

    parser.add_argument(
        "--workflow",
        default="configs/workflows/valid/workflow.json",
        help="Path to the workflow plan configuration file."
    )

    parser.add_argument(
        "--connector",
        default="configs/connectors/valid/connector.json",
        help="Path to the source data connector configuration file."
    )

    return parser.parse_args()


if __name__ == "__main__":
    args: Namespace = parse_program_args()
    main(args.workflow, args.connector)

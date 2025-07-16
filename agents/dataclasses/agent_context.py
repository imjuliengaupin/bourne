
from dataclasses import dataclass

from rich.live import Live

from core.connector_manager import ConnectorManager
from core.dashboard import Dashboard
from core.logger import Logger
from core.workflow_manager import WorkflowManager


@dataclass
class AgentContext:
    logger: Logger
    dashboard: Dashboard
    dashboard_state: Live
    workflow_plan_state: WorkflowManager
    source_data_connector_state: ConnectorManager

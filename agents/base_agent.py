
import inspect
import time
from abc import ABC
from types import FrameType

from rich.live import Live

from core.dashboard import Dashboard
from core.logger import Logger
from core.workflow.workflow_config_manager import WorkflowConfigManager
from core.workflow.workflow_state import WorkflowState


class BaseAgent(ABC):
    # NOTE: Create abstract methods using the @abstractmethod decorator

    def __init__(self, logger: Logger, dashboard: Dashboard, dashboard_state: Live, workflow_plan_conf: WorkflowConfigManager, workflow_state: WorkflowState) -> None:
        self.logger: Logger = logger
        self.dashboard: Dashboard = dashboard
        self.dashboard_state: Live = dashboard_state
        self.workflow_plan_conf: WorkflowConfigManager = workflow_plan_conf
        self.workflow_state: WorkflowState = workflow_state

    def get_class_label(self) -> str:
        return type(self).__name__

    def get_caller_method(self) -> str:
        frame: FrameType = inspect.currentframe()

        if frame is not None and frame.f_back is not None:
            return frame.f_back.f_code.co_name + "()"

        return "unknown_caller_method()"

    def log_and_update_dashboard(self, message: str, data_before_transform=None, data_after_transform=None) -> None:
        self.logger.log(self.get_class_label(), message)

        self.dashboard_state.update(self.dashboard.render(
            self.workflow_state.get_tasks(),
            self.logger.get_logs(),
            data_before_transform=data_before_transform,
            data_after_transform=data_after_transform
        ))

        time.sleep(0.5)

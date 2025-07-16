
import inspect
import time
from abc import ABC
from types import FrameType
from typing import Optional

from agents.dataclasses.agent_context import AgentContext


class BaseAgent(ABC):
    # NOTE Create abstract methods using the @abstractmethod decorator

    def __init__(self, agent_context: AgentContext) -> None:
        self.agent_context: AgentContext = agent_context

    def get_class_label(self) -> str:
        return type(self).__name__

    def get_caller_method(self) -> str:
        frame: Optional[FrameType] = inspect.currentframe()

        if frame is not None and frame.f_back is not None:
            return frame.f_back.f_code.co_name + "()"

        return "unknown_caller_method()"

    def log_and_update_dashboard(self, message: Optional[str] = None, data_before_transformation=None, data_after_transformation=None) -> None:
        if message:
            self.agent_context.logger.log(self.get_class_label(), message)

        if hasattr(self.agent_context, 'dashboard_state') and self.agent_context.dashboard_state:
            self.agent_context.dashboard_state.update(self.agent_context.dashboard.render(
                self.agent_context.workflow_plan_state.get_workflow_tasks(),
                self.agent_context.logger.get_logs(),
                data_before_transformation=data_before_transformation,
                data_after_transformation=data_after_transformation
            ))

            time.sleep(0.5)

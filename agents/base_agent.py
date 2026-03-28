
import time
from abc import ABC
from typing import Any, Dict, Optional

from agents.dataclasses.agent_context import AgentContext
from core.base_utility import IntrospectionMixin


class BaseAgent(IntrospectionMixin, ABC):
    # Create abstract methods using the @abstractmethod decorator

    def __init__(self, agent_context: AgentContext) -> None:
        self.agent_context: AgentContext = agent_context

    def log_and_update_dashboard(self, message: Optional[str] = None, data_before_transformation: Optional[Dict[str, Any]] = None, data_after_transformation: Optional[Dict[str, Any]] = None) -> None:
        if message:
            self.agent_context.logger.log(self.get_class_label(), message)

        if self.agent_context.logger.debug_mode_enabled and hasattr(self.agent_context, 'dashboard_state') and self.agent_context.dashboard_state:
            self.agent_context.dashboard_state.update(self.agent_context.dashboard.render(
                self.agent_context.workflow_plan_state.get_workflow_tasks(),
                self.agent_context.logger.get_logs(),
                data_before_transformation=data_before_transformation,
                data_after_transformation=data_after_transformation
            ))

            time.sleep(0.05)


import json
import os
from typing import Any, Dict, List

from rich.live import Live

from agents.base_agent import BaseAgent
from core.dashboard import Dashboard
from core.logger import Logger
from core.workflow.workflow_config_manager import WorkflowConfigManager
from core.workflow.workflow_state import WorkflowState


class DataStorageAgent(BaseAgent):

    def __init__(self, logger: Logger, dashboard: Dashboard, dashboard_state: Live, workflow_plan_conf: WorkflowConfigManager, workflow_state: WorkflowState) -> None:
        super().__init__(logger, dashboard, dashboard_state, workflow_plan_conf, workflow_state)

        output_path_config = self.workflow_plan_conf.get("transform_output_path")
        self.output_path: str = output_path_config if output_path_config else "data/data_transformed.txt"
        self.output_dir: str = os.path.dirname(self.output_path)

        if not output_path_config:
            self.log_and_update_dashboard("⚠️ WARNING:  Configuration 'transform_output_path' is not specified. Setting to default.")

    def save_data(self, data: List[Dict[str, Any]]) -> bool:
        if not data:
            self.log_and_update_dashboard("⚠️ WARNING: No data provided.")
            return False

        self.log_and_update_dashboard(f"▶️ START: Attempting to save {len(data)} records to {self.output_path}.")

        try:
            os.makedirs(self.output_dir, exist_ok=True)

            with open(self.output_path, 'w', encoding="utf-8") as file:
                if self.output_path.endswith(".ndjson"):
                    for record in data:
                        file.write(json.dumps(record, ensure_ascii=False) + "\n")
                else:
                    json.dump(data, file, indent=2, ensure_ascii=False)

            self.log_and_update_dashboard(f"✅ SUCCESS: Saved {len(data)} records to {self.output_path}.")
            return True

        except Exception as e:
            self.log_and_update_dashboard(f"❌ FAILURE: Error occurred in {self.get_caller_method()}\n{e}")
            return False

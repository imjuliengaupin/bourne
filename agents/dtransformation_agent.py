
import time
from typing import Any, Dict, List, Optional

from pydantic import TypeAdapter
from rich.live import Live

from agents.base_agent import BaseAgent
from core.dashboard import Dashboard
from core.logger import Logger
from core.workflow.workflow_config_manager import WorkflowConfigManager
from core.workflow.workflow_state import WorkflowState
from schemas.shared_input_data import Record


class DataTransformationAgent(BaseAgent):

    def __init__(self, logger: Logger, dashboard: Dashboard, dashboard_state: Live, workflow_plan_conf: WorkflowConfigManager, workflow_state: WorkflowState) -> None:
        super().__init__(logger, dashboard, dashboard_state, workflow_plan_conf, workflow_state)

    def transform_data(self, shared_input_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        self.log_and_update_dashboard(f"▶️ START: Attempting to transform {len(shared_input_data)} records.")

        mode: Optional[str] = self.workflow_plan_conf.get("transform_mode")

        if mode is None:
            self.log_and_update_dashboard("❌ FAILURE: Configuration 'transform_mode' is not specified.")
            return []

        records: List[Dict[str, Any]] = []

        try:
            if isinstance(shared_input_data, dict):
                records = [shared_input_data]

            elif isinstance(shared_input_data, list):
                if all(isinstance(item, dict) for item in shared_input_data):
                    records = shared_input_data
                else:
                    self.log_and_update_dashboard("❌ FAILURE: Invalid data format, input list contains non-dictionary items.")
                    return []
            else:
                self.log_and_update_dashboard(f"❌ FAILURE: Invalid data format, expected a dictionary or list of dictionaries, but got {type(shared_input_data).__name__}.")
                return []

            if not records:
                self.log_and_update_dashboard("⚠️ WARNING: No data provided.")
                return []

            transformed_records: List[Dict[str, Any]] = []

            for record in records:
                transformed = self.apply_transformation(record, mode)
                transformed_records.append(transformed)
                time.sleep(0.1)

            try:
                # Validate the transformed records against the Pydantic schema
                TypeAdapter(List[Record]).validate_python(transformed_records)
                self.log_and_update_dashboard(f"✅ SUCCESS: Transformed {len(transformed_records)} records.")

            except Exception as e:
                self.log_and_update_dashboard(f"❌ FAILURE: Output schema validation failed\n{e}")
                return []

            return transformed_records

        except Exception as e:
            self.log_and_update_dashboard(f"❌ FAILURE: Error occurred in {self.get_caller_method()}\n{e}")
            return []

    def apply_transformation(self, data_before_transform: Dict[str, Any], mode: str) -> Dict[str, Any]:

        if not isinstance(data_before_transform, dict):
            return data_before_transform

        data_after_transform: Dict[str, Any] = {}

        try:
            if mode == "lowercase_keys":
                data_after_transform = {key.lower(): value for key, value in data_before_transform.items()}
            else:
                self.log_and_update_dashboard(f"⚠️ WARNING: Unknown transform mode '{mode}', defaulting to original record.")
                data_after_transform = data_before_transform.copy()

            data_after_transform["is_transformed"] = True
            data_after_transform["transformed_on"] = time.strftime("%Y-%m-%d %H:%M:%S")

            self.log_and_update_dashboard("Transformed record", data_before_transform, data_after_transform)

        except Exception as e:
            self.log_and_update_dashboard(f"❌ FAILURE: Error occurred in {self.get_caller_method()}\n{e}")
            return {"error": e, "original_record": data_before_transform}

        return data_after_transform

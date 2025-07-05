
from typing import Any, Dict, List, Optional, Type

from pydantic import TypeAdapter
from rich.live import Live

from agents.base_agent import BaseAgent
from core.dashboard import Dashboard
from core.logger import Logger
from core.workflow.workflow_config_manager import WorkflowConfigManager
from core.workflow.workflow_state import WorkflowState
from schemas.shared_input_data import Record


class DataValidationAgent(BaseAgent):

    TYPE_MAP: Dict[str, Type[Any]] = {
        "str": str,
        "int": int,
        "float": float,
        "list": list,
        "dict": dict,
        "bool": bool
    }

    def __init__(self, logger: Logger, dashboard: Dashboard, dashboard_state: Live, workflow_plan_conf: WorkflowConfigManager, workflow_state: WorkflowState) -> None:
        super().__init__(logger, dashboard, dashboard_state, workflow_plan_conf, workflow_state)
        self.expected_schema: Dict[str, Type[Any]] = {}
        self.raw_schema: Optional[Dict[str, str]] = self.workflow_plan_conf.get("expected_schema")

        if self.raw_schema:
            for key, type_name in self.raw_schema.items():
                type_obj: Optional[Type[Any]] = self.TYPE_MAP.get(str(type_name).lower())

                if type_obj:
                    self.expected_schema[key] = type_obj
                else:
                    self.log_and_update_dashboard(f"⚠️ WARNING: Unknown type '{type_name}' in 'expected_schema' for key '{key}'. Skipping...")
        else:
            self.log_and_update_dashboard("⚠️ WARNING: Configuration 'expected_schema' is not specified.")

    def validate_data(self, shared_input_data: Any) -> bool:
        self.log_and_update_dashboard(f"▶️ START: Attempting to validate {len(shared_input_data)} records.")

        if not self.expected_schema:
            self.log_and_update_dashboard("❌ FAILURE: Configuration 'expected_schema' is not specified.")
            return False

        records: List[Dict[str, Any]] = []

        try:
            if isinstance(shared_input_data, dict):
                records = [shared_input_data]

            elif isinstance(shared_input_data, list):
                if all(isinstance(item, dict) for item in shared_input_data):
                    records = shared_input_data
                else:
                    self.log_and_update_dashboard(f"❌ FAILURE: Invalid data format, expected a dictionary or list of dictionaries, but got {type(records).__name__}.")
                    return False
            else:
                self.log_and_update_dashboard(f"❌ FAILURE: Invalid data format, expected a dictionary or list of dictionaries, but got {type(records).__name__}.")
                return False

            if not records:
                self.log_and_update_dashboard("❌ FAILURE: No data provided.")
                return False

            for i, record in enumerate(records):
                if not isinstance(record, dict):
                    self.log_and_update_dashboard(f"❌ FAILURE: Invalid record format at index {i}, expected a dictionary, but got {type(record).__name__}.")
                    return False

                for key, expected_type in self.expected_schema.items():
                    if key not in record:
                        self.log_and_update_dashboard(f"❌ FAILURE: Missing key: '{key}' in record.")
                        return False

                    actual_value = record[key]

                    if not isinstance(actual_value, expected_type):
                        self.log_and_update_dashboard(f"❌ FAILURE: Incorrect type for key '{key}' in record at index {i}. Expected {expected_type.__name__}, but got {type(actual_value).__name__}.")
                        return False

            try:
                validated: List[Record] = TypeAdapter(List[Record]).validate_python(shared_input_data)
                self.log_and_update_dashboard(f"✅ SUCCESS: Validated {len(validated)} records.")

            except Exception as e:
                self.log_and_update_dashboard(f"❌ FAILURE: Schema validation failed\n{e}")
                return False

            return True

        except Exception as e:
            self.log_and_update_dashboard(f"❌ FAILURE: Error occurred in {self.get_caller_method()}\n{e}")
            return False

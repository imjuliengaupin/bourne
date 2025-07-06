
import json
import os
from typing import Any, Dict, List, Optional, Union

from rich.live import Live

from agents.base_agent import BaseAgent
from core import constants
from core.dashboard import Dashboard
from core.logger import Logger
from core.workflow.workflow_config_manager import WorkflowConfigManager
from core.workflow.workflow_state import WorkflowState


class DataIngestionAgent(BaseAgent):

    def __init__(self, logger: Logger, dashboard: Dashboard, dashboard_state: Live, workflow_plan_conf: WorkflowConfigManager, workflow_state: WorkflowState) -> None:
        super().__init__(logger, dashboard, dashboard_state, workflow_plan_conf, workflow_state)

    def ingest_data(self) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:
        source_type: Optional[str] = self.workflow_plan_conf.get("source_type")
        source_path: Optional[str] = self.workflow_plan_conf.get("source_path")

        self.log_and_update_dashboard(f"▶️ START: Attempting to fetch records from '{source_type}' under {source_path}.")

        if not source_type:
            self.log_and_update_dashboard("❌ FAILURE: Configuration 'source_type' is not specified.")
            return None

        if not source_path:
            self.log_and_update_dashboard("❌ FAILURE: Configuration 'source_path' is not specified.")
            return None

        try:
            if source_type == constants.LOCAL_FILE_TYPE:
                return self.ingesting_local_file(source_type, source_path)
            else:
                self.log_and_update_dashboard(f"❌ FAILURE: Unsupported 'source_type' specified ('{source_type}').")
                return None

        except Exception as e:
            self.log_and_update_dashboard(f"❌ FAILURE: Error occurred in {self.get_caller_method()}\n{e}")
            return None

    def ingesting_local_file(self, source_type: str, source_path: str) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:
        try:
            if not os.path.exists(source_path):
                self.log_and_update_dashboard(f"❌ FAILURE: '{source_type}' not found under {source_path}.")
                return None

            records: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None

            with open(source_path, 'r', encoding="utf-8") as file:
                if source_path.endswith(".ndjson"):
                    records = [json.loads(line) for line in file if line.strip()]
                else:
                    records = json.load(file)

            if records:
                num_records = len(records) if isinstance(records, (list, dict)) else 1

                self.log_and_update_dashboard(f"✅ SUCCESS: Fetched {num_records} records from '{source_type}' under {source_path}.")
                return records
            else:
                self.log_and_update_dashboard(f"⚠️ WARNING: No data provided, empty structure found in '{source_type}' under {source_path}.")
                return None

        except Exception as e:
            self.log_and_update_dashboard(f"❌ FAILURE: Error occurred in {self.get_caller_method()}\n{e}")
            return None

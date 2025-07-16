
import json
import os
from typing import Any, Dict, List, Optional, Union

from agents.base_agent import BaseAgent
from agents.dataclasses.agent_context import AgentContext
from core import constants


class DataIngestionAgent(BaseAgent):

    def __init__(self, agent_context: AgentContext) -> None:
        super().__init__(agent_context)
        self.source_type: Optional[str] = self.agent_context.source_data_connector_state.get("source_type")
        self.source_path: Optional[str] = self.agent_context.source_data_connector_state.get("source_path")
        self.supported_connectors: List[str] = [
            constants.LOCAL_FILE_TYPE,
        ]

    def ingest_data(self) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:
        self.log_and_update_dashboard(f"▶️ START: Ingesting data from '{self.source_type}' source: {self.source_path}.")

        try:
            if self.source_type == constants.LOCAL_FILE_TYPE:
                return self.ingest_local_file(self.source_type, self.source_path)
            else:
                self.log_and_update_dashboard(f"❌ FAILURE: Unknown source data connector specified: '{self.source_type}'. Supported source data connectors: {self.supported_connectors}.")
                return None

        except Exception as e:
            self.log_and_update_dashboard(f"❌ FAILURE: Error occurred in '{self.get_caller_method()}'.\n{e}")
            return None

    def ingest_local_file(self, source_type: str, source_path: str) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:
        try:
            if not os.path.exists(source_path):
                self.log_and_update_dashboard(f"❌ FAILURE: '{source_type}' not found under {source_path}.")
                return None

            # TODO Add support for other file formats like CSV, Parquet, etc.
            records: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None

            with open(source_path, 'r', encoding="utf-8") as file:
                if source_path.endswith(".ndjson"):
                    records = [json.loads(line) for line in file if line.strip()]
                else:
                    records = json.load(file)

            if records:
                num_records: int = len(records) if isinstance(records, (list, dict)) else 1
                file_size: int = os.path.getsize(source_path)

                self.log_and_update_dashboard(f"✅ SUCCESS: Ingested {num_records} records ({file_size} bytes) from '{source_type}': {source_path}.")
                return records
            else:
                self.log_and_update_dashboard(f"⚠️ WARNING: No data provided, empty structure found in '{source_type}' under {source_path}.")
                return None

        except Exception as e:
            self.log_and_update_dashboard(f"❌ FAILURE: Error occurred in '{self.get_caller_method()}'.\n{e}")
            return None

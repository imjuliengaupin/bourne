import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from agents.base_agent import BaseAgent
from agents.dataclasses.agent_context import AgentContext
from core import constants

JsonRecords = Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]


class DataIngestionAgent(BaseAgent):

    def __init__(self, agent_context: AgentContext) -> None:
        super().__init__(agent_context)
        source_state: Dict[str, str] = getattr(self.agent_context, "source_data_connector_state", {}) or {}
        self.source_type: Optional[str] = source_state.get("source_type")
        self.source_path: Optional[str] = source_state.get("source_path")
        self.supported_connectors: List[str] = [constants.LOCAL_FILE_TYPE]

    def ingest_data(self) -> JsonRecords:
        self.log_and_update_dashboard(f"▶️ START: Ingesting data from '{self.source_type}' source: {self.source_path}.")

        try:
            if self.source_type == constants.LOCAL_FILE_TYPE and self.source_path is not None:
                return self.ingest_local_file(self.source_type, self.source_path)

            self.log_and_update_dashboard(
                f"❌ FAILURE: Unknown source data connector specified: '{self.source_type}'. "
                f"Supported source data connectors: {self.supported_connectors}."
            )
            return None

        except Exception as e:
            self.log_and_update_dashboard(f"❌ FAILURE: Error occurred in '{self.get_caller_method()}'.\n{e}")
            return None

    def ingest_local_file(self, source_type: str, source_path: str) -> JsonRecords:
        try:
            path = Path(source_path)
            if not path.exists():
                self.log_and_update_dashboard(f"❌ FAILURE: '{source_type}' not found under {source_path}.")
                return None

            records = self._load_local_records(path)

            if records is None:
                self.log_and_update_dashboard(
                    f"⚠️ WARNING: No data provided, empty structure found in '{source_type}' under {source_path}."
                )
                return None

            num_records: int = 1 if isinstance(records, dict) else len(records)
            file_size: int = path.stat().st_size

            self.log_and_update_dashboard(
                f"✅ SUCCESS: Ingested {num_records} record(s) ({file_size} bytes) from '{source_type}': {source_path}."
            )
            return records

        except Exception as e:
            self.log_and_update_dashboard(f"❌ FAILURE: Error occurred in '{self.get_caller_method()}'.\n{e}")
            return None

    def _load_local_records(self, path: Path) -> JsonRecords:
        with path.open('r', encoding="utf-8") as file:
            if path.suffix == ".ndjson":
                return [json.loads(line) for line in file if line.strip()]
            return json.load(file)

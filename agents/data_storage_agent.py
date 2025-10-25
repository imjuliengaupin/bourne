
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from agents.base_agent import BaseAgent
from agents.dataclasses.agent_context import AgentContext


class DataStorageAgent(BaseAgent):

    def __init__(self, agent_context: AgentContext) -> None:
        super().__init__(agent_context)

        transform_output_path_conf: Optional[str] = self.agent_context.source_data_connector_state.get("transform_output_path")
        self.transform_output_path: Optional[str] = transform_output_path_conf if transform_output_path_conf else None

        if not transform_output_path_conf:
            self.log_and_update_dashboard("ℹ️ INFO: Optional configuration 'transform_output_path' is not specified. Proceeding...")

    def save_data(self, shared_input_data: List[Dict[str, Any]]) -> bool:
        if not shared_input_data:
            self.log_and_update_dashboard("⚠️ WARNING: No data provided.")
            return True

        if not self.transform_output_path:
            self.log_and_update_dashboard("⚠️ WARNING: No transformation output path specified, skipping data save operation.")
            return True

        try:
            output_path: Path = Path(self.transform_output_path)

            if not output_path.suffix:
                self.log_and_update_dashboard("❌ FAILURE: Output path must include file extension.")
                return False

        except Exception as e:
            self.log_and_update_dashboard(f"❌ FAILURE: Invalid output path format.\n{e}")
            return False

        self.log_and_update_dashboard(f"▶️ START: Attempting to save {len(shared_input_data)} record(s) to {self.transform_output_path}.")

        try:
            os.makedirs(os.path.dirname(self.transform_output_path), exist_ok=True)

            with open(self.transform_output_path, "w", encoding="utf-8") as file:
                if self.transform_output_path.endswith(".ndjson"):
                    for record in shared_input_data:
                        file.write(json.dumps(record, ensure_ascii=False) + "\n")
                else:
                    json.dump(shared_input_data, file, indent=2, ensure_ascii=False)

            self.log_and_update_dashboard(f"✅ SUCCESS: Saved {len(shared_input_data)} record(s) to {self.transform_output_path}.")
            return True

        except Exception as e:
            self.log_and_update_dashboard(f"❌ FAILURE: Error occurred in '{self.get_caller_method()}'.\n{e}")
            return False

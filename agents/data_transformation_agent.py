
import time
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, TypeAdapter

from agents.base_agent import BaseAgent
from agents.dataclasses.agent_context import AgentContext
from core import constants
from schemas.fallback_schema import Record
from schemas.schema_generator import SchemaGenerator


class DataTransformationAgent(BaseAgent):

    def __init__(self, agent_context: AgentContext) -> None:
        super().__init__(agent_context)

        self.transform_mode: Optional[str] = self.agent_context.source_data_connector_state.get("transform_mode") if self.agent_context.source_data_connector_state.get("transform_mode") else None
        self.expected_schema: Dict[str, str] = self.agent_context.source_data_connector_state.get("expected_schema")
        self.pydantic_model: Optional[Type[BaseModel]] = None
        self.supported_transformation_modes: List[str] = [
            constants.LOWERCASE_KEYS,
        ]

        if not self.transform_mode:
            self.log_and_update_dashboard("ℹ️ INFO: Optional configuration 'transform_mode' is not specified. Proceeding...")

        try:
            self.pydantic_model = SchemaGenerator.create_record_model(self.expected_schema)

        except Exception as e:
            self.log_and_update_dashboard(f"⚠️ WARNING: Failed to create dynamic Pydantic schema, using fallback schema.\n{e}")

    def transform_data(self, shared_input_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        self.log_and_update_dashboard(f"▶️ START: Attempting to transform {len(shared_input_data)} records.")

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
                self.log_and_update_dashboard(f"❌ FAILURE: Invalid data format, expected a dictionary or list of dictionaries, but got {type(shared_input_data).__name__} instead.")
                return []

            if not records:
                self.log_and_update_dashboard("⚠️ WARNING: No data provided.")
                return []

            transformed_records: List[Dict[str, Any]] = []

            for record in records:
                transformed_records.append(self.apply_transformation(record, self.transform_mode))
                time.sleep(0.1)

            if self.pydantic_model:
                try:
                    TypeAdapter(List[self.pydantic_model]).validate_python(transformed_records)
                    self.log_and_update_dashboard(f"✅ SUCCESS: Transformed {len(transformed_records)} records.")

                except Exception as e:
                    self.log_and_update_dashboard(f"❌ FAILURE: Dynamic Pydantic schema validation failed, using fallback schema.\n{e}")
                    return self.transform_data_with_fallback(transformed_records)
            else:
                self.log_and_update_dashboard("⚠️ WARNING: Dynamic Pydantic schema unavailable, using fallback schema.")
                return self.transform_data_with_fallback(transformed_records)

            return transformed_records

        except Exception as e:
            self.log_and_update_dashboard(f"❌ FAILURE: Error occurred in {self.get_caller_method()}.\n{e}")
            return []

    def transform_data_with_fallback(self, transformed_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        try:
            TypeAdapter(List[Record]).validate_python(transformed_records)
            self.log_and_update_dashboard(f"✅ SUCCESS: Transformed {len(transformed_records)} records (using fallback schema).")
            return transformed_records

        except Exception as e:
            self.log_and_update_dashboard(f"❌ FAILURE: Fallback schema validation failed.\n{e}")
            return []

    def apply_transformation(self, data_before_transformation: Dict[str, Any], transformation_mode: Optional[str]) -> Dict[str, Any]:
        if not isinstance(data_before_transformation, dict):
            self.log_and_update_dashboard(f"❌ FAILURE: Invalid data type for transformation: '{type(data_before_transformation)}'.")
            return {}

        data_after_transformation: Dict[str, Any] = {}

        try:
            if not transformation_mode:
                self.log_and_update_dashboard("ℹ️ INFO: No transformation mode specified. Returning record unchanged.")
                return data_before_transformation.copy()
            elif transformation_mode == constants.LOWERCASE_KEYS:
                data_after_transformation = {key.lower(): value for key, value in data_before_transformation.items()}
                data_after_transformation["is_transformed"] = True
                data_after_transformation["transformed_on"] = time.strftime("%Y-%m-%d %H:%M:%S")
                self.log_and_update_dashboard(None, data_before_transformation, data_after_transformation)
            else:
                self.log_and_update_dashboard(f"⚠️ WARNING: Unknown transformation mode '{transformation_mode}'. Supported modes: {self.supported_transformation_modes}. Returning record unchanged.")
                return data_before_transformation.copy()

        except Exception as e:
            self.log_and_update_dashboard(f"❌ FAILURE: Error occurred in {self.get_caller_method()}.\n{e}")
            return {"error": e, "original_record": data_before_transformation.copy()}

        return data_after_transformation

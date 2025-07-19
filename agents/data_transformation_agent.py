
import re
import time
from typing import Any, Dict, List, Optional

from agents.base_agent import BaseAgent
from agents.dataclasses.agent_context import AgentContext
from core import constants


class DataTransformationAgent(BaseAgent):

    def __init__(self, agent_context: AgentContext) -> None:
        super().__init__(agent_context)

        self.transform_mode: Optional[str] = self.agent_context.source_data_connector_state.get("transform_mode") if self.agent_context.source_data_connector_state.get("transform_mode") else None

        if not self.transform_mode:
            self.log_and_update_dashboard("ℹ️ INFO: Optional configuration 'transform_mode' is not specified. Proceeding...")

        self.supported_transformation_modes: List[str] = [
            constants.LOWERCASE_KEYS,
            constants.UPPERCASE_KEYS,
            constants.SNAKE_CASE_KEYS,
            constants.NORMALIZE_TYPES,
        ]

    def transform_data(self, shared_input_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        shared_input_data_count: int = 0

        if isinstance(shared_input_data, dict):
            shared_input_data_count = 1
        elif isinstance(shared_input_data, list):
            shared_input_data_count = len(shared_input_data)

        self.log_and_update_dashboard(f"▶️ START: Attempting to transform {shared_input_data_count} record(s).")

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
            is_records_transformed: bool = False

            for record in records:
                transformed_record = self.apply_data_transformation(record, self.transform_mode)

                transformed_records.append(transformed_record)

                if 'is_transformed' in transformed_record:
                    is_records_transformed = True

                time.sleep(0.1)

            if is_records_transformed:
                self.log_and_update_dashboard(f"✅ SUCCESS: Transformed {len(transformed_records)} record(s).")
                self.update_schema_for_transformed_data()

            return transformed_records

        except Exception as e:
            self.log_and_update_dashboard(f"❌ FAILURE: Error occurred in {self.get_caller_method()}.\n{e}")
            return []

    def apply_data_transformation(self, data_before_transformation: Dict[str, Any], transformation_mode: Optional[str]) -> Dict[str, Any]:
        if not isinstance(data_before_transformation, dict):
            self.log_and_update_dashboard(f"❌ FAILURE: Invalid data type for transformation: '{type(data_before_transformation)}'.")
            return {}

        data_after_transformation: Dict[str, Any] = {}
        metadata_timestamp: str = time.strftime("%Y-%m-%d %H:%M:%S")

        try:
            if not transformation_mode:
                self.log_and_update_dashboard("ℹ️ INFO: No transformation mode specified. Returning record(s) unchanged.")
                return data_before_transformation.copy()
            elif transformation_mode == constants.LOWERCASE_KEYS:
                data_after_transformation = {key.lower(): value for key, value in data_before_transformation.items()}
                data_after_transformation["is_transformed"] = True
                data_after_transformation["transformed_on"] = metadata_timestamp

                self.log_and_update_dashboard(None, data_before_transformation, data_after_transformation)
            elif transformation_mode == constants.UPPERCASE_KEYS:
                data_after_transformation = {key.upper(): value for key, value in data_before_transformation.items()}
                data_after_transformation["is_transformed"] = True
                data_after_transformation["transformed_on"] = metadata_timestamp

                self.log_and_update_dashboard(None, data_before_transformation, data_after_transformation)
            elif transformation_mode == constants.SNAKE_CASE_KEYS:
                for key, value in data_before_transformation.items():
                    snake_case_key: str = re.sub(r'(?<!^)(?=[A-Z])', '_', key).lower()
                    data_after_transformation[snake_case_key] = value

                data_after_transformation["is_transformed"] = True
                data_after_transformation["transformed_on"] = metadata_timestamp

                self.log_and_update_dashboard(None, data_before_transformation, data_after_transformation)
            elif transformation_mode == constants.NORMALIZE_TYPES:
                for key, value in data_before_transformation.items():
                    data_after_transformation[key] = str(value)

                data_after_transformation["is_transformed"] = True
                data_after_transformation["transformed_on"] = metadata_timestamp

                self.log_and_update_dashboard(None, data_before_transformation, data_after_transformation)
            else:
                self.log_and_update_dashboard(f"⚠️ WARNING: Unknown transformation mode '{transformation_mode}'. Supported modes: {self.supported_transformation_modes}. Returning record unchanged.")
                return data_before_transformation.copy()

        except Exception as e:
            self.log_and_update_dashboard(f"❌ FAILURE: Error occurred in {self.get_caller_method()}.\n{e}")
            return {"error": e, "original_record": data_before_transformation.copy()}

        return data_after_transformation

    def apply_schema_transformation(self, original_schema: Dict[str, str]) -> Dict[str, str]:
        transformed_schema: Dict[str, str] = {}

        if not self.transform_mode:
            return original_schema.copy()

        elif self.transform_mode == constants.LOWERCASE_KEYS:
            for key, value in original_schema.items():
                transformed_schema[key.lower()] = value

            return transformed_schema

        elif self.transform_mode == constants.UPPERCASE_KEYS:
            for key, value in original_schema.items():
                transformed_schema[key.upper()] = value

            return transformed_schema

        elif self.transform_mode == constants.SNAKE_CASE_KEYS:
            for key, value in original_schema.items():
                snake_case_key = re.sub(r'(?<!^)(?=[A-Z])', '_', key).lower()
                transformed_schema[snake_case_key] = value

            return transformed_schema

        elif self.transform_mode == constants.NORMALIZE_TYPES:
            for key, value in original_schema.items():
                transformed_schema[key] = "str"

            return transformed_schema

        else:
            self.log_and_update_dashboard(f"⚠️ WARNING: Unknown transformation mode '{self.transform_mode}' in schema update. Using original schema.")
            return original_schema.copy()

    def update_schema_for_transformed_data(self) -> None:
        try:
            current_schema: Dict[str, str] = self.agent_context.source_data_connector_state.get("expected_schema") or {}

            # Apply transformation-specific schema changes
            transformed_schema: Dict[str, str] = self.apply_schema_transformation(current_schema)

            # Add transformation metadata fields (regardless of transformation type)
            transformed_schema["is_transformed"] = "bool"
            transformed_schema["transformed_on"] = "str"

            self.agent_context.source_data_connector_state.source_data_connector["expected_schema"] = transformed_schema
            self.log_and_update_dashboard(f"ℹ️ INFO: Updated schema for transformed data validation: {list(transformed_schema.keys())}.")

        except Exception as e:
            self.log_and_update_dashboard(f"⚠️ WARNING: Failed to update schema for transformed data validation.\n{e}")


import re
import time
from typing import Any, Dict, List, Optional, Union

from agents.base_agent import BaseAgent
from agents.dataclasses.agent_context import AgentContext
from core import constants
from schemas.schema_generator import SchemaGenerator


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

                if "is_transformed" in transformed_record:
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

        if not transformation_mode:
            self.log_and_update_dashboard("⚠️ WARNING: No transformation mode specified. Returning record(s) unchanged.")
            return data_before_transformation.copy()

        metadata_timestamp: str = time.strftime("%Y-%m-%d %H:%M:%S")

        try:
            data_after_transformation: Dict[str, Any] = self.apply_nested_data_transformation(data_before_transformation, transformation_mode)

            # Handle type normalization separately since it affects values, not keys
            if transformation_mode == constants.NORMALIZE_TYPES:
                data_after_transformation = self.normalize_all_types_recursively(data_after_transformation)

            data_after_transformation["is_transformed"] = True
            data_after_transformation["transformed_on"] = metadata_timestamp

            self.log_and_update_dashboard(None, data_before_transformation, data_after_transformation)
            return data_after_transformation

        except Exception as e:
            self.log_and_update_dashboard(f"❌ FAILURE: Error occurred in {self.get_caller_method()}.\n{e}")
            return {"error": str(e), "original_record": data_before_transformation.copy()}

    def apply_nested_data_transformation(self, data: Dict[str, Any], transformation_mode: Optional[str]) -> Dict[str, Any]:
        transformed_data: Dict[str, Any] = {}

        for key, value in data.items():
            transformed_key = self.transform_single_key(key, transformation_mode)

            if isinstance(value, dict):
                # Recursively transform nested dictionary objects
                transformed_nested = self.apply_nested_data_transformation(value, transformation_mode)
                transformed_data[transformed_key] = transformed_nested
            elif isinstance(value, list):
                transformed_array = self.transform_array_recursively(value, transformation_mode)
                transformed_data[transformed_key] = transformed_array
            else:
                # Transform non-dictionary (primitive) field values
                transformed_data[transformed_key] = value

        return transformed_data

    def apply_schema_transformation(self, original_schema: Dict[str, Union[str, Dict[str, Any], List[Any]]]) -> Dict[str, Union[str, Dict[str, Any], List[Any]]]:
        if not self.transform_mode:
            return original_schema.copy()

        if self.transform_mode == constants.NORMALIZE_TYPES:
            return self.normalize_schema_types_recursively(original_schema)
        else:
            return SchemaGenerator.transform_nested_schema_recursively(original_schema, self.transform_mode)

    def update_schema_for_transformed_data(self) -> None:
        try:
            current_schema: Dict[str, Union[str, Dict[str, Any], List[Any]]] = self.agent_context.source_data_connector_state.get("expected_schema") or {}

            # Apply transformation-specific schema changes
            transformed_schema: Dict[str, Union[str, Dict[str, Any], List[Any]]] = self.apply_schema_transformation(current_schema)

            # Add transformation metadata fields (regardless of transformation type)
            transformed_schema["is_transformed"] = "bool"
            transformed_schema["transformed_on"] = "str"

            self.agent_context.source_data_connector_state.source_data_connector["expected_schema"] = transformed_schema

            all_keys = self.get_all_schema_keys(transformed_schema)

            self.log_and_update_dashboard(f"ℹ️ INFO: Updated schema for transformed data validation: {all_keys}.")

        except Exception as e:
            self.log_and_update_dashboard(f"⚠️ WARNING: Failed to update schema for transformed data validation.\n{e}")

    def transform_single_key(self, key: str, transformation_mode: Optional[str]) -> str:
        if not transformation_mode:
            return key

        if transformation_mode == constants.LOWERCASE_KEYS:
            return key.lower()
        elif transformation_mode == constants.UPPERCASE_KEYS:
            return key.upper()
        elif transformation_mode == constants.SNAKE_CASE_KEYS:
            # Handle sequences of capitals followed by lowercase (XMLParser -> XML_Parser)
            key = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', key)

            # Handle lowercase/digit followed by uppercase (camelCase -> camel_Case, test1Data -> test1_Data)
            key = re.sub(r'([a-z])([A-Z])', r'\1_\2', key)

            # Handle special cases with numbers (ID2Name -> ID2_Name)
            key = re.sub(r'([0-9])([A-Z])', r'\1_\2', key)

            return key.lower()
        else:
            return key

    def normalize_all_types_recursively(self, data: Dict[str, Any]) -> Dict[str, Any]:
        normalized_data: Dict[str, Any] = {}

        for key, value in data.items():
            if isinstance(value, dict):
                # Recursively normalize nested objects
                normalized_data[key] = self.normalize_all_types_recursively(value)
            elif isinstance(value, list):
                # Normalize arrays (including nested objects in arrays)
                normalized_data[key] = self.normalize_array_recursively(value)
            else:
                normalized_data[key] = str(value)

        return normalized_data

    def normalize_array_recursively(self, array: List[Any]) -> List[str]:
        normalized_array: List[str] = []

        for item in array:
            if isinstance(item, dict):
                # Convert nested object to string representation
                normalized_array.append(str(item))
            elif isinstance(item, list):
                # Convert nested array to string representation
                normalized_array.append(str(item))
            else:
                # Convert primitive to string
                normalized_array.append(str(item))

        return normalized_array

    def transform_array_recursively(self, array: List[Any], transformation_mode: Optional[str]) -> List[Any]:
        transformed_array: List[Any] = []

        for item in array:
            if isinstance(item, dict):
                # Transform nested object within array
                transformed_item = self.apply_nested_data_transformation(item, transformation_mode)
                transformed_array.append(transformed_item)
            elif isinstance(item, list):
                # Handle nested arrays
                transformed_nested_array = self.transform_array_recursively(item, transformation_mode)
                transformed_array.append(transformed_nested_array)
            else:
                # Keep primitive values in arrays as-is
                transformed_array.append(item)

        return transformed_array

    def get_all_schema_keys(self, schema: Dict[str, Union[str, Dict[str, Any], List[Any]]], prefix: str = "") -> List[str]:
        """Get all keys from nested schema for better logging"""
        all_keys: List[str] = []

        for key, value in schema.items():
            full_key = f"{prefix}.{key}" if prefix else key
            all_keys.append(full_key)

            if isinstance(value, dict):
                # Add nested object keys
                nested_keys = self.get_all_schema_keys(value, full_key)
                all_keys.extend(nested_keys)
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                # Add array of nested objects keys
                array_keys = self.get_all_schema_keys(value[0], f"{full_key}[]")
                all_keys.extend(array_keys)

        return all_keys

    def normalize_schema_types_recursively(self, schema: Dict[str, Union[str, Dict[str, Any], List[Any]]]) -> Dict[str, Union[str, Dict[str, Any], List[Any]]]:
        """Recursively normalize all types to string in nested schema"""
        normalized_schema: Dict[str, Union[str, Dict[str, Any], List[Any]]] = {}

        for key, value in schema.items():
            if isinstance(value, dict):
                # Recursively normalize nested object schema
                normalized_schema[key] = self.normalize_schema_types_recursively(value)
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                # Normalize array of nested objects schema
                normalized_array_item = self.normalize_schema_types_recursively(value[0])
                normalized_schema[key] = [normalized_array_item]
            else:
                # Convert all primitive types to "str"
                normalized_schema[key] = "str"

        return normalized_schema

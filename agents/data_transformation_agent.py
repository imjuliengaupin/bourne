
import time
from typing import Any, Dict, List, Optional, Union

from agents.base_agent import BaseAgent
from agents.dataclasses.agent_context import AgentContext
from core import constants
from core.constants import AgentTaskResult
from schemas.schema_generator import SchemaGenerator
from schemas.schema_key_transformer import SchemaKeyTransformer


class ResultWithStatus(list):
    """A list subclass that supports setting status attributes"""

    def __init__(self, data: Optional[List[Any]] = None) -> None:
        super().__init__(data or [])
        self.bourne_status: Optional[AgentTaskResult] = None


class DataTransformationAgent(BaseAgent):

    def __init__(self, agent_context: AgentContext) -> None:
        super().__init__(agent_context)

        transform_mode: Any | None = self.agent_context.source_data_connector_state.get("transform_mode")
        self.transform_mode: Optional[str] = transform_mode if transform_mode else None

        strict_mode: bool = self.agent_context.source_data_connector_state.is_strict_mode()

        if not self.transform_mode:
            if strict_mode:
                error_msg: str = "❌ FAILURE: Optional configuration 'transform_mode' is not specified (strict mode enabled)."
                self.log_and_update_dashboard(error_msg)
            else:
                info_msg: str = "ℹ️ INFO: Optional configuration 'transform_mode' is not specified. Proceeding..."
                self.log_and_update_dashboard(info_msg)

        self.supported_transformation_modes: List[str] = [
            constants.LOWERCASE_KEYS,
            constants.UPPERCASE_KEYS,
            constants.SNAKE_CASE_KEYS,
            constants.CAMEL_CASE_KEYS,
            constants.PASCAL_CASE_KEYS,
            constants.NORMALIZE_TYPES,
        ]

    def transform_data(self, shared_input_data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> ResultWithStatus:
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
                    failed_result: ResultWithStatus = ResultWithStatus([])
                    failed_result.bourne_status = AgentTaskResult.FAILED
                    return failed_result
            else:
                self.log_and_update_dashboard(f"❌ FAILURE: Invalid data format, expected a dictionary or list of dictionaries, but got {type(shared_input_data).__name__} instead.")
                failed_result = ResultWithStatus([])
                failed_result.bourne_status = AgentTaskResult.FAILED
                return failed_result

            if not records:
                strict_mode: bool = self.agent_context.source_data_connector_state.is_strict_mode()

                if strict_mode:
                    self.log_and_update_dashboard("❌ FAILURE: No data provided (strict mode enabled).")

                    failed_result = ResultWithStatus([])
                    failed_result.bourne_status = AgentTaskResult.FAILED
                    return failed_result

                self.log_and_update_dashboard("⚠️ WARNING: No data provided.")

                warning_result: ResultWithStatus = ResultWithStatus([])
                warning_result.bourne_status = AgentTaskResult.SUCCESS_WITH_WARNINGS
                return warning_result

            transformed_records: List[Dict[str, Any]] = []
            is_records_transformed: bool = False
            has_errors: bool = False

            for record in records:
                transformed_record: Dict[str, Any] = self.apply_data_transformation(record, self.transform_mode)

                # Check if strict mode returned an error
                if "error" in transformed_record and "original_record" in transformed_record:
                    has_errors = True
                    self.log_and_update_dashboard("❌ FAILURE: Transformation failed for record in strict mode.")
                    failed_result = ResultWithStatus([])
                    failed_result.bourne_status = AgentTaskResult.FAILED
                    return failed_result  # Fail fast in strict mode

                transformed_records.append(transformed_record)

                # Check if transformation was applied (transformation mode was specified and executed)
                if self.transform_mode:
                    is_records_transformed = True

                time.sleep(0.1)

            if is_records_transformed:
                self.log_and_update_dashboard(f"✅ SUCCESS: Transformed {len(transformed_records)} record(s).")
                self.update_schema_for_transformed_data()
                # Mark the data as successfully transformed
                success_result: ResultWithStatus = ResultWithStatus(transformed_records)
                success_result.bourne_status = AgentTaskResult.SUCCESS
                return success_result
            elif not has_errors:
                # No transformation occurred, but no errors either (relaxed mode)
                self.log_and_update_dashboard(f"✅ SUCCESS: Processed {len(transformed_records)} record(s) without transformation.")
                # Mark the data as having warnings
                warning_result = ResultWithStatus(transformed_records)
                warning_result.bourne_status = AgentTaskResult.SUCCESS_WITH_WARNINGS
                return warning_result
            else:
                # Mark as failed (shouldn't reach here due to fail-fast, but for safety)
                failed_result = ResultWithStatus([])
                failed_result.bourne_status = AgentTaskResult.FAILED
                return failed_result

        except Exception as e:
            self.log_and_update_dashboard(f"❌ FAILURE: Error occurred in {self.get_caller_method()}.\n{e}")
            failed_result = ResultWithStatus([])
            failed_result.bourne_status = AgentTaskResult.FAILED
            return failed_result

    def apply_data_transformation(self, data_before_transformation: Dict[str, Any], transformation_mode: Optional[str]) -> Dict[str, Any]:
        if not isinstance(data_before_transformation, dict):
            self.log_and_update_dashboard(f"❌ FAILURE: Invalid data type for transformation: '{type(data_before_transformation)}'.")
            return {}

        if not transformation_mode:
            strict_mode: bool = self.agent_context.source_data_connector_state.is_strict_mode()

            if strict_mode:
                self.log_and_update_dashboard("❌ FAILURE: No transformation mode specified (strict mode enabled).")
                return {"error": "No transformation mode specified in strict mode", "original_record": data_before_transformation.copy()}
            else:
                self.log_and_update_dashboard("⚠️ WARNING: No transformation mode specified. Returning record(s) unchanged.")
                return data_before_transformation.copy()

        metadata_timestamp: str = time.strftime("%Y-%m-%d %H:%M:%S")

        try:
            data_after_transformation: Dict[str, Any] = self.apply_nested_data_transformation(data_before_transformation, transformation_mode)

            # Add metadata fields with transformation-specific casing (if enabled)
            # For normalize_types, add metadata BEFORE normalization so values get converted to strings
            include_metadata: bool = self.agent_context.source_data_connector_state.get("include_transformation_metadata") or False

            if include_metadata:
                is_transformed_key, transformed_on_key = self.get_transformed_metadata_keys(transformation_mode)
                data_after_transformation[is_transformed_key] = True
                data_after_transformation[transformed_on_key] = metadata_timestamp

            # Handle type normalization separately since it affects values, not keys
            if transformation_mode == constants.NORMALIZE_TYPES:
                data_after_transformation = self.normalize_all_types_recursively(data_after_transformation)

            self.log_and_update_dashboard(None, data_before_transformation, data_after_transformation)
            return data_after_transformation

        except Exception as e:
            self.log_and_update_dashboard(f"❌ FAILURE: Error occurred in {self.get_caller_method()}.\n{e}")
            return {"error": str(e), "original_record": data_before_transformation.copy()}

    def apply_nested_data_transformation(self, data: Dict[str, Any], transformation_mode: Optional[str]) -> Dict[str, Any]:
        transformed_data: Dict[str, Any] = {}

        for key, value in data.items():
            transformed_key: str = self.transform_single_key(key, transformation_mode)

            if isinstance(value, dict):
                # Recursively transform nested dictionary objects
                transformed_nested: Dict[str, Any] = self.apply_nested_data_transformation(value, transformation_mode)
                transformed_data[transformed_key] = transformed_nested
            elif isinstance(value, list):
                transformed_array: List[Any] = self.transform_array_recursively(value, transformation_mode)
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

            # Add transformation metadata fields with transformation-specific casing (if enabled)
            include_metadata: bool = self.agent_context.source_data_connector_state.get("include_transformation_metadata") or False
            if include_metadata:
                is_transformed_key, transformed_on_key = self.get_transformed_metadata_keys(self.transform_mode)
                transformed_schema[is_transformed_key] = "bool"
                transformed_schema[transformed_on_key] = "str"

            self.agent_context.source_data_connector_state.source_data_connector["expected_schema"] = transformed_schema

            all_keys = self.get_all_schema_keys(transformed_schema)

            self.log_and_update_dashboard(f"ℹ️ INFO: Updated schema for transformed data validation: {all_keys}.")

        except Exception as e:
            self.log_and_update_dashboard(f"⚠️ WARNING: Failed to update schema for transformed data validation.\n{e}")

    def get_transformed_metadata_keys(self, transformation_mode: Optional[str]) -> tuple[str, str]:
        """Transform metadata field names to match the data transformation mode.

        Returns tuple of (is_transformed_key, transformed_on_key).
        Metadata keys automatically align with the current transform_mode casing.
        """
        base_keys: tuple[str, str] = ("is_transformed", "transformed_on")

        # Map common aliases
        alias_map: Dict[str, str] = {
            "snake_case": "snake",
            "snake": "snake",
            "lowercase": "lower",
            "lower": "lower",
            "uppercase": "upper",
            "upper": "upper",
        }

        # Always match metadata casing to transform mode
        data_mode: str = transformation_mode or "snake"
        target_mode: str = alias_map.get(data_mode, data_mode)

        # Transform keys using SchemaKeyTransformer when not snake (default)
        if target_mode == "snake":
            return base_keys

        transformed: List[str] = [SchemaKeyTransformer.transform_key(k, target_mode) for k in base_keys]
        return (transformed[0], transformed[1])

    def transform_single_key(self, key: str, transformation_mode: Optional[str]) -> str:
        if not transformation_mode:
            return key

        result: str = SchemaKeyTransformer.transform_key(key, transformation_mode)

        if result == key and transformation_mode not in self.supported_transformation_modes:
            # Log warning for unsupported transformation modes but don't fail
            self.log_and_update_dashboard(f"⚠️ WARNING: Unsupported transformation mode '{transformation_mode}'. Returning key unchanged.")

        return result

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

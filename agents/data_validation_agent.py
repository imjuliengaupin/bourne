
import re
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel, TypeAdapter

from agents.base_agent import BaseAgent
from agents.dataclasses.agent_context import AgentContext
from core.constants import AgentTaskResult, DataTransformationMetadata
from schemas.schema_generator import SchemaGenerator
from schemas.schema_generator_fallback import FallbackSchemaGenerator


class DataValidationAgent(BaseAgent):

    def __init__(self, agent_context: AgentContext) -> None:
        super().__init__(agent_context)
        self.pydantic_record_model: Optional[Type[BaseModel]] = None
        self.expected_schema: Dict[str, Type[Any]] = {}
        self.setup_pydantic_schema()

    # AGENT METHOD(S) ################################################################################################################################################

    def validate_data(self, shared_input_data: Any) -> AgentTaskResult:
        if not shared_input_data:
            self.log_and_update_dashboard("⚠️ WARNING: No data provided.")
            return AgentTaskResult.FAILED

        input_data: List[Dict[str, Any]] = []

        if isinstance(shared_input_data, dict):
            input_data = [shared_input_data]
        elif isinstance(shared_input_data, list):
            input_data = shared_input_data
        else:
            self.log_and_update_dashboard(f"❌ FAILURE: Invalid data format, expected a 'dict' or 'list', but found a '{type(shared_input_data).__name__}'.")
            return AgentTaskResult.FAILED

        input_data_schema_changed: bool = self.is_schema_transformed(input_data)

        if input_data_schema_changed:
            self.log_and_update_dashboard("ℹ️ INFO: Detected schema changes, recreating Pydantic schema with updated keys.")
            self.setup_pydantic_schema()

        if self.pydantic_record_model is not None:
            try:
                num_records: int = len(input_data)
                self.log_and_update_dashboard(f"▶️ START: Attempting to validate {num_records} record(s) using dynamic Pydantic schema: {self.expected_schema}.")

                # NOTE: There is a mypy limitation with tracking self.pydantic_model across method boundaries even though it's properly defined in __init__ and we have a None check above.
                # This is a known limitation with dynamic Pydantic model creation where mypy cannot statically verify the type of dynamically created models at analysis time.
                # The type: ignore[name-defined] suppresses this specific mypy error while maintaining type safety elsewhere and proper runtime behavior.
                pydantic_validator: TypeAdapter[List[BaseModel]] = TypeAdapter(List[self.pydantic_record_model])  # type: ignore[name-defined]
                validated_input_data: List[BaseModel] = pydantic_validator.validate_python(input_data)
                success_summary: str = self.get_validation_success_summary(validated_input_data)

                self.log_and_update_dashboard(f"✅ SUCCESS: Validated {len(validated_input_data)} record(s) using dynamic Pydantic schema. {success_summary}")
                return AgentTaskResult.SUCCESS

            except Exception as e:
                pydantic_error_message: str = str(e)
                error_summary: str = self.get_validation_failure_summary(pydantic_error_message)
                self.log_and_update_dashboard(f"❌ FAILURE: Pydantic record model (schema) validation failed. {error_summary}.\nUsing dynamic fallback schema...")

            fallback_result: AgentTaskResult = self.attempt_validation_with_dynamic_fallback(input_data)

            if fallback_result.is_success:
                return AgentTaskResult.SUCCESS_WITH_WARNINGS
            else:
                return AgentTaskResult.FAILED

        self.log_and_update_dashboard("⚠️ WARNING: Pydantic record model (schema) not found.\nUsing dynamic fallback schema...")
        dynamic_fallback_result: AgentTaskResult = self.attempt_validation_with_dynamic_fallback(input_data)

        if dynamic_fallback_result.is_success:
            return AgentTaskResult.SUCCESS_WITH_WARNINGS
        else:
            return AgentTaskResult.FAILED

    # PYDANTIC METHOD(S) #############################################################################################################################################

    def setup_pydantic_schema(self) -> None:
        raw_expected_schema: Dict[str, Union[str, Dict[str, Any], List[Any]]] = self.agent_context.source_data_connector_state.get("expected_schema") or {}

        try:
            pydantic_compatible_schema: Dict[str, str] = self.convert_complex_schema_to_simple(raw_expected_schema)
            # Convert simple schema back to complex format for create_record_model
            complex_schema_for_pydantic: Dict[str, Union[str, Dict[str, Any], List[Any]]] = {
                k: v for k, v in pydantic_compatible_schema.items()
            }
            self.pydantic_record_model = SchemaGenerator.create_record_model(complex_schema_for_pydantic)

            pydantic_schema_summary: List[str] = self.get_schema_summary(raw_expected_schema)
            self.log_and_update_dashboard(f"ℹ️ INFO: Created a dynamic Pydantic schema using enhanced nested support for the 'expected_schema' fields: {pydantic_schema_summary}.")

        except Exception as e:
            self.log_and_update_dashboard(f"⚠️ WARNING: Failed to create a dynamic Pydantic schema, using fallback schema.\n{e}")

        self.expected_schema = self.setup_expected_schema(raw_expected_schema)

    def convert_complex_schema_to_simple(self, complex_schema: Dict[str, Union[str, Dict[str, Any], List[Any]]]) -> Dict[str, str]:
        simple_schema: Dict[str, str] = {}

        for key, field_type in complex_schema.items():
            if isinstance(field_type, dict):
                simple_schema[key] = "dict"
            elif isinstance(field_type, list):
                simple_schema[key] = "list"
            else:
                simple_schema[key] = str(field_type).lower()

        return simple_schema

    def setup_expected_schema(self, raw_expected_schema: Dict[str, Union[str, Dict[str, Any], List[Any]]]) -> Dict[str, Type[Any]]:
        expected_schema: Dict[str, Type[Any]] = {}

        for key, field_type in raw_expected_schema.items():
            if isinstance(field_type, dict):
                # Handle nested object(s), treat as dict type for manual fallback
                expected_schema[key] = dict
            elif isinstance(field_type, list):
                # Handle array(s), treat as list type for manual fallback
                expected_schema[key] = list
            else:
                # Handle non-dictionary (primitive) types
                field_type_obj: Optional[Type[Any]] = SchemaGenerator.TYPE_MAP.get(str(field_type).lower())

                if field_type_obj:
                    expected_schema[key] = field_type_obj
                else:
                    self.log_and_update_dashboard(f"⚠️ WARNING: Unknown Python type '{field_type}' found in 'expected_schema' for key '{key}'. Using 'str' type as a fallback.")
                    expected_schema[key] = str

        return expected_schema

    def get_schema_summary(self, schema: Dict[str, Union[str, Dict[str, Any], List[Any]]], prefix: str = "") -> List[str]:
        schema_summary_keys: List[str] = []

        # Recursively capture the summary for each schema attribute
        for key, field_type in schema.items():
            key = f"{prefix}.{key}" if prefix else key

            if isinstance(field_type, dict):
                schema_summary_keys.append(f"{key} (nested object)")
                nested_object_keys: List[str] = self.get_schema_summary(field_type, key)
                schema_summary_keys.extend(nested_object_keys)

            elif isinstance(field_type, list) and field_type and isinstance(field_type[0], dict):
                schema_summary_keys.append(f"{key} (array of objects)")
                array_keys = self.get_schema_summary(field_type[0], f"{key}[]")
                schema_summary_keys.extend(array_keys)

            elif isinstance(field_type, list):
                schema_summary_keys.append(f"{key} (array of {field_type[0] if field_type else 'unknown'})")
            else:
                schema_summary_keys.append(f"{key} ({field_type})")

        return schema_summary_keys

    # SCHEMA VALIDATION METHOD(S) ####################################################################################################################################

    def is_schema_transformed(self, input_data: Any) -> bool:
        if not isinstance(input_data, list) or not input_data:
            return False

        sample_record: Dict[str, Any] = input_data[0]
        sample_record_keys: set = set(sample_record.keys())

        if not isinstance(sample_record, dict):
            return False

        # Detection Method 1: Look for (Bourne-injected) transformation metadata fields
        has_transformation_markers: bool = DataTransformationMetadata.has_transformation_markers(sample_record)

        # Detection Method 2: Look for implicit schema changes by comparing data keys against the original 'expected_schema'
        current_schema: Dict[str, str] = self.agent_context.source_data_connector_state.get("expected_schema") or {}
        current_schema_keys: set = set(current_schema.keys())
        has_schema_changes: bool = not sample_record_keys.issubset(current_schema_keys)

        return has_transformation_markers or has_schema_changes

    def get_validation_success_summary(self, validated_input_data: List[BaseModel]) -> str:
        if not validated_input_data:
            return "No schema fields validated."

        sample_record: BaseModel = validated_input_data[0]
        schema_field_count = len(sample_record.model_fields) if hasattr(sample_record, "model_fields") else len(sample_record.__dict__)

        return f"Schema fields validated (per record): {schema_field_count}."

    def get_validation_failure_summary(self, pydantic_error_message: str) -> str:
        if "validation error" in pydantic_error_message.lower():
            lines: List[str] = pydantic_error_message.split('\n')
            field_names: List[str] = []

            for line in lines:
                line: str = line.strip()

                # Extract "fieldname" from "index.fieldname" format (e.g. "0.Timestamp")
                if re.match(r'^\d+\.', line):
                    parts: List[str] = line.split('.')

                    if len(parts) > 1 and re.match(r'^[A-Za-z_]\w*$', parts[1]):
                        field_name: str = parts[1]

                        # Avoid duplicates
                        if field_name not in field_names:
                            field_names.append(field_name)

                # Check for direct field names
                elif re.match(r'^[A-Za-z_]\w*$', line):

                    # Avoid duplicates
                    if line not in field_names:
                        field_names.append(line)

                # Check for dot notation (non-numeric prefix)
                elif '.' in line and not line[0].isdigit():
                    parts: List[str] = line.split('.')

                    if len(parts) > 1 and re.match(r'^[A-Za-z_]\w*$', parts[-1]):
                        field_name: str = parts[-1]

                        # Avoid duplicates
                        if field_name not in field_names:
                            field_names.append(field_name)

            # Extract all error types
            type_pattern = r"(missing|type_error|value_error|required|string_type|int_parsing)"
            type_matches: List[Any] = re.findall(type_pattern, pydantic_error_message, re.IGNORECASE)

            if field_names and type_matches:
                if len(field_names) == 1:
                    return f"Field path: {field_names[0]}, Error type: {type_matches[0]}"
                else:
                    field_list: str = ", ".join(field_names)
                    unique_types: List[Any] = list(set(type_matches))
                    return f"Multiple field errors: {field_list} (Error types: {', '.join(unique_types[:3])})"

        return pydantic_error_message[:100] + "..." if len(pydantic_error_message) > 100 else pydantic_error_message

    def attempt_validation_with_dynamic_fallback(self, input_data: List[Dict[str, Any]]) -> AgentTaskResult:
        try:
            raw_expected_schema: Dict[str, Union[str, Dict[str, Any], List[Any]]] = self.agent_context.source_data_connector_state.get("expected_schema") or {}

            if not raw_expected_schema:
                self.log_and_update_dashboard("❌ FAILURE: No 'expected_schema' defined.")
                return AgentTaskResult.FAILED

            if not input_data:
                self.log_and_update_dashboard("❌ FAILURE: No data provided.")
                return AgentTaskResult.FAILED

            self.log_and_update_dashboard(f"▶️ START: Attempting to validate {len(input_data)} record(s) using dynamic fallback schema: {raw_expected_schema}")

            fallback_record_model: Optional[Type[BaseModel]] = FallbackSchemaGenerator.create_dynamic_enhanced_fallback_record_model(raw_expected_schema)

            # NOTE: There is a mypy limitation with tracking self.pydantic_model across method boundaries even though it's properly defined in __init__ and we have a None check above.
            # This is a known limitation with dynamic Pydantic model creation where mypy cannot statically verify the type of dynamically created models at analysis time.
            # The type: ignore[name-defined] suppresses this specific mypy error while maintaining type safety elsewhere and proper runtime behavior.
            pydantic_validator: TypeAdapter[List[BaseModel]] = TypeAdapter(List[fallback_record_model])  # type: ignore[name-defined]
            validated_input_data: List[BaseModel] = pydantic_validator.validate_python(input_data)
            success_summary: str = self.get_validation_success_summary(validated_input_data)

            self.log_and_update_dashboard(f"✅ SUCCESS: Validated {len(validated_input_data)} record(s) using dynamic fallback schema. {success_summary}")
            return AgentTaskResult.SUCCESS

        except Exception as e:
            pydantic_error_message: str = str(e)
            error_summary: str = self.get_validation_failure_summary(pydantic_error_message)
            self.log_and_update_dashboard(f"❌ FAILURE: Dynamic fallback record model (schema) validation failed. {error_summary}.\nUsing manual fallback schema...")

            manual_fallback_result: AgentTaskResult = self.attempt_validation_with_manual_fallback(input_data)
            return manual_fallback_result

    # REVIEW
    def attempt_validation_with_manual_fallback(self, input_data: List[Dict[str, Any]]) -> AgentTaskResult:
        self.log_and_update_dashboard(f"▶️ START: Attempting to validate {len(input_data)} record(s) using manual fallback schema: {self.expected_schema}")

        try:
            if not self.expected_schema:
                self.log_and_update_dashboard("❌ FAILURE: No 'expected_schema' defined.")
                return AgentTaskResult.FAILED

            if not input_data:
                self.log_and_update_dashboard("❌ FAILURE: No data provided.")
                return AgentTaskResult.FAILED

            validation_errors: List[str] = []

            for i, record in enumerate(input_data):
                if not isinstance(record, dict):
                    validation_errors.append(f"Record {i}: Expected a 'dict', but got '{type(record).__name__}'.")
                    return AgentTaskResult.FAILED

                record_errors = self.validate_record_enhanced(record, self.expected_schema, f"Record[{i}]")
                validation_errors.extend(record_errors)

            if validation_errors:
                error_summary = self.format_validation_errors(validation_errors)
                self.log_and_update_dashboard(f"❌ FAILURE: Manual fallback record model (schema) validation failed. {error_summary}")

                for error in validation_errors:
                    self.log_and_update_dashboard(f"⚠️ {error}")

                return AgentTaskResult.FAILED

            self.log_and_update_dashboard(f"✅ SUCCESS: Validated {len(input_data)} record(s) using manual fallback schema.")
            return AgentTaskResult.SUCCESS

        except Exception as e:
            self.log_and_update_dashboard(f"❌ FAILURE: Error occurred in {self.get_caller_method()}.\n{str(e)}")
            return AgentTaskResult.FAILED

    # REVIEW
    def validate_record_enhanced(self, record: Dict[str, Any], schema: Dict[str, Type[Any]], record_path: str) -> List[str]:
        """Enhanced recursive record validation with detailed error paths"""
        errors: List[str] = []

        for key, expected_type in schema.items():
            field_path = f"{record_path}.{key}"

            if key not in record:
                errors.append(f"{field_path}: Missing required field")
                continue

            actual_value: Any = record[key]

            if actual_value is None:
                continue  # Allow null values

            # Enhanced type checking with array support
            if expected_type == list:
                if not isinstance(actual_value, list):
                    errors.append(f"{field_path}: Expected array, got {type(actual_value).__name__}")
                elif actual_value:  # Non-empty array
                    # Validate array items if they are objects
                    for item in actual_value:
                        if isinstance(item, dict):
                            # For nested objects in arrays, we'd need the nested schema
                            # For now, just validate it's a dict
                            continue
                        # For primitive arrays, items can be of any type
            elif expected_type == dict:
                if not isinstance(actual_value, dict):
                    errors.append(f"{field_path}: Expected object, got {type(actual_value).__name__}")
                # For nested objects, we'd need recursive validation with nested schema
            else:
                if not isinstance(actual_value, expected_type):
                    value_preview = str(actual_value)[:30] + "..." if len(str(actual_value)) > 30 else str(actual_value)
                    errors.append(f"{field_path}: Expected {expected_type.__name__}, got {type(actual_value).__name__} (value: '{value_preview}')")

        return errors

    # REVIEW
    def format_validation_errors(self, errors: List[str]) -> str:
        if not errors:
            return "No errors"

        if len(errors) == 1:
            return errors[0]
        elif len(errors) <= 3:
            return f"{len(errors)} errors: " + "; ".join(errors)
        else:
            return f"{len(errors)} errors: " + "; ".join(errors[:2]) + f"; ... and {len(errors) - 2} more"


from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, TypeAdapter

from agents.base_agent import BaseAgent
from agents.dataclasses.agent_context import AgentContext
from schemas.fallback_schema_generator import FallbackSchemaGenerator
from schemas.schema_generator import SchemaGenerator


class DataValidationAgent(BaseAgent):

    def __init__(self, agent_context: AgentContext) -> None:
        super().__init__(agent_context)
        self.setup_pydantic_schema()

    def setup_pydantic_schema(self) -> None:
        self.pydantic_model: Optional[Type[BaseModel]] = None
        raw_expected_schema: Dict[str, str] = self.agent_context.source_data_connector_state.get("expected_schema") or {}

        try:
            self.pydantic_model = SchemaGenerator.create_record_model(raw_expected_schema)
            self.log_and_update_dashboard(f"ℹ️ INFO: Created dynamic Pydantic schema with fields: {list(raw_expected_schema.keys())}.")

        except Exception as e:
            self.pydantic_model = None
            self.log_and_update_dashboard(f"⚠️ WARNING: Failed to create dynamic Pydantic schema, using fallback schema.\n{e}")

        self.expected_schema: Dict[str, Type[Any]] = {}

        # Keep existing type mapping for backwards compatibility
        for key, python_type_name in raw_expected_schema.items():
            python_type_obj: Optional[Type[Any]] = SchemaGenerator.TYPE_MAP.get(str(python_type_name).lower())

            if python_type_obj:
                self.expected_schema[key] = python_type_obj
            else:
                self.log_and_update_dashboard(f"⚠️ WARNING: Unknown type '{python_type_name}' in 'expected_schema' for key '{key}'. Skipping...")

    def validate_data(self, shared_input_data: Any) -> bool:
        if not shared_input_data:
            self.log_and_update_dashboard("⚠️ WARNING: No data provided.")
            return False

        validation_input_data: List[Dict[str, Any]] = []

        if isinstance(shared_input_data, dict):
            validation_input_data = [shared_input_data]
        elif isinstance(shared_input_data, list):
            validation_input_data = shared_input_data
        else:
            self.log_and_update_dashboard(f"❌ FAILURE: Invalid data format, expected dict or list, got {type(shared_input_data).__name__}.")
            return False

        if self.is_schema_transformed(validation_input_data):
            self.log_and_update_dashboard("ℹ️ INFO: Detected schema changes, recreating validation schema with updated keys.")
            self.setup_pydantic_schema()

        if self.pydantic_model is not None:
            try:
                self.log_and_update_dashboard(f"▶️ START: Attempting to validate {len(validation_input_data)} record(s) using dynamic Pydantic schema.")

                # NOTE There is a mypy limitation with tracking self.pydantic_model across method boundaries even though it's properly defined in __init__ and we have a None check above.
                # This is a known limitation with dynamic Pydantic model creation where mypy cannot statically verify the type of dynamically created models at analysis time.
                # The type: ignore[name-defined] suppresses this specific mypy error while maintaining type safety elsewhere and proper runtime behavior.
                validator: TypeAdapter[List[BaseModel]] = TypeAdapter(List[self.pydantic_model])  # type: ignore[name-defined]
                validated_data: List[BaseModel] = validator.validate_python(validation_input_data)

                self.log_and_update_dashboard(f"✅ SUCCESS: Validated {len(validated_data)} record(s) using dynamic Pydantic schema.")
                return True

            except Exception as e:
                self.log_and_update_dashboard(f"❌ FAILURE: Dynamic Pydantic schema validation failed.\n{e}")
                return False
        else:
            self.log_and_update_dashboard("⚠️ WARNING: Dynamic Pydantic schema unavailable, using fallback schema.")
            return self.validate_data_with_fallback(validation_input_data)

    def validate_data_with_fallback(self, validation_input_data: List[Dict[str, Any]]) -> bool:
        self.log_and_update_dashboard(f"▶️ START: Attempting to validate {len(validation_input_data)} record(s) (using dynamic Pydantic fallback schema).")

        try:
            current_schema: Dict[str, str] = self.agent_context.source_data_connector_state.get("expected_schema") or {}

            if not current_schema:
                self.log_and_update_dashboard("❌ FAILURE: No validation schema is available.")
                return False

            fallback_model: Type[BaseModel] = FallbackSchemaGenerator.create_fallback_record_model(current_schema)

            # NOTE In this method, mypy cannot statically verify dynamically created Pydantic models as valid types.
            # This is a known limitation with dynamic Pydantic model creation where mypy cannot statically verify the type of dynamically created models at analysis time.
            # The type: ignore[name-defined] suppresses this specific mypy error while maintaining type safety elsewhere and proper runtime behavior.
            validator: TypeAdapter[List[BaseModel]] = TypeAdapter(List[fallback_model])  # type: ignore[valid-type]
            validated_data: List[BaseModel] = validator.validate_python(validation_input_data)

            self.log_and_update_dashboard(f"✅ SUCCESS: Validated {len(validated_data)} record(s) using dynamic fallback schema.")
            return True

        except Exception as e:
            self.log_and_update_dashboard(f"❌ FAILURE: Dynamic fallback schema validation failed.\n{e}")
            return self.validate_data_with_manual_fallback(validation_input_data)

    def validate_data_with_manual_fallback(self, validation_input_data: List[Dict[str, Any]]) -> bool:
        self.log_and_update_dashboard(f"▶️ START: Attempting to validate {len(validation_input_data)} record(s) (using fallback schema).")

        if not self.expected_schema:
            self.log_and_update_dashboard("❌ FAILURE: No validation schema is specified.")
            return False

        records: List[Dict[str, Any]] = validation_input_data

        try:
            if not records:
                self.log_and_update_dashboard("❌ FAILURE: No data provided.")
                return False

            for i, record in enumerate(records):
                if not isinstance(record, dict):
                    self.log_and_update_dashboard(f"❌ FAILURE: Invalid record format at index {i}, expected a dictionary, but got {type(record).__name__} instead.")
                    return False

                for key, expected_type in self.expected_schema.items():
                    if key not in record:
                        self.log_and_update_dashboard(f"❌ FAILURE: Missing key: '{key}' in record.")
                        return False

                    actual_value: Any = record[key]

                    if actual_value is None:
                        self.log_and_update_dashboard(f"⚠️ WARNING: Null value found for key '{key}' in record at index {i}.")
                        continue

                    if not isinstance(actual_value, expected_type):
                        value_preview: str = str(actual_value)[:50] + "..." if len(str(actual_value)) > 50 else str(actual_value)
                        self.log_and_update_dashboard(f"❌ FAILURE: Type mismatch for key '{key}' in record at index {i}. Expected {expected_type.__name__}, but got {type(actual_value).__name__} instead. Actual value: '{value_preview}'.")
                        return False

            self.log_and_update_dashboard(f"✅ SUCCESS: Validated {len(records)} record(s) (using fallback schema).")
            return True

        except Exception as e:
            self.log_and_update_dashboard(f"❌ FAILURE: Error occurred in {self.get_caller_method()}.\n{e}")
            return False

    def is_schema_transformed(self, data: Any) -> bool:
        if not isinstance(data, list) or not data:
            return False

        sample_record: Dict[str, Any] = data[0]
        sample_record_keys: set = set(sample_record.keys())

        if not isinstance(sample_record, dict):
            return False

        has_transformed_fields: bool = "is_transformed" in sample_record or "transformed_on" in sample_record
        current_schema: Dict[str, str] = self.agent_context.source_data_connector_state.get("expected_schema") or {}
        current_schema_keys: set = set(current_schema.keys())

        return has_transformed_fields or not sample_record_keys.issubset(current_schema_keys)

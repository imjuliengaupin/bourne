
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, TypeAdapter, ValidationError

from agents.base_agent import BaseAgent
from agents.dataclasses.agent_context import AgentContext
from schemas.schema_generator import SchemaGenerator


class DataValidationAgent(BaseAgent):

    def __init__(self, agent_context: AgentContext) -> None:
        super().__init__(agent_context)

        self.expected_schema: Dict[str, Type[Any]] = {}
        self.pydantic_model: Optional[Type[BaseModel]] = None

        raw_expected_schema: Dict[str, str] = self.agent_context.source_data_connector_state.get("expected_schema")

        try:
            self.pydantic_model = SchemaGenerator.create_record_model(raw_expected_schema)
            self.log_and_update_dashboard(f"ℹ️ INFO: Created dynamic schema with fields: {list(raw_expected_schema.keys())}")

        except Exception as e:
            self.log_and_update_dashboard(f"❌ FAILURE: Failed to create dynamic schema: {e}")

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

        if self.pydantic_model:
            try:
                self.log_and_update_dashboard(f"▶️ START: Attempting to validate {len(shared_input_data)} records using dynamic Pydantic schema.")

                validator: TypeAdapter[List[BaseModel]] = TypeAdapter(List[self.pydantic_model])
                validated_data: List[BaseModel] = validator.validate_python(shared_input_data)

                self.log_and_update_dashboard(f"✅ SUCCESS: Validated {len(validated_data)} records using dynamic Pydantic schema.")
                return True

            except Exception as e:
                self.log_and_update_dashboard(f"❌ FAILURE: Dynamic Pydantic schema validation failed.\n{e}")
                return False

        self.log_and_update_dashboard("⚠️ WARNING: Dynamic Pydantic schema unavailable, using fallback schema.")
        return self.validate_data_with_fallback(shared_input_data)

    def validate_data_with_fallback(self, shared_input_data: Any) -> bool:
        self.log_and_update_dashboard(f"▶️ START: Attempting to validate {len(shared_input_data)} records (using fallback schema).")

        if not self.expected_schema:
            self.log_and_update_dashboard("❌ FAILURE: No validation schema is specified.")
            return False

        records: List[Dict[str, Any]] = []

        try:
            if isinstance(shared_input_data, dict):
                records = [shared_input_data]
            elif isinstance(shared_input_data, list):
                if all(isinstance(item, dict) for item in shared_input_data):
                    records = shared_input_data
                else:
                    self.log_and_update_dashboard(f"❌ FAILURE: Invalid data format, expected a dictionary or list of dictionaries, but got {type(shared_input_data).__name__} instead.")
                    return False
            else:
                self.log_and_update_dashboard(f"❌ FAILURE: Invalid data format, expected a dictionary or list of dictionaries, but got {type(shared_input_data).__name__} instead.")
                return False

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

                    if not isinstance(actual_value, expected_type):
                        value_preview: str = str(actual_value)[:50] + "..." if len(str(actual_value)) > 50 else str(actual_value)
                        self.log_and_update_dashboard(f"❌ FAILURE: Type mismatch for key '{key}' in record at index {i}. Expected {expected_type.__name__}, but got {type(actual_value).__name__} instead. Actual value: '{value_preview}'.")
                        return False

            self.log_and_update_dashboard(f"✅ SUCCESS: Validated {len(records)} records (using fallback schema).")
            return True

        except Exception as e:
            self.log_and_update_dashboard(f"❌ FAILURE: Error occurred in {self.get_caller_method()}.\n{e}")
            return False

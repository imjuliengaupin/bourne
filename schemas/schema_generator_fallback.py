"""**Fallback Schema Generator for Error Recovery**

Provides **simplified schema generation** when the main SchemaGenerator fails, offering multiple fallback strategies for different complexity levels and **graceful degradation** for `DataValidationAgent` steps.

## Fallback Strategies

1. **Simple Fallback**: Basic type mapping for flat schemas
2. **Enhanced Fallback**: Handles nested objects and arrays as generic types
3. **Generic Fallback**: Accepts any fields when schema is unavailable

## Use Cases

- **Error recovery** when dynamic schema generation fails
- **Data migration** scenarios with unknown structures
- **Testing environments** requiring flexible validation
- **Legacy data** with inconsistent schemas
"""

from typing import Any, Dict, List, Type, Union

from pydantic import BaseModel, Field, create_model

from schemas.schema_generator import SchemaGenerator


class FallbackSchemaGenerator:
    """Simplified schema generator for error recovery and graceful degradation. Provides **multiple fallback strategies** when the main SchemaGenerator encounters errors or when dealing with unpredictable data structures that require more flexible validation approaches."""

    @classmethod
    def create_dynamic_fallback_record_model(cls, expected_schema: Dict[str, str]) -> Type[BaseModel]:
        """**Generates a simple Pydantic model** with basic type mapping for flat data structures, using required fields with no nested object support.

        Args:
            expected_schema: Simple schema mapping field names to type strings

        Returns:
            Pydantic model class with basic field validation

        Note:
            Falls back to a **generic model** if schema is empty. All Pydantic fields are **required** ([Field(...)](https://docs.pydantic.dev/latest/api/fields/#pydantic.fields.Field)) with no optional or default values.

        Example:
            ```python
            expected_schema = {
                "ID": "int",
                "Timestamp": "str"
            }

            DynamicFallbackRecordModel = FallbackSchemaGenerator.create_dynamic_fallback_record_model(expected_schema)

            # Usage
            record = DynamicFallbackRecordModel(
                ID=1,
                Timestamp="2099-01-01 00:00:00"
            )
            ```
        """
        if not expected_schema:
            return cls.create_generic_fallback_record_model()

        fields: Dict[str, Any] = {}

        for field_name, field_type in expected_schema.items():
            python_type: Type[Any] = SchemaGenerator.TYPE_MAP.get(field_type.lower(), str)
            fields[field_name] = (python_type, Field(...))

        fallback_model: Type[BaseModel] = create_model(
            'DynamicFallbackRecordModel',
            **fields
        )

        return fallback_model

    @classmethod
    def create_dynamic_enhanced_fallback_record_model(cls, expected_schema: Dict[str, Union[str, Dict[str, Any], List[Any]]]) -> Type[BaseModel]:
        """**Handles complex schemas** with nested objects and arrays by mapping them to generic dict/list types, providing basic validation without deep structure analysis.

        Args:
            expected_schema: Complex schema with nested objects and arrays

        Returns:
            Pydantic model class with generic nested type support

        Note:
            **Nested objects** are validated as [dict](https://docs.python.org/3/library/stdtypes.html#dict) type and **arrays** as [list](https://docs.python.org/3/library/stdtypes.html#list) type, providing structure validation without deep type checking.

        Example:
            ```python
            expected_schema = {
                "ID": "int",
                "Metadata": {"Timestamp": "str"},
                "Tags": ["str"]
            }

            DynamicEnhancedFallbackRecordModel = FallbackSchemaGenerator.create_dynamic_enhanced_fallback_record_model(expected_schema)

            # Usage
            record = DynamicEnhancedFallbackRecordModel(
                ID=1,
                Metadata={"Timestamp": "2099-01-01 00:00:00"},
                Tags=["Developer", "Tester", "Admin"]
            )
            ```
        """
        if not expected_schema:
            return cls.create_generic_fallback_record_model()

        fields: Dict[str, Any] = {}

        for field_name, field_type in expected_schema.items():
            if isinstance(field_type, dict):
                # Handle nested objects as generic dict
                fields[field_name] = (dict, Field(...))
            elif isinstance(field_type, list):
                # Handle arrays as generic list
                fields[field_name] = (list, Field(...))
            else:
                # Handle primitive types
                python_type: Type[Any] = SchemaGenerator.TYPE_MAP.get(str(field_type).lower(), str)
                fields[field_name] = (python_type, Field(...))

        fallback_model: Type[BaseModel] = create_model(
            'DynamicEnhancedFallbackRecordModel',
            **fields
        )

        return fallback_model

    @classmethod
    def create_generic_fallback_record_model(cls) -> Type[BaseModel]:
        """**Ultimate fallback** that accepts any field names and values when schema information is unavailable or unreliable. Useful for data migration and unknown data structures.

        Returns:
            Pydantic model class configured with [extra="allow"](https://docs.pydantic.dev/latest/api/config/#pydantic.config.ConfigDict.extra) to accept arbitrary field names and values, providing maximum flexibility for unknown data structures.

        Warning:
            Provides **minimal validation**, use only when other fallback strategies are insufficient or when maximum flexibility is required.

        Example:
            ```python
            GenericFallbackRecordModel = FallbackSchemaGenerator.create_generic_fallback_record_model()

            # Accepts any data structure
            record = GenericFallbackRecordModel(
                ID=1,
                Timestamp="2099-01-01 00:00:00"
            )
            ```
        """

        class GenericFallbackRecordModel(BaseModel):
            """**Generic record model** that accepts any additional fields."""

            class Config:
                """**Model configuration** allowing extra fields for maximum flexibility."""
                extra: str = "allow"

        return GenericFallbackRecordModel

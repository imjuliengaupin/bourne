
import re
from typing import Any, ClassVar, Dict, List, Optional, Tuple, Type, Union

from pydantic import BaseModel, ConfigDict, Field, create_model

from core import constants


class SchemaGenerator:

    TYPE_MAP: Dict[str, Type[Any]] = {
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "list": list,
        "dict": dict,
        "nested_object": dict,
        "array": list
    }

    class ConfiguredBaseModel(BaseModel):
        model_config: ClassVar[ConfigDict] = ConfigDict(populate_by_name=True)

    @classmethod
    def create_record_model(cls, expected_schema: Dict[str, Union[str, Dict[str, Any], List[Any]]]) -> Type[BaseModel]:
        fields: Dict[str, Tuple[Type[Any], Any]] = {}

        for field_name, field_type in expected_schema.items():
            if isinstance(field_type, dict):
                nested_model: Type[BaseModel] = cls.create_nested_record_model(field_name, field_type)
                fields[field_name.lower()] = (nested_model, Field(alias=field_name))

            elif isinstance(field_type, list) and field_type:
                if isinstance(field_type[0], dict):
                    # Handle array of nested objects: [{"field": "type"}]
                    nested_model = cls.create_nested_record_model(f"{field_name}Item", field_type[0])
                    fields[field_name.lower()] = (List[nested_model], Field(alias=field_name))
                else:
                    # Handle array of primitives: ["str"] or ["int"]
                    primitive_type = cls.TYPE_MAP.get(str(field_type[0]).lower(), str)
                    fields[field_name.lower()] = (List[primitive_type], Field(alias=field_name))

            else:
                # field_type is a string here
                python_type: Optional[Type[Any]] = cls.TYPE_MAP.get(str(field_type).lower())

                if python_type:
                    fields[field_name.lower()] = (python_type, Field(alias=field_name))
                else:
                    fields[field_name.lower()] = (str, Field(alias=field_name))

        # NOTE There is a mypy limitation with create_model()'s overload system
        # The core issue is that mypy is interpreting the arguments as positional instead of keyword-only arguments.
        # The signature clearly shows that after the /, there's a *, which means everything must be keyword-only.
        # The problem is that Python's argument unpacking with **fields happens before the keyword arguments are processed, so mypy sees it as positional arguments in the wrong order.
        # At runtime, Python correctly processes __base__ as a keyword argument and **fields as field definitions, but mypy's static analysis cannot properly infer this argument unpacking pattern.
        # The type: ignore[call-overload] suppresses this specific mypy error while maintaining runtime correctness.
        model: Type[BaseModel] = create_model(  # type: ignore[call-overload]
            'DynamicRecordModel',
            __base__=(cls.ConfiguredBaseModel,),
            **fields
        )

        return model

    @classmethod
    def create_nested_record_model(cls, parent_field_name: str, nested_schema: Dict[str, Union[str, Dict[str, Any], List[Any]]]) -> Type[BaseModel]:
        nested_fields: Dict[str, Tuple[Type[Any], Any]] = {}

        for nested_field_name, nested_field_type in nested_schema.items():
            if isinstance(nested_field_type, dict):
                # Handle deep nested objects (3+ levels)
                deep_nested_model = cls.create_nested_record_model(f"{parent_field_name}{nested_field_name}", nested_field_type)
                nested_fields[nested_field_name.lower()] = (deep_nested_model, Field(alias=nested_field_name))

            elif isinstance(nested_field_type, list) and nested_field_type:
                # Handle arrays within nested objects
                if isinstance(nested_field_type[0], dict):
                    # Handle arrays of nested objects within a already nested object
                    array_item_model = cls.create_nested_record_model(f"{parent_field_name}{nested_field_name}Item", nested_field_type[0])
                    nested_fields[nested_field_name.lower()] = (List[array_item_model], Field(alias=nested_field_name))
                else:
                    # Handle arrays of primitives within nested objects
                    primitive_type = cls.TYPE_MAP.get(str(nested_field_type[0]).lower(), str)
                    nested_fields[nested_field_name.lower()] = (List[primitive_type], Field(alias=nested_field_name))

            else:
                # nested_field_type is a string here
                python_type: Optional[Type[Any]] = cls.TYPE_MAP.get(str(nested_field_type).lower())

                if python_type:
                    nested_fields[nested_field_name.lower()] = (python_type, Field(alias=nested_field_name))
                else:
                    nested_fields[nested_field_name.lower()] = (str, Field(alias=nested_field_name))

        # NOTE There is a mypy limitation with create_model()'s overload system
        # The core issue is that mypy is interpreting the arguments as positional instead of keyword-only arguments.
        # The signature clearly shows that after the /, there's a *, which means everything must be keyword-only.
        # The problem is that Python's argument unpacking with **fields happens before the keyword arguments are processed, so mypy sees it as positional arguments in the wrong order.
        # At runtime, Python correctly processes __base__ as a keyword argument and **fields as field definitions, but mypy's static analysis cannot properly infer this argument unpacking pattern.
        # The type: ignore[call-overload] suppresses this specific mypy error while maintaining runtime correctness.
        nested_model: Type[BaseModel] = create_model(  # type: ignore[call-overload]
            f'DynamicNested{parent_field_name}RecordModel',
            __base__=(cls.ConfiguredBaseModel,),
            **nested_fields
        )

        return nested_model

    @classmethod
    def infer_python_type(cls, value: Any) -> str:
        if isinstance(value, str):
            return "str"
        elif isinstance(value, int):
            return "int"
        elif isinstance(value, float):
            return "float"
        elif isinstance(value, bool):
            return "bool"
        elif isinstance(value, list):
            return "list"
        elif isinstance(value, dict):
            return "dict"
        else:
            return "str"

    @classmethod
    def infer_nested_schema_from_data(cls, data: List[Dict[str, Any]]) -> Dict[str, Union[str, Dict[str, Any], List[Any]]]:
        if not data or not isinstance(data, list) or not data[0]:
            return {}

        sample_record = data[0]
        inferred_schema: Dict[str, Union[str, Dict[str, Any], List[Any]]] = {}

        for key, value in sample_record.items():
            if isinstance(value, dict):
                # Nested object, recursively infer its schema
                nested_schema = cls.infer_nested_object_schema(value)
                inferred_schema[key] = nested_schema
            elif isinstance(value, list) and value:
                # Array, infer array schema
                array_schema = cls.infer_array_schema(value)
                inferred_schema[key] = array_schema
            else:
                # Primitive type
                inferred_schema[key] = cls.infer_python_type(value)

        return inferred_schema

    @classmethod
    def infer_nested_object_schema(cls, nested_object: Dict[str, Any]) -> Dict[str, Union[str, Dict[str, Any], List[Any]]]:
        nested_schema: Dict[str, Union[str, Dict[str, Any], List[Any]]] = {}

        for nested_key, nested_value in nested_object.items():
            if isinstance(nested_value, dict):
                # Deep nesting (3+ levels)
                nested_schema[nested_key] = cls.infer_nested_object_schema(nested_value)
            elif isinstance(nested_value, list) and nested_value:
                # Array within nested object
                nested_schema[nested_key] = cls.infer_array_schema(nested_value)
            else:
                # Primitive field
                nested_schema[nested_key] = cls.infer_python_type(nested_value)

        return nested_schema

    @classmethod
    def infer_array_schema(cls, array: List[Any]) -> List[Union[str, Dict[str, Any]]]:
        if not array:
            return ["str"]  # Default fallback

        first_item = array[0]

        if isinstance(first_item, dict):
            # Array of nested objects
            nested_schema = cls.infer_nested_object_schema(first_item)
            return [nested_schema]
        else:
            # Array of primitives
            primitive_type = cls.infer_python_type(first_item)
            return [primitive_type]

    @classmethod
    def transform_nested_schema_recursively(cls, schema: Dict[str, Union[str, Dict[str, Any], List[Any]]], transformation_mode: str) -> Dict[str, Union[str, Dict[str, Any], List[Any]]]:
        """Transform nested schema keys recursively"""

        transformed_schema: Dict[str, Union[str, Dict[str, Any], List[Any]]] = {}

        for key, value in schema.items():
            # Transform the key
            transformed_key = cls.transform_schema_key(key, transformation_mode)

            if isinstance(value, dict):
                # Recursively transform nested object schema
                transformed_schema[transformed_key] = cls.transform_nested_schema_recursively(value, transformation_mode)
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                # Transform array of nested objects schema
                transformed_array_item = cls.transform_nested_schema_recursively(value[0], transformation_mode)
                transformed_schema[transformed_key] = [transformed_array_item]
            else:
                # Keep primitive types as-is
                transformed_schema[transformed_key] = value

        return transformed_schema

    @classmethod
    def transform_schema_key(cls, key: str, transformation_mode: str) -> str:
        """Transform a single key based on transformation mode"""
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


from typing import Any, ClassVar, Dict, List, Optional, Tuple, Type, Union

from pydantic import BaseModel, ConfigDict, Field, create_model


class SchemaGenerator:

    TYPE_MAP: Dict[str, Type[Any]] = {
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "list": list,
        "dict": dict,
        "nested_object": dict
    }

    class ConfiguredBaseModel(BaseModel):
        model_config: ClassVar[ConfigDict] = ConfigDict(populate_by_name=True)

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
    def create_record_model(cls, expected_schema: Dict[str, str]) -> Type[BaseModel]:
        fields: Dict[str, Tuple[Type[Any], Any]] = {}

        for field_name, field_type in expected_schema.items():
            if isinstance(field_type, dict):
                nested_model: Type[BaseModel] = cls.create_nested_record_model(field_name, field_type)
                fields[field_name.lower()] = (nested_model, Field(alias=field_name))
            else:
                python_type: Optional[Type[Any]] = cls.TYPE_MAP.get(field_type.lower())

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
    def create_nested_record_model(cls, parent_field_name: str, nested_schema: Dict[str, str]) -> Type[BaseModel]:
        nested_fields: Dict[str, Tuple[Type[Any], Any]] = {}

        for nested_field_name, nested_field_type in nested_schema.items():
            python_type: Optional[Type[Any]] = cls.TYPE_MAP.get(nested_field_type.lower())

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
    def infer_nested_schema_from_data(cls, data: List[Dict[str, Any]]) -> Dict[str, Union[str, Dict[str, str]]]:
        if not data or not isinstance(data, list) or not data[0]:
            return {}

        sample_record = data[0]
        inferred_schema: Dict[str, Union[str, Dict[str, str]]] = {}

        for key, value in sample_record.items():
            if isinstance(value, dict):
                nested_schema: Dict[str, str] = {}

                for nested_key, nested_value in value.items():
                    nested_schema[nested_key] = cls.infer_python_type(nested_value)

                inferred_schema[key] = nested_schema
            else:
                inferred_schema[key] = cls.infer_python_type(value)

        return inferred_schema

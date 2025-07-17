
from typing import Any, ClassVar, Dict, Optional, Tuple, Type

from pydantic import BaseModel, ConfigDict, Field, create_model


class SchemaGenerator:

    TYPE_MAP: Dict[str, Type[Any]] = {
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "list": list,
        "dict": dict
    }

    class ConfiguredBaseModel(BaseModel):
        model_config: ClassVar[ConfigDict] = ConfigDict(populate_by_name=True)

    @classmethod
    def create_record_model(cls, expected_schema: Dict[str, str]) -> Type[BaseModel]:
        fields: Dict[str, Tuple[Type[Any], Any]] = {}

        for field_name, field_type in expected_schema.items():
            python_type: Optional[Type[Any]] = cls.TYPE_MAP.get(field_type.lower())

            if python_type:
                # Create field with original name as alias (for case transformations)
                fields[field_name.lower()] = (python_type, Field(alias=field_name))
            else:
                # Default to str for unknown types
                fields[field_name.lower()] = (str, Field(alias=field_name))

        # NOTE There is a mypy limitation with create_model()'s overload system
        # The core issue is that mypy is interpreting the arguments as positional instead of keyword-only arguments.
        # The signature clearly shows that after the /, there's a *, which means everything must be keyword-only.
        # The problem is that Python's argument unpacking with **fields happens before the keyword arguments are processed, so mypy sees it as positional arguments in the wrong order.
        # At runtime, Python correctly processes __base__ as a keyword argument and **fields as field definitions, but mypy's static analysis cannot properly infer this argument unpacking pattern.
        # The type: ignore[call-overload] suppresses this specific mypy error while maintaining runtime correctness.
        model: Type[BaseModel] = create_model(  # type: ignore[call-overload]
            'DynamicRecord',
            __base__=(cls.ConfiguredBaseModel,),
            **fields
        )

        return model

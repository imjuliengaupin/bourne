
from typing import Any, Dict, Optional, Type

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

    @classmethod
    def create_record_model(cls, expected_schema: Dict[str, str]) -> Type[BaseModel]:
        fields: Dict[str, tuple[Type[Any], Field]] = {}

        for field_name, field_type in expected_schema.items():
            python_type: Optional[Type[Any]] = cls.TYPE_MAP.get(field_type.lower())

            if python_type:
                # Create field with original name as alias (for case transformations)
                fields[field_name.lower()] = (python_type, Field(alias=field_name))
            else:
                # Default to str for unknown types
                fields[field_name.lower()] = (str, Field(alias=field_name))

        # Dynamically create the model
        return create_model(
            'DynamicRecord',
            **fields,
            __config__=ConfigDict(populate_by_name=True)
        )


from typing import Any, Dict, List, Type, Union

from pydantic import BaseModel, Field, create_model

from schemas.schema_generator import SchemaGenerator


class FallbackSchemaGenerator:

    @classmethod
    def create_fallback_record_model(cls, expected_schema: Dict[str, str]) -> Type[BaseModel]:
        if not expected_schema:
            return cls.create_generic_fallback_model()

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
    def create_enhanced_fallback_record_model(cls, expected_schema: Dict[str, Union[str, Dict[str, Any], List[Any]]]) -> Type[BaseModel]:
        if not expected_schema:
            return cls.create_generic_fallback_model()

        fields: Dict[str, Any] = {}

        for field_name, field_type in expected_schema.items():
            if isinstance(field_type, dict):
                fields[field_name] = (dict, Field(...))
            elif isinstance(field_type, list):
                fields[field_name] = (list, Field(...))
            else:
                python_type: Type[Any] = SchemaGenerator.TYPE_MAP.get(str(field_type).lower(), str)
                fields[field_name] = (python_type, Field(...))

        fallback_model: Type[BaseModel] = create_model(
            'DynamicEnhancedFallbackRecordModel',
            **fields
        )

        return fallback_model

    @classmethod
    def create_generic_fallback_model(cls) -> Type[BaseModel]:
        class GenericFallbackRecord(BaseModel):
            class Config:
                extra: str = "allow"

        return GenericFallbackRecord

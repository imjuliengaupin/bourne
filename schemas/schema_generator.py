"""**Schema Generator for Dynamic Pydantic Models**

Generates Pydantic models dynamically from JSON schema definitions, supporting **nested objects**, **arrays**, and **primitive types** with automatic field mapping and alias generation.

## Features

- **Dynamic model creation** from schema definitions
- **Recursive nested object** support (unlimited depth)
- **Array handling** for both primitives and nested objects
- **Type inference** from actual data
- **Schema transformation** with various key naming conventions
"""

from typing import (TYPE_CHECKING, Any, ClassVar, Dict, List, Optional, Tuple,
                    Type, Union)

from pydantic import BaseModel, ConfigDict, Field, create_model

from schemas.schema_key_transformer import SchemaKeyTransformer

# NOTE: TYPE_CHECKING guard to avoid circular imports at runtime while supporting
# type-only imports for static analysis. The if block is a placeholder for future
# type aliases or Protocol definitions that don't need to execute at runtime.
if TYPE_CHECKING:
    pass


class SchemaGenerator:
    """Dynamic Pydantic model generator for complex data schemas.

    Provides utilities to:
    - Create Pydantic models from schema definitions, infer schemas from data, and transform field names according to various conventions.
    - Handle **String-to-Python type mapping** for schema field types.
    - Map schema type strings to actual Python types for Pydantic model generation. Supports both primitive types and collection types.
    """
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
        """**Base model class** with configured settings for dynamic models. Provides consistent configuration for all dynamically generated Pydantic models, enabling field population by both field names and aliases."""
        model_config: ClassVar[ConfigDict] = ConfigDict(populate_by_name=True)

    @classmethod
    def create_record_model(cls, expected_schema: Dict[str, Union[str, Dict[str, Any], List[Any]]]) -> Type[BaseModel]:
        """**Dynamically generates** a Pydantic model class with proper field types, aliases, and nested model support based on the provided schema.

        Args:
            expected_schema: Schema definition mapping field names to types. Supports strings for primitives, dicts for nested objects, and lists for arrays.

        Returns:
            Dynamically created Pydantic model class

        See Also:
            [`create_nested_record_model()`](#create_nested_record_model): Recursive model creation method for schemas containing nested elements

        Example:
            ```python
            expected_schema = {
                "ID": "int",
                "Timestamp": "str"
            }

            # Usage
            model = SchemaGenerator.create_record_model(expected_schema)
            ```
        """
        fields: Dict[str, Tuple[Type[Any], Any]] = {}

        for field_name, field_type in expected_schema.items():
            if isinstance(field_type, dict):
                nested_model_type: Type[BaseModel] = cls.create_nested_record_model(field_name, field_type)
                fields[field_name.lower()] = (nested_model_type, Field(alias=field_name))
            elif isinstance(field_type, list) and field_type:
                if isinstance(field_type[0], dict):
                    # Handle array of nested objects: [{"field": "type"}]
                    array_nested_model_class: Type[BaseModel] = cls.create_nested_record_model(f"ParentField_{field_name}", field_type[0])

                    # NOTE: Static type checker limitation with dynamic type creation for List[DynamicType]
                    #
                    # Problem:
                    #   Static type checkers cannot validate List[variable] where the variable contains a dynamically created type.
                    #   Even though `array_nested_model_class` is correctly typed as `Type[BaseModel]`, static analysis
                    #   cannot verify that the runtime type is valid for use as a generic type parameter in List[...].
                    #
                    # Why no proper solution exists:
                    #   1. Dynamic Pydantic models are created at runtime using `create_model()`, making static analysis impossible
                    #   2. Static type systems require compile-time type knowledge for generic parameters
                    #   3. Using TypeVar, Generic, or other typing constructs still requires static type definitions
                    #   4. The `typing.cast()` function doesn't work here as it would cast the value, not the type itself
                    #
                    # Runtime behavior:
                    #   This code works perfectly at runtime because Python's dynamic typing allows List[runtime_type].
                    #   The type ignore only suppresses static analysis limitation, not a real type error.
                    array_type = List[array_nested_model_class]  # type: ignore[valid-type,misc]

                    fields[field_name.lower()] = (array_type, Field(alias=field_name))
                else:
                    # Handle array of primitives: ["str"] or ["int"]
                    array_primitive_class: Type[Any] = cls.TYPE_MAP.get(str(field_type[0]).lower(), str)

                    # NOTE: Same mypy limitation as above, but for primitive types in List[primitive_type]
                    #
                    # Even though `array_primitive_class` contains a valid type like `str` or `int`, mypy cannot
                    # statically verify this because the type is determined at runtime from the TYPE_MAP lookup.
                    array_type = List[array_primitive_class]  # type: ignore[valid-type,misc]

                    fields[field_name.lower()] = (array_type, Field(alias=field_name))
            else:
                # Default field_type is always ["str"] here
                python_type: Optional[Type[Any]] = cls.TYPE_MAP.get(str(field_type).lower())

                if python_type:
                    fields[field_name.lower()] = (python_type, Field(alias=field_name))
                else:
                    fields[field_name.lower()] = (str, Field(alias=field_name))

        # NOTE: MyPy limitation with Pydantic's [`create_model()`](https://docs.pydantic.dev/latest/api/main/#pydantic.create_model) method overload system
        #
        # Problem:
        #   MyPy cannot properly analyze the complex method signature of `create_model()` when using keyword argument unpacking.
        #   The method signature: `create_model(model_name, /, *, __base__=None, **field_definitions)` requires
        #   all arguments after the `*` to be keyword-only, but mypy's static analysis gets confused by the
        #   combination of `__base__` and `**fields` unpacking.
        #
        # Technical Details:
        #   - `create_model()` has multiple overloads with different parameter patterns
        #   - MyPy sees `**fields` as positional argument expansion happening before keyword processing
        #   - The analysis incorrectly assumes arguments are in the wrong order for the overload signatures
        #   - This is a limitation in mypy's overload resolution, not an actual runtime error
        #
        # Why no proper solution exists:
        #   1. The Pydantic API requires this exact calling pattern for dynamic field injection
        #   2. Alternative approaches (manual class creation, metaclasses) would be far more complex
        #   3. MyPy's overload system cannot handle this specific runtime argument unpacking pattern
        #   4. The function works perfectly at runtime - this is purely a static analysis limitation
        #
        # Runtime behavior:
        #   Python correctly processes `__base__` as a keyword argument and `**fields` as field definitions.
        #   The `create_model()` function receives exactly what it expects and creates valid Pydantic models.
        model: Type[BaseModel] = create_model(
            'DynamicRecordModel',
            __base__=(cls.ConfiguredBaseModel,),
            **fields  # type: ignore[call-overload]
        )

        return model

    @classmethod
    def create_nested_record_model(cls, parent_field_name: str, nested_schema: Dict[str, Union[str, Dict[str, Any], List[Any]]]) -> Type[BaseModel]:
        """**Recursively generates** Pydantic models for nested object schemas, supporting unlimited nesting depth and mixed field types.

        Args:
            parent_field_name: Name of the parent field (used for model naming)
            nested_schema: Schema definition for the nested object

        Returns:
            Dynamically created nested Pydantic model class

        See Also:
            [`create_record_model()`](#create_record_model): Main model creation method

        Example:
            ```python
            nested_schema = {
                "ID": "str",
                Metadata": {
                    "Timestamp": "str"
                }
            }

            # Usage
            model = SchemaGenerator.create_nested_record_model("ParentField_?_NestedField_?", nested_schema)
            ```
        """
        nested_fields: Dict[str, Tuple[Type[Any], Any]] = {}

        for nested_field_name, nested_field_type in nested_schema.items():
            if isinstance(nested_field_type, dict):
                # Handle deep nested objects (3+ levels)
                deep_nested_model: Type[BaseModel] = cls.create_nested_record_model(f"{parent_field_name}{nested_field_name}", nested_field_type)
                nested_fields[nested_field_name.lower()] = (deep_nested_model, Field(alias=nested_field_name))
            elif isinstance(nested_field_type, list) and nested_field_type:
                # Handle arrays within nested objects
                if isinstance(nested_field_type[0], dict):
                    # Handle arrays of nested objects within a already nested object
                    nested_array_item_model_class: Type[BaseModel] = cls.create_nested_record_model(f"ParentField_{parent_field_name}_NestedField_{nested_field_name}", nested_field_type[0])

                    # NOTE: Same static type checker limitation with dynamic nested model types in arrays
                    #
                    # This is the same issue as above but occurs in deeply nested schemas where we have
                    # arrays of objects within nested objects (e.g., User.Roles[].Permissions[]).
                    # Static type checkers cannot validate the dynamically created nested model type.
                    nested_array_type = List[nested_array_item_model_class]  # type: ignore[valid-type,misc]

                    nested_fields[nested_field_name.lower()] = (nested_array_type, Field(alias=nested_field_name))
                else:
                    # Handle arrays of primitives within nested objects
                    nested_primitive_class: Type[Any] = cls.TYPE_MAP.get(str(nested_field_type[0]).lower(), str)

                    # NOTE: Same static type checker limitation for primitive arrays in nested contexts
                    nested_array_type = List[nested_primitive_class]  # type: ignore[valid-type,misc]

                    nested_fields[nested_field_name.lower()] = (nested_array_type, Field(alias=nested_field_name))
            else:
                python_type: Optional[Type[Any]] = cls.TYPE_MAP.get(str(nested_field_type).lower())

                if python_type:
                    nested_fields[nested_field_name.lower()] = (python_type, Field(alias=nested_field_name))
                else:
                    nested_fields[nested_field_name.lower()] = (str, Field(alias=nested_field_name))

        # NOTE: Same MyPy limitation with Pydantic's `create_model()` as above, but for nested model creation
        #
        # Problem:
        #   Identical to the issue in `create_record_model()` - mypy cannot properly analyze the overloaded
        #   method signature when using `**nested_fields` unpacking with the `__base__` keyword argument.
        #
        # Context-specific details:
        #   - This occurs during recursive nested model creation for complex schemas
        #   - The `nested_fields` dict contains dynamically generated field definitions
        #   - Each nested level may contain further arrays or objects requiring recursive processing
        #
        # Runtime behavior:
        #   Functions identically to the parent method - Python handles the argument unpacking correctly
        #   and creates properly structured nested Pydantic models with full validation capabilities.
        nested_model: Type[BaseModel] = create_model(
            f'DynamicNested{parent_field_name}RecordModel',
            __base__=(cls.ConfiguredBaseModel,),
            **nested_fields  # type: ignore[call-overload]
        )

        return nested_model

    @classmethod
    def infer_python_type(cls, value: Any) -> str:
        """**Analyzes a value** and returns the corresponding Python type string for use in schema definitions.

        Args:
            value: Any Python type value to analyze

        Returns:
            String representation of the inferred type

        See Also:
            [`infer_nested_object_schema()`](#infer_nested_object_schema): For nested object analysis
            [`infer_array_schema()`](#infer_array_schema): For array structure analysis

        Example:
            ```python
            SchemaGenerator.infer_python_type(1)
            # Returns "int"

            SchemaGenerator.infer_python_type("Bourne")
            # Returns "str"

            SchemaGenerator.infer_python_type([1,2,3])
            # Returns "list"
            ```
        """
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
        """**Automatically generates** schema definitions by analyzing the structure and types of actual data records, including nested objects and arrays.

        Args:
            data: List of data records to analyze

        Returns:
            Inferred schema definition suitable for [`create_record_model()`](#create_record_model)

        Note:
            Uses the **first record** as the schema template. Always ensure the data is representative of the expected structure.

        Example:
            ```python
            data = [
                {"ID": 1, "Metadata": {"Timestamp": "2099-01-01 00:00:00"}},
                {"ID": 2, "Metadata": {"Timestamp": "2099-01-01 00:00:00"}},
                {"ID": 3, "Metadata": {"Timestamp": "2099-01-01 00:00:00"}}
            ]

            schema = SchemaGenerator.infer_nested_schema_from_data(data)
            # Returns {"ID": "int", "Metadata": {"Timestamp": "str"}}
            ```
        """
        if not data or not isinstance(data, list) or not data[0]:
            return {}

        sample_record: Dict[str, Any] = data[0]
        inferred_schema: Dict[str, Union[str, Dict[str, Any], List[Any]]] = {}

        for key, value in sample_record.items():
            if isinstance(value, dict):
                # Nested object, recursively infer its schema
                nested_schema: Dict[str, str | Dict[str, Any] | List[Any]] = cls.infer_nested_object_schema(value)
                inferred_schema[key] = nested_schema
            elif isinstance(value, list) and value:
                # Array, infer array schema
                array_schema: List[str | Dict[str, Any]] = cls.infer_array_schema(value)
                inferred_schema[key] = array_schema
            else:
                # Primitive type
                inferred_schema[key] = cls.infer_python_type(value)

        return inferred_schema

    @classmethod
    def infer_nested_object_schema(cls, nested_object: Dict[str, Any]) -> Dict[str, Union[str, Dict[str, Any], List[Any]]]:
        """**Recursively analyzes** nested objects to build complete schema definitions supporting deep nesting and mixed data types.

        Args:
            nested_object: Dictionary representing a nested object

        Returns:
            Schema definition for the nested object structure

        Example:
            ```python
            nested_object = {
                "ID", 1,
                "Metadata": {
                    "Timestamp": "2099-01-01 00:00:00"
                },
                "Tags": [
                    {"ID": 1, "Tag": "Developer"},
                    {"ID": 2, "Tag": "Tester"},
                    {"ID": 3, "Tag": "Admin"},
                ]
            }

            complex_schema = SchemaGenerator.infer_nested_object_schema(nested_object)
            # Returns {"ID": "int", "Metadata": {"Timestamp": "str"}, "Tags": [{"ID": "int", "Tag": "str"}]}
            ```
        """
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
        """**Analyzes array structure content** to determine if it contains primitives or nested objects, returning appropriate schema definitions.

        Args:
            array: List to analyze for schema inference

        Returns:
            Array schema definition, either `[primitive_type]` or `[{nested_object}]`

        Example:
            ```python
            SchemaGenerator.infer_array_schema([1, 2, 3])
            # Returns ["int"]

            SchemaGenerator.infer_array_schema([{"ID": 1}, {"ID": 2}, {"ID": 3}])
            # Returns [{"ID": "int"}]
            ```
        """
        if not array:
            return ["str"]  # Default fallback

        first_item: Any = array[0]

        if isinstance(first_item, dict):
            # Array of nested objects
            nested_schema: Dict[str, str | Dict[str, Any] | List[Any]] = cls.infer_nested_object_schema(first_item)
            return [nested_schema]
        else:
            # Array of primitives
            primitive_type: str = cls.infer_python_type(first_item)
            return [primitive_type]

    @classmethod
    def transform_nested_schema_recursively(cls, schema: Dict[str, Union[str, Dict[str, Any], List[Any]]], transformation_mode: str) -> Dict[str, Union[str, Dict[str, Any], List[Any]]]:
        """**Applies naming transformations** to all field names in a schema, including nested objects and array items (recursively), while preserving the schema structure.

        Args:
            schema: Schema definition to transform
            transformation_mode: Transformation type (lowercase, uppercase, snake_case, etc.)

        Returns:
            Transformed schema with updated field names

        Example:
            ```python
            schema = {
                "ID": "int",
                "Metadata": {
                    "Timestamp": "str"
                }
            }

            transformed_schema = SchemaGenerator.transform_nested_schema_recursively(schema, "lowercase")
            # Returns {"id": "int", "metadata": {"timestamp": "str"}}
            ```
        """
        transformed_schema: Dict[str, Union[str, Dict[str, Any], List[Any]]] = {}

        for key, value in schema.items():
            # Transform the key
            transformed_key: str = cls.transform_schema_key(key, transformation_mode)

            if isinstance(value, dict):
                # Recursively transform nested object schema
                transformed_schema[transformed_key] = cls.transform_nested_schema_recursively(value, transformation_mode)
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                # Transform array of nested objects schema
                transformed_array_item: Dict[str, str | Dict[str, Any] | List[Any]] = cls.transform_nested_schema_recursively(value[0], transformation_mode)
                transformed_schema[transformed_key] = [transformed_array_item]
            else:
                # Keep primitive types as-is
                transformed_schema[transformed_key] = value

        return transformed_schema

    @classmethod
    def transform_schema_key(cls, key: str, transformation_mode: str) -> str:
        """**Applies specific naming conventions** to schema field names using regex patterns for consistent transformation across different input formats.

        Args:
            key: Schema field name to transform
            transformation_mode: Type of transformation to apply

        Returns:
            Transformed schema field name

        Note:
            Snake case transformation also handles **complex cases** like consecutive capitals, numbers, and mixed casing with sophisticated regex patterns.

        Example:
            ```python
            SchemaGenerator.transform_schema_key("SchemaKey", "lowercase")
            # Returns "schemakey"

            SchemaGenerator.transform_schema_key("SchemaKey", "uppercase")
            # Returns "SCHEMAKEY"

            SchemaGenerator.transform_schema_key("SchemaKey", "snake_case")
            # Returns "schema_key"
            ```
        """
        return SchemaKeyTransformer.transform_key(key, transformation_mode)

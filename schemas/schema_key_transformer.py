"""Key transformation utilities for schema and data field name normalization."""

import re

from core import constants


class SchemaKeyTransformer:
    """Utility class for key transformation operations supporting multiple naming conventions."""

    @staticmethod
    def transform_key(key: str, transformation_mode: str) -> str:
        """Transform a key according to the specified mode.

        Args:
            key: The key name to transform
            transformation_mode: The transformation mode (lowercase, uppercase, snake_case, etc.)

        Returns:
            The transformed key string
        """
        if transformation_mode == constants.LOWERCASE_KEYS:
            return key.lower()
        if transformation_mode == constants.UPPERCASE_KEYS:
            return key.upper()
        if transformation_mode == constants.SNAKE_CASE_KEYS:
            # Handle sequences of capitals followed by lowercase (XMLParser -> XML_Parser)
            key = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', key)
            # Handle lowercase/digit followed by uppercase (camelCase -> camel_Case, test1Data -> test1_Data)
            key = re.sub(r'([a-z])([A-Z])', r'\1_\2', key)
            # Handle special cases with numbers (ID2Name -> ID2_Name)
            key = re.sub(r'([0-9])([A-Z])', r'\1_\2', key)
            return key.lower()
        if transformation_mode == constants.CAMEL_CASE_KEYS:
            # First convert to snake_case as intermediate format
            intermediate = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', key)
            intermediate = re.sub(r'([a-z])([A-Z])', r'\1_\2', intermediate)
            intermediate = re.sub(r'([0-9])([A-Z])', r'\1_\2', intermediate)
            # Now convert snake_case to camelCase
            parts = re.split(r'[_\s-]+', intermediate.lower())
            if not parts:
                return key
            # First part lowercase, rest title case
            result = parts[0]
            for part in parts[1:]:
                if part:
                    result += part[0].upper() + part[1:] if len(part) > 1 else part.upper()
            return result
        if transformation_mode == constants.PASCAL_CASE_KEYS:
            # First convert to snake_case as intermediate format
            intermediate = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', key)
            intermediate = re.sub(r'([a-z])([A-Z])', r'\1_\2', intermediate)
            intermediate = re.sub(r'([0-9])([A-Z])', r'\1_\2', intermediate)
            # Now convert snake_case to PascalCase
            parts = re.split(r'[_\s-]+', intermediate.lower())
            if not parts:
                return key
            # All parts title case
            result = ""
            for part in parts:
                if part:
                    result += part[0].upper() + part[1:] if len(part) > 1 else part.upper()
            return result
        else:
            return key

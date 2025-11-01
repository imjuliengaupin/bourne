"""**Manual Fallback Schema Generator**

Provides **hardcoded Pydantic models** as a fallback mechanism when dynamic schema generation fails, or for testing purposes with known data structures.

## Purpose

This module serves as a **safety net** when:
- Dynamic schema generation encounters errors
- Testing requires predictable model structures
- Validation needs to fall back to known schemas

## Models

- `FallbackRecordModel`: Individual record with predefined fields
- `FallbackRecordModelList`: Collection of FallbackRecord instances
"""

from typing import ClassVar, List

from pydantic import BaseModel, ConfigDict, Field, RootModel


class FallbackRecordModel(BaseModel):
    """Custom fallback record model with hardcoded fields for manual data validation. Provides a **predefined structure** for records containing fields with proper field aliasing and validation rules.

    Note:
        Uses **field aliases** to support both original casing and lowercase field names for flexible data input.

    Example:
        ```python
        # Create from dict with original casing for field names
        record = FallbackRecordModel(
            ID=1,
            Timestamp="2099-01-01 00:00:00"
        )

        # Create from dict with lowercase field names
        record = FallbackRecordModel(
            id=1,
            timestamp="2099-01-01 00:00:00"
        )
        ```
    """
    id: int = Field(alias="ID")
    timestamp: str = Field(alias="Timestamp")
    # NOTE: Add more fields as needed for manually testing specific connectors

    model_config: ClassVar[ConfigDict] = ConfigDict(
        populate_by_name=True,
    )


class FallbackRecordModelList(RootModel[List[FallbackRecordModel]]):
    """Collection wrapper for multiple FallbackRecordModel instances. Provides **list validation** and parsing for collections of fallback records, enabling batch processing and validation of multiple records at once.

    Note:
        Inherits from **[`RootModel`](https://docs.pydantic.dev/latest/api/root_model/#pydantic.root_model.RootModel)** to enable direct list validation while maintaining type safety and Pydantic's validation features.
    """

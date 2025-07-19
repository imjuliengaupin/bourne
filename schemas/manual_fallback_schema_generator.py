
from typing import ClassVar, List

from pydantic import BaseModel, ConfigDict, Field, RootModel


class FallbackRecord(BaseModel):
    id: int = Field(alias="ID")
    name: str = Field(alias="Name")
    timestamp: str = Field(alias="Timestamp")

    model_config: ClassVar[ConfigDict] = ConfigDict(
        populate_by_name=True,
    )


class FallbackRecordList(RootModel[List[FallbackRecord]]):
    pass

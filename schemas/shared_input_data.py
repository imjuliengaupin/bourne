
from typing import ClassVar, List

from pydantic import BaseModel, Field, RootModel


class Record(BaseModel):
    id: int = Field(alias='ID')
    name: str = Field(alias='Name')
    timestamp: str = Field(alias='Timestamp')

    model_config: ClassVar[dict] = {
        "populate_by_name": True,
    }


class RecordList(RootModel[List[Record]]):
    pass

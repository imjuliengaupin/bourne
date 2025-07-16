
from typing import List

from pydantic import BaseModel, ConfigDict, Field, RootModel


class Record(BaseModel):
    id: int = Field(alias="ID")
    name: str = Field(alias="Name")
    timestamp: str = Field(alias="Timestamp")

    model_config: ConfigDict = ConfigDict(
        populate_by_name=True,
    )


class RecordList(RootModel[List[Record]]):
    pass

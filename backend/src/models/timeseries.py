from pydantic import BaseModel, field_validator
from datetime import datetime
from enum import Enum


class StatusEnum(str, Enum):
    VORLAEUFIG = "V"
    ERSATZ = "E"
    WAHR = "W"


class TimeSeriesDataPoint(BaseModel):
    timestamp: datetime
    value: float
    status: StatusEnum

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_custom_datetime(cls, value):
        if isinstance(value, str):
            return datetime.strptime(value, "%d.%m.%Y %H:%M")
        return value


class TimeSeriesCreate(BaseModel):
    name: str
    data: list[TimeSeriesDataPoint]


class TimeSeriesRead(BaseModel):
    id: int
    name: str
    data_count: int
    data: list[TimeSeriesDataPoint] = []

from pydantic import BaseModel
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


class TimeSeriesCreate(BaseModel):
    name: str
    data: list[TimeSeriesDataPoint]


class TimeSeriesRead(BaseModel):
    id: int
    name: str
    data_count: int
    next_cursor: datetime | None = None
    data: list[TimeSeriesDataPoint] = []


class TimeSeriesListItem(BaseModel):
    id: int
    name: str


class TimeSeriesListResponse(BaseModel):
    total: int
    items: list[TimeSeriesListItem]


class TimeSeriesAppend(BaseModel):
    data: list[TimeSeriesDataPoint]


class TimeSeriesAppendResponse(BaseModel):
    appended_count: int

from fastapi import APIRouter, Depends, HTTPException, Query, status
from datetime import datetime

from src.core.security import get_current_user
from src.services.timeseries_service import TimeSeriesService
from src.models.timeseries import (
    TimeSeriesCreate,
    TimeSeriesDataPoint,
    TimeSeriesRead,
    TimeSeriesListItem,
    TimeSeriesListResponse,
    TimeSeriesAppend,
    TimeSeriesAppendResponse,
)
from src.db.schema import AsyncSessionLocal

import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/timeseries",
    tags=["timeseries"],
    dependencies=[Depends(get_current_user)],
)


async def get_timeseries_service():
    async with AsyncSessionLocal() as session:
        try:
            yield TimeSeriesService(session)
            await session.commit()  # ← commit after the endpoint returns
        except Exception:
            await session.rollback()  # ← rollback on any error
            raise
        finally:
            await session.close()


@router.get("/", response_model=TimeSeriesListResponse)
async def list_timeseries(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    service: TimeSeriesService = Depends(get_timeseries_service),
):
    """List all timeseries with pagination."""
    total, rows = await service.list_timeseries(offset=offset, limit=limit)
    return TimeSeriesListResponse(
        total=total,
        items=[TimeSeriesListItem(id=row.id, name=row.name) for row in rows],
    )


@router.post("/", response_model=TimeSeriesRead, status_code=status.HTTP_201_CREATED)
async def create_timeseries(
    timeseries: TimeSeriesCreate,
    service: TimeSeriesService = Depends(get_timeseries_service),
):
    """Create a new timeseries and optionally insert initial data points."""
    ts = await service.create_timeseries(name=timeseries.name, data=timeseries.data)
    return TimeSeriesRead(id=ts.id, name=ts.name, data_count=len(timeseries.data))


@router.post(
    "/{timeseries_id}/data",
    response_model=TimeSeriesAppendResponse,
    status_code=status.HTTP_200_OK,
)
async def append_timeseries(
    timeseries_id: int,
    timeseries: TimeSeriesAppend,
    service: TimeSeriesService = Depends(get_timeseries_service),
):
    """Append data points to an existing timeseries."""
    appended = await service.append_timeseries_data(timeseries_id, timeseries.data)
    if appended is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Timeseries not found"
        )
    return TimeSeriesAppendResponse(appended_count=appended)


@router.get("/{timeseries_id}", response_model=TimeSeriesRead)
async def get_timeseries(
    timeseries_id: int,
    after: datetime | None = Query(default=None),
    limit: int = Query(default=1000, ge=1, le=10000),
    service: TimeSeriesService = Depends(get_timeseries_service),
):
    """Retrieve a timeseries with its data points. Supports keyset pagination via `after` and `limit`."""
    result = await service.get_timeseries(timeseries_id, after=after, limit=limit)
    if result is None:
        raise HTTPException(
            status_code=404, detail=f"Timeseries {timeseries_id} not found"
        )
    ts, data = result
    next_cursor = data[-1].timestamp if len(data) == limit else None
    return TimeSeriesRead(
        id=ts.id,
        name=ts.name,
        data_count=len(data),
        next_cursor=next_cursor,
        data=[
            TimeSeriesDataPoint(timestamp=d.timestamp, value=d.value, status=d.status)
            for d in data
        ],
    )


@router.delete("/{timeseries_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_timeseries(
    timeseries_id: int,
    service: TimeSeriesService = Depends(get_timeseries_service),
):
    """Delete a timeseries and all its data points."""
    deleted = await service.delete_timeseries(timeseries_id=timeseries_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Timeseries not found"
        )

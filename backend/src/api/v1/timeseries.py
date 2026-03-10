from fastapi import APIRouter, Depends, HTTPException, status

from src.core.security import get_current_user
from src.services.timeseries_service import TimeSeriesService
from src.models.timeseries import (
    TimeSeriesCreate,
    TimeSeriesDataPoint,
    TimeSeriesRead,
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


@router.post("/", response_model=TimeSeriesRead, status_code=status.HTTP_201_CREATED)
async def create_timeseries(
    timeseries: TimeSeriesCreate,
    service: TimeSeriesService = Depends(get_timeseries_service),
):
    ts = await service.create_timeseries(name=timeseries.name, data=timeseries.data)
    return TimeSeriesRead(id=ts.id, name=ts.name, data_count=len(timeseries.data))


@router.get("/{timeseries_id}", response_model=TimeSeriesRead)
async def get_timeseries(
    timeseries_id: int,
    service: TimeSeriesService = Depends(get_timeseries_service),
):
    result = await service.get_timeseries(timeseries_id)
    if result is None:
        raise HTTPException(
            status_code=404, detail=f"Timeseries {timeseries_id} not found"
        )
    ts, data = result
    return TimeSeriesRead(
        id=ts.id,
        name=ts.name,
        data_count=len(data),
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
    deleted = await service.delete_timeseries(timeseries_id=timeseries_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Timeseries not found"
        )

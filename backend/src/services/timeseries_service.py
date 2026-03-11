from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, exists, func
from datetime import datetime
from sqlalchemy.dialects.postgresql import insert
from src.db.models.timeseries import TimeSeries, TimeSeriesData
from src.models.timeseries import TimeSeriesDataPoint

import logging

logger = logging.getLogger(__name__)


class TimeSeriesService:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def timeseries_exists(self, timeseries_id: int) -> bool:
        return await self._session.scalar(
            select(exists().where(TimeSeries.id == timeseries_id))
        )

    async def create_timeseries(
        self, name: str, data: list[TimeSeriesDataPoint] | None = None
    ) -> TimeSeries:
        result = await self._session.execute(
            insert(TimeSeries)
            .values(name=name)
            .on_conflict_do_nothing(index_elements=["name"])
            .returning(TimeSeries)
        )
        ts = result.scalar_one_or_none()

        if ts is None:
            # Already exists, fetch it
            ts = await self._session.scalar(
                select(TimeSeries).where(TimeSeries.name == name)
            )

        if ts is None:
            raise RuntimeError(f"Failed to create or fetch timeseries '{name}'")

        if data:
            await self._session.execute(
                insert(TimeSeriesData),
                [
                    {
                        "timeseries_id": ts.id,
                        "timestamp": dp.timestamp,
                        "value": dp.value,
                        "status": dp.status,
                    }
                    for dp in data
                ],
            )

        return ts

    async def get_timeseries(
        self,
        timeseries_id: int,
        after: datetime | None = None,
        before: datetime | None = None,
        limit: int = 1000,
    ) -> tuple[TimeSeries, list[TimeSeriesData]] | None:
        ts = await self._session.scalar(
            select(TimeSeries).where(TimeSeries.id == timeseries_id)
        )
        if ts is None:
            return None
        query = (
            select(TimeSeriesData)
            .distinct(TimeSeriesData.timestamp)
            .where(TimeSeriesData.timeseries_id == timeseries_id)
            .order_by(TimeSeriesData.timestamp, TimeSeriesData.created_at.desc())
            .limit(limit)
        )
        if after is not None:
            query = query.where(TimeSeriesData.timestamp > after)
        if before is not None:
            query = query.where(TimeSeriesData.timestamp < before)
        result = await self._session.execute(query)
        data = result.scalars().all()
        return ts, data

    async def list_timeseries(
        self, offset: int = 0, limit: int = 50
    ) -> tuple[int, list]:
        total = await self._session.scalar(select(func.count()).select_from(TimeSeries))
        result = await self._session.execute(
            # Comment: discard the skipped rows, so it gets slower as offset grows
            select(TimeSeries.id, TimeSeries.name)
            .offset(offset)
            .limit(limit)
        )
        return total, result.all()

    async def append_timeseries_data(
        self, timeseries_id: int, data: list[TimeSeriesDataPoint]
    ) -> int | None:
        if not await self.timeseries_exists(timeseries_id):
            return None
        await self._session.execute(
            insert(TimeSeriesData),
            [
                {
                    "timeseries_id": timeseries_id,
                    "timestamp": dp.timestamp,
                    "value": dp.value,
                    "status": dp.status,
                }
                for dp in data
            ],
        )
        return len(data)

    async def delete_timeseries(self, timeseries_id: int) -> bool:
        if not await self.timeseries_exists(timeseries_id):
            return False
        # delete timeseries data
        await self._session.execute(
            delete(TimeSeriesData).where(TimeSeriesData.timeseries_id == timeseries_id)
        )
        # delete timeseries
        await self._session.execute(
            delete(TimeSeries).where(TimeSeries.id == timeseries_id)
        )
        return True

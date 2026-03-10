from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, exists
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
        self, timeseries_id: int
    ) -> tuple[TimeSeries, list[TimeSeriesData]] | None:
        ts = await self._session.scalar(
            select(TimeSeries).where(TimeSeries.id == timeseries_id)
        )
        if ts is None:
            return None
        result = await self._session.execute(
            select(TimeSeriesData)
            .distinct(TimeSeriesData.timestamp)
            .where(TimeSeriesData.timeseries_id == timeseries_id)
            .order_by(TimeSeriesData.timestamp, TimeSeriesData.created_at.desc())
        )
        data = result.scalars().all()
        return ts, data

    async def update_timeseries(
        self, timeseries_id: int, updates: dict
    ) -> TimeSeries | None:
        ts = await self.get_timeseries(timeseries_id)
        if ts is None:
            return None
        for key, value in updates.items():
            setattr(ts, key, value)
        return ts

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

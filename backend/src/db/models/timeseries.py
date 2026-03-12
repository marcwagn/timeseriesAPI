from datetime import datetime
from sqlalchemy import DateTime
from sqlalchemy import text


from sqlalchemy import (
    ForeignKeyConstraint,
    String,
    Sequence,
    PrimaryKeyConstraint,
    UniqueConstraint,
    Enum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.schema import Base
from src.models.timeseries import StatusEnum


class TimeSeries(Base):
    __tablename__ = "timeseries"

    id: Mapped[int] = mapped_column(Sequence("timeseries_id_seq"))
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(String(100))
    owner_id: Mapped[int] = mapped_column(nullable=False)

    data: Mapped[list["TimeSeriesData"]] = relationship("TimeSeriesData", lazy="noload")

    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_timeseries_id"),
        UniqueConstraint("name", name="uq_timeseries_name"),
        ForeignKeyConstraint(["owner_id"], ["users.id"], name="fk_timeseries_owner_id"),
    )


class TimeSeriesData(Base):
    __tablename__ = "timeseries_data"

    id: Mapped[int] = mapped_column(Sequence("timeseries_data_id_seq"))
    timeseries_id: Mapped[int] = mapped_column()
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    value: Mapped[float] = mapped_column(nullable=False)
    status: Mapped[StatusEnum] = mapped_column(String(1), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("clock_timestamp()"), nullable=False
    )

    __table_args__ = (
        PrimaryKeyConstraint("id", "timestamp", name="pk_timeseries_data_id"),
        ForeignKeyConstraint(
            ["timeseries_id"],
            ["timeseries.id"],
            name="fk_timeseries_data_timeseries_id",
        ),
        {
            "timescaledb_hypertable": {
                "time_column_name": "timestamp",
                "chunk_time_interval": "1 day",
                "partitioning_column": "timeseries_id",
            }
        },
    )

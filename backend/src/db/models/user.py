from datetime import datetime

from sqlalchemy import Boolean, DateTime, PrimaryKeyConstraint, Sequence, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.schema import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Sequence("users_id_seq"))
    username: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=text("clock_timestamp()"), nullable=False
    )

    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_users_id"),
        UniqueConstraint("username", name="uq_users_username"),
        UniqueConstraint("email", name="uq_users_email"),
    )

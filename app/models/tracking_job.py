from datetime import date, datetime

from pydantic import Field
from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class TrackingJob(Base):
    __tablename__ = "tracking_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    movie_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    target_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    platform: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    city: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    theater: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    theater_id: Mapped[int | None] = mapped_column(
        ForeignKey("theaters.id"),
        nullable=True,
    )

    target_date: Mapped[date] = mapped_column(
    Date,
    nullable=False,
)

    start_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    end_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    poll_interval_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=60,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PENDING",
    )

    created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    nullable=False,
    server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    last_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_result_json: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    user = relationship("User", back_populates="tracking_jobs")

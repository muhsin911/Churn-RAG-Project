"""SQLAlchemy table for source profiles, predictions, and actual outcomes."""

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class CustomerRecord(Base):
    """One customer profile with separate predicted and observed churn values."""

    __tablename__ = "customers"
    __table_args__ = (
        CheckConstraint("tenure >= 0 AND tenure <= 120", name="ck_customer_tenure"),
        CheckConstraint(
            "monthly_charges >= 0 AND total_charges >= 0",
            name="ck_customer_charges",
        ),
    )

    customer_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenure: Mapped[int] = mapped_column(Integer, nullable=False)
    monthly_charges: Mapped[float] = mapped_column(Float, nullable=False)
    total_charges: Mapped[float] = mapped_column(Float, nullable=False)
    contract_type: Mapped[str] = mapped_column(String(32), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(32), nullable=False)
    gender: Mapped[str | None] = mapped_column(String(16))
    senior_citizen: Mapped[int | None] = mapped_column(Integer)
    partner: Mapped[str | None] = mapped_column(String(24))
    dependents: Mapped[str | None] = mapped_column(String(24))
    phone_service: Mapped[str | None] = mapped_column(String(24))
    multiple_lines: Mapped[str | None] = mapped_column(String(32))
    internet_service: Mapped[str | None] = mapped_column(String(24))
    online_security: Mapped[str | None] = mapped_column(String(32))
    online_backup: Mapped[str | None] = mapped_column(String(32))
    device_protection: Mapped[str | None] = mapped_column(String(32))
    tech_support: Mapped[str | None] = mapped_column(String(32))
    streaming_tv: Mapped[str | None] = mapped_column(String(32))
    streaming_movies: Mapped[str | None] = mapped_column(String(32))
    paperless_billing: Mapped[str | None] = mapped_column(String(24))
    actual_churn: Mapped[bool | None] = mapped_column(Boolean)
    predicted_churn: Mapped[bool | None] = mapped_column(Boolean)
    churn_probability: Mapped[float | None] = mapped_column(Float)
    record_source: Mapped[str] = mapped_column(String(24), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

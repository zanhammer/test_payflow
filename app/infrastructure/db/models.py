from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class PaymentModel(Base):
    __tablename__ = "payments"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=2),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, server_default="{}"
    )

    status: Mapped[str] = mapped_column(String(20), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True
    )
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    webhook_url: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class OutboxEventModel(Base):
    __tablename__ = "outbox_events"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    aggregate_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("payments.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    published: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index(
            "ix_outbox_events_unpublished",
            "published",
            postgresql_where="published = false",
        ),
    )

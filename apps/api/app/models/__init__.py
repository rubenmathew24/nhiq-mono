"""SQLAlchemy ORM models for auth and saved lookups."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    # DB column is hashed_password; app code uses password_hash
    password_hash: Mapped[Optional[str]] = mapped_column("hashed_password", Text)
    full_name: Mapped[Optional[str]] = mapped_column(Text)
    tier: Mapped[str] = mapped_column(Text, default="free")
    lookup_count_this_month: Mapped[int] = mapped_column(Integer, default=0)
    billing_cycle_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(Text)
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    saved_lookups: Mapped[list["SavedLookup"]] = relationship(back_populates="user")


class AddressLookup(Base):
    __tablename__ = "address_lookups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    address_raw: Mapped[str] = mapped_column(Text, nullable=False)
    address_normalized: Mapped[Optional[str]] = mapped_column(Text)
    latitude: Mapped[Optional[float]] = mapped_column(Numeric(10, 7))
    longitude: Mapped[Optional[float]] = mapped_column(Numeric(10, 7))
    geoid: Mapped[Optional[str]] = mapped_column(Text)
    lookup_count: Mapped[int] = mapped_column(Integer, default=1)
    first_looked_up_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_looked_up_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    saved_lookups: Mapped[list["SavedLookup"]] = relationship(back_populates="address_lookup")


class SavedLookup(Base):
    __tablename__ = "saved_lookups"
    __table_args__ = (UniqueConstraint("user_id", "address_lookup_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    address_lookup_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("address_lookups.id")
    )
    label: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="saved_lookups")
    address_lookup: Mapped["AddressLookup"] = relationship(back_populates="saved_lookups")

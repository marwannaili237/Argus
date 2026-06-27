from sqlalchemy import String, Integer, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import mapped_column, Mapped, relationship
from datetime import datetime, timezone
from database import Base


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    investigations: Mapped[list["Investigation"]] = relationship(back_populates="user")
    monitors: Mapped[list["Monitor"]] = relationship(back_populates="user")


class Investigation(Base):
    __tablename__ = "investigations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    target: Mapped[str] = mapped_column(String(512), nullable=False)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    telegram_chat_id: Mapped[int] = mapped_column(Integer, nullable=True)
    telegram_message_id: Mapped[int] = mapped_column(Integer, nullable=True)

    user: Mapped["User"] = relationship(back_populates="investigations")
    evidence: Mapped[list["Evidence"]] = relationship(back_populates="investigation", cascade="all, delete-orphan")


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    investigation_id: Mapped[int] = mapped_column(Integer, ForeignKey("investigations.id"), nullable=False)
    plugin_name: Mapped[str] = mapped_column(String(64), nullable=False)
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    investigation: Mapped["Investigation"] = relationship(back_populates="evidence")


class Monitor(Base):
    __tablename__ = "monitors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    target: Mapped[str] = mapped_column(String(512), nullable=False)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    telegram_chat_id: Mapped[int] = mapped_column(Integer, nullable=False)
    schedule: Mapped[str] = mapped_column(String(16), default="daily")   # hourly | daily | weekly
    interval_hours: Mapped[int] = mapped_column(Integer, default=24)
    last_checked: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    next_check: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_hash: Mapped[str] = mapped_column(String(64), nullable=True)
    last_investigation_id: Mapped[int] = mapped_column(Integer, nullable=True)
    change_count: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    user: Mapped["User"] = relationship(back_populates="monitors")

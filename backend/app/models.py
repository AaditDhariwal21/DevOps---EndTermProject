from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    requester_email: Mapped[str] = mapped_column(String(254), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False, default="other")
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium", index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open", index=True)
    assignee: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class TicketActivity(Base):
    """Append-only audit log that powers the dashboard activity feed."""

    __tablename__ = "ticket_activity"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # SET NULL (not CASCADE) so the history survives ticket deletion.
    ticket_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("tickets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    ticket_title: Mapped[str] = mapped_column(String(200), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    detail: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

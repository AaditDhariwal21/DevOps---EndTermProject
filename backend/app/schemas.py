from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Status(StrEnum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"


class Priority(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class Category(StrEnum):
    bug = "bug"
    billing = "billing"
    account = "account"
    feature = "feature"
    other = "other"


class TicketBase(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(default="", max_length=5000)
    requester_email: EmailStr
    category: Category = Category.other
    priority: Priority = Priority.medium
    assignee: str | None = Field(default=None, max_length=100)


class TicketCreate(TicketBase):
    status: Status = Status.open


class TicketUpdate(BaseModel):
    """Partial update: only the fields sent by the client are changed."""

    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    requester_email: EmailStr | None = None
    category: Category | None = None
    priority: Priority | None = None
    status: Status | None = None
    assignee: str | None = Field(default=None, max_length=100)


class TicketRead(TicketBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: Status
    created_at: datetime
    updated_at: datetime


class TicketList(BaseModel):
    total: int
    items: list[TicketRead]


class TicketStats(BaseModel):
    total: int
    by_status: dict[str, int]
    by_priority: dict[str, int]
    by_category: dict[str, int]
    open_urgent: int
    unassigned: int
    resolution_rate: float


class ActivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int | None
    ticket_title: str
    action: str
    detail: str
    created_at: datetime


class SystemInfo(BaseModel):
    app: str
    version: str
    git_sha: str
    environment: str
    database: str

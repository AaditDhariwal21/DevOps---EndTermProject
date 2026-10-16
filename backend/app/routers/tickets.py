from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from prometheus_client import Counter
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Ticket, TicketActivity
from app.schemas import (
    Category,
    Priority,
    Status,
    TicketCreate,
    TicketList,
    TicketRead,
    TicketStats,
    TicketUpdate,
)

router = APIRouter(prefix="/api/tickets", tags=["tickets"])

# Business metric, scraped by Prometheus alongside the HTTP metrics.
TICKETS_CREATED = Counter(
    "deskflow_tickets_created_total", "Tickets created, by priority", ["priority"]
)


def _log(db: Session, ticket: Ticket, action: str, detail: str = "") -> None:
    db.add(
        TicketActivity(ticket_id=ticket.id, ticket_title=ticket.title, action=action, detail=detail)
    )


def _get_or_404(db: Session, ticket_id: int) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    return ticket


@router.get("", response_model=TicketList)
def list_tickets(
    status_filter: Status | None = Query(default=None, alias="status"),
    priority: Priority | None = None,
    category: Category | None = None,
    unassigned: bool = False,
    q: str | None = Query(default=None, max_length=100, description="Search title/requester"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> TicketList:
    stmt = select(Ticket)
    if status_filter:
        stmt = stmt.where(Ticket.status == status_filter.value)
    if priority:
        stmt = stmt.where(Ticket.priority == priority.value)
    if category:
        stmt = stmt.where(Ticket.category == category.value)
    if unassigned:
        stmt = stmt.where(Ticket.assignee.is_(None))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Ticket.title.ilike(like), Ticket.requester_email.ilike(like)))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Ticket.created_at.desc(), Ticket.id.desc()).limit(limit).offset(offset)
    ).all()
    return TicketList(total=total, items=[TicketRead.model_validate(t) for t in rows])


# Declared before /{ticket_id} so "stats" is not parsed as an id.
@router.get("/stats", response_model=TicketStats)
def ticket_stats(db: Session = Depends(get_db)) -> TicketStats:
    def grouped(column) -> dict[str, int]:
        return {k: v for k, v in db.execute(select(column, func.count()).group_by(column)).all()}

    by_status = {s.value: 0 for s in Status} | grouped(Ticket.status)
    by_priority = {p.value: 0 for p in Priority} | grouped(Ticket.priority)
    by_category = {c.value: 0 for c in Category} | grouped(Ticket.category)
    total = sum(by_status.values())

    open_states = (Status.open.value, Status.in_progress.value)
    open_urgent = db.scalar(
        select(func.count()).where(
            Ticket.priority == Priority.urgent.value, Ticket.status.in_(open_states)
        )
    )
    unassigned = db.scalar(
        select(func.count()).where(Ticket.assignee.is_(None), Ticket.status.in_(open_states))
    )
    done = by_status[Status.resolved.value] + by_status[Status.closed.value]

    return TicketStats(
        total=total,
        by_status=by_status,
        by_priority=by_priority,
        by_category=by_category,
        open_urgent=open_urgent or 0,
        unassigned=unassigned or 0,
        resolution_rate=round(done / total * 100, 1) if total else 0.0,
    )


@router.get("/{ticket_id}", response_model=TicketRead)
def get_ticket(ticket_id: int, db: Session = Depends(get_db)) -> Ticket:
    return _get_or_404(db, ticket_id)


@router.post("", response_model=TicketRead, status_code=status.HTTP_201_CREATED)
def create_ticket(payload: TicketCreate, db: Session = Depends(get_db)) -> Ticket:
    ticket = Ticket(**payload.model_dump(mode="json"))
    db.add(ticket)
    db.flush()  # assigns ticket.id for the activity entry
    _log(db, ticket, "created", f"{ticket.priority} priority · {ticket.category}")
    db.commit()
    db.refresh(ticket)
    TICKETS_CREATED.labels(priority=ticket.priority).inc()
    return ticket


@router.put("/{ticket_id}", response_model=TicketRead)
def update_ticket(ticket_id: int, payload: TicketUpdate, db: Session = Depends(get_db)) -> Ticket:
    ticket = _get_or_404(db, ticket_id)
    changes = payload.model_dump(mode="json", exclude_unset=True)

    changed = []
    for field, value in changes.items():
        if field != "assignee" and value is None:
            continue  # only assignee may be cleared explicitly
        if getattr(ticket, field) != value:
            changed.append(field)
            setattr(ticket, field, value)

    if changed:
        if "status" in changed:
            detail = f"status → {ticket.status}"
        elif "assignee" in changed:
            detail = f"assigned to {ticket.assignee}" if ticket.assignee else "unassigned"
        else:
            detail = "updated " + ", ".join(changed)
        _log(db, ticket, "updated", detail)
        db.commit()
        db.refresh(ticket)
    return ticket


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ticket(ticket_id: int, db: Session = Depends(get_db)) -> Response:
    ticket = _get_or_404(db, ticket_id)
    _log(db, ticket, "deleted")
    db.delete(ticket)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

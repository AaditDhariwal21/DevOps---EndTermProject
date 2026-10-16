from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import TicketActivity
from app.schemas import ActivityRead

router = APIRouter(prefix="/api/activity", tags=["activity"])


@router.get("", response_model=list[ActivityRead])
def recent_activity(
    limit: int = Query(default=15, ge=1, le=100), db: Session = Depends(get_db)
) -> list[TicketActivity]:
    stmt = select(TicketActivity).order_by(
        TicketActivity.created_at.desc(), TicketActivity.id.desc()
    )
    return list(db.scalars(stmt.limit(limit)).all())

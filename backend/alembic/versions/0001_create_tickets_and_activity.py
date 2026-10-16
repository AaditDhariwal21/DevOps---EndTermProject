"""create tickets and ticket_activity tables

Revision ID: 0001
Revises:
Create Date: 2026-10-16
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tickets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("requester_email", sa.String(254), nullable=False),
        sa.Column("category", sa.String(20), nullable=False, server_default="other"),
        sa.Column("priority", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("assignee", sa.String(100), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "status IN ('open','in_progress','resolved','closed')", name="ck_tickets_status"
        ),
        sa.CheckConstraint(
            "priority IN ('low','medium','high','urgent')", name="ck_tickets_priority"
        ),
        sa.CheckConstraint(
            "category IN ('bug','billing','account','feature','other')", name="ck_tickets_category"
        ),
    )
    op.create_index("ix_tickets_status", "tickets", ["status"])
    op.create_index("ix_tickets_priority", "tickets", ["priority"])

    op.create_table(
        "ticket_activity",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "ticket_id",
            sa.Integer(),
            sa.ForeignKey("tickets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("ticket_title", sa.String(200), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("detail", sa.String(300), nullable=False, server_default=""),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_ticket_activity_ticket_id", "ticket_activity", ["ticket_id"])
    op.create_index("ix_ticket_activity_created_at", "ticket_activity", ["created_at"])


def downgrade() -> None:
    op.drop_table("ticket_activity")
    op.drop_table("tickets")

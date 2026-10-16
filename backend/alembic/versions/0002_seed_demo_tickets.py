"""seed demo tickets so a fresh environment has data to show

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-16
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEMO_TICKETS = [
    ("Checkout page returns 500 on coupon apply", "bug", "urgent", "in_progress", "Aadit",
     "ops@brightcart.in", "Applying SAVE20 throws a server error for every customer."),
    ("Charged twice for October subscription", "billing", "high", "open", None,
     "rahul.m@finlytics.io", "Two identical debits on the same card."),
    ("SSO login loops back to sign-in page", "account", "urgent", "open", None,
     "it-admin@northwind.co", "Okta SSO redirects forever since this morning."),
    ("Export tickets to CSV", "feature", "low", "open", None,
     "maya@studio9.design", "We need a CSV export for our monthly report."),
    ("Reset 2FA for departed employee", "account", "medium", "resolved", "Neha",
     "hr@greenleaf.org", "Account owner left the company."),
    ("Invoice shows wrong GST number", "billing", "medium", "in_progress", "Neha",
     "accounts@kiranstores.in", "GSTIN on invoice INV-2291 is outdated."),
    ("Dashboard charts load slowly", "bug", "high", "open", "Aadit",
     "cto@quickhire.app", "Takes ~8s to render the analytics tab."),
    ("Add Slack notifications for new tickets", "feature", "medium", "closed", "Sam",
     "support@pixelforge.gg", "Shipped in v1.4."),
]


def upgrade() -> None:
    tickets = sa.table(
        "tickets",
        sa.column("title", sa.String),
        sa.column("description", sa.Text),
        sa.column("requester_email", sa.String),
        sa.column("category", sa.String),
        sa.column("priority", sa.String),
        sa.column("status", sa.String),
        sa.column("assignee", sa.String),
    )
    activity = sa.table(
        "ticket_activity",
        sa.column("ticket_id", sa.Integer),
        sa.column("ticket_title", sa.String),
        sa.column("action", sa.String),
        sa.column("detail", sa.String),
    )
    conn = op.get_bind()
    for title, category, priority, status, assignee, email, description in DEMO_TICKETS:
        ticket_id = conn.execute(
            tickets.insert()
            .values(
                title=title,
                description=description,
                requester_email=email,
                category=category,
                priority=priority,
                status=status,
                assignee=assignee,
            )
            .returning(sa.literal_column("id"))
        ).scalar_one()
        conn.execute(
            activity.insert().values(
                ticket_id=ticket_id,
                ticket_title=title,
                action="created",
                detail=f"{priority} priority · {category}",
            )
        )


def downgrade() -> None:
    titles = [t[0] for t in DEMO_TICKETS]
    op.execute(
        sa.text("DELETE FROM ticket_activity WHERE ticket_title = ANY(:t)").bindparams(t=titles)
    )
    op.execute(sa.text("DELETE FROM tickets WHERE title = ANY(:t)").bindparams(t=titles))

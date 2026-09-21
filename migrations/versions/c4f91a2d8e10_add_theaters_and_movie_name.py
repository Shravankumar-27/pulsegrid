"""add theaters and movie_name on jobs

Revision ID: c4f91a2d8e10
Revises: 8832834c0234
Create Date: 2026-09-21 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4f91a2d8e10"
down_revision: Union[str, Sequence[str], None] = "8832834c0234"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "theaters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("bookmyshow_venue_id", sa.String(length=100), nullable=True),
        sa.Column("district_venue_id", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "name",
            "city",
            name="uq_theaters_user_name_city",
        ),
    )
    op.create_index(
        op.f("ix_theaters_user_id"),
        "theaters",
        ["user_id"],
        unique=False,
    )

    op.add_column(
        "tracking_jobs",
        sa.Column("movie_name", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "tracking_jobs",
        sa.Column("theater_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_tracking_jobs_theater_id",
        "tracking_jobs",
        "theaters",
        ["theater_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_tracking_jobs_theater_id",
        "tracking_jobs",
        type_="foreignkey",
    )
    op.drop_column("tracking_jobs", "theater_id")
    op.drop_column("tracking_jobs", "movie_name")
    op.drop_index(op.f("ix_theaters_user_id"), table_name="theaters")
    op.drop_table("theaters")

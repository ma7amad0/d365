"""Identity, authorization, audit, and D365 configuration foundation.

Revision ID: 0001
Revises:
Create Date: 2026-08-21
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
        "employee_identity_mapping",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("entra_oid", sa.String(64)),
        sa.Column("entra_upn", sa.String(320)),
        sa.Column("entra_email", sa.String(320)),
        sa.Column("d365_personnel_number", sa.String(64), nullable=False),
        sa.Column("d365_worker_id", sa.String(128)),
        sa.Column("d365_company", sa.String(32)),
        sa.Column("mapping_source", sa.String(32), nullable=False),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entra_oid", name="uq_identity_mapping_entra_oid"),
    )
    op.create_index(
        "ix_identity_mapping_personnel_company",
        "employee_identity_mapping",
        ["d365_personnel_number", "d365_company"],
    )
    op.create_table(
        "employee_identity_mapping_history",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("mapping_id", sa.Uuid(), nullable=False),
        sa.Column(
            "changed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("changed_by_oid", sa.String(64), nullable=False),
        sa.Column("change_type", sa.String(32), nullable=False),
        sa.Column("before_values", sa.JSON()),
        sa.Column("after_values", sa.JSON()),
        sa.ForeignKeyConstraint(
            ["mapping_id"], ["employee_identity_mapping.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "user_role_assignment",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("entra_oid", sa.String(64), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("assigned_by_oid", sa.String(64)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entra_oid", "role", name="uq_user_role_assignment"),
    )
    op.create_index("ix_user_role_assignment_entra_oid", "user_role_assignment", ["entra_oid"])
    op.create_table(
        "audit_event",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("entra_oid", sa.String(64)),
        sa.Column("user_upn", sa.String(320)),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("resource", sa.String(256), nullable=False),
        sa.Column("target_employee", sa.String(64)),
        sa.Column("client_ip", sa.String(64)),
        sa.Column("user_agent", sa.String(512)),
        sa.Column("result", sa.String(32), nullable=False),
        sa.Column("correlation_id", sa.String(128), nullable=False),
        sa.Column("details", sa.JSON()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_event_entra_oid", "audit_event", ["entra_oid"])
    op.create_index("ix_audit_event_correlation_id", "audit_event", ["correlation_id"])
    op.create_index("ix_audit_timestamp_action", "audit_event", ["timestamp", "action"])
    op.create_table(
        "portal_setting",
        sa.Column("key", sa.String(128), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("sensitive", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_table(
        "d365_entity_mapping",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("mapping_key", sa.String(64), nullable=False),
        sa.Column("entity_name", sa.String(128), nullable=False),
        sa.Column("personnel_number_field", sa.String(128)),
        sa.Column("company_field", sa.String(128)),
        sa.Column("email_field", sa.String(128)),
        sa.Column("position_field", sa.String(128)),
        sa.Column("department_field", sa.String(128)),
        sa.Column("manager_field", sa.String(128)),
        sa.Column("field_mapping", sa.JSON(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("metadata_confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("metadata_environment", sa.String(512)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("mapping_key"),
    )


def downgrade() -> None:
    op.drop_table("d365_entity_mapping")
    op.drop_table("portal_setting")
    op.drop_index("ix_audit_timestamp_action", table_name="audit_event")
    op.drop_index("ix_audit_event_correlation_id", table_name="audit_event")
    op.drop_index("ix_audit_event_entra_oid", table_name="audit_event")
    op.drop_table("audit_event")
    op.drop_index("ix_user_role_assignment_entra_oid", table_name="user_role_assignment")
    op.drop_table("user_role_assignment")
    op.drop_table("employee_identity_mapping_history")
    op.drop_index("ix_identity_mapping_personnel_company", table_name="employee_identity_mapping")
    op.drop_table("employee_identity_mapping")

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class EmployeeIdentityMapping(TimestampMixin, Base):
    __tablename__ = "employee_identity_mapping"
    __table_args__ = (
        UniqueConstraint("entra_oid", name="uq_identity_mapping_entra_oid"),
        Index("ix_identity_mapping_personnel_company", "d365_personnel_number", "d365_company"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    entra_oid: Mapped[str | None] = mapped_column(String(64))
    entra_upn: Mapped[str | None] = mapped_column(String(320))
    entra_email: Mapped[str | None] = mapped_column(String(320))
    d365_personnel_number: Mapped[str] = mapped_column(String(64), nullable=False)
    d365_worker_id: Mapped[str | None] = mapped_column(String(128))
    d365_company: Mapped[str | None] = mapped_column(String(32))
    mapping_source: Mapped[str] = mapped_column(String(32), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class EmployeeIdentityMappingHistory(Base):
    __tablename__ = "employee_identity_mapping_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    mapping_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("employee_identity_mapping.id", ondelete="RESTRICT"), nullable=False
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    changed_by_oid: Mapped[str] = mapped_column(String(64), nullable=False)
    change_type: Mapped[str] = mapped_column(String(32), nullable=False)
    before_values: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    after_values: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class UserRoleAssignment(TimestampMixin, Base):
    __tablename__ = "user_role_assignment"
    __table_args__ = (UniqueConstraint("entra_oid", "role", name="uq_user_role_assignment"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    entra_oid: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    assigned_by_oid: Mapped[str | None] = mapped_column(String(64))


class AuditEvent(Base):
    __tablename__ = "audit_event"
    __table_args__ = (Index("ix_audit_timestamp_action", "timestamp", "action"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    entra_oid: Mapped[str | None] = mapped_column(String(64), index=True)
    user_upn: Mapped[str | None] = mapped_column(String(320))
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    resource: Mapped[str] = mapped_column(String(256), nullable=False)
    target_employee: Mapped[str | None] = mapped_column(String(64))
    client_ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(512))
    result: Mapped[str] = mapped_column(String(32), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class PortalSetting(TimestampMixin, Base):
    __tablename__ = "portal_setting"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    sensitive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class D365EntityMapping(TimestampMixin, Base):
    __tablename__ = "d365_entity_mapping"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    mapping_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    entity_name: Mapped[str] = mapped_column(String(128), nullable=False)
    personnel_number_field: Mapped[str | None] = mapped_column(String(128))
    company_field: Mapped[str | None] = mapped_column(String(128))
    email_field: Mapped[str | None] = mapped_column(String(128))
    position_field: Mapped[str | None] = mapped_column(String(128))
    department_field: Mapped[str | None] = mapped_column(String(128))
    manager_field: Mapped[str | None] = mapped_column(String(128))
    field_mapping: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    metadata_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_environment: Mapped[str | None] = mapped_column(String(512))

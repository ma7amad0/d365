from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.schemas import AuthenticatedUser
from app.core.exceptions import PortalError, portal_error_handler
from app.database.models import D365EntityMapping, EmployeeIdentityMapping
from app.database.session import get_session
from app.employees.router import portal_user, router

AUTO_OID = "385e90b1-5b38-4a9a-980f-61807210100f"


class FakeSession:
    def __init__(self) -> None:
        self.mapping = EmployeeIdentityMapping(
            entra_oid="oid-employee-a",
            d365_personnel_number="EmployeeA",
            d365_company="SSSA",
            mapping_source="manual_approved",
            verified=True,
            enabled=True,
        )
        self.configuration = D365EntityMapping(
            mapping_key="profile",
            entity_name="EmployeesV2",
            personnel_number_field="PersonnelNumber",
            company_field="EmploymentLegalEntityId",
            field_mapping={"personnelNumber": "PersonnelNumber", "displayName": "Name"},
            enabled=True,
        )

    async def scalars(self, _statement):
        result = MagicMock()
        result.all.return_value = [self.mapping]
        return result

    async def scalar(self, _statement):
        return self.configuration

    def add(self, _model) -> None:
        return None

    async def commit(self) -> None:
        return None


def test_query_parameter_cannot_select_employee_b() -> None:
    session = FakeSession()
    d365_client = MagicMock()
    d365_client.get_entity = AsyncMock(
        return_value={"value": [{"PersonnelNumber": "EmployeeA", "Name": "Employee A"}]}
    )

    app = FastAPI()
    app.state.d365_client = d365_client
    app.include_router(router)
    app.add_exception_handler(PortalError, portal_error_handler)

    async def user_override() -> AuthenticatedUser:
        return AuthenticatedUser(oid="oid-employee-a", tid="tenant", roles=frozenset({"employee"}))

    async def session_override():
        yield session

    app.dependency_overrides[portal_user] = user_override
    app.dependency_overrides[get_session] = session_override

    with TestClient(app) as client:
        response = client.get("/api/v1/me/profile?employee_id=EmployeeB")

    assert response.status_code == 200
    assert response.json()["employee"]["personnelNumber"] == "EmployeeA"
    _, query = d365_client.get_entity.call_args.args
    assert "EmployeeA" in str(query.filter_expression)
    assert "EmployeeB" not in str(query.filter_expression)


def test_leave_query_parameter_cannot_select_employee_b() -> None:
    session = FakeSession()
    session.configuration = D365EntityMapping(
        mapping_key="leave_balance",
        entity_name="EssLeaveBalances",
        personnel_number_field="PersonnelNumber",
        company_field="dataAreaId",
        field_mapping={"leaveType": "LeaveTypeId", "available": "BalanceAvailable"},
        enabled=True,
    )
    d365_client = MagicMock()
    d365_client.get_entity = AsyncMock(return_value={"value": []})

    app = FastAPI()
    app.state.d365_client = d365_client
    app.include_router(router)
    app.add_exception_handler(PortalError, portal_error_handler)

    async def user_override() -> AuthenticatedUser:
        return AuthenticatedUser(oid="oid-employee-a", tid="tenant", roles=frozenset({"employee"}))

    async def session_override():
        yield session

    app.dependency_overrides[portal_user] = user_override
    app.dependency_overrides[get_session] = session_override

    with TestClient(app) as client:
        response = client.get("/api/v1/me/leave-balances?employee_id=EmployeeB")

    assert response.status_code == 200
    _, query = d365_client.get_entity.call_args.args
    assert "EmployeeA" in str(query.filter_expression)
    assert "EmployeeB" not in str(query.filter_expression)


def test_me_auto_provisions_exact_d365_oid_match() -> None:
    database = MagicMock()
    database.scalar = AsyncMock(
        return_value=D365EntityMapping(
            mapping_key="identity",
            entity_name="EssWorkerDetails",
            field_mapping={
                "entraOid": "AadUserObjectId",
                "entraUpn": "AadUserPrincipalName",
                "personnelNumber": "PersonnelNumber",
                "company": "company",
            },
            enabled=True,
        )
    )
    empty = MagicMock()
    empty.all.return_value = []
    database.scalars = AsyncMock(return_value=empty)
    database.commit = AsyncMock()
    d365_client = MagicMock()
    d365_client.get_entity = AsyncMock(
        return_value={
            "value": [
                {
                    "AadUserObjectId": AUTO_OID,
                    "AadUserPrincipalName": "employee@example.test",
                    "PersonnelNumber": "6666",
                    "company": "SSSA",
                }
            ]
        }
    )

    app = FastAPI()
    app.state.d365_client = d365_client
    app.include_router(router)
    app.add_exception_handler(PortalError, portal_error_handler)

    async def user_override() -> AuthenticatedUser:
        return AuthenticatedUser(
            oid=AUTO_OID,
            tid="tenant",
            preferred_username="employee@example.test",
            roles=frozenset({"employee"}),
        )

    async def session_override():
        yield database

    app.dependency_overrides[portal_user] = user_override
    app.dependency_overrides[get_session] = session_override

    with TestClient(app) as client:
        response = client.get("/api/v1/me")

    assert response.status_code == 200
    assert response.json()["mapping_status"] == "verified"
    assert database.add.call_count == 4  # mapping, history, provisioning audit, profile audit

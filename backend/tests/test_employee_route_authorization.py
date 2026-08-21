from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.schemas import AuthenticatedUser
from app.core.exceptions import PortalError, portal_error_handler
from app.database.models import D365EntityMapping, EmployeeIdentityMapping
from app.database.session import get_session
from app.employees.router import portal_user, router


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

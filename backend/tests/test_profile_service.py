from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import PortalError
from app.d365.profile_service import D365ProfileService
from app.database.models import D365EntityMapping, EmployeeIdentityMapping


def configuration() -> D365EntityMapping:
    return D365EntityMapping(
        mapping_key="profile",
        entity_name="EmployeesV2",
        personnel_number_field="PersonnelNumber",
        company_field="EmploymentLegalEntityId",
        field_mapping={
            "personnelNumber": "PersonnelNumber",
            "displayName": "Name",
            "email": "PrimaryContactEmail",
            "unapprovedSensitiveField": "BirthDate",
        },
        enabled=True,
    )


def identity(personnel_number: str = "000123") -> EmployeeIdentityMapping:
    return EmployeeIdentityMapping(
        entra_oid="oid-a",
        d365_personnel_number=personnel_number,
        d365_company="SSSA",
        mapping_source="manual_approved",
        verified=True,
        enabled=True,
    )


@pytest.mark.asyncio
async def test_profile_query_uses_only_mapped_employee_and_allow_listed_fields() -> None:
    session = MagicMock()
    session.scalar = AsyncMock(return_value=configuration())
    client = MagicMock()
    client.get_entity = AsyncMock(
        return_value={
            "value": [
                {
                    "PersonnelNumber": "000123",
                    "Name": "Employee A",
                    "PrimaryContactEmail": "a@example.test",
                    "BirthDate": "private-value",
                }
            ]
        }
    )
    profile = await D365ProfileService(session, client).get_profile(identity())
    assert profile.employee.personnelNumber == "000123"
    assert profile.employee.displayName == "Employee A"
    _, query = client.get_entity.call_args.args
    assert query.select == ("PersonnelNumber", "Name", "PrimaryContactEmail")
    assert "000123" in str(query.filter_expression)
    assert "EmployeeB" not in str(query.filter_expression)
    assert "BirthDate" not in query.select


@pytest.mark.asyncio
async def test_employee_a_cannot_substitute_employee_b() -> None:
    session = MagicMock()
    session.scalar = AsyncMock(return_value=configuration())
    client = MagicMock()
    client.get_entity = AsyncMock(
        return_value={"value": [{"PersonnelNumber": "EmployeeB", "Name": "Employee B"}]}
    )
    with pytest.raises(PortalError) as error:
        await D365ProfileService(session, client).get_profile(identity("EmployeeA"))
    assert error.value.code == "PROFILE_CONFLICT"
    _, query = client.get_entity.call_args.args
    assert "EmployeeA" in str(query.filter_expression)
    assert "EmployeeB" not in str(query.filter_expression)


@pytest.mark.asyncio
async def test_multiple_d365_records_fail_closed() -> None:
    session = MagicMock()
    session.scalar = AsyncMock(return_value=configuration())
    client = MagicMock()
    client.get_entity = AsyncMock(return_value={"value": [{}, {}]})
    with pytest.raises(PortalError) as error:
        await D365ProfileService(session, client).get_profile(identity())
    assert error.value.code == "PROFILE_CONFLICT"

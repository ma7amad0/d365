from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import PortalError
from app.d365.leave_service import D365LeaveService
from app.database.models import D365EntityMapping, EmployeeIdentityMapping


def configuration() -> D365EntityMapping:
    return D365EntityMapping(
        mapping_key="leave_balance",
        entity_name="EssLeaveBalances",
        personnel_number_field="PersonnelNumber",
        company_field="dataAreaId",
        field_mapping={
            "leaveType": "LeaveTypeId",
            "available": "BalanceAvailable",
            "taken": "TakenThisYear",
            "total": "TotalThisYear",
            "unapprovedField": "PrivateValue",
        },
        enabled=True,
    )


def identity() -> EmployeeIdentityMapping:
    return EmployeeIdentityMapping(
        entra_oid="oid-a",
        d365_personnel_number="6666",
        d365_company="SSSA",
        mapping_source="manual_approved",
        verified=True,
        enabled=True,
    )


@pytest.mark.asyncio
async def test_balances_are_scoped_to_mapped_employee_and_allow_listed_fields() -> None:
    session = MagicMock()
    session.scalar = AsyncMock(return_value=configuration())
    client = MagicMock()
    client.get_entity = AsyncMock(
        return_value={
            "value": [
                {
                    "PersonnelNumber": "6666",
                    "dataAreaId": "sssa",
                    "LeaveTypeId": "ANNUAL",
                    "BalanceAvailable": 18.5,
                    "TakenThisYear": 3,
                    "TotalThisYear": 21.5,
                }
            ]
        }
    )

    response = await D365LeaveService(session, client).get_balances(identity())

    assert response.balances[0].leaveType == "ANNUAL"
    assert str(response.balances[0].available) == "18.5"
    _, query = client.get_entity.call_args.args
    assert "6666" in str(query.filter_expression)
    assert "SSSA" in str(query.filter_expression)
    assert "PrivateValue" not in query.select


@pytest.mark.asyncio
async def test_leave_record_for_another_employee_fails_closed() -> None:
    session = MagicMock()
    session.scalar = AsyncMock(return_value=configuration())
    client = MagicMock()
    client.get_entity = AsyncMock(
        return_value={
            "value": [
                {
                    "PersonnelNumber": "7777",
                    "dataAreaId": "SSSA",
                    "LeaveTypeId": "ANNUAL",
                }
            ]
        }
    )

    with pytest.raises(PortalError) as error:
        await D365LeaveService(session, client).get_balances(identity())

    assert error.value.code == "LEAVE_CONFLICT"

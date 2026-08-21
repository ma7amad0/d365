from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.auth.schemas import AuthenticatedUser
from app.core.exceptions import PortalError
from app.database.models import D365EntityMapping, EmployeeIdentityMapping
from app.employees.provisioning_service import IdentityProvisioningService

OID = "385e90b1-5b38-4a9a-980f-61807210100f"
UPN = "employee@example.test"


def configuration() -> D365EntityMapping:
    return D365EntityMapping(
        mapping_key="identity",
        entity_name="EssWorkerDetails",
        field_mapping={
            "entraOid": "AadUserObjectId",
            "entraUpn": "AadUserPrincipalName",
            "personnelNumber": "PersonnelNumber",
            "company": "company",
            "displayName": "Name",
        },
        enabled=True,
    )


def user(oid: str = OID) -> AuthenticatedUser:
    return AuthenticatedUser(
        oid=oid,
        tid="tenant",
        preferred_username=UPN,
        email=UPN,
        roles=frozenset({"employee"}),
    )


def session(existing: list[EmployeeIdentityMapping] | None = None) -> MagicMock:
    value = MagicMock()
    value.scalar = AsyncMock(return_value=configuration())
    result = MagicMock()
    result.all.return_value = existing or []
    value.scalars = AsyncMock(return_value=result)
    value.commit = AsyncMock()
    value.rollback = AsyncMock()
    return value


def client(returned_oid: str = OID) -> MagicMock:
    value = MagicMock()
    value.get_entity = AsyncMock(
        return_value={
            "value": [
                {
                    "AadUserObjectId": returned_oid,
                    "AadUserPrincipalName": UPN,
                    "PersonnelNumber": "6666",
                    "company": "SSSA",
                }
            ]
        }
    )
    return value


@pytest.mark.asyncio
async def test_exact_d365_oid_match_creates_verified_mapping_and_history() -> None:
    database = session()

    mapping = await IdentityProvisioningService(database, client()).provision(user())

    assert mapping is not None
    assert mapping.entra_oid == OID
    assert mapping.d365_personnel_number == "6666"
    assert mapping.d365_company == "SSSA"
    assert mapping.mapping_source == "d365_oid_auto_verified"
    assert mapping.verified is True
    assert mapping.enabled is True
    assert database.add.call_count == 2
    database.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_d365_oid_mismatch_fails_closed_without_writing() -> None:
    database = session()

    with pytest.raises(PortalError) as error:
        await IdentityProvisioningService(
            database, client("11111111-1111-1111-1111-111111111111")
        ).provision(user())

    assert error.value.code == "MAPPING_CONFLICT"
    database.add.assert_not_called()
    database.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_existing_worker_mapping_to_another_oid_fails_closed() -> None:
    existing = EmployeeIdentityMapping(
        entra_oid="11111111-1111-1111-1111-111111111111",
        d365_personnel_number="6666",
        d365_company="SSSA",
        mapping_source="manual_approved",
        verified=True,
        enabled=True,
    )
    database = session([existing])

    with pytest.raises(PortalError) as error:
        await IdentityProvisioningService(database, client()).provision(user())

    assert error.value.code == "MAPPING_CONFLICT"
    database.add.assert_not_called()


@pytest.mark.asyncio
async def test_user_without_upn_is_not_auto_mapped() -> None:
    database = session()
    d365_client = client()
    entra_user = user()
    entra_user = entra_user.model_copy(update={"preferred_username": None})

    mapping = await IdentityProvisioningService(database, d365_client).provision(entra_user)

    assert mapping is None
    d365_client.get_entity.assert_not_awaited()

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import PortalError
from app.employees.mapping_service import IdentityMappingService


@pytest.mark.asyncio
async def test_unmapped_identity_fails_closed() -> None:
    session = MagicMock()
    session.scalars = AsyncMock()
    result = MagicMock()
    result.all.return_value = []
    session.scalars.return_value = result
    with pytest.raises(PortalError) as error:
        await IdentityMappingService(session).require_verified("oid-a")
    assert error.value.code == "MAPPING_REQUIRED"
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_ambiguous_mapping_fails_closed() -> None:
    session = MagicMock()
    session.scalars = AsyncMock()
    result = MagicMock()
    result.all.return_value = [MagicMock(), MagicMock()]
    session.scalars.return_value = result
    with pytest.raises(PortalError) as error:
        await IdentityMappingService(session).find_verified("oid-a")
    assert error.value.code == "MAPPING_CONFLICT"

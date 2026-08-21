from __future__ import annotations

import argparse
import asyncio
import sys
import uuid

from app.core.config import get_settings
from app.d365.client import D365Client
from app.d365.exceptions import D365Error
from app.d365.query import ODataQuery, equals
from app.d365.token_service import D365TokenService

ENTITY = "EssWorkerDetails"
OID_FIELD = "AadUserObjectId"
OUTPUT_FIELDS = (
    "AadUserObjectId",
    "AadUserPrincipalName",
    "PersonnelNumber",
    "company",
    "Name",
)


async def run(raw_oid: str) -> int:
    entra_oid = str(uuid.UUID(raw_oid))
    settings = get_settings()
    try:
        async with D365Client(settings, D365TokenService(settings)) as client:
            payload = await client.get_entity(
                ENTITY,
                ODataQuery(
                    select=OUTPUT_FIELDS,
                    filter_expression=equals(OID_FIELD, entra_oid),
                    top=2,
                ),
            )
        records = payload.get("value")
        if not isinstance(records, list):
            print("[ERROR] D365 returned an unexpected response shape", file=sys.stderr)
            return 1
        if not records:
            print("[NOT FOUND] No D365 worker has this exact Entra object ID")
            return 2
        if len(records) != 1 or not isinstance(records[0], dict):
            print("[CONFLICT] Multiple D365 workers have this Entra object ID", file=sys.stderr)
            return 3

        worker = records[0]
        print("[FOUND] Exact Entra object-ID match; verify before approval")
        for field in OUTPUT_FIELDS:
            print(f"{field}: {worker.get(field) or '-'}")
        return 0
    except (D365Error, ValueError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read-only lookup of a D365 worker by exact Entra object ID"
    )
    parser.add_argument("--oid", required=True, help="Entra user object ID")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args.oid)))


if __name__ == "__main__":
    main()

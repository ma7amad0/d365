from __future__ import annotations

import argparse
import asyncio
import uuid

from sqlalchemy import and_, or_, select

from app.core.config import get_settings
from app.database.models import EmployeeIdentityMapping, EmployeeIdentityMappingHistory
from app.database.session import create_engine, create_session_factory


async def run(args: argparse.Namespace) -> int:
    entra_oid = str(uuid.UUID(args.oid))
    approved_by_oid = str(uuid.UUID(args.approved_by_oid))
    personnel_number = args.personnel_number.strip()
    company = args.company.strip()
    if not personnel_number or len(personnel_number) > 64:
        raise SystemExit("[ERROR] Personnel number is empty or too long")
    if not company or len(company) > 32:
        raise SystemExit("[ERROR] Company is empty or too long")
    settings = get_settings()
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    async with factory() as session:
        existing = await session.scalar(
            select(EmployeeIdentityMapping).where(
                or_(
                    EmployeeIdentityMapping.entra_oid == entra_oid,
                    and_(
                        EmployeeIdentityMapping.d365_personnel_number == personnel_number,
                        EmployeeIdentityMapping.d365_company == company,
                        EmployeeIdentityMapping.enabled.is_(True),
                    ),
                )
            )
        )
        if existing is not None:
            raise SystemExit("[ERROR] A conflicting identity or employee mapping already exists")
        mapping = EmployeeIdentityMapping(
            id=uuid.uuid4(),
            entra_oid=entra_oid,
            entra_upn=args.upn.casefold() if args.upn else None,
            entra_email=args.email.casefold() if args.email else None,
            d365_personnel_number=personnel_number,
            d365_company=company,
            mapping_source="manual_approved",
            verified=True,
            enabled=True,
        )
        session.add(mapping)
        session.add(
            EmployeeIdentityMappingHistory(
                mapping_id=mapping.id,
                changed_by_oid=approved_by_oid,
                change_type="CREATE_VERIFIED",
                after_values={
                    "entra_oid": entra_oid,
                    "d365_personnel_number": personnel_number,
                    "d365_company": company,
                },
            )
        )
        await session.commit()
    await engine.dispose()
    print(f"[OK] Verified mapping created for personnel number {personnel_number}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an explicitly approved identity mapping")
    parser.add_argument("--oid", required=True)
    parser.add_argument("--personnel-number", required=True)
    parser.add_argument("--company", required=True)
    parser.add_argument("--approved-by-oid", required=True)
    parser.add_argument("--upn")
    parser.add_argument("--email")
    raise SystemExit(asyncio.run(run(parser.parse_args())))


if __name__ == "__main__":
    main()

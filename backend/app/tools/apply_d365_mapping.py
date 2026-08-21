from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.core.config import get_settings
from app.d365.client import D365Client
from app.d365.metadata import D365MetadataService
from app.d365.query import validate_identifier
from app.d365.token_service import D365TokenService
from app.database.models import D365EntityMapping
from app.database.session import create_engine, create_session_factory


def load_configuration(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("mappings"), list):
        raise ValueError("Configuration must contain a mappings array")
    return raw


async def run(path: Path, apply: bool) -> int:
    settings = get_settings()
    try:
        configuration = load_configuration(path)
        expected = str(configuration.get("environment", "")).rstrip("/")
        actual = str(settings.D365_BASE_URL).rstrip("/")
        if expected != actual:
            raise ValueError(f"Configuration environment {expected!r} does not match {actual!r}")

        tokens = D365TokenService(settings)
        async with D365Client(settings, tokens) as client:
            metadata_service = D365MetadataService(
                client, max_bytes=settings.D365_METADATA_MAX_BYTES
            )
            entities = {
                item.entity_set: set(item.properties)
                for item in metadata_service.parse(await metadata_service.fetch_xml())
            }

        for item in configuration["mappings"]:
            entity_name = validate_identifier(str(item["entity_name"]))
            available = entities.get(entity_name)
            if available is None:
                raise ValueError(f"Entity {entity_name!r} is not present in current metadata")
            configured_fields = {
                str(value) for key, value in item.items() if key.endswith("_field") and value
            }
            configured_fields.update(str(value) for value in item.get("field_mapping", {}).values())
            missing = configured_fields - available
            if missing:
                raise ValueError(f"Entity {entity_name!r} is missing fields: {sorted(missing)}")

        print(f"[OK] Validated {len(configuration['mappings'])} mappings against {actual}")
        if not apply:
            print("[DRY RUN] No database changes made; pass --apply to persist mappings")
            return 0

        engine = create_engine(settings)
        factory = create_session_factory(engine)
        async with factory() as session:
            for item in configuration["mappings"]:
                key = str(item["mapping_key"])
                model = await session.scalar(
                    select(D365EntityMapping).where(D365EntityMapping.mapping_key == key)
                )
                if model is None:
                    model = D365EntityMapping(mapping_key=key, entity_name=str(item["entity_name"]))
                    session.add(model)
                for field in (
                    "entity_name",
                    "personnel_number_field",
                    "company_field",
                    "email_field",
                    "position_field",
                    "department_field",
                    "manager_field",
                    "field_mapping",
                    "enabled",
                ):
                    if field in item:
                        setattr(model, field, item[field])
                model.metadata_confirmed_at = datetime.now(UTC)
                model.metadata_environment = actual
            await session.commit()
        await engine.dispose()
        print("[OK] D365 entity mappings applied")
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and apply D365 entity mappings")
    parser.add_argument("configuration", type=Path)
    parser.add_argument("--apply", action="store_true", help="Persist validated mappings")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args.configuration, args.apply)))


if __name__ == "__main__":
    main()

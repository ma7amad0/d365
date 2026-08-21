from __future__ import annotations

import argparse
import asyncio
import sys

from app.core.config import get_settings
from app.d365.client import D365Client
from app.d365.exceptions import D365Error
from app.d365.metadata import D365MetadataService
from app.d365.token_service import D365TokenService


async def run(term: str, include_fields: bool, refresh: bool) -> int:
    settings = get_settings()
    try:
        tokens = D365TokenService(settings)
        async with D365Client(settings, tokens) as client:
            service = D365MetadataService(client)
            matches = await service.search(term, refresh=refresh)
        print(f"Possible entity sets ({len(matches)} matches):")
        for entity in matches:
            print(f"\n- {entity.entity_set} ({entity.entity_type})")
            if include_fields:
                print(
                    "  Fields: "
                    + (", ".join(entity.properties) if entity.properties else "none exposed")
                )
        return 0
    except (D365Error, ValueError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Search actual D365 OData metadata")
    parser.add_argument("term", help="Case-insensitive entity or property search term")
    parser.add_argument("--fields", action="store_true", help="Print matching entity fields")
    parser.add_argument("--refresh", action="store_true", help="Bypass any future shared cache")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args.term, args.fields, args.refresh)))


if __name__ == "__main__":
    main()

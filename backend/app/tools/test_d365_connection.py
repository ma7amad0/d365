from __future__ import annotations

import argparse
import asyncio
import sys

from app.core.config import get_settings
from app.d365.client import D365Client
from app.d365.exceptions import D365Error
from app.d365.metadata import D365MetadataService
from app.d365.token_service import D365TokenService


async def run(include_metadata: bool) -> int:
    settings = get_settings()
    try:
        tokens = D365TokenService(settings)
        await tokens.get_access_token()
        print("[OK] Entra token acquired")
        async with D365Client(settings, tokens) as client:
            if include_metadata:
                metadata = D365MetadataService(client, max_bytes=settings.D365_METADATA_MAX_BYTES)
                xml = await metadata.fetch_xml(refresh=True)
                entity_count = len(metadata.parse(xml))
                print("[OK] D365 connection successful")
                print(f"[OK] OData metadata accessible ({entity_count} entity sets)")
            else:
                response = await client.get_metadata()
                print(f"[OK] D365 connection successful (HTTP {response.status_code})")
        print(f"Environment: {str(settings.D365_BASE_URL).rstrip('/')}")
        return 0
    except (D365Error, ValueError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Safely test D365 app-only connectivity")
    parser.add_argument("--metadata", action="store_true", help="Parse and count OData entity sets")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args.metadata)))


if __name__ == "__main__":
    main()

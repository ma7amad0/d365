from __future__ import annotations

from dataclasses import dataclass

import structlog
from defusedxml import ElementTree
from redis.asyncio import Redis

from app.d365.client import D365Client
from app.d365.exceptions import D365MetadataError


@dataclass(frozen=True, slots=True)
class EntityDescription:
    entity_set: str
    entity_type: str
    properties: tuple[str, ...]


class D365MetadataService:
    CACHE_KEY = "d365:metadata:v1"

    def __init__(
        self,
        client: D365Client,
        redis: Redis | None = None,
        cache_ttl: int = 21_600,
        max_bytes: int = 268_435_456,
    ) -> None:
        self._client = client
        self._redis = redis
        self._cache_ttl = cache_ttl
        self._max_bytes = max_bytes

    async def fetch_xml(self, *, refresh: bool = False) -> str:
        if self._redis is not None and not refresh:
            try:
                cached = await self._redis.get(self.CACHE_KEY)
                if cached:
                    return str(cached)
            except Exception as exc:
                structlog.get_logger().warning(
                    "d365_metadata_cache_read_failed", error_type=type(exc).__name__
                )
        response = await self._client.get_metadata()
        size = len(response.content)
        if size > self._max_bytes:
            raise D365MetadataError(
                "D365 metadata document exceeds the configured safety limit "
                f"({size} bytes received; limit is {self._max_bytes} bytes)"
            )
        xml = response.text
        if self._redis is not None:
            try:
                await self._redis.set(self.CACHE_KEY, xml, ex=self._cache_ttl)
            except Exception as exc:
                structlog.get_logger().warning(
                    "d365_metadata_cache_write_failed", error_type=type(exc).__name__
                )
        return xml

    @staticmethod
    def parse(xml: str) -> list[EntityDescription]:
        try:
            root = ElementTree.fromstring(xml)
        except ElementTree.ParseError as exc:
            raise D365MetadataError("D365 returned invalid metadata XML") from exc

        entity_types: dict[str, tuple[str, ...]] = {}
        for schema in root.iter():
            if schema.tag.rsplit("}", 1)[-1] != "Schema":
                continue
            namespace = schema.attrib.get("Namespace", "")
            for child in schema:
                if child.tag.rsplit("}", 1)[-1] != "EntityType":
                    continue
                name = child.attrib.get("Name", "")
                properties = tuple(
                    item.attrib["Name"]
                    for item in child
                    if item.tag.rsplit("}", 1)[-1] == "Property" and "Name" in item.attrib
                )
                entity_types[f"{namespace}.{name}"] = properties

        entities: list[EntityDescription] = []
        for element in root.iter():
            if element.tag.rsplit("}", 1)[-1] != "EntitySet":
                continue
            entity_set = element.attrib.get("Name")
            entity_type = element.attrib.get("EntityType")
            if entity_set and entity_type:
                entities.append(
                    EntityDescription(entity_set, entity_type, entity_types.get(entity_type, ()))
                )
        return sorted(entities, key=lambda item: item.entity_set.lower())

    async def search(self, term: str, *, refresh: bool = False) -> list[EntityDescription]:
        normalized = term.casefold().strip()
        if not normalized:
            raise ValueError("Search term cannot be empty")
        entities = self.parse(await self.fetch_xml(refresh=refresh))
        return [
            entity
            for entity in entities
            if normalized in entity.entity_set.casefold()
            or normalized in entity.entity_type.casefold()
            or any(normalized in field.casefold() for field in entity.properties)
        ]

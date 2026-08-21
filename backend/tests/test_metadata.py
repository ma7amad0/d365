import httpx
import pytest

from app.d365.exceptions import D365MetadataError
from app.d365.metadata import D365MetadataService

METADATA = """<?xml version="1.0" encoding="utf-8"?>
<edmx:Edmx xmlns:edmx="http://docs.oasis-open.org/odata/ns/edmx" Version="4.0">
 <edmx:DataServices>
  <Schema xmlns="http://docs.oasis-open.org/odata/ns/edm" Namespace="Example">
   <EntityType Name="DemoWorker"><Key><PropertyRef Name="RecordId"/></Key>
    <Property Name="RecordId" Type="Edm.Int64" Nullable="false"/>
    <Property Name="WorkEmail" Type="Edm.String"/>
   </EntityType>
   <EntityContainer Name="Container">
    <EntitySet Name="DemoWorkers" EntityType="Example.DemoWorker"/>
   </EntityContainer>
  </Schema>
 </edmx:DataServices>
</edmx:Edmx>"""


def test_metadata_parser_discovers_entity_sets_and_fields() -> None:
    entities = D365MetadataService.parse(METADATA)
    assert len(entities) == 1
    assert entities[0].entity_set == "DemoWorkers"
    assert entities[0].properties == ("RecordId", "WorkEmail")


def test_metadata_parser_rejects_malformed_xml() -> None:
    with pytest.raises(D365MetadataError, match="invalid metadata"):
        D365MetadataService.parse("<not-closed>")


class StubClient:
    async def get_metadata(self):  # pragma: no cover - search test overrides fetch
        raise AssertionError


class MetadataClient:
    def __init__(self, content: bytes) -> None:
        self.content = content

    async def get_metadata(self) -> httpx.Response:
        return httpx.Response(200, content=self.content)


@pytest.mark.asyncio
async def test_search_matches_property_names() -> None:
    service = D365MetadataService(StubClient())  # type: ignore[arg-type]

    async def fetch_xml(*, refresh: bool = False) -> str:
        return METADATA

    service.fetch_xml = fetch_xml  # type: ignore[method-assign]
    matches = await service.search("email")
    assert [item.entity_set for item in matches] == ["DemoWorkers"]


@pytest.mark.asyncio
async def test_metadata_size_limit_is_configurable() -> None:
    service = D365MetadataService(MetadataClient(b"12345"), max_bytes=4)  # type: ignore[arg-type]
    with pytest.raises(D365MetadataError, match="5 bytes received; limit is 4 bytes"):
        await service.fetch_xml(refresh=True)

import pytest

from app.d365.query import ODataQuery, equals, quote_odata_string


def test_odata_string_escapes_apostrophe() -> None:
    assert quote_odata_string("O'Brien") == "'O''Brien'"
    assert equals("ConfiguredEmailField", "o'brien@example.test") == (
        "ConfiguredEmailField eq 'o''brien@example.test'"
    )


@pytest.mark.parametrize("value", ["Name eq 'x'", "field;drop", "https://evil.test"])
def test_untrusted_identifier_is_rejected(value: str) -> None:
    with pytest.raises(ValueError, match="Invalid OData identifier"):
        ODataQuery(select=[value]).to_params()


def test_query_bounds_paging() -> None:
    with pytest.raises(ValueError, match="between"):
        ODataQuery(top=1001).to_params()
    with pytest.raises(ValueError, match="negative"):
        ODataQuery(skip=-1).to_params()


def test_cross_company_is_explicitly_serialized() -> None:
    assert ODataQuery(cross_company=True).to_params()["cross-company"] == "true"

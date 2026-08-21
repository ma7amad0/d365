from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_./]*$")


def validate_identifier(value: str) -> str:
    if not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"Invalid OData identifier: {value!r}")
    return value


def quote_odata_string(value: str) -> str:
    """Create an OData string literal by doubling embedded apostrophes."""
    if "\x00" in value or "\r" in value or "\n" in value:
        raise ValueError("OData string values cannot contain control characters")
    return "'" + value.replace("'", "''") + "'"


@dataclass(frozen=True, slots=True)
class ODataQuery:
    select: Sequence[str] = ()
    filter_expression: str | None = None
    expand: Sequence[str] = ()
    orderby: Sequence[str] = ()
    top: int | None = None
    skip: int | None = None
    count: bool | None = None

    def to_params(self) -> dict[str, str]:
        params: dict[str, str] = {}
        if self.select:
            params["$select"] = ",".join(validate_identifier(v) for v in self.select)
        if self.filter_expression:
            params["$filter"] = self.filter_expression
        if self.expand:
            params["$expand"] = ",".join(validate_identifier(v) for v in self.expand)
        if self.orderby:
            params["$orderby"] = ",".join(validate_identifier(v) for v in self.orderby)
        if self.top is not None:
            if not 1 <= self.top <= 1000:
                raise ValueError("$top must be between 1 and 1000")
            params["$top"] = str(self.top)
        if self.skip is not None:
            if self.skip < 0:
                raise ValueError("$skip cannot be negative")
            params["$skip"] = str(self.skip)
        if self.count is not None:
            params["$count"] = str(self.count).lower()
        return params


def equals(field: str, value: str) -> str:
    """Safe equality filter builder for trusted field configuration and untrusted values."""
    return f"{validate_identifier(field)} eq {quote_odata_string(value)}"


def and_all(*expressions: str) -> str:
    if not expressions or any(not expression for expression in expressions):
        raise ValueError("At least one non-empty OData expression is required")
    return " and ".join(f"({expression})" for expression in expressions)

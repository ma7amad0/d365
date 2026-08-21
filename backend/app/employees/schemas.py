from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel


class EmployeeProfile(BaseModel):
    personnelNumber: str
    displayName: str | None = None
    email: str | None = None
    phone: str | None = None
    officeLocation: str | None = None
    professionalTitle: str | None = None
    legalEntity: str | None = None
    employmentStartDate: str | None = None
    employmentEndDate: str | None = None


class EmployeeProfileResponse(BaseModel):
    employee: EmployeeProfile


class LeaveBalance(BaseModel):
    leaveType: str
    available: Decimal | None = None
    taken: Decimal | None = None
    total: Decimal | None = None


class LeaveBalancesResponse(BaseModel):
    balances: list[LeaveBalance]

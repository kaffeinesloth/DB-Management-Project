"""Authenticated user session data."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UserSession:
    login_name: str
    database_user: str
    employee_id: int
    full_name: str
    roles: list[str]


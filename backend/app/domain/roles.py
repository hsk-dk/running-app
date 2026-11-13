"""Roles from identity-provider groups. Deny by default: no matching group means no access."""
from __future__ import annotations

ADMIN = "admin"
FAMILY = "family"


def parse_groups(header: str | None) -> list[str]:
    """Authentik sends groups as one header, separated by '|' (some setups use ',')."""
    if not header:
        return []
    parts = header.replace(",", "|").split("|")
    return [p.strip() for p in parts if p.strip()]


def role_from_groups(groups: list[str], admin_groups: list[str], family_groups: list[str]) -> str | None:
    if any(g in admin_groups for g in groups):
        return ADMIN
    if any(g in family_groups for g in groups):
        return FAMILY
    return None

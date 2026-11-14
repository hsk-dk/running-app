"""Who is calling, and what may they see. The HTTP layer only passes headers and the peer address in."""
from __future__ import annotations

import ipaddress
import logging
from dataclasses import dataclass
from typing import Mapping

from app.config import settings
from app.db import DEFAULT_USER_ID, get_conn
from app.domain.roles import ADMIN, parse_groups, role_from_groups
from app.errors import ForbiddenError, NotFoundError, UnauthorizedError
from app.repositories import users as user_repo

logger = logging.getLogger(__name__)

SHARING_LEVELS = ("private", "overview", "all")


@dataclass(frozen=True)
class CurrentUser:
    id: int
    external_id: str
    username: str
    display_name: str
    role: str
    sharing_level: str
    is_child: bool = False

    @property
    def is_admin(self) -> bool:
        return self.role == ADMIN


def _to_user(row) -> CurrentUser:
    return CurrentUser(
        id=row["id"],
        external_id=row["external_id"],
        username=row["username"],
        display_name=row["display_name"] or row["username"],
        role=row["role"],
        sharing_level=row["sharing_level"] if settings.FAMILY_SHARING_ENABLED else "private",
        is_child=bool(row["is_child"]),
    )


def is_trusted_peer(peer_ip: str | None) -> bool:
    """True when the request comes from a proxy listed in TRUSTED_PROXIES (IPs or CIDR ranges)."""
    if not peer_ip:
        return False
    try:
        peer = ipaddress.ip_address(peer_ip)
    except ValueError:
        return False
    for entry in settings.TRUSTED_PROXIES:
        try:
            if peer in ipaddress.ip_network(entry, strict=False):
                return True
        except ValueError:
            logger.warning("Ignoring invalid TRUSTED_PROXIES entry %r", entry)
    return False


def _claims_legacy_data(conn, username: str, role: str) -> bool:
    """The first person to sign in takes over the data that existed before users were added."""
    legacy = user_repo.get(conn, DEFAULT_USER_ID)
    if legacy is None or legacy["external_id"] != "local":
        return False
    if settings.AUTH_OWNER_USERNAME:
        return username == settings.AUTH_OWNER_USERNAME
    return role == ADMIN


def resolve(peer_ip: str | None, headers: Mapping[str, str]) -> CurrentUser:
    """AUTH_MODE=none: the single local user. AUTH_MODE=proxy: the Authentik headers, from a trusted proxy only."""
    conn = get_conn()
    try:
        if settings.AUTH_MODE != "proxy":
            row = user_repo.get(conn, DEFAULT_USER_ID)
            if row is None:  # cannot happen after migrations, but fail clearly
                raise UnauthorizedError("No local user")
            return _to_user(row)

        if not is_trusted_peer(peer_ip):
            raise ForbiddenError("Requests must come through the identity proxy")

        username = (headers.get("x-authentik-username") or "").strip()
        external_id = (headers.get("x-authentik-uid") or username).strip()
        if not external_id:
            raise UnauthorizedError("Not signed in")

        role = role_from_groups(
            parse_groups(headers.get("x-authentik-groups")), settings.AUTH_ADMIN_GROUPS, settings.AUTH_FAMILY_GROUPS
        )
        if role is None:
            raise ForbiddenError("Your account has no access to this app")

        name = (headers.get("x-authentik-name") or "").strip() or None
        username = username or external_id

        row = user_repo.get_by_external_id(conn, external_id)
        if row is None and _claims_legacy_data(conn, username, role):
            user_repo.update_identity(conn, DEFAULT_USER_ID, username, name, role)
            user_repo.set_external_id(conn, DEFAULT_USER_ID, external_id)
            row = user_repo.get(conn, DEFAULT_USER_ID)
        elif row is None:
            user_id = user_repo.create(conn, external_id, username, name, role)
            row = user_repo.get(conn, user_id)
        else:
            user_repo.update_identity(conn, row["id"], username, name or row["display_name"], role)
            row = user_repo.get(conn, row["id"])
        conn.commit()
        return _to_user(row)
    finally:
        conn.close()


def get_user(user_id: int) -> CurrentUser:
    conn = get_conn()
    try:
        row = user_repo.get(conn, user_id)
        if row is None:
            raise NotFoundError(f"User {user_id} not found")
        return _to_user(row)
    finally:
        conn.close()


def update_profile(user_id: int, sharing_level: str | None, display_name: str | None) -> CurrentUser:
    conn = get_conn()
    try:
        if user_repo.get(conn, user_id) is None:
            raise NotFoundError(f"User {user_id} not found")
        if sharing_level is not None:
            if sharing_level not in SHARING_LEVELS:
                raise ValueError(f"Unknown sharing level {sharing_level!r}")
            user_repo.set_sharing_level(conn, user_id, sharing_level)
        if display_name is not None:
            user_repo.set_display_name(conn, user_id, display_name.strip() or None)
        conn.commit()
        return _to_user(user_repo.get(conn, user_id))
    finally:
        conn.close()


def list_users() -> list[CurrentUser]:
    conn = get_conn()
    try:
        return [_to_user(r) for r in user_repo.list_all(conn)]
    finally:
        conn.close()


def list_people(admin: CurrentUser) -> list[dict]:
    """Everyone with an account, for the parents' settings. Only admins (the parents) may ask."""
    if not admin.is_admin:
        raise ForbiddenError("Only an admin can see the list of people")
    conn = get_conn()
    try:
        return [
            {"id": r["id"], "name": r["display_name"] or r["username"], "username": r["username"], "role": r["role"], "is_child": bool(r["is_child"])}
            for r in user_repo.list_all(conn)
        ]
    finally:
        conn.close()


def set_child(admin: CurrentUser, user_id: int, is_child: bool) -> CurrentUser:
    """A parent (admin) marks someone as a child, or not. A person cannot change that about themselves."""
    if not admin.is_admin:
        raise ForbiddenError("Only an admin can mark someone as a child")
    if admin.id == user_id:
        raise ForbiddenError("You cannot mark yourself as a child")
    conn = get_conn()
    try:
        if user_repo.get(conn, user_id) is None:
            raise NotFoundError(f"User {user_id} not found")
        user_repo.set_child(conn, user_id, is_child)
        conn.commit()
        return _to_user(user_repo.get(conn, user_id))
    finally:
        conn.close()

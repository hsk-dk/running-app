"""Layering rules from the backend refactor (#10, #2).

routers (app/api) -> services -> repositories / domain; SQL only in repositories and db.py.
"""
import ast
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[1] / "app"


def _imports(path: Path) -> set[str]:
    found = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
            found.update(f"{node.module}.{alias.name}" for alias in node.names)
    return found


def _files(package: str) -> list[Path]:
    return sorted((APP / package).glob("*.py"))


def _violations(package: str, forbidden: tuple[str, ...]) -> list[str]:
    bad = []
    for path in _files(package):
        for name in _imports(path):
            if any(name == f or name.startswith(f + ".") for f in forbidden):
                bad.append(f"{path.relative_to(APP)} imports {name}")
    return bad


def test_routers_only_use_services_and_schemas():
    assert _violations("api", ("app.db", "app.repositories", "app.domain", "sqlite3", "app.strava")) == []


def test_routers_contain_no_sql():
    for path in _files("api"):
        text = path.read_text().upper()
        assert "SELECT " not in text and "INSERT " not in text and "UPDATE " not in text, path.name


def test_domain_is_pure():
    assert _violations(
        "domain", ("app.db", "app.repositories", "app.services", "app.api", "sqlite3", "requests")
    ) == []


def test_repositories_do_not_depend_on_upper_layers():
    assert _violations("repositories", ("app.services", "app.api", "app.domain", "app.db")) == []


def test_services_do_not_depend_on_http_layer():
    assert _violations("services", ("app.api", "fastapi")) == []


def test_sql_only_in_repositories_and_db():
    allowed = {"db.py"}
    offenders = []
    for path in APP.rglob("*.py"):
        rel = path.relative_to(APP)
        if rel.parts[0] == "repositories" or rel.name in allowed:
            continue
        text = path.read_text()
        if ".execute(" in text or ".executemany(" in text or ".executescript(" in text:
            offenders.append(str(rel))
    assert offenders == []


def test_main_only_wires_the_app():
    imports = _imports(APP / "main.py")
    assert not any(name.startswith(("app.repositories", "app.domain", "sqlite3")) for name in imports)
    assert len((APP / "main.py").read_text().splitlines()) < 60


def test_old_shim_modules_are_gone():
    for name in ("planning", "matching", "metrics", "ingest", "webhooks", "admin_status", "ai_suggestions"):
        assert not (APP / f"{name}.py").exists(), f"app/{name}.py should have moved into services/"

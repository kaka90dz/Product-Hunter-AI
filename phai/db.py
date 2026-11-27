"""Accès SQLite. Deux bases : market.db (collectes) et user.db (favoris, réglages)."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_DIR = Path(__file__).resolve().parent / "schema"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init(path: Path, schema_file: str) -> None:
    sql = (SCHEMA_DIR / schema_file).read_text(encoding="utf-8")
    with connect(path) as con:
        con.executescript(sql)


def init_all() -> None:
    from phai import config

    init(config.MARKET_DB, "market.sql")
    init(config.USER_DB, "user.sql")
    sync_reference_data()


def sync_reference_data() -> None:
    """Recopie les référentiels YAML (pays, sources) dans market.db."""
    from phai import config

    with connect(config.MARKET_DB) as con:
        for c in config.countries():
            con.execute(
                "INSERT INTO countries(code,name_fr,currency,languages,region) VALUES(?,?,?,?,?) "
                "ON CONFLICT(code) DO UPDATE SET name_fr=excluded.name_fr, currency=excluded.currency, "
                "languages=excluded.languages, region=excluded.region",
                (c["code"], c["name_fr"], c["currency"], ",".join(c["languages"]), c["region"]),
            )
        for s in config.sources():
            con.execute(
                "INSERT INTO sources(key,name,category,access_method,status,needs_key,free_quota,notes,last_checked) "
                "VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(key) DO UPDATE SET name=excluded.name, "
                "category=excluded.category, access_method=excluded.access_method, status=excluded.status, "
                "needs_key=excluded.needs_key, free_quota=excluded.free_quota, notes=excluded.notes, "
                "last_checked=excluded.last_checked",
                (s["key"], s["name"], s["category"], s["access"], s["status"], int(bool(s["needs_key"])),
                 s["quota"], s["notes"], str(s["checked"])),
            )

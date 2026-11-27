"""Suivi des collectes et cache : on ne relance pas une collecte trop récente."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from phai import config, db


def last_success(collector: str, scope: str = "") -> str | None:
    with db.connect(config.MARKET_DB) as con:
        row = con.execute(
            "SELECT MAX(finished_at) FROM collection_runs WHERE collector=? AND scope=? AND status='ok'",
            (collector, scope),
        ).fetchone()
    return row[0]


def is_fresh(collector: str, ttl_hours: float, scope: str = "") -> bool:
    last = last_success(collector, scope)
    if not last:
        return False
    return datetime.fromisoformat(last) > datetime.now(timezone.utc) - timedelta(hours=ttl_hours)


class Run:
    def __init__(self, run_id: int):
        self.id = run_id
        self.items = 0
        self.message = ""


@contextmanager
def track(collector: str, scope: str = "", mode: str = "eco"):
    with db.connect(config.MARKET_DB) as con:
        cur = con.execute(
            "INSERT INTO collection_runs(collector,scope,mode,started_at) VALUES(?,?,?,?)",
            (collector, scope, mode, db.now_iso()),
        )
        run = Run(cur.lastrowid)
    status = "ok"
    try:
        yield run
    except Exception as e:  # noqa: BLE001 — on enregistre l'échec, puis on le propage
        status, run.message = "erreur", f"{type(e).__name__}: {e}"[:500]
        raise
    finally:
        with db.connect(config.MARKET_DB) as con:
            con.execute(
                "UPDATE collection_runs SET finished_at=?, status=?, items=?, message=? WHERE id=?",
                (db.now_iso(), status, run.items, run.message, run.id),
            )

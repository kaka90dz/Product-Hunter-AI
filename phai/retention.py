"""Politique de conservation des données, par source."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from phai import config


def _ago(days):
    return (datetime.now(timezone.utc) - timedelta(days=days)).replace(microsecond=0).isoformat()


def apply(con) -> dict:
    r = config.settings()["retention_days"]
    yt = _ago(r["youtube_api_data"])
    out = {}
    # YouTube : données de l'API supprimées si non rafraîchies depuis moins de 30 jours.
    out["releves_youtube"] = con.execute("DELETE FROM video_stats WHERE collected_at < ?", (yt,)).rowcount
    out["videos_youtube"] = con.execute(
        "DELETE FROM videos WHERE platform='youtube' AND id NOT IN (SELECT DISTINCT video_id FROM video_stats)").rowcount
    out["signaux_youtube"] = con.execute(
        "DELETE FROM keyword_signals WHERE source='youtube' AND ref NOT IN "
        "(SELECT external_id FROM videos WHERE platform='youtube')").rowcount
    # Les scores intègrent des comptages issus de YouTube : même durée de conservation.
    out["scores"] = con.execute("DELETE FROM scores WHERE computed_at < ?", (yt,)).rowcount
    out["tendances"] = con.execute("DELETE FROM trend_signals WHERE collected_at < ?", (_ago(r["google_trends"]),)).rowcount
    con.execute("DELETE FROM keyword_signals WHERE source='google_trends' AND CAST(substr(ref, 2) AS INTEGER) "
                "NOT IN (SELECT id FROM trend_signals)")
    out["journal"] = con.execute("DELETE FROM collection_runs WHERE started_at < ?", (_ago(r["collection_runs"]),)).rowcount
    con.execute("DELETE FROM search_runs WHERE started_at < ?", (_ago(r["collection_runs"]),))
    con.commit()
    return out

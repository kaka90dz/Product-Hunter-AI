"""Google Trends — recherches en hausse du jour, par pays (flux RSS public)."""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

from phai import config, db, http, runs

KEY = "google_trends_rss"
URL = "https://trends.google.com/trending/rss"
NS = {"ht": "https://trends.google.com/trending/rss"}


def parse_traffic(text: str | None) -> int | None:
    """'200+' -> 200 ; '1 000+' / '1,000+' -> 1000 ; '2K+' -> 2000 ; '1M+' -> 1000000."""
    if not text:
        return None
    t = text.strip().replace(" ", "").replace(" ", "").replace(",", "").replace(".", "").rstrip("+")
    m = re.fullmatch(r"(\d+)([KkMm]?)", t)
    if not m:
        return None
    mult = {"": 1, "k": 1_000, "m": 1_000_000}[m.group(2).lower()]
    return int(m.group(1)) * mult


def parse(xml_text: str, country: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    out = []
    for item in root.iter("item"):
        term = (item.findtext("title") or "").strip()
        if not term:
            continue
        pub = item.findtext("pubDate")
        started = parsedate_to_datetime(pub).isoformat() if pub else None
        traffic = item.findtext("ht:approx_traffic", namespaces=NS)
        news = [
            {
                "title": n.findtext("ht:news_item_title", namespaces=NS),
                "url": n.findtext("ht:news_item_url", namespaces=NS),
                "source": n.findtext("ht:news_item_source", namespaces=NS),
            }
            for n in item.findall("ht:news_item", NS)
        ]
        out.append({
            "country": country, "term": term, "approx_traffic": traffic,
            "traffic_min": parse_traffic(traffic), "started_at": started,
            "url": f"https://trends.google.com/trends/explore?geo={country}&q={term}",
            "news": news,
        })
    return out


def collect(force: bool = False) -> dict:
    s = config.settings()
    ttl = s["cache_ttl_hours"][KEY]
    delay = s["quotas"]["http_delay_seconds"]
    summary = {"pays": 0, "nouveaux": 0, "ignores_cache": 0, "erreurs": []}
    for c in config.active_countries(s):
        code = c["code"]
        if not force and runs.is_fresh(KEY, ttl, scope=code):
            summary["ignores_cache"] += 1
            continue
        try:
            with runs.track(KEY, scope=code) as run:
                r = http.get(URL, params={"geo": code}, delay=delay)
                items = parse(r.text, code)
                collected = db.now_iso()
                with db.connect(config.MARKET_DB) as con:
                    for it in items:
                        cur = con.execute(
                            "INSERT OR IGNORE INTO trend_signals(source,country,term,approx_traffic,traffic_min,"
                            "started_at,url,news_json,collected_at,run_id) VALUES(?,?,?,?,?,?,?,?,?,?)",
                            (KEY, code, it["term"], it["approx_traffic"], it["traffic_min"], it["started_at"],
                             it["url"], json.dumps(it["news"], ensure_ascii=False), collected, run.id),
                        )
                        run.items += cur.rowcount
                summary["pays"] += 1
                summary["nouveaux"] += run.items
        except Exception as e:  # noqa: BLE001
            summary["erreurs"].append(f"{code}: {e}")
    return summary

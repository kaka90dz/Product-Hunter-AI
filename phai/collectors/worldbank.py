"""Banque mondiale : PIB par habitant en parité de pouvoir d'achat (dollars internationaux courants)."""
from __future__ import annotations

from phai import config, db, http, runs

KEY = "worldbank"
INDICATORS = {"NY.GDP.PCAP.PP.CD": "pib_hab_ppa_usd"}


def collect(force: bool = False) -> dict:
    s = config.settings()
    if not force and runs.is_fresh(KEY, s["cache_ttl_hours"][KEY]):
        return {"ignore_cache": True}
    codes = [c["code"] for c in config.countries()]
    out = {}
    with runs.track(KEY) as run:
        for wb_code, name in INDICATORS.items():
            url = f"https://api.worldbank.org/v2/country/{';'.join(codes)}/indicator/{wb_code}"
            payload = http.get(url, params={"format": "json", "mrv": 1, "per_page": 100}).json()
            rows = payload[1] if len(payload) > 1 and payload[1] else []
            collected = db.now_iso()
            with db.connect(config.MARKET_DB) as con:
                for row in rows:
                    if row.get("value") is None:
                        continue
                    con.execute(
                        "INSERT OR REPLACE INTO country_indicators(country,indicator,year,value,source,source_url,collected_at)"
                        " VALUES(?,?,?,?,?,?,?)",
                        (row["country"]["id"], name, int(row["date"]), row["value"],
                         f"Banque mondiale {wb_code}", f"https://data.worldbank.org/indicator/{wb_code}", collected),
                    )
                    run.items += 1
            out[name] = run.items
    return out

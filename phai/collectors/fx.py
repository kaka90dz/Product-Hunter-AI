"""Taux de change de référence de la BCE via l'API Frankfurter (sans clé)."""
from __future__ import annotations

from phai import config, db, http, runs

KEY = "fx_rates"
URL = "https://api.frankfurter.dev/v1/latest"
SOURCE = "BCE via api.frankfurter.dev"


def collect(force: bool = False) -> dict:
    s = config.settings()
    if not force and runs.is_fresh(KEY, s["cache_ttl_hours"][KEY]):
        return {"ignore_cache": True}
    quotes = sorted({c["currency"] for c in config.countries()} - {"EUR"})
    with runs.track(KEY) as run:
        data = http.get(URL, params={"base": "EUR", "symbols": ",".join(quotes)}).json()
        collected = db.now_iso()
        with db.connect(config.MARKET_DB) as con:
            for q, rate in data["rates"].items():
                con.execute(
                    "INSERT OR REPLACE INTO fx_rates(rate_date,base,quote,rate,source,collected_at) VALUES(?,?,?,?,?,?)",
                    (data["date"], "EUR", q, rate, SOURCE, collected),
                )
                run.items += 1
        missing = set(quotes) - set(data["rates"])
        run.message = f"date BCE {data['date']}" + (f" ; manquants : {sorted(missing)}" if missing else "")
    return {"date": data["date"], "devises": run.items, "manquantes": sorted(missing)}

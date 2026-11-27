"""Lectures pour le tableau de bord (lecture seule, sans IA)."""
from __future__ import annotations

import json

import pandas as pd

from phai import config, db


def _df(sql: str, params=()) -> pd.DataFrame:
    if not config.MARKET_DB.exists():
        return pd.DataFrame()
    with db.connect(config.MARKET_DB) as con:
        return pd.read_sql_query(sql, con, params=params)


def counts() -> dict:
    q = {
        "tendances": "SELECT COUNT(*) n FROM trend_signals",
        "pays_tendances": "SELECT COUNT(DISTINCT country) n FROM trend_signals",
        "produits": "SELECT COUNT(*) n FROM products",
        "niches": "SELECT COUNT(*) n FROM niches",
        "videos": "SELECT COUNT(*) n FROM videos",
    }
    out = {}
    for k, sql in q.items():
        d = _df(sql)
        out[k] = int(d["n"].iloc[0]) if not d.empty else 0
    return out


def last_runs(limit: int = 15) -> pd.DataFrame:
    return _df(
        "SELECT collector AS source, scope AS perimetre, status AS statut, items AS elements, "
        "finished_at AS termine_le, message FROM collection_runs ORDER BY id DESC LIMIT ?", (limit,))


def last_collect_time() -> str | None:
    d = _df("SELECT MAX(finished_at) t FROM collection_runs WHERE status='ok'")
    return None if d.empty else d["t"].iloc[0]


def trends(country: str | None = None, days: int = 7) -> pd.DataFrame:
    sql = (
        "SELECT t.country AS pays, c.name_fr AS nom_pays, t.term AS recherche, t.approx_traffic AS trafic, "
        "t.traffic_min, t.started_at AS debut, t.collected_at AS collecte_le, t.url, t.news_json "
        "FROM trend_signals t LEFT JOIN countries c ON c.code=t.country "
        "WHERE t.collected_at >= datetime('now', ?)"
    )
    params: list = [f"-{int(days)} days"]
    if country:
        sql += " AND t.country = ?"
        params.append(country)
    sql += " ORDER BY t.traffic_min DESC NULLS LAST, t.collected_at DESC"
    d = _df(sql, params)
    if not d.empty:
        d["article"] = d["news_json"].map(lambda j: (json.loads(j) or [{}])[0].get("url") if j else None)
        d = d.drop(columns=["news_json"])
    return d


def multi_country_terms(days: int = 7) -> pd.DataFrame:
    """Recherches en hausse dans plusieurs pays à la fois (signal de tendance internationale)."""
    return _df(
        "SELECT lower(term) AS recherche, COUNT(DISTINCT country) AS nb_pays, "
        "group_concat(DISTINCT country) AS pays, MAX(traffic_min) AS trafic_max "
        "FROM trend_signals WHERE collected_at >= datetime('now', ?) "
        "GROUP BY lower(term) HAVING nb_pays >= 2 ORDER BY nb_pays DESC, trafic_max DESC",
        (f"-{int(days)} days",))


def markets() -> pd.DataFrame:
    return _df(
        "SELECT c.code, c.name_fr AS pays, c.region AS region, c.languages AS langues, c.currency AS devise, "
        "CASE WHEN c.currency='EUR' THEN 1.0 ELSE fx.rate END AS taux_eur, "
        "CASE WHEN c.currency='EUR' THEN '(euro)' ELSE fx.rate_date END AS date_taux, ci.value AS pib_hab_ppa_usd, ci.year AS annee_pib "
        "FROM countries c "
        "LEFT JOIN fx_rates fx ON fx.quote=c.currency AND fx.base='EUR' "
        "  AND fx.rate_date=(SELECT MAX(rate_date) FROM fx_rates WHERE quote=c.currency) "
        "LEFT JOIN country_indicators ci ON ci.country=c.code AND ci.indicator='pib_hab_ppa_usd' "
        "  AND ci.year=(SELECT MAX(year) FROM country_indicators WHERE country=c.code AND indicator='pib_hab_ppa_usd') "
        "ORDER BY c.name_fr")


def sources() -> pd.DataFrame:
    return _df("SELECT name AS source, category AS categorie, status AS statut, access_method AS acces, "
               "needs_key AS cle_requise, free_quota AS quota, notes, last_checked AS verifie_le "
               "FROM sources ORDER BY CASE status WHEN 'actif' THEN 0 WHEN 'a_configurer' THEN 1 "
               "WHEN 'manuel' THEN 2 ELSE 3 END, name")

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
        "candidats": "SELECT COUNT(*) n FROM products WHERE status='candidat'",
        "mots_cles": "SELECT COUNT(*) n FROM keywords",
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


# ----------------------------------------------------------------------------- produits
def _udf(sql: str, params=()) -> pd.DataFrame:
    if not config.USER_DB.exists():
        return pd.DataFrame()
    with db.connect(config.USER_DB) as con:
        return pd.read_sql_query(sql, con, params=params)


def products() -> pd.DataFrame:
    d = _df(
        "SELECT p.id, p.canonical_name AS produit, p.language AS langue, n.name_fr AS niche, p.status AS statut, "
        "p.status_reason AS motif, p.origin AS origine, p.first_seen AS decouvert_le, s.score AS points, "
        "s.confidence AS confiance, s.details_json, s.computed_at AS note_le "
        "FROM products p LEFT JOIN niches n ON n.id=p.niche_id "
        "LEFT JOIN scores s ON s.id=(SELECT MAX(id) FROM scores WHERE product_id=p.id) "
        "ORDER BY s.score DESC NULLS LAST, p.first_seen DESC")
    if d.empty:
        return d
    det = d["details_json"].map(lambda j: json.loads(j) if j else {})
    d["max_evaluable"] = det.map(lambda x: x.get("max_evaluable"))
    d["createurs"] = det.map(lambda x: x.get("createurs_independants"))
    d["sources"] = det.map(lambda x: x.get("types_de_sources"))
    d["details"] = det
    return d.drop(columns=["details_json"])


def product_videos(product_id: int) -> pd.DataFrame:
    return _df(
        "SELECT v.title AS titre, v.channel_title AS chaine, v.url, v.region AS region_recherche, v.format_hint AS format, "
        "v.published_at AS publie_le, st.views AS vues, st.likes AS likes, st.comments AS commentaires, "
        "st.collected_at AS releve_le FROM products p JOIN keyword_signals ks ON ks.keyword_id=p.keyword_id "
        "AND ks.source='youtube' JOIN videos v ON v.external_id=ks.ref "
        "LEFT JOIN video_stats st ON st.video_id=v.id AND st.collected_at=(SELECT MAX(collected_at) FROM video_stats "
        "WHERE video_id=v.id) WHERE p.id=? ORDER BY st.views DESC", (product_id,))


def product_trends(product_id: int) -> pd.DataFrame:
    return _df(
        "SELECT t.country AS pays, t.term AS recherche, t.approx_traffic AS trafic, t.collected_at AS collecte_le, t.url "
        "FROM products p JOIN keyword_signals ks ON ks.keyword_id=p.keyword_id AND ks.source='google_trends' "
        "JOIN trend_signals t ON 't' || t.id = ks.ref WHERE p.id=?", (product_id,))


def product_risks(product_id: int) -> pd.DataFrame:
    return _df("SELECT kind AS type, severity AS gravite, description, source, collected_at AS detecte_le "
               "FROM risks WHERE product_id=?", (product_id,))


def youtube_videos(limit: int = 300) -> pd.DataFrame:
    return _df(
        "SELECT v.title AS titre, v.channel_title AS chaine, v.url, v.language AS langue, v.region AS region_recherche, "
        "v.format_hint AS format, v.query AS requete, v.published_at AS publie_le, st.views AS vues, st.likes AS likes, "
        "st.comments AS commentaires, st.channel_subscribers AS abonnes, st.collected_at AS releve_le "
        "FROM videos v LEFT JOIN video_stats st ON st.video_id=v.id AND st.collected_at="
        "(SELECT MAX(collected_at) FROM video_stats WHERE video_id=v.id) "
        "WHERE v.platform='youtube' ORDER BY st.views DESC LIMIT ?", (limit,))


def keywords_summary() -> pd.DataFrame:
    return _df(
        "SELECT k.term AS mot_cle, k.language AS langue, k.status AS statut, k.first_seen AS vu_le, "
        "(SELECT COUNT(*) FROM keyword_signals ks WHERE ks.keyword_id=k.id) AS observations "
        "FROM keywords k ORDER BY observations DESC, k.last_seen DESC LIMIT 500")


def last_search() -> dict | None:
    d = _df("SELECT * FROM search_runs ORDER BY id DESC LIMIT 1")
    if d.empty:
        return None
    r = d.iloc[0].to_dict()
    r["sources"] = json.loads(r["sources_json"]) if r.get("sources_json") else {}
    r["erreurs"] = json.loads(r["errors_json"]) if r.get("errors_json") else []
    return r


def youtube_units_today() -> int:
    d = _df("SELECT units FROM api_usage WHERE api='youtube' AND day=date('now')")
    return 0 if d.empty else int(d["units"].iloc[0])


def favorites() -> pd.DataFrame:
    return _udf("SELECT id, product_name AS produit, country AS pays, list_name AS liste, note, updated_at AS modifie_le "
                "FROM favorites ORDER BY updated_at DESC")


def manual_videos() -> pd.DataFrame:
    d = _udf("SELECT * FROM manual_videos ORDER BY created_at DESC")
    if d.empty:
        return d
    pub = pd.to_datetime(d["published_at"], errors="coerce", utc=True)
    obs = pd.to_datetime(d["observed_at"], errors="coerce", utc=True)
    days = ((obs - pub).dt.total_seconds() / 86400).clip(lower=1)
    d["vues_par_jour (calcul)"] = (d["views"] / days).round(0)
    d["vues/abonnés (calcul)"] = (d["views"] / d["account_followers"]).round(2)
    return d

"""Test de bout en bout du moteur de découverte avec une API YouTube simulée (aucun appel réseau)."""
import json

from phai import config, db, discovery, scoring
from phai.collectors import youtube as yt
from phai.extract import extract

TITLES = {
    "v1": ("Sunset lamp that changed my room #shorts", "chanA"),
    "v2": ("This sunset lamp is a must have", "chanB"),
    "v3": ("Pepper spray keychain review", "chanC"),
    "v4": ("Pepper spray keychain for runners", "chanD"),
    "v5": ("My cat loves this self cleaning brush", "chanE"),
}


class FakeResp:
    def __init__(self, data):
        self._d = data

    def json(self):
        return self._d


def fake_get(url, params=None, **_):
    if url.endswith("/search"):
        return FakeResp({"items": [{"id": {"videoId": v}} for v in TITLES]})
    if url.endswith("/videos"):
        return FakeResp({"items": [{
            "id": v, "snippet": {"title": t, "channelId": c, "channelTitle": c, "publishedAt": "2026-11-20T00:00:00Z",
                                 "description": ""},
            "statistics": {"viewCount": "1000"}, "contentDetails": {"duration": "PT30S"}} for v, (t, c) in TITLES.items()
            if v in params["id"].split(",")]})
    if url.endswith("/channels"):
        return FakeResp({"items": [{"id": c, "statistics": {"subscriberCount": "10"}} for _, c in TITLES.values()]})
    raise AssertionError(url)


def test_end_to_end(monkeypatch, tmp_db):
    monkeypatch.setenv("YOUTUBE_API_KEY", "test")
    monkeypatch.setattr("phai.http.get", fake_get)
    with db.connect(config.MARKET_DB) as con:
        r = discovery.youtube_discovery(con)
        assert r["statut"] == "ok" and r["videos"] == 5
        assert r["unites_quota"] <= config.settings()["discovery"]["youtube_units_per_run"]
        assert discovery.promote(con)["nouveaux_produits"] == 2
        prods = {p["canonical_name"]: p for p in con.execute("SELECT * FROM products")}
        assert prods["sunset lamp"]["status"] == "candidat"
        assert prods["pepper spray keychain"]["status"] == "elimine"     # filtre éliminatoire
        assert "self cleaning brush" not in prods                         # un seul créateur : reste observé
        scoring.score_all(con)
        d = json.loads(con.execute("SELECT details_json FROM scores").fetchone()[0])
        assert d["composantes"]["profitability"]["statut"] == "manquant"  # jamais inventé
        assert d["confiance"] == "Faible"
        # Boule de neige : le produit découvert devient une requête de recherche
        plan = discovery.plan(con, 10)
        assert any(q["origin"] == "boule_de_neige" and q["query"] == "sunset lamp" for q in plan)


def test_quota_cap(monkeypatch, tmp_db):
    monkeypatch.setenv("YOUTUBE_API_KEY", "test")
    with db.connect(config.MARKET_DB) as con:
        con.execute("INSERT INTO api_usage VALUES(date('now'), 'youtube', 99999)")
        assert discovery.youtube_discovery(con)["statut"] == "quota_atteint"


def test_format_hint():
    assert yt.format_hint(30, "x #Shorts", "").startswith("Short déclaré")
    assert "non confirmé" in yt.format_hint(45, "x", "")
    assert yt.format_hint(600, "x", "") == "vidéo longue"


def test_extract_multilingual():
    assert extract("Cette lampe de chevet est géniale !", "fr") == ["lampe de chevet"]
    assert extract("Best Car Vacuum Cleaner 2026", "en") == ["car vacuum cleaner"]
    assert extract("Genialer Autostaubsauger", "de") == ["autostaubsauger"]


def test_manual_score_uses_views_per_day(tmp_db):
    ev = {"yt_channels": 0, "yt_videos": 0, "yt_regions": 0, "yt_last": None, "trend_countries": 0,
          "trend_last": None, "manual": [{"vues_par_jour": 10000.0, "author": "x"}]}
    r = scoring.score(ev, config.settings()["weights_product"])
    assert r["composantes"]["viral"]["statut"] == "partiel"
    assert r["composantes"]["demand"]["statut"] == "manquant"


def test_manual_video_creates_scored_product(tmp_db):
    with db.connect(config.USER_DB) as u:
        u.execute("INSERT INTO manual_videos(url, platform, author, product_name, language, published_at, observed_at, "
                  "views, is_ad, created_at) VALUES('https://www.tiktok.com/@a/video/1','tiktok','@a','Posture Corrector',"
                  "'en','2026-11-01','2026-11-21',200000,'inconnu','2026-11-21')")
    with db.connect(config.MARKET_DB) as con:
        discovery.manual_to_keywords(con)
        assert discovery.promote(con)["nouveaux_produits"] == 1
        p = con.execute("SELECT * FROM products").fetchone()
        assert p["origin"] == "manuel" and p["canonical_name"] == "posture corrector"
        ev = scoring.evidence(con, p)
        assert round(ev["manual"][0]["vues_par_jour"]) == 10000  # 200 000 vues en 20 jours

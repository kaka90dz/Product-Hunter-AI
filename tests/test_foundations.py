import json

from phai import config, db, runs
from phai.collectors import google_trends_rss as gt
from phai.collectors import youtube as yt

RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:ht="https://trends.google.com/trending/rss" version="2.0"><channel>
<item><title>heated lunch box</title><ht:approx_traffic>2,000+</ht:approx_traffic>
<pubDate>Thu, 26 Nov 2026 22:20:00 -0800</pubDate>
<ht:news_item><ht:news_item_title>T</ht:news_item_title><ht:news_item_url>https://ex.com/a</ht:news_item_url>
<ht:news_item_source>Ex</ht:news_item_source></ht:news_item></item>
</channel></rss>"""


def test_parse_traffic():
    assert gt.parse_traffic("200+") == 200
    assert gt.parse_traffic("2,000+") == 2000
    assert gt.parse_traffic("1 000+") == 1000
    assert gt.parse_traffic("2K+") == 2000
    assert gt.parse_traffic(None) is None


def test_parse_rss():
    items = gt.parse(RSS, "US")
    assert items[0]["term"] == "heated lunch box"
    assert items[0]["traffic_min"] == 2000
    assert items[0]["news"][0]["url"] == "https://ex.com/a"
    assert items[0]["started_at"].startswith("2026-11-26T22:20")


def test_iso_duration():
    assert yt.iso_duration_to_s("PT45S") == 45
    assert yt.iso_duration_to_s("PT1M5S") == 65


def test_youtube_without_key_is_skipped(monkeypatch, tmp_db):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    assert "ignore" in yt.collect()


def test_reference_data_and_norway(tmp_db):
    with db.connect(config.MARKET_DB) as con:
        assert con.execute("SELECT COUNT(*) FROM countries").fetchone()[0] == 19
        assert con.execute("SELECT languages FROM countries WHERE code='NO'").fetchone()[0] == "no"


def test_cache_freshness(tmp_db):
    assert not runs.is_fresh("x", 1)
    with runs.track("x"):
        pass
    assert runs.is_fresh("x", 1)


def test_user_settings_override(tmp_db):
    with db.connect(config.USER_DB) as con:
        con.execute("INSERT INTO settings VALUES('financial', ?, ?)",
                    (json.dumps({"min_product_margin_pct": 50}), db.now_iso()))
    s = config.settings()
    assert s["financial"]["min_product_margin_pct"] == 50
    assert s["financial"]["max_delivery_days"] == 10  # valeur par défaut conservée


def test_weights_sum_to_100():
    s = config.default_settings()
    assert sum(s["weights_product"].values()) == 100
    assert sum(s["weights_market"].values()) == 100

"""YouTube Data API v3 : vidéos courtes (Shorts) récentes sur des requêtes de découverte.

Coût en quota (gratuit, 10 000 unités/jour) : search.list = 100, videos.list = 1, channels.list = 1.
Chaque relevé est historisé dans video_stats pour mesurer la croissance des vues."""
from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone

from phai import config, db, http, runs

KEY = "youtube"
API = "https://www.googleapis.com/youtube/v3"
COST = {"search": 100, "videos": 1, "channels": 1}


def api_key() -> str | None:
    return os.environ.get("YOUTUBE_API_KEY") or None


def iso_duration_to_s(d: str | None) -> int | None:
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", d or "")
    if not m:
        return None
    days, h, mi, s = (int(x or 0) for x in m.groups())
    return days * 86400 + h * 3600 + mi * 60 + s


def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def collect(force: bool = False) -> dict:
    key = api_key()
    if not key:
        return {"ignore": "YOUTUBE_API_KEY absente — source non configurée"}
    s = config.settings()
    yt = s["youtube"]
    budget = s["quotas"]["youtube_units_per_run"]
    ttl = s["cache_ttl_hours"][KEY]
    lang_by_region = {c["code"]: c["languages"] for c in config.countries()}
    since = (datetime.now(timezone.utc) - timedelta(days=yt["max_age_days"])).strftime("%Y-%m-%dT%H:%M:%SZ")
    used, found, skipped = 0, {}, 0

    with runs.track(KEY) as run:
        for region in yt["regions"]:
            for lang in lang_by_region.get(region, ["en"]):
                for q in yt["seed_queries"].get(lang, []):
                    scope = f"{region}|{lang}|{q}"
                    if not force and runs.is_fresh(KEY + ":search", ttl, scope=scope):
                        skipped += 1
                        continue
                    if used + COST["search"] > budget:
                        break
                    with runs.track(KEY + ":search", scope=scope) as srun:
                        data = http.get(f"{API}/search", delay=0.2, params={
                            "key": key, "part": "snippet", "type": "video", "videoDuration": "short",
                            "q": q, "regionCode": region, "relevanceLanguage": lang,
                            "order": "viewCount", "publishedAfter": since, "maxResults": 25,
                        }).json()
                        used += COST["search"]
                        for it in data.get("items", []):
                            vid = it["id"]["videoId"]
                            found.setdefault(vid, (q, region, lang))
                        srun.items = len(data.get("items", []))

        ids = list(found)
        videos, channels = {}, {}
        for chunk in _chunks(ids, 50):
            data = http.get(f"{API}/videos", delay=0.2, params={
                "key": key, "part": "snippet,statistics,contentDetails", "id": ",".join(chunk)}).json()
            used += COST["videos"]
            for v in data.get("items", []):
                videos[v["id"]] = v
        ch_ids = list({v["snippet"]["channelId"] for v in videos.values()})
        for chunk in _chunks(ch_ids, 50):
            data = http.get(f"{API}/channels", delay=0.2, params={
                "key": key, "part": "statistics", "id": ",".join(chunk)}).json()
            used += COST["channels"]
            for c in data.get("items", []):
                st = c.get("statistics", {})
                channels[c["id"]] = None if st.get("hiddenSubscriberCount") else int(st.get("subscriberCount", 0))

        now = db.now_iso()
        with db.connect(config.MARKET_DB) as con:
            for vid, v in videos.items():
                sn, st = v["snippet"], v.get("statistics", {})
                q, region, lang = found[vid]
                con.execute(
                    "INSERT INTO videos(platform,external_id,url,title,channel_id,channel_title,published_at,"
                    "duration_s,language,query,region,first_seen) VALUES('youtube',?,?,?,?,?,?,?,?,?,?,?) "
                    "ON CONFLICT(platform,external_id) DO UPDATE SET title=excluded.title",
                    (vid, f"https://www.youtube.com/shorts/{vid}", sn.get("title"), sn["channelId"],
                     sn.get("channelTitle"), sn.get("publishedAt"),
                     iso_duration_to_s(v.get("contentDetails", {}).get("duration")),
                     sn.get("defaultAudioLanguage") or sn.get("defaultLanguage") or lang, q, region, now),
                )
                row_id = con.execute("SELECT id FROM videos WHERE platform='youtube' AND external_id=?", (vid,)).fetchone()[0]
                con.execute(
                    "INSERT OR REPLACE INTO video_stats(video_id,collected_at,views,likes,comments,channel_subscribers)"
                    " VALUES(?,?,?,?,?,?)",
                    (row_id, now, _int(st.get("viewCount")), _int(st.get("likeCount")),
                     _int(st.get("commentCount")), channels.get(sn["channelId"])),
                )
        run.items = len(videos)
        run.message = f"{used} unités de quota utilisées ; {skipped} requêtes ignorées (cache)"
    return {"videos": len(videos), "unites_quota": used, "requetes_en_cache": skipped}


def _int(x):
    return int(x) if x is not None else None

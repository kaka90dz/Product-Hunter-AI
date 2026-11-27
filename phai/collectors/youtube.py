"""Client YouTube Data API v3 (officiel) avec comptage du quota gratuit.

Règles YouTube respectées (Developer Policies, section III.E.4) :
- les données de l'API sont supprimées ou rafraîchies sous 30 jours (voir phai/retention.py) ;
- aucun indicateur dérivé (vues/jour, vues/abonnés, croissance) n'est calculé à partir de ces données ;
- aucun accès aux pages youtube.com en dehors de l'API."""
from __future__ import annotations

import os
import re
from datetime import date

from phai import db, http

API = "https://www.googleapis.com/youtube/v3"
COST = {"search": 100, "videos": 1, "channels": 1}


def api_key() -> str | None:
    return os.environ.get("YOUTUBE_API_KEY") or None


def iso_duration_to_s(d: str | None) -> int | None:
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", d or "")
    if not m or not any(m.groups()):
        return None
    days, h, mi, s = (int(x or 0) for x in m.groups())
    return days * 86400 + h * 3600 + mi * 60 + s


def format_hint(duration_s: int | None, title: str, description: str) -> str:
    """L'API ne dit pas si une vidéo est un Short : on donne un indice, jamais une certitude."""
    tagged = "#shorts" in f"{title} {description}".lower()
    if duration_s is None:
        return "durée inconnue"
    if duration_s <= 180 and tagged:
        return "Short déclaré (#shorts)"
    if duration_s <= 60:
        return "vidéo courte ≤ 60 s (Short non confirmé)"
    if duration_s <= 180:
        return "vidéo courte ≤ 3 min (Short non confirmé)"
    return "vidéo longue"


def units_used_today(con) -> int:
    row = con.execute("SELECT units FROM api_usage WHERE day=? AND api='youtube'", (date.today().isoformat(),)).fetchone()
    return row[0] if row else 0


def _charge(con, units: int) -> None:
    con.execute(
        "INSERT INTO api_usage(day, api, units) VALUES(?, 'youtube', ?) "
        "ON CONFLICT(day, api) DO UPDATE SET units = units + excluded.units",
        (date.today().isoformat(), units))


def search(con, key: str, q: str, region: str, lang: str, published_after: str, max_results: int) -> list[dict]:
    data = http.get(f"{API}/search", delay=0.2, params={
        "key": key, "part": "snippet", "type": "video", "videoDuration": "short", "q": q,
        "regionCode": region, "relevanceLanguage": lang, "order": "viewCount",
        "publishedAfter": published_after, "maxResults": max_results, "safeSearch": "moderate"}).json()
    _charge(con, COST["search"])
    return data.get("items", [])


def videos(con, key: str, ids: list[str]) -> list[dict]:
    out = []
    for i in range(0, len(ids), 50):
        data = http.get(f"{API}/videos", delay=0.2, params={
            "key": key, "part": "snippet,statistics,contentDetails", "id": ",".join(ids[i:i + 50])}).json()
        _charge(con, COST["videos"])
        out += data.get("items", [])
    return out


def channels(con, key: str, ids: list[str]) -> dict[str, int | None]:
    out = {}
    for i in range(0, len(ids), 50):
        data = http.get(f"{API}/channels", delay=0.2, params={
            "key": key, "part": "statistics", "id": ",".join(ids[i:i + 50])}).json()
        _charge(con, COST["channels"])
        for c in data.get("items", []):
            st = c.get("statistics", {})
            out[c["id"]] = None if st.get("hiddenSubscriberCount") else _int(st.get("subscriberCount"))
    return out


def store_videos(con, items: list[dict], meta: dict[str, tuple], subs: dict) -> None:
    now = db.now_iso()
    for v in items:
        sn, st = v["snippet"], v.get("statistics", {})
        q, region, lang, _niche = meta[v["id"]]
        dur = iso_duration_to_s(v.get("contentDetails", {}).get("duration"))
        desc = (sn.get("description") or "")[:500]
        con.execute(
            "INSERT INTO videos(platform,external_id,url,title,channel_id,channel_title,published_at,duration_s,"
            "language,query,region,format_hint,description,first_seen) VALUES('youtube',?,?,?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(platform,external_id) DO UPDATE SET title=excluded.title, description=excluded.description, "
            "format_hint=excluded.format_hint",
            (v["id"], f"https://www.youtube.com/watch?v={v['id']}", sn.get("title"), sn["channelId"],
             sn.get("channelTitle"), sn.get("publishedAt"), dur,
             sn.get("defaultAudioLanguage") or sn.get("defaultLanguage") or lang, q, region,
             format_hint(dur, sn.get("title") or "", desc), desc, now))
        vid = con.execute("SELECT id FROM videos WHERE platform='youtube' AND external_id=?", (v["id"],)).fetchone()[0]
        con.execute(
            "INSERT OR REPLACE INTO video_stats(video_id,collected_at,views,likes,comments,channel_subscribers) "
            "VALUES(?,?,?,?,?,?)",
            (vid, now, _int(st.get("viewCount")), _int(st.get("likeCount")), _int(st.get("commentCount")),
             subs.get(sn["channelId"])))


def _int(x):
    return int(x) if x is not None else None

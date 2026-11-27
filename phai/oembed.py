"""Pré-remplissage par oEmbed (point d'accès officiel et public des plateformes).
Ne renvoie que titre et auteur : aucune statistique (vues, likes) n'est disponible ainsi."""
from __future__ import annotations

import re

from phai import http

ENDPOINTS = {
    "tiktok": "https://www.tiktok.com/oembed",
    "youtube": "https://www.youtube.com/oembed",
}


def platform_of(url: str) -> str:
    u = url.lower()
    if "tiktok.com" in u:
        return "tiktok"
    if "instagram.com" in u:
        return "instagram"
    if "youtube.com" in u or "youtu.be" in u:
        return "youtube"
    if "pinterest." in u:
        return "pinterest"
    if "facebook.com" in u or "fb.watch" in u:
        return "facebook"
    return "autre"


def author_from_url(url: str) -> str | None:
    m = re.search(r"(?:tiktok\.com|instagram\.com)/@?([A-Za-z0-9._]+)", url)
    if m and m.group(1) not in ("p", "reel", "reels", "tv", "video", "t"):
        return "@" + m.group(1).lstrip("@")
    return None


def fetch(url: str) -> dict:
    """Titre et auteur si la plateforme les fournit (YouTube : oui ; TikTok : auteur lu dans l'URL)."""
    p = platform_of(url)
    if p in ("tiktok", "instagram"):
        return {"title": None, "author": author_from_url(url)}
    if p not in ENDPOINTS or not re.match(r"https?://", url):
        return {}
    try:
        d = http.get(ENDPOINTS[p], params={"url": url, "format": "json"}, delay=0.5, retries=0, timeout=15).json()
    except Exception:  # noqa: BLE001 — l'utilisateur saisit alors les champs lui-même
        return {}
    return {"title": d.get("title"), "author": d.get("author_name")}

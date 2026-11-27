"""Client HTTP poli : identifiant générique, délais, nouvelles tentatives limitées.
Aucune technique de contournement (pas de rotation d'IP ni d'usurpation)."""
from __future__ import annotations

import time

import requests

USER_AGENT = "ProductHunterAI/0.1 (outil de recherche personnel)"
_last_call: dict[str, float] = {}


class AccessRefused(Exception):
    """La source refuse l'accès (401/403/429…) : on s'arrête, on ne contourne pas."""


def get(url: str, *, params=None, delay: float = 1.5, timeout: int = 30, retries: int = 2) -> requests.Response:
    host = requests.utils.urlparse(url).netloc
    wait = delay - (time.monotonic() - _last_call.get(host, 0))
    if wait > 0:
        time.sleep(wait)
    for attempt in range(retries + 1):
        _last_call[host] = time.monotonic()
        try:
            r = requests.get(url, params=params, timeout=timeout, headers={"User-Agent": USER_AGENT})
        except requests.RequestException:
            if attempt == retries:
                raise
            time.sleep(2 ** attempt * 2)
            continue
        if r.status_code in (401, 403, 429):
            raise AccessRefused(f"{host} a refusé l'accès (HTTP {r.status_code})")
        if r.status_code >= 500 and attempt < retries:
            time.sleep(2 ** attempt * 2)
            continue
        r.raise_for_status()
        return r
    raise RuntimeError("inaccessible")

"""Accès aux données pour le tableau de bord.

- Hébergé (Streamlit Cloud) : les bases sont lues dans la branche « data » du dépôt GitHub privé,
  et les modifications de l'utilisateur (favoris, saisies) y sont réécrites immédiatement.
- Local (sans jeton) : fichiers du dossier data/ ; rien n'est envoyé dans GitHub."""
from __future__ import annotations

import sqlite3
import tempfile
import time
from pathlib import Path

import streamlit as st

from phai import config, db
from phai.store import ConflictError, GitHubStore

CACHE_DIR = Path(tempfile.gettempdir()) / "phai-data"


TOKEN_NAMES = ("token", "GITHUB_TOKEN", "github_token", "GH_TOKEN")


def _secrets() -> dict | None:
    """Accepte la section [github] (recommandée) ou un jeton placé directement à la racine des secrets."""
    try:
        sec = st.secrets
        g = sec.get("github")
        if g and any(g.get(n) for n in TOKEN_NAMES):
            g = dict(g)
            return {**g, "token": next(g[n] for n in TOKEN_NAMES if g.get(n))}
        for n in TOKEN_NAMES:
            if sec.get(n):
                return {"token": sec[n], "repo": sec.get("repo", "kaka90dz/Product-Hunter-AI"),
                        "data_branch": sec.get("data_branch", "data")}
    except Exception:  # noqa: BLE001 — pas de fichier secrets en local
        return None
    return None


def secret_names() -> list[str]:
    """Noms (jamais les valeurs) des secrets visibles, pour le diagnostic."""
    try:
        out = []
        for k in st.secrets.keys():
            v = st.secrets[k]
            out.append(f"[{k}] → " + ", ".join(v.keys()) if hasattr(v, "keys") else k)
        return out
    except Exception:  # noqa: BLE001
        return []


def on_streamlit_cloud() -> bool:
    import os
    return os.path.isdir("/mount/src") or os.environ.get("HOSTNAME", "").startswith("streamlit")


@st.cache_resource
def store() -> GitHubStore | None:
    s = _secrets()
    return GitHubStore(s["token"], s.get("repo", "kaka90dz/Product-Hunter-AI"), s.get("data_branch", "data")) if s else None


def hosted() -> bool:
    return store() is not None


@st.cache_data(ttl=60, show_spinner=False)
def _branch_sha() -> str:
    return store().branch_sha()


def sync() -> None:
    """Télécharge les bases si la branche data a changé (vérifié au plus toutes les 60 s)."""
    if not hosted():
        db.init_all()
        return
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    config.MARKET_DB, config.USER_DB = CACHE_DIR / "market.db", CACHE_DIR / "user.db"
    sha = _branch_sha()
    if st.session_state.get("_data_sha") == sha and config.MARKET_DB.exists():
        return
    with st.spinner("Chargement des données…"):
        for name in ("market.db", "user.db"):
            content, _ = store().download(name)
            (CACHE_DIR / name).write_bytes(content)
    st.session_state["_data_sha"] = sha


def write_user(fn) -> None:
    """Applique fn(connexion) à user.db et l'enregistre durablement (nouvel essai si conflit)."""
    if not hosted():
        with db.connect(config.USER_DB) as con:
            fn(con)
        return
    for attempt in range(2):
        content, sha = store().download("user.db")
        tmp = CACHE_DIR / "user.edit.db"
        tmp.write_bytes(content)
        con = sqlite3.connect(tmp)
        con.row_factory = sqlite3.Row
        try:
            fn(con)
            con.commit()
        finally:
            con.close()
        try:
            store().upload("user.db", tmp.read_bytes(), sha, "Tableau de bord : mise à jour des données utilisateur")
            tmp.replace(CACHE_DIR / "user.db")
            _branch_sha.clear()
            st.session_state.pop("_data_sha", None)
            return
        except ConflictError:
            if attempt:
                raise
            time.sleep(1)

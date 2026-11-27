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


def _secrets() -> dict | None:
    try:
        g = st.secrets.get("github")
    except Exception:  # noqa: BLE001 — pas de fichier secrets en local
        return None
    return dict(g) if g and g.get("token") else None


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

"""Chemins et paramètres (YAML par défaut + surcharges de l'utilisateur)."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
MARKET_DB = DATA_DIR / "market.db"
USER_DB = DATA_DIR / "user.db"


def _load_yaml(name: str):
    with open(CONFIG_DIR / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


def default_settings() -> dict:
    return _load_yaml("settings.yaml")


def countries() -> list[dict]:
    return _load_yaml("countries.yaml")


def sources() -> list[dict]:
    return _load_yaml("sources.yaml")


def _deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def settings() -> dict:
    """Paramètres effectifs : valeurs par défaut + surcharges stockées dans user.db."""
    from phai import db

    base = default_settings()
    if not USER_DB.exists():
        return base
    with db.connect(USER_DB) as con:
        rows = con.execute("SELECT key, value_json FROM settings").fetchall()
    override = {k: json.loads(v) for k, v in rows}
    return _deep_merge(base, override)


def active_countries(s: dict | None = None) -> list[dict]:
    s = s or settings()
    excluded = set(s.get("countries_excluded") or [])
    return [c for c in countries() if c["code"] not in excluded]

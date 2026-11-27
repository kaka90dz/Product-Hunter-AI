"""Ligne de commande : python -m phai <commande>.

Toutes ces commandes sont du code classique : elles ne consomment aucun crédit Claude."""
from __future__ import annotations

import argparse
import json

from phai import db

COLLECTORS = ["google_trends_rss", "fx", "worldbank"]


def cmd_init(_args):
    db.init_all()
    print("Bases initialisées : data/market.db, data/user.db")


def cmd_collect(args):
    import importlib

    db.init_all()
    names = COLLECTORS if args.source == "all" else [args.source]
    results, failed = {}, False
    for name in names:
        mod = importlib.import_module(f"phai.collectors.{name}")
        try:
            results[name] = mod.collect(force=args.force)
        except Exception as e:  # noqa: BLE001 — une source en panne ne bloque pas les autres
            results[name] = {"erreur": f"{type(e).__name__}: {e}"}
            failed = True
    print(json.dumps(results, ensure_ascii=False, indent=2))
    if failed and args.strict:
        raise SystemExit(1)


def cmd_run(args):
    from phai import pipeline

    r = pipeline.run(force=args.force)
    print(json.dumps(r, ensure_ascii=False, indent=2, default=str))


def cmd_verify(args):
    """Vérifie l'intégrité d'une base (test de restauration)."""
    import sqlite3
    from pathlib import Path

    for name in ("market.db", "user.db"):
        path = Path(args.dir) / name
        con = sqlite3.connect(path)
        ok = con.execute("PRAGMA integrity_check").fetchone()[0]
        tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
        print(name, ok, counts)
        if ok != "ok":
            raise SystemExit(f"{name} corrompue")


def cmd_status(_args):
    from phai import config

    db.init_all()
    with db.connect(config.MARKET_DB) as con:
        for t in ["trend_signals", "fx_rates", "country_indicators", "videos", "video_stats", "keywords", "products"]:
            print(f"{t:20} {con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]}")
        print("\nDernières collectes :")
        for r in con.execute(
            "SELECT collector, scope, status, items, finished_at, message FROM collection_runs ORDER BY id DESC LIMIT 10"
        ):
            print(" ", dict(r))


def main(argv=None):
    p = argparse.ArgumentParser(prog="phai", description="Product Hunter AI")
    sub = p.add_subparsers(required=True)
    sub.add_parser("init", help="Créer/mettre à jour les bases").set_defaults(func=cmd_init)
    c = sub.add_parser("collect", help="Lancer une collecte (mode Eco, sans IA)")
    c.add_argument("source", nargs="?", default="all", choices=["all", *COLLECTORS])
    c.add_argument("--force", action="store_true", help="Ignorer le cache")
    c.add_argument("--strict", action="store_true", help="Code d'erreur si une source échoue")
    c.set_defaults(func=cmd_collect)
    sub.add_parser("status", help="Résumé de la base").set_defaults(func=cmd_status)
    r = sub.add_parser("run", help="Recherche complète de produits (mode Eco, sans IA)")
    r.add_argument("--force", action="store_true")
    r.set_defaults(func=cmd_run)
    v = sub.add_parser("verify", help="Tester l'intégrité des bases d'un dossier")
    v.add_argument("dir")
    v.set_defaults(func=cmd_verify)
    args = p.parse_args(argv)
    args.func(args)

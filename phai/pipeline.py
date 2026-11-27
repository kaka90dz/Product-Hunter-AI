"""Recherche complète en mode Eco (aucun appel IA). Lancée par GitHub Actions."""
from __future__ import annotations

import json
import os

from phai import config, db, discovery, retention, scoring
from phai.collectors import fx, google_trends_rss, worldbank


def run(force: bool = False, trigger: str | None = None) -> dict:
    db.init_all()
    trigger = trigger or os.environ.get("PHAI_TRIGGER") or "manuel"
    with db.connect(config.MARKET_DB) as con:
        before = con.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        run_id = con.execute("INSERT INTO search_runs(trigger, mode, started_at) VALUES(?, 'eco', ?)",
                             (trigger, db.now_iso())).lastrowid
    sources, errors = {}, []

    def step(name, fn):
        try:
            sources[name] = fn()
            errs = sources[name].get("erreurs") if isinstance(sources[name], dict) else None
            if errs:
                errors.extend(f"{name} : {e}" for e in (errs if isinstance(errs, list) else [errs]))
        except Exception as e:  # noqa: BLE001 — une source en panne n'arrête pas la recherche
            sources[name] = {"statut": "erreur", "message": f"{type(e).__name__}: {e}"}
            errors.append(f"{name} : {e}")

    step("google_trends", lambda: google_trends_rss.collect(force))
    step("taux_de_change", lambda: fx.collect(force))
    step("banque_mondiale", lambda: worldbank.collect(force))
    with db.connect(config.MARKET_DB) as con:
        kw_before = con.execute("SELECT COUNT(*) FROM keywords").fetchone()[0]
        step("youtube", lambda: discovery.youtube_discovery(con, force))
        step("extraction_produits", lambda: discovery.rebuild_youtube_signals(con))
        step("tendances_vers_produits", lambda: discovery.trends_to_keywords(con))
        step("saisies_manuelles", lambda: discovery.manual_to_keywords(con))
        step("creation_produits", lambda: discovery.promote(con))
        step("retention", lambda: retention.apply(con))
        step("scores", lambda: scoring.score_all(con))
        new_kw = con.execute("SELECT COUNT(*) FROM keywords").fetchone()[0] - kw_before
        new_p = con.execute("SELECT COUNT(*) FROM products").fetchone()[0] - before
        con.execute("UPDATE search_runs SET finished_at=?, status=?, sources_json=?, new_keywords=?, new_products=?, "
                    "errors_json=? WHERE id=?",
                    (db.now_iso(), "ok" if not errors else "ok_avec_erreurs",
                     json.dumps(sources, ensure_ascii=False, default=str), new_kw, new_p,
                     json.dumps(errors, ensure_ascii=False), run_id))
    return {"recherche": run_id, "nouveaux_mots_cles": new_kw, "nouveaux_produits": new_p,
            "sources": sources, "erreurs": errors}

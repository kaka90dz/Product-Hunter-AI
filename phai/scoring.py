"""Score produit partiel (mode Eco, sans IA).

Chaque composante n'est notée que si des preuves existent ; sinon elle est « manquante » et
ne rapporte aucun point. On affiche donc « X points sur Y évaluables », jamais un score complet
inventé. Les données YouTube ne servent qu'au comptage de créateurs et de régions où le produit
apparaît (aucun calcul sur les vues, conformément aux règles YouTube). Les indicateurs de vues
par jour ne sont calculés que sur les vidéos saisies à la main (TikTok, Instagram…)."""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone

from phai import config, db

MISSING = {
    "problem_solved": "Analyse qualitative à réaliser (Claude, mode Standard)",
    "profitability": "Prix fournisseur et prix de vente non collectés (étape 5)",
    "competition": "Concurrents non analysés (étape 5)",
    "supplier_reliability": "Fournisseurs non recherchés (étape 5)",
}
LABELS = {
    "viral": "Potentiel viral organique", "profitability": "Rentabilité", "demand": "Demande",
    "problem_solved": "Problème résolu", "competition": "Opportunité concurrentielle",
    "supplier_reliability": "Fiabilité des fournisseurs", "video_ease": "Facilité de création vidéo",
}


def _days_since(iso: str | None) -> float | None:
    if not iso:
        return None
    try:
        t = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return max((datetime.now(timezone.utc) - t).total_seconds() / 86400, 0)


def manual_videos_for(dedup_key: str) -> list[dict]:
    from phai.extract import dedup_key as dk

    if not config.USER_DB.exists():
        return []
    with db.connect(config.USER_DB) as ucon:
        rows = [dict(r) for r in ucon.execute("SELECT * FROM manual_videos")]
    return [r for r in rows if dk(r["product_name"].strip().lower(), r["language"] or "en") == dedup_key]


def evidence(con, product) -> dict:
    kid = product["keyword_id"]
    yt = con.execute(
        "SELECT COUNT(DISTINCT v.channel_id) ch, COUNT(DISTINCT v.id) nv, COUNT(DISTINCT ks.country) rg, "
        "MAX(ks.observed_at) last FROM keyword_signals ks JOIN videos v ON v.external_id=ks.ref "
        "WHERE ks.keyword_id=? AND ks.source='youtube'", (kid,)).fetchone()
    tr = con.execute(
        "SELECT COUNT(DISTINCT country) c, MAX(observed_at) last FROM keyword_signals "
        "WHERE keyword_id=? AND source='google_trends'", (kid,)).fetchone()
    manual = manual_videos_for(product["dedup_key"])
    for m in manual:  # vues au moment du relevé ÷ jours écoulés entre publication et relevé
        pub, obs = _days_since(m.get("published_at")), _days_since(m.get("observed_at"))
        age = (pub - obs) if (pub is not None and obs is not None) else None
        m["vues_par_jour"] = (m["views"] / max(age, 1)) if (m.get("views") is not None and age is not None) else None
    return {"yt_channels": yt["ch"] or 0, "yt_videos": yt["nv"] or 0, "yt_regions": yt["rg"] or 0,
            "yt_last": yt["last"], "trend_countries": tr["c"] or 0, "trend_last": tr["last"], "manual": manual}


def score(ev: dict, weights: dict) -> dict:
    comps = {}

    def comp(name, subs):
        """subs : liste (poids relatif, valeur 0..1 ou None, explication, nature)."""
        avail = [(w, v, why, nat) for w, v, why, nat in subs if v is not None]
        W = weights[name]
        if not avail:
            comps[name] = {"libelle": LABELS[name], "points": None, "max": W, "statut": "manquant",
                           "preuves": [why for _, _, why, _ in subs] or [MISSING.get(name, "")]}
            return
        wsum = sum(w for w, *_ in subs)
        max_eval = W * sum(w for w, *_ in avail) / wsum
        pts = W * sum(w * v for w, v, *_ in avail) / wsum
        comps[name] = {"libelle": LABELS[name], "points": round(pts, 1), "max": W, "max_evaluable": round(max_eval, 1),
                       "statut": "partiel" if len(avail) < len(subs) else "evalue",
                       "preuves": [f"[{nat}] {why}" for _, _, why, nat in avail] +
                                  [f"[manquant] {why}" for w, v, why, nat in subs if v is None]}

    ch, man = ev["yt_channels"], ev["manual"]
    best_vpd = max((m["vues_par_jour"] for m in man if m.get("vues_par_jour") is not None), default=None)
    comp("viral", [
        (0.5, min(ch, 5) / 5 if ch else None,
         f"Présent chez {ch} créateur(s) YouTube différent(s) dans nos résultats de recherche (max. retenu : 5)", "vérifié"),
        (0.5, min(math.log10(best_vpd + 1) / 5, 1) if best_vpd is not None else None,
         (f"Meilleure vidéo saisie : {best_vpd:,.0f} vues/jour en moyenne depuis sa publication".replace(",", " ")
          if best_vpd is not None else "Aucune vidéo TikTok/Instagram saisie avec ses statistiques"), "saisie manuelle — estimation"),
    ])
    comp("demand", [
        (0.5, min(ev["trend_countries"], 3) / 3 if ev["trend_countries"] else None,
         f"Recherche Google en forte hausse dans {ev['trend_countries']} pays" if ev["trend_countries"]
         else "Aucune hausse Google Trends détectée (flux du jour)", "vérifié"),
        (0.5, min(ev["yt_regions"], 4) / 4 if ev["yt_regions"] else None,
         f"Trouvé dans les résultats de {ev['yt_regions']} région(s) de recherche YouTube (≠ pays de l'audience)", "vérifié"),
    ])
    nvid = ev["yt_videos"] + len(man)
    comp("video_ease", [(1, min(nvid, 3) / 3 if nvid else None,
                         f"{nvid} vidéo(s) de démonstration existante(s) : format filmable confirmé", "vérifié")])
    for name, why in MISSING.items():
        comps[name] = {"libelle": LABELS[name], "points": None, "max": weights[name], "statut": "manquant", "preuves": [why]}

    points = sum(c["points"] for c in comps.values() if c["points"] is not None)
    max_eval = sum(c.get("max_evaluable", c["max"]) for c in comps.values() if c["points"] is not None)
    sources = (ch > 0) + (ev["trend_countries"] > 0) + (len(man) > 0)
    last = min(filter(None, [_days_since(ev["yt_last"]), _days_since(ev["trend_last"])]), default=None)
    independent = ch + len({m.get("author") for m in man if m.get("author")})
    if sources >= 2 and independent >= 3 and last is not None and last <= 14:
        conf = "Moyen"
    else:
        conf = "Faible"
    # « Élevé » impossible tant que fournisseurs et rentabilité ne sont pas évalués.
    return {"points": round(points, 1), "max_evaluable": round(max_eval, 1), "confiance": conf,
            "composantes": comps, "types_de_sources": sources, "createurs_independants": independent}


def score_all(con) -> dict:
    weights = config.settings()["weights_product"]
    now = db.now_iso()
    n = 0
    for p in con.execute("SELECT * FROM products WHERE status != 'elimine'").fetchall():
        r = score(evidence(con, p), weights)
        con.execute("INSERT INTO scores(product_id, score_type, score, confidence, details_json, weights_json, computed_at) "
                    "VALUES(?,?,?,?,?,?,?)", (p["id"], "produit_partiel", r["points"], r["confiance"],
                                               json.dumps(r, ensure_ascii=False), json.dumps(weights), now))
        n += 1
    con.commit()
    return {"produits_notes": n}

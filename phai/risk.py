"""Filtres de risque par mots-clés (premier niveau, automatique). Ne remplace pas une vérification humaine."""
from __future__ import annotations

import re
from functools import lru_cache

from phai import config
from phai.extract import strip_accents

LABELS = {
    "securite": "Risque de sécurité / arme",
    "sante_allegations": "Allégations de santé ou produit réglementé",
    "propriete_intellectuelle": "Marque déposée citée (risque de contrefaçon / PI)",
    "enfants_normes": "Produit pour enfants (normes de sécurité obligatoires)",
    "batterie_lithium": "Batterie lithium (transport et conformité)",
    "cosmetique": "Cosmétique (réglementation spécifique)",
    "contact_alimentaire": "Contact alimentaire (normes)",
}


@lru_cache(maxsize=1)
def _patterns():
    out = []
    for level, cats in config.discovery()["risks"].items():
        for cat, words in cats.items():
            for w in words:
                pat = re.compile(r"\b" + re.escape(strip_accents(w.lower())) + r"s?\b")
                out.append((level, cat, w, pat))
    return out


def assess(text: str) -> list[dict]:
    """Retourne les risques détectés : [{niveau, categorie, libelle, mot}]."""
    t = strip_accents(text.lower())
    hits, seen = [], set()
    for level, cat, word, pat in _patterns():
        if cat not in seen and pat.search(t):
            seen.add(cat)
            hits.append({"niveau": level, "categorie": cat, "libelle": LABELS.get(cat, cat), "mot": word})
    return hits


def status_from_risks(hits: list[dict]) -> tuple[str, str | None]:
    if any(h["niveau"] == "eliminatoire" for h in hits):
        return "elimine", "; ".join(h["libelle"] for h in hits if h["niveau"] == "eliminatoire")
    if hits:
        return "en_attente", "À vérifier : " + "; ".join(h["libelle"] for h in hits)
    return "candidat", None

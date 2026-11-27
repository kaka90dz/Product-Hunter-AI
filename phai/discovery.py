"""Moteur de découverte de produits (mode Eco : aucune IA).

1. Planifie des recherches YouTube (requêtes commerciales multilingues + niches + mots-clés
   découverts lors des recherches précédentes = enrichissement progressif « boule de neige »).
2. Extrait les noms de produits des titres et descriptions.
3. Croise avec les tendances Google et les vidéos saisies à la main.
4. Crée des produits candidats lorsqu'un mot-clé est observé chez plusieurs créateurs."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from phai import config, db, extract, risk
from phai.collectors import youtube as yt


def _ago(days: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).replace(microsecond=0).isoformat()


# ----------------------------------------------------------------------------- planification
def seed_queries() -> list[dict]:
    d = config.discovery()
    seeds = []
    for lang, qs in d["generic_queries"].items():
        seeds += [{"query": q, "language": lang, "origin": "generique", "niche": None} for q in qs]
    for slug, n in d["niches"].items():
        for lang, q in n["q"].items():
            seeds.append({"query": q, "language": lang, "origin": "niche", "niche": slug})
    return seeds


def plan(con, n_searches: int, force: bool = False) -> list[dict]:
    d, s = config.discovery(), config.settings()["discovery"]
    excluded = set(config.settings().get("countries_excluded") or [])
    regions = {lang: [r for r in rs if r not in excluded] for lang, rs in d["regions_by_language"].items()}
    last = {(r["query"], r["language"], r["region"]): r["last_searched_at"]
            for r in con.execute("SELECT query, language, region, last_searched_at FROM query_log")}

    # a) Boule de neige : mots-clés observés chez plusieurs créateurs, à approfondir
    n_snow = int(n_searches * s["snowball_share"])
    snow = []
    # Priorité : produits créés à approfondir, puis noms précis (≥ 2 mots) vus une fois, à vérifier
    # chez d'autres créateurs, puis rafraîchissement des produits (preuves < 30 jours).
    rows = con.execute(
        "SELECT k.id, k.term, k.language, k.niche_slug, COUNT(DISTINCT v.channel_id) AS ch, "
        " CASE WHEN k.status='a_rechercher' THEN 0 WHEN k.status='observe' THEN 1 ELSE 2 END AS prio "
        "FROM keywords k JOIN keyword_signals ks ON ks.keyword_id=k.id AND ks.source='youtube' "
        "JOIN videos v ON v.external_id=ks.ref "
        "WHERE k.status='a_rechercher' OR (k.status='observe' AND k.last_searched_at IS NULL AND k.term LIKE '% %') "
        "   OR (k.status='recherche' AND k.last_searched_at < ? "
        "       AND EXISTS (SELECT 1 FROM products p WHERE p.keyword_id=k.id AND p.status != 'elimine')) "
        "GROUP BY k.id ORDER BY prio, ch DESC, LENGTH(k.term) DESC, k.last_seen DESC LIMIT 200",
        (_ago(s["snowball_refresh_days"]),)).fetchall()
    for r in rows:
        for region in regions.get(r["language"], [])[: (2 if r["prio"] == 0 else 1)]:
            snow.append({"query": r["term"], "language": r["language"], "region": region,
                         "origin": "boule_de_neige", "niche": r["niche_slug"], "keyword_id": r["id"]})
    snow = snow[:n_snow]

    # b) Requêtes de départ, en rotation (la moins récemment cherchée d'abord), toutes langues alternées
    cutoff = _ago(s["seed_refresh_days"])
    by_lang: dict[str, list] = {}
    for sd in seed_queries():
        for region in regions.get(sd["language"], []):
            t = last.get((sd["query"], sd["language"], region))
            if force or not t or t < cutoff:
                by_lang.setdefault(sd["language"], []).append({**sd, "region": region, "_t": t or ""})
    for lst in by_lang.values():
        lst.sort(key=lambda x: x["_t"])
    seeds, i = [], 0
    while len(seeds) < n_searches - len(snow) and any(by_lang.values()):
        for lang in list(by_lang):
            if by_lang[lang]:
                seeds.append(by_lang[lang].pop(0))
                if len(seeds) >= n_searches - len(snow):
                    break
        i += 1
    return snow + seeds


# ----------------------------------------------------------------------------- mots-clés
def upsert_keyword(con, term: str, lang: str, niche: str | None) -> tuple[int, bool]:
    key = extract.dedup_key(term, lang)
    now = db.now_iso()
    row = con.execute("SELECT id FROM keywords WHERE dedup_key=?", (key,)).fetchone()
    if row:
        con.execute("UPDATE keywords SET last_seen=?, niche_slug=COALESCE(niche_slug, ?) WHERE id=?", (now, niche, row[0]))
        return row[0], False
    cur = con.execute(
        "INSERT INTO keywords(dedup_key, term, language, niche_slug, first_seen, last_seen) VALUES(?,?,?,?,?,?)",
        (key, term, lang, niche, now, now))
    return cur.lastrowid, True


def add_signal(con, kw_id: int, source: str, ref: str, country: str | None) -> None:
    con.execute("INSERT OR IGNORE INTO keyword_signals(keyword_id, source, ref, country, observed_at) VALUES(?,?,?,?,?)",
                (kw_id, source, ref, country, db.now_iso()))


# ----------------------------------------------------------------------------- étapes
def youtube_discovery(con, force: bool = False) -> dict:
    key = yt.api_key()
    if not key:
        return {"statut": "non_configure", "message": "Clé YOUTUBE_API_KEY absente"}
    s = config.settings()["discovery"]
    remaining = min(s["youtube_units_per_run"], s["youtube_units_per_day"] - yt.units_used_today(con))
    n = max(0, (remaining - 60) // yt.COST["search"])   # réserve pour videos.list / channels.list
    if n == 0:
        return {"statut": "quota_atteint", "message": "Plafond quotidien de quota YouTube atteint"}
    queries = plan(con, n, force)
    since = _ago(30).replace("+00:00", "Z")
    meta, errors, done = {}, [], 0
    for q in queries:
        try:
            items = yt.search(con, key, q["query"], q["region"], q["language"], since, s["max_results_per_search"])
        except Exception as e:  # noqa: BLE001
            errors.append(f"{q['query']} ({q['region']}) : {e}")
            if "refusé" in str(e):
                break
            continue
        done += 1
        con.execute(
            "INSERT INTO query_log(query, language, region, origin, niche_slug, last_searched_at, results) "
            "VALUES(?,?,?,?,?,?,?) ON CONFLICT(query, language, region) DO UPDATE SET "
            "last_searched_at=excluded.last_searched_at, results=excluded.results",
            (q["query"], q["language"], q["region"], q["origin"], q["niche"], db.now_iso(), len(items)))
        if q.get("keyword_id"):
            con.execute("UPDATE keywords SET status='recherche', last_searched_at=? WHERE id=?", (db.now_iso(), q["keyword_id"]))
        for it in items:
            meta.setdefault(it["id"]["videoId"], (q["query"], q["region"], q["language"], q["niche"]))
        con.commit()
    vids = yt.videos(con, key, list(meta)) if meta else []
    subs = yt.channels(con, key, list({v["snippet"]["channelId"] for v in vids})) if vids else {}
    yt.store_videos(con, vids, meta, subs)
    con.commit()
    return {"statut": "ok", "recherches": done, "videos": len(vids),
            "unites_quota": yt.units_used_today(con), "erreurs": errors}


def rebuild_youtube_signals(con) -> dict:
    """(Re)calcule les mots-clés à partir des vidéos en base. Sans appel à l'API : les améliorations
    de l'extraction s'appliquent ainsi à tout l'historique, sans consommer de quota."""
    niche_of = {(r["query"], r["language"], r["region"]): r["niche_slug"]
                for r in con.execute("SELECT query, language, region, niche_slug FROM query_log")}
    con.execute("DELETE FROM keyword_signals WHERE source='youtube'")
    n_sig = 0
    for v in con.execute("SELECT external_id, title, description, query, region, language FROM videos "
                         "WHERE platform='youtube'").fetchall():
        qlang = next((lang for (q, lang, reg) in niche_of if q == v["query"] and reg == v["region"]), None)
        niche = niche_of.get((v["query"], qlang, v["region"]))
        text = f"{v['title'] or ''} | {(v['description'] or '')[:120]}"
        # La vidéo n'est pas forcément dans la langue de la requête : langue de la requête,
        # langue déclarée par la vidéo, et anglais (langue dominante des titres de produits).
        langs = dict.fromkeys(x for x in ("en", qlang, (v["language"] or "")[:2]) if x)
        seen_tokens: set[str] = set()   # un même nom n'est compté qu'une fois, en anglais en priorité
        for lang in langs:
            for phrase in extract.extract(text, lang):
                tok_key = extract.dedup_key(phrase, "xx")
                if tok_key in seen_tokens:
                    continue
                seen_tokens.add(tok_key)
                for form in [phrase] + extract.variants(phrase, lang):
                    kw_id, _ = upsert_keyword(con, form, lang, niche)
                    add_signal(con, kw_id, "youtube", v["external_id"], v["region"])
                    n_sig += 1
    # Produits découverts dont plus aucune observation ne subsiste (extraction corrigée ou preuves
    # expirées sans rafraîchissement) : supprimés. Les produits saisis à la main sont conservés.
    orphan = "SELECT id FROM keywords WHERE id NOT IN (SELECT keyword_id FROM keyword_signals)"
    gone = [r[0] for r in con.execute(f"SELECT id FROM products WHERE origin='decouverte' AND keyword_id IN ({orphan})")]
    for pid in gone:
        for table in ("risks", "scores", "evidence"):
            con.execute(f"DELETE FROM {table} WHERE product_id=?", (pid,))
        con.execute("DELETE FROM products WHERE id=?", (pid,))
    removed = con.execute(f"DELETE FROM keywords WHERE id IN ({orphan}) "
                          "AND dedup_key NOT IN (SELECT dedup_key FROM products)").rowcount
    con.commit()
    return {"observations": n_sig, "mots_cles_supprimes": removed, "produits_sans_preuve_supprimes": len(gone)}


def trends_to_keywords(con) -> dict:
    langs = {c["code"]: c["languages"][0] for c in config.countries()}
    rows = con.execute(
        "SELECT id, country, term FROM trend_signals t WHERE collected_at >= ? AND NOT EXISTS "
        "(SELECT 1 FROM keyword_signals ks WHERE ks.source='google_trends' AND ks.ref='t' || t.id)", (_ago(3),)).fetchall()
    found = 0
    for r in rows:
        for phrase in extract.extract(r["term"], langs.get(r["country"], "en")):
            kw_id, _ = upsert_keyword(con, phrase, langs.get(r["country"], "en"), None)
            add_signal(con, kw_id, "google_trends", f"t{r['id']}", r["country"])
            found += 1
    con.commit()
    return {"tendances_examinees": len(rows), "tendances_produits": found}


def manual_to_keywords(con) -> dict:
    """Intègre les vidéos saisies à la main (user.db, lecture seule)."""
    if not config.USER_DB.exists():
        return {"videos_manuelles": 0}
    with db.connect(config.USER_DB) as ucon:
        rows = ucon.execute("SELECT id, product_name, language, audience_country FROM manual_videos").fetchall()
    for r in rows:
        kw_id, _ = upsert_keyword(con, r["product_name"].strip().lower(), r["language"] or "en", None)
        add_signal(con, kw_id, "manuel", f"mv{r['id']}", r["audience_country"])
        con.execute("UPDATE keywords SET status='a_rechercher' WHERE id=? AND status='observe'", (kw_id,))
    con.commit()
    return {"videos_manuelles": len(rows)}


def promote(con) -> dict:
    """Crée les produits candidats. Seuil : plusieurs créateurs YouTube différents, ou YouTube + tendance
    Google, ou saisie manuelle. Les filtres de risque s'appliquent dès la création."""
    min_ch = config.settings()["discovery"]["min_channels_for_product"]
    rows = con.execute(
        "SELECT k.*, "
        " (SELECT COUNT(DISTINCT v.channel_id) FROM keyword_signals ks JOIN videos v ON v.external_id=ks.ref "
        "   WHERE ks.keyword_id=k.id AND ks.source='youtube') AS ch, "
        " (SELECT COUNT(*) FROM keyword_signals ks WHERE ks.keyword_id=k.id AND ks.source='google_trends') AS tr, "
        " (SELECT COUNT(*) FROM keyword_signals ks WHERE ks.keyword_id=k.id AND ks.source='manuel') AS mn "
        "FROM keywords k WHERE NOT EXISTS (SELECT 1 FROM products p WHERE p.dedup_key=k.dedup_key)").fetchall()
    eligible = [k for k in rows if k["ch"] >= min_ch or (k["ch"] >= 1 and k["tr"] >= 1) or k["mn"] >= 1]
    chans = {k["id"]: frozenset(r[0] for r in con.execute(
        "SELECT DISTINCT v.channel_id FROM keyword_signals ks JOIN videos v ON v.external_id=ks.ref "
        "WHERE ks.keyword_id=? AND ks.source='youtube'", (k["id"],))) for k in eligible}
    existing = [(r["term"], frozenset(r2[0] for r2 in con.execute(
        "SELECT DISTINCT v.channel_id FROM keyword_signals ks JOIN videos v ON v.external_id=ks.ref "
        "WHERE ks.keyword_id=? AND ks.source='youtube'", (r["keyword_id"],))))
        for r in con.execute("SELECT p.keyword_id, k.term FROM products p JOIN keywords k ON k.id=p.keyword_id")]
    pool = existing + [(k["term"], chans[k["id"]]) for k in eligible]
    new = 0
    for k in sorted(eligible, key=lambda k: -len(k["term"])):
        # Forme générale sans créateur supplémentaire (« spray keychain » ⊂ « pepper spray keychain ») : ignorée
        if not k["mn"] and any(f" {k['term']} " in f" {t} " and t != k["term"] and c >= chans[k["id"]] for t, c in pool):
            continue
        hits = risk.assess(k["term"])
        status, reason = risk.status_from_risks(hits)
        now = db.now_iso()
        niche_id = None
        if k["niche_slug"]:
            n = config.discovery()["niches"].get(k["niche_slug"], {})
            con.execute("INSERT OR IGNORE INTO niches(slug, name_fr, created_at) VALUES(?,?,?)",
                        (k["niche_slug"], n.get("fr", k["niche_slug"]), now))
            niche_id = con.execute("SELECT id FROM niches WHERE slug=?", (k["niche_slug"],)).fetchone()[0]
        cur = con.execute(
            "INSERT INTO products(canonical_name, language, keyword_id, origin, dedup_key, niche_id, status, "
            "status_reason, first_seen, updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (k["term"], k["language"], k["id"], "manuel" if k["mn"] and not k["ch"] else "decouverte",
             k["dedup_key"], niche_id, status, reason, now, now))
        for h in hits:
            con.execute("INSERT INTO risks(product_id, kind, severity, description, source, collected_at) "
                        "VALUES(?,?,?,?,?,?)", (cur.lastrowid, h["categorie"],
                                                "majeur" if h["niveau"] == "eliminatoire" else "moyen",
                                                f"{h['libelle']} (mot détecté : « {h['mot']} »)", "filtre automatique", now))
        if k["status"] == "observe":
            con.execute("UPDATE keywords SET status='a_rechercher' WHERE id=?", (k["id"],))
        new += 1
    con.commit()
    return {"nouveaux_produits": new}

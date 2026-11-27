from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from phai import app_data, queries

st.title("🔎 Product Hunter AI")
st.caption("Découverte internationale de produits e-commerce — version 0.2")

c = queries.counts()
cols = st.columns(4)
cols[0].metric("Produits candidats", c["candidats"], help="Produits à approfondir (aucun n'est encore « validé »)")
cols[1].metric("Mots-clés découverts", c["mots_cles"])
cols[2].metric("Vidéos YouTube", c["videos"])
cols[3].metric("Pays suivis (tendances)", c["pays_tendances"])

# ----------------------------------------------------------------------------- recherche
st.subheader("Recherche automatique")


def _fmt(ts):
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().strftime("%d/%m/%Y %H:%M")
    except Exception:  # noqa: BLE001
        return ts or "—"


if not app_data.hosted():
    st.button("🔎 Trouver de nouveaux produits", disabled=True, use_container_width=True)
    st.info("Ce bouton déclenche la recherche sur GitHub Actions. Il devient actif dès que le tableau de bord "
            "est en ligne avec son jeton GitHub (voir docs/GUIDE_INSTALLATION.md). En attendant, la recherche "
            "tourne automatiquement chaque jour.", icon="ℹ️")
else:
    @st.fragment(run_every=20)
    def search_panel():
        store = app_data.store()
        try:
            active = store.active_run()
            last = store.runs(1)
        except Exception as e:  # noqa: BLE001
            st.error(f"GitHub inaccessible : {e}")
            return
        pending = st.session_state.get("dispatched_at")
        if active:
            st.button("⏳ Recherche en cours…", disabled=True, use_container_width=True)
            st.info(f"Démarrée le {_fmt(active['created_at'])} — état : **{active['status']}**. "
                    f"[Voir le détail sur GitHub]({active['html_url']}). Durée habituelle : 2 à 6 minutes.")
            st.session_state.pop("dispatched_at", None)
            st.session_state["was_active"] = True
        elif pending and (datetime.now(timezone.utc) - pending).total_seconds() < 90:
            st.button("⏳ Démarrage…", disabled=True, use_container_width=True)
            st.info("Recherche demandée, démarrage sur GitHub…")
        else:
            if st.session_state.pop("was_active", False):
                app_data._branch_sha.clear()
                st.rerun(scope="app")
            if st.button("🔎 Trouver de nouveaux produits", type="primary", use_container_width=True):
                try:
                    store.dispatch({"declencheur": "tableau_de_bord"})
                    st.session_state["dispatched_at"] = datetime.now(timezone.utc)
                    st.rerun(scope="fragment")
                except Exception as e:  # noqa: BLE001
                    st.error(f"Lancement impossible : {e}")
            if last:
                r = last[0]
                verdict = {"success": "✅ réussie", "failure": "❌ échouée", "cancelled": "⏹️ annulée"}.get(
                    r.get("conclusion"), r.get("conclusion") or r["status"])
                st.caption(f"Dernière exécution GitHub : {verdict} le {_fmt(r['updated_at'])} — "
                           f"[détail]({r['html_url']})")

    search_panel()

ls = queries.last_search()
if ls:
    st.markdown(f"**Dernière recherche enregistrée** : {_fmt(ls['finished_at'] or ls['started_at'])} "
                f"({ls['trigger']}) — **{ls['new_products'] or 0}** nouveau(x) produit(s), "
                f"**{ls['new_keywords'] or 0}** nouveau(x) mot(s)-clé(s).")
    rows = []
    for name, res in ls["sources"].items():
        if isinstance(res, dict):
            statut = res.get("statut") or ("ignoré (cache)" if res.get("ignore_cache") else "ok")
            detail = res.get("message") or ", ".join(f"{k} : {v}" for k, v in res.items()
                                                       if k not in ("statut", "erreurs", "message") and not isinstance(v, (list, dict)))
        else:
            statut, detail = "ok", str(res)
        rows.append({"Étape / source": name, "Statut": statut, "Détail": detail})
    with st.expander("Sources utilisées et détails"):
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    if ls["erreurs"]:
        st.warning("Erreurs : " + " · ".join(ls["erreurs"][:5]))
else:
    st.write("Aucune recherche complète enregistrée pour le moment.")

# ----------------------------------------------------------------------------- aperçu
st.subheader("Meilleurs candidats à approfondir")
p = queries.products()
if p.empty or (p["statut"] == "candidat").sum() == 0:
    st.write("Aucun produit candidat pour le moment. Les produits apparaissent quand un même produit est "
             "repéré chez plusieurs créateurs différents (YouTube doit être configuré).")
else:
    top = p[p["statut"] == "candidat"].head(10).copy()
    top["score"] = top.apply(lambda r: f"{r['points']:.0f} / {r['max_evaluable']:.0f}" if pd.notna(r["points"]) else "—", axis=1)
    st.dataframe(top[["produit", "niche", "langue", "score", "confiance", "createurs"]], hide_index=True,
                 use_container_width=True, column_config={"score": "Points / évaluables", "createurs": "Créateurs"})
    st.caption("Score partiel : seules les composantes avec des preuves sont notées. Aucun produit n'est "
               "déclaré gagnant tant que fournisseurs et rentabilité ne sont pas vérifiés.")

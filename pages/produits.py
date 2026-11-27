import pandas as pd
import streamlit as st

from phai import app_data, db, queries

st.title("🛍️ Produits")
st.caption("Produits découverts automatiquement. Statut « candidat » = à approfondir, jamais « gagnant ».")

p = queries.products()
if p.empty:
    st.info("Aucun produit pour le moment.")
    st.stop()

STATUTS = {"candidat": "🔍 Candidat à approfondir", "en_attente": "⏸️ En attente (risque à vérifier)",
           "elimine": "⛔ Éliminé", "preselectionne": "✅ Présélectionné", "finaliste": "🏁 Finaliste"}
c1, c2, c3 = st.columns(3)
statut = c1.multiselect("Statut", list(STATUTS), default=["candidat", "en_attente"], format_func=STATUTS.get)
niches = sorted(p["niche"].dropna().unique())
niche = c2.multiselect("Niche", niches)
texte = c3.text_input("Rechercher")
f = p[p["statut"].isin(statut)] if statut else p
if niche:
    f = f[f["niche"].isin(niche)]
if texte:
    f = f[f["produit"].str.contains(texte, case=False, na=False)]

view = f.copy()
view["statut"] = view["statut"].map(STATUTS)
view["score"] = view.apply(lambda r: f"{r['points']:.0f} / {r['max_evaluable']:.0f}" if pd.notna(r["points"]) else "—", axis=1)
st.write(f"**{len(view)}** produit(s)")
st.dataframe(view[["produit", "niche", "langue", "statut", "score", "confiance", "createurs", "decouvert_le"]],
             hide_index=True, use_container_width=True,
             column_config={"score": "Points / évaluables", "createurs": "Créateurs", "decouvert_le": "Découvert le"})
st.download_button("Exporter en CSV", view.drop(columns=["details"]).to_csv(index=False).encode("utf-8"),
                   "produits.csv", "text/csv")

# ----------------------------------------------------------------------------- fiche
st.divider()
if f.empty:
    st.stop()
pid = st.selectbox("Fiche détaillée", f["id"].tolist(), format_func=lambda i: f.loc[f["id"] == i, "produit"].iloc[0])
row = f[f["id"] == pid].iloc[0]
st.header(row["produit"])
st.write(f"{STATUTS.get(row['statut'], row['statut'])} · Langue : {row['langue']} · Niche : {row['niche'] or '—'} · "
         f"Origine : {row['origine']}")
if row["motif"]:
    st.warning(row["motif"])

d = row["details"] or {}
if d:
    a, b, c = st.columns(3)
    a.metric("Points obtenus", f"{d['points']:.0f}")
    b.metric("Points évaluables", f"{d['max_evaluable']:.0f} / 100")
    c.metric("Confiance", d["confiance"])
    st.caption("Un score n'est pas une probabilité de succès. Les composantes sans preuve ne rapportent aucun point.")
    comp = [{"Composante": v["libelle"], "Points": "—" if v["points"] is None else f"{v['points']} / {v['max']}",
             "Statut": {"manquant": "❓ donnée manquante", "partiel": "◐ partiel", "evalue": "✔ évalué"}[v["statut"]],
             "Preuves / justification": " · ".join(v["preuves"])} for v in d["composantes"].values()]
    st.dataframe(pd.DataFrame(comp), hide_index=True, use_container_width=True)

st.subheader("Vidéos où le produit apparaît")
v = queries.product_videos(int(pid))
if v.empty:
    st.write("Aucune vidéo YouTube liée actuellement.")
else:
    st.dataframe(v, hide_index=True, use_container_width=True,
                 column_config={"url": st.column_config.LinkColumn("Lien", display_text="Ouvrir"),
                                "region_recherche": "Région de recherche"})
    st.caption("Statistiques : source YouTube (données brutes, non retraitées), rafraîchies ou supprimées sous 30 jours. "
               "La région de recherche n'indique pas le pays de l'audience.")
t = queries.product_trends(int(pid))
if not t.empty:
    st.subheader("Tendances Google liées")
    st.dataframe(t, hide_index=True, use_container_width=True,
                 column_config={"url": st.column_config.LinkColumn("Google Trends", display_text="Ouvrir")})
r = queries.product_risks(int(pid))
if not r.empty:
    st.subheader("Risques détectés")
    st.dataframe(r, hide_index=True, use_container_width=True)

st.subheader("Ajouter à mes listes")
with st.form("fav"):
    liste = st.selectbox("Liste", ["favori", "a_tester", "elimine"],
                         format_func={"favori": "⭐ Favoris", "a_tester": "🧪 À tester", "elimine": "🗑️ Éliminés"}.get)
    pays = st.text_input("Pays visé (facultatif, code ISO, ex. US)")
    note = st.text_area("Note personnelle")
    if st.form_submit_button("Enregistrer"):
        def add(con):
            now = db.now_iso()
            con.execute("INSERT INTO favorites(product_id, product_name, country, list_name, note, created_at, updated_at) "
                        "VALUES(?,?,?,?,?,?,?)", (int(pid), row["produit"], pays.upper() or None, liste, note, now, now))
        try:
            app_data.write_user(add)
            st.success("Enregistré.")
        except Exception as e:  # noqa: BLE001
            st.error(f"Échec de l'enregistrement : {e}")
